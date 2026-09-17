import hashlib
from typing import Optional
import uuid
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.db.models.document import Document
from app.schemas.document import (
    DocumentResponse,
    DocumentResponseList,
    DocumentStatus,
    Pageination,
    DocumentUpdate,
)
from app.api.deps.auth_dep import get_db, require_role
from app.workers.process_doc import process_document_task
from app.core.config import settings
from app.utils.helper import read_file_in_chunks

router = APIRouter()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_document(
    title: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("tenant_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload PDF document for processing and chunking
    """
    safe_tenant_id = f"tenant_{current_user.tenant_id}"

    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files supported"
        )

    doc_id = str(uuid.uuid4())
    file_path = settings.UPLOAD_DIR / f"{doc_id}_{file.filename}"   
   
    # check for duplicate file
    # file_bytes = file.file.read()
    # file_hash = hashlib.md5(file_bytes).hexdigest()
    
    size = 0
    hasher = hashlib.md5()

    try:
        with open(file_path, "wb") as f:
            async for chunk in read_file_in_chunks(file):
                size += len(chunk)

                if size > settings.MAX_UPLOAD_SIZE_DOCUMENT:
                    f.close()
                    file_path.unlink(missing_ok=True)

                    raise HTTPException(
                        status_code=400,
                        detail="File too large. Max size is 50MB."
                    )

                hasher.update(chunk)
                f.write(chunk)

    finally:
        await file.close()

    file_hash = hasher.hexdigest()

#  Duplicate check
    stmt = (
        select(Document)
        .where(Document.doc_hash == file_hash)
        .where(Document.tenant_id == current_user.tenant_id)
    )

    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        file_path.unlink(missing_ok=True)  # cleanup

        raise HTTPException(
            status_code=400,
            detail="Document already exists"
    )   
   
    # Save file
    #file_path.write_bytes(file_bytes)

    # Queue background processing
    task = process_document_task.delay(str(file_path), doc_id, safe_tenant_id, category)

    document = Document(
        id=doc_id,
        tenant_id=current_user.tenant_id,
        title=title,
        category=category,
        #file_name=file.filename,
        file_name = file_path.name,
        author_id=current_user.id,
        doc_hash=file_hash,
        processing_status=DocumentStatus.PROCESSING.value,
        processing_id=task.id,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)
    # UPLOAD_COUNTER.labels(tenant=tenant_id, status="queued").inc()

    return DocumentResponse(
        doc_id=doc_id,
        filename=file.filename,
        status=DocumentStatus.PROCESSING.value,
        tenant_id=current_user.tenant_id,
    )


@router.get("", response_model=DocumentResponseList)
async def list_documents(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    title: str | None = Query(None),
    category: str | None = Query(None),
    current_user: User = Depends(require_role("tenant_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all processed documents with pagination
    """

    # Base query (scoped to tenant)
    base_query = select(Document).where(Document.tenant_id == current_user.tenant_id)

    if title:
        base_query = base_query.where(Document.title.ilike(f"%{title}%"))

    if category:
        base_query = base_query.where(Document.category.ilike(f"%{category}%"))

    # Get total count
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply ordering + pagination
    stmt = (
        base_query.order_by(
            Document.created_at.desc()
        )  # Always order paginated results
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    documents = result.scalars().all()

    document_responses = [
        DocumentResponse(
            doc_id=str(doc.id),
            filename=doc.file_name,
            status=doc.processing_status,
            tenant_id=str(doc.tenant_id),
            category=doc.category,
        )
        for doc in documents
    ]

    return DocumentResponseList(
        data=document_responses,
        pagination=Pageination(
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total,
        ),
    )


@router.patch("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    payload: DocumentUpdate,
    current_user: User = Depends(require_role("tenant_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update document metadata (title, category)
    """

    stmt = (
        select(Document)
        .where(Document.id == doc_id)
        .where(Document.tenant_id == current_user.tenant_id)
    )

    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Do not allow update during processing
    if document.processing_status == DocumentStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update while document is processing",
        )

    if payload.title is not None:
        document.title = payload.title

    if payload.category is not None:
        document.category = payload.category

    await db.commit()
    await db.refresh(document)

    return DocumentResponse(
        doc_id=document.id,
        filename=document.file_name,
        status=document.processing_status,
        tenant_id=document.tenant_id,
        category=document.category,
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    request: Request,
    doc_id: str,
    current_user: User = Depends(require_role("tenant_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its chunks"""
    tenant_id = current_user.tenant_id

    stmt = (
        select(Document)
        .filter(Document.author_id == current_user.id)
        .filter(Document.tenant_id == tenant_id)
        .filter(Document.id == doc_id)
    )

    result = await db.execute(stmt)

    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not exists"
        )

    vectordb = request.app.state.models["vectordb"]

    await vectordb.delete_collection(doc.tenant_id, doc.doc_hash)

    await db.delete(doc)
    await db.commit()

    return {"message": f"Document {doc_id} deleted"}


@router.get("/categories")
async def get_categories(
    current_user: User = Depends(require_role("tenant_admin")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Document.category)
        .where(Document.tenant_id == current_user.tenant_id)
        .distinct()
    )

    result = await db.execute(stmt)

    categories = [row[0] for row in result.fetchall() if row[0]]

    return {"categories": categories}
