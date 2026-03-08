from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.response import err, ok
from app.security.admin import require_admin
from app.security.rate_limit import admin_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin-upload"],
    dependencies=[Depends(require_admin), Depends(admin_rate_limit)],
)

# Папка относительно корня проекта (рядом с app/)
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
EXT_MAP = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


@router.post("/upload")
async def admin_upload_image(file: UploadFile = File(...)):
    """Загрузить фото товара. Возвращает URL для поля «Ссылка на фото»."""
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in ALLOWED_CONTENT_TYPES:
        return JSONResponse(
            status_code=400,
            content=err("bad_request", "Разрешены только изображения: JPEG, PNG, WebP, GIF").model_dump(),
        )
    try:
        body = await file.read()
    except Exception as e:
        logger.warning("upload.read_failed", extra={"error": str(e)})
        return JSONResponse(status_code=400, content=err("bad_request", "Не удалось прочитать файл").model_dump())
    if len(body) > MAX_SIZE:
        return JSONResponse(
            status_code=400,
            content=err("bad_request", "Файл не более 5 МБ").model_dump(),
        )
    ext = EXT_MAP.get(ct, ".jpg")
    name = f"{uuid.uuid4().hex}{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / name
    try:
        path.write_bytes(body)
    except Exception as e:
        logger.exception("upload.write_failed", extra={"path": str(path)})
        return JSONResponse(status_code=500, content=err("internal_error", "Ошибка сохранения файла").model_dump())
    url = f"/uploads/{name}"
    return ok({"url": url})
