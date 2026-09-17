from fastapi import APIRouter, Depends, HTTPException,UploadFile,File,Form,Query
from sqlalchemy.orm import Session
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.theme import ThemeCreate, ThemeUpdate, ThemeResponse, ThemeResponseList
from app.db.models.theme import ThemeConfig
from app.db.models.user import User
from app.api.deps.auth_dep import get_db, require_role
from app.schemas.theme import ThemeAssetType
import uuid
from app.core.config import settings
from app.schemas.document import Pageination
from fastapi.responses import FileResponse
from pathlib import Path
import hashlib
from app.utils.helper import read_file_in_chunks

router = APIRouter()


@router.post("/", response_model=ThemeResponse)
async def create_theme(
    data: ThemeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):
    
    # check if theme already exists for tenant
    
    # stmt = select(ThemeConfig).where(ThemeConfig.tenant_id == current_user.tenant_id)
    # result = await db.execute(stmt)

    # theme = result.scalars().first()

    # if theme:
        # update existing
    # for key, value in data.model_dump(exclude_unset=True).items():
    #     setattr(theme, key, value)
    
        # create new
    theme = ThemeConfig(**data.model_dump())
    theme.tenant_id = current_user.tenant_id
    db.add(theme)

    await db.commit()
    await db.refresh(theme)

    return theme


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):

    # print(f"Fetching theme for tenant_id: {tenant_id}")  # Debug log

    # print(f"Fetching theme for tenant_id: {current_user.tenant_id}")  # Debug log
    # 🔒 tenant isolation
   

    stmt = select(ThemeConfig).where(ThemeConfig.id == theme_id).where(ThemeConfig.tenant_id == current_user.tenant_id)

    result = await db.execute(stmt)
    theme = result.scalars().first()

    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    return theme


@router.put("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    theme_id: int,
    data: ThemeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):

    stmt = select(ThemeConfig).where(ThemeConfig.id == theme_id).where(ThemeConfig.tenant_id == current_user.tenant_id)

    result = await db.execute(stmt)

    theme = result.scalars().first()

    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    # update only provided fields
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(theme, key, value)

    await db.commit()
    await db.refresh(theme)

    return theme


@router.delete("/{theme_id}")
async def delete_theme(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):

    stmt = select(ThemeConfig).where(ThemeConfig.id == theme_id).where(ThemeConfig.tenant_id == current_user.tenant_id)

    result = await db.execute(stmt)
    theme = result.scalars().first()

    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    await db.delete(theme)
    await db.commit()

    return {"message": "Theme deleted successfully"}

@router.post("/asset")
async def upload_theme_asset(
    file: UploadFile = File(...),
    type: ThemeAssetType = Form(...),

    current_user: User = Depends(require_role("tenant_admin")),
):

    # validate image
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")
    
    #contents = await file.read()
   

    # if len(contents) > settings.MAX_UPLOAD_SIZE:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"File too large. Max size is {settings.MAX_UPLOAD_SIZE} bytes.",
    #     )

    # create subfolder inside uploads
    upload_dir = settings.UPLOAD_DIR / type.value
    upload_dir.mkdir(parents=True, exist_ok=True)

    # unique filename
    file_ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_ext}"

    file_path = upload_dir / filename

    # # save file
    # with open(file_path, "wb") as f:
    #     f.write(await file.read())
    
    size = 0

    try:
        with open(file_path, "wb") as f:
            async for chunk in read_file_in_chunks(file):
                size += len(chunk)

                if size > settings.MAX_UPLOAD_SIZE:
                    f.close()
                    file_path.unlink(missing_ok=True)  # cleanup

                    raise HTTPException(
                        status_code=400,
                        detail="File too large, max size is 2MB."
                    )

                f.write(chunk)

    finally:
        await file.close()
    return {
        "message": "File uploaded successfully",
        "file_path": f"/uploads/{type.value}/{filename}",
        "type": type.value
    }
    
    
@router.get("/asset/download/{type}/{filename}")
async def download_theme_asset(type: str, filename: str):
    full_path = settings.UPLOAD_DIR / type / filename
    
    print("full_path:", full_path)  # Debug log

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(full_path, filename=filename)


@router.get("/", response_model=ThemeResponseList)
async def list_themes(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):
    # Base query
    base_query = select(ThemeConfig).where(ThemeConfig.tenant_id == current_user.tenant_id)

    # Apply pagination
    stmt = base_query.order_by(ThemeConfig.created_at.desc()).limit(limit).offset(offset)

    # Total count
    count_stmt = select(func.count()).select_from(base_query)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    result = await db.execute(stmt)
    
    return ThemeResponseList(
        themes=result.scalars().all(),
        pagination=Pageination(
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total,
        ),
    )

