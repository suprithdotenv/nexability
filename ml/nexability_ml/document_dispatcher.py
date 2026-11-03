from __future__ import annotations

import logging
from collections.abc import Mapping

from .job_processing import JobDocumentProcessor
from .resume_processing import ResumeExtractionProcessor

logger = logging.getLogger(__name__)


class DocumentProcessingDispatcher:
    """Dispatches each pending backend document independently by declared type."""

    def __init__(
        self,
        *,
        resume_processor: ResumeExtractionProcessor,
        job_processor: JobDocumentProcessor,
    ) -> None:
        self.resume_processor = resume_processor
        self.job_processor = job_processor

    def process_pending_documents(self) -> dict[str, int]:
        queue = self.resume_processor.client.list_pending_documents()
        if (
            not isinstance(queue, Mapping)
            or not isinstance(queue.get("active_resumes"), list)
            or not isinstance(queue.get("pending_job_documents"), list)
        ):
            raise RuntimeError("The backend pending-documents response has an invalid shape.")

        counts = {"processed": 0, "skipped": 0, "failed": 0}
        documents = [
            ("RESUME", item) for item in queue["active_resumes"]
        ] + [
            ("JOB_DOCUMENT", item) for item in queue["pending_job_documents"]
        ]
        for expected_type, item in documents:
            try:
                if not isinstance(item, Mapping):
                    raise ValueError("invalid_queue_item")
                if item.get("document_type") != expected_type:
                    raise ValueError("document_type_mismatch")
                if expected_type == "RESUME":
                    outcome = self.resume_processor.process_resume_metadata(item)
                else:
                    outcome = self.job_processor.process_job_metadata(item)
                if outcome not in counts:
                    raise RuntimeError("Processor returned an invalid outcome.")
            except Exception as exc:
                outcome = "failed"
                logger.warning(
                    "Document processing failed: type=%s error_class=%s",
                    expected_type,
                    type(exc).__name__,
                )
            counts[outcome] += 1
        return counts
