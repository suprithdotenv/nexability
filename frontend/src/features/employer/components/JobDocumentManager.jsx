import { useState, useEffect } from "react";
import employerService from "../services/employerService.js";

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDate(isoString) {
  if (!isoString) return "-";
  try {
    return new Date(isoString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

export function JobDocumentManager() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    setIsLoading(true);
    setError("");
    try {
      const data = await employerService.getJobDocuments();
      setDocuments(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Failed to load uploaded job documents.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleFileChange(e) {
    setError("");
    setSuccessMessage("");
    const file = e.target.files?.[0];
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const name = file.name.toLowerCase();
    if (!name.endsWith(".pdf") && !name.endsWith(".docx")) {
      setError("Invalid file format. Only PDF and DOCX files are supported.");
      setSelectedFile(null);
      e.target.value = "";
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("File exceeds 10MB limit.");
      setSelectedFile(null);
      e.target.value = "";
      return;
    }

    setSelectedFile(file);
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a PDF or DOCX file to upload.");
      return;
    }

    setIsUploading(true);
    setError("");
    setSuccessMessage("");

    try {
      const res = await employerService.uploadJobDocument(selectedFile);
      setSuccessMessage(
        `Document "${res.original_filename}" uploaded successfully. It is queued for background processing.`
      );
      setSelectedFile(null);
      // Reset input element
      const input = document.getElementById("job-doc-file-input");
      if (input) input.value = "";
      await loadDocuments();
    } catch (err) {
      setError(err.message || "Document upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload(doc) {
    setDownloadingId(doc.id);
    setError("");
    try {
      if (doc.download_url) {
        window.open(doc.download_url, "_blank", "noopener,noreferrer");
      } else {
        const res = await employerService.downloadJobDocument(doc.id);
        if (res && res.blob) {
          const url = window.URL.createObjectURL(res.blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = res.filename || doc.original_filename || "job-document";
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.URL.revokeObjectURL(url);
        }
      }
    } catch (err) {
      setError(err.message || "Failed to download document.");
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleDelete(id, name) {
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) {
      return;
    }

    setDeletingId(id);
    setError("");
    setSuccessMessage("");
    try {
      await employerService.deleteJobDocument(id);
      setSuccessMessage(`Document "${name}" deleted.`);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(err.message || "Failed to delete document.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="job-documents-manager">
      <div className="section-header-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h2>Job Description Documents</h2>
          <p className="card-description">
            Upload PDF or DOCX job descriptions. Documents are automatically indexed with semantic embeddings for matching.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={loadDocuments}
          disabled={isLoading}
          aria-label="Refresh document list"
        >
          {isLoading ? "Refreshing..." : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <div className="form-error" role="alert" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {successMessage && (
        <div className="form-status" role="status" style={{ marginBottom: "1rem" }}>
          {successMessage}
        </div>
      )}

      {/* Upload Box */}
      <section className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", border: "1px dashed var(--color-border-strong, #7aa3c4)" }} aria-labelledby="upload-heading">
        <h3 id="upload-heading" style={{ fontSize: "1.125rem", marginBottom: "0.5rem" }}>
          Upload New Job Description
        </h3>
        <form onSubmit={handleUpload} style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "center" }}>
          <div style={{ flex: 1, minWidth: "250px" }}>
            <label htmlFor="job-doc-file-input" className="sr-only">Choose job description file (PDF or DOCX)</label>
            <input
              id="job-doc-file-input"
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileChange}
              disabled={isUploading}
              style={{ width: "100%", padding: "0.5rem" }}
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? "Uploading..." : "Upload Document"}
          </button>
        </form>
        <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.5rem", marginBotom: 0 }}>
          Supported: <strong>PDF</strong> and <strong>DOCX</strong> up to 10MB.
        </p>
      </section>

      {/* Documents Table */}
      {isLoading && documents.length === 0 ? (
        <p>Loading documents...</p>
      ) : documents.length === 0 ? (
        <div className="empty-state" style={{ textAlign: "center", padding: "2rem", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)" }}>
          <p>No job description documents uploaded yet.</p>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
            Upload role specifications or team job briefs above to make them available for matching.
          </p>
        </div>
      ) : (
        <div className="table-responsive" tabIndex="0" aria-label="Uploaded job documents table">
          <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "2px solid var(--color-border)" }}>
                <th style={{ padding: "0.75rem" }}>Filename</th>
                <th style={{ padding: "0.75rem" }}>Size</th>
                <th style={{ padding: "0.75rem" }}>Uploaded</th>
                <th style={{ padding: "0.75rem" }}>Status</th>
                <th style={{ padding: "0.75rem", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td style={{ padding: "0.75rem", fontWeight: "500" }}>
                    <span aria-hidden="true" style={{ marginRight: "0.5rem" }}>
                      {doc.original_filename.endsWith(".pdf") ? "📄" : "📝"}
                    </span>
                    {doc.original_filename}
                  </td>
                  <td style={{ padding: "0.75rem", fontSize: "0.875rem" }}>
                    {formatBytes(doc.file_size_bytes)}
                  </td>
                  <td style={{ padding: "0.75rem", fontSize: "0.875rem" }}>
                    {formatDate(doc.created_at)}
                  </td>
                  <td style={{ padding: "0.75rem" }}>
                    <span
                      className={`status-badge ${
                        doc.status === "PARSED" || doc.status === "EXTRACTED"
                          ? "status-active"
                          : doc.status === "PROCESSING"
                            ? "status-warning"
                            : "status-neutral"
                      }`}
                      style={{ fontSize: "0.75rem", textTransform: "uppercase" }}
                    >
                      {doc.status || "UPLOADED"}
                    </span>
                  </td>
                  <td style={{ padding: "0.75rem", textAlign: "right", whiteSpace: "nowrap" }}>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => handleDownload(doc)}
                      disabled={downloadingId === doc.id}
                      style={{ marginRight: "0.5rem", padding: "0.25rem 0.5rem" }}
                      aria-label={`Download ${doc.original_filename}`}
                    >
                      {downloadingId === doc.id ? "..." : "⬇ Download"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => handleDelete(doc.id, doc.original_filename)}
                      disabled={deletingId === doc.id}
                      style={{ padding: "0.25rem 0.5rem", color: "var(--color-error)" }}
                      aria-label={`Delete ${doc.original_filename}`}
                    >
                      {deletingId === doc.id ? "Deleting..." : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default JobDocumentManager;
