import { useEffect, useId, useRef, useState } from "react";
import { candidateService } from "../api/index.js";

/**
 * ResumeManager Component
 * Accessible interface to upload, view metadata, download, replace, and delete candidate resume.
 * Integrates with:
 * - POST /api/v1/candidates/me/resume
 * - GET /api/v1/candidates/me/resume
 * - GET /api/v1/candidates/me/resume/download
 * - DELETE /api/v1/candidates/me/resume
 */
export function ResumeManager({ onResumeUpdated }) {
  const [resume, setResume] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const fileInputRef = useRef(null);
  const fileInputId = useId();

  // Load active resume metadata on mount
  useEffect(() => {
    let isMounted = true;
    async function loadResume() {
      setIsLoading(true);
      setError("");
      try {
        const data = await candidateService.getResume();
        if (isMounted) {
          setResume(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Failed to load resume details.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadResume();
    return () => {
      isMounted = false;
    };
  }, []);

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 KB";
    const k = 1024;
    const dm = 1;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
  }

  function handleFileSelected(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    // Reset input so re-selecting the same file fires onChange
    event.target.value = "";
    uploadFile(file);
  }

  async function uploadFile(file) {
    setError("");
    setSuccessMessage("");

    // Client-side validation: formats
    const validExtensions = [".pdf", ".docx"];
    const fileName = file.name.toLowerCase();
    const isValidExt = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValidExt) {
      setError("Unsupported file format. Please upload a PDF (.pdf) or Word document (.docx).");
      return;
    }

    // Client-side validation: max 5MB (5,242,880 bytes)
    const maxSizeBytes = 5 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      setError("File size exceeds the 5MB maximum limit. Please upload a smaller document.");
      return;
    }

    setIsUploading(true);
    try {
      const uploaded = await candidateService.uploadResume(file);
      setResume(uploaded);
      setConfirmDelete(false);
      setSuccessMessage(`Resume "${file.name}" uploaded successfully.`);
      if (onResumeUpdated) {
        onResumeUpdated(uploaded);
      }
    } catch (err) {
      setError(err.message || "Failed to upload resume. Please verify the file and try again.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload() {
    if (!resume) return;
    setError("");
    setIsDownloading(true);

    try {
      const result = await candidateService.downloadResume();
      if (!result || !result.blob) {
        throw new Error("Unable to retrieve file stream from server.");
      }

      // Trigger accessible browser download
      const downloadUrl = window.URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = result.filename || resume.original_filename || "resume.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      setError(err.message || "Failed to download resume. Please try again.");
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleDelete() {
    setError("");
    setSuccessMessage("");
    setIsDeleting(true);

    try {
      await candidateService.deleteResume();
      setResume(null);
      setConfirmDelete(false);
      setSuccessMessage("Active resume deleted successfully.");
      if (onResumeUpdated) {
        onResumeUpdated(null);
      }
    } catch (err) {
      setError(err.message || "Failed to delete resume. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="resume-manager-component">
      {successMessage && (
        <div className="form-status" role="status" aria-live="polite">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="form-error" role="alert" aria-live="assertive">
          {error}
        </div>
      )}

      {/* Hidden native accessible file input */}
      <input
        ref={fileInputRef}
        id={fileInputId}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={handleFileSelected}
        style={{ display: "none" }}
        disabled={isUploading || isDeleting}
        aria-hidden="true"
      />

      {isLoading ? (
        <p className="loading-hint" role="status">
          Loading resume information...
        </p>
      ) : resume ? (
        <div className="active-resume-card">
          <div className="resume-details-header">
            <div className="resume-file-icon" aria-hidden="true">
              📄
            </div>
            <div className="resume-file-info">
              <h3 className="resume-file-name">{resume.original_filename}</h3>
              <p className="resume-file-meta">
                <span>{formatBytes(resume.file_size_bytes)}</span>
                <span> &bull; </span>
                <span>
                  Uploaded {new Date(resume.created_at).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </p>
            </div>
            <span className="status-badge status-active" aria-label="Status: Active on file">
              Active
            </span>
          </div>

          {confirmDelete ? (
            <div className="delete-confirmation-box" role="alert">
              <p>
                <strong>Are you sure you want to delete this resume?</strong>
                <br />
                Employers will no longer have access to your resume until you upload a replacement.
              </p>
              <div className="auth-button-group">
                <button
                  type="button"
                  className="btn btn-error"
                  onClick={handleDelete}
                  disabled={isDeleting}
                >
                  {isDeleting ? "Deleting..." : "Yes, Delete Resume"}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setConfirmDelete(false)}
                  disabled={isDeleting}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="resume-actions-group">
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleDownload}
                disabled={isDownloading || isUploading}
                aria-label={`Download ${resume.original_filename}`}
              >
                {isDownloading ? "Downloading..." : "Download Resume"}
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading || isDownloading}
                aria-label="Upload a new file to replace the existing resume"
              >
                {isUploading ? "Uploading..." : "Replace Resume"}
              </button>

              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setConfirmDelete(true)}
                disabled={isDeleting || isUploading}
                aria-label="Delete active resume from file"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="resume-empty-state">
          <p className="empty-state-title">No active resume uploaded</p>
          <p className="empty-state-desc">
            Upload your resume in PDF or DOCX format (maximum 5MB). Inclusive hiring teams review
            your skills, experience, and strengths.
          </p>
          <div className="resume-upload-cta">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              {isUploading ? "Uploading..." : "Upload Resume (PDF/DOCX)"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ResumeManager;

