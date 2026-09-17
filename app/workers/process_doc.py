from pathlib import Path
import asyncio

from sqlalchemy.future import select
from app.core.logger import logger
from app.services.document_service import DocumentProcessor
from app.workers.celery_task import celery_app
from app.db.session import SessionLocal
from app.db.models.document import Document
from app.schemas.document import DocumentStatus
from app.core.shared_resources import get_shared_models

# Loaded models
models = get_shared_models()


@celery_app.task(bind=True, max_retries=3)
def process_document_task(
    self, file_path: str, doc_id: str, tenant_id: str, category: str
):
    try:
        service: DocumentProcessor = models["doc_processor"]
        file_path = Path(file_path)

        # If ingest_document is async, we’ll handle that separately
        success, policy = asyncio.run(
            service.ingest_document(file_path, doc_id, tenant_id, category)
        )

        status = DocumentStatus.FAILED if not success else DocumentStatus.COMPLETED

        # Sync DB update
        with SessionLocal() as session:
            doc = session.query(Document).filter(Document.id == doc_id).first()

            if doc:
                doc.processing_status = status.value
                session.commit()

        if not success:
            return {
                "status": status,
                "doc_id": doc_id,
                "chunks": -1,
                "category": "",
                "error": policy,
            }

        return {
            "status": status,
            "doc_id": doc_id,
            "chunks": policy.chunk_count,
            "category": policy.category,
            "error": "",
        }

    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        raise self.retry(countdown=60, exc=exc)
