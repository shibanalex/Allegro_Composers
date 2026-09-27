"""Content service: a composer's «Материалы» — books, links and files shown in their hall"""
import re
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from allegro_common.db import get_db
from allegro_common.deps import get_current_user
from allegro_common.media_refs import check_url, delete_own
from allegro_common.models import Material, User
from allegro_common.schemas import Attachment, ORMModel, UTCDateTime
from allegro_common.storage import storage

router = APIRouter(tags=["content"])

Kind = Literal["book", "link", "file"]


class MaterialFields(BaseModel):
    kind: Optional[Kind] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    url: Optional[str] = Field(None, max_length=1024)
    file: Optional[Attachment] = None
    cover_url: Optional[str] = Field(None, max_length=512)
    position: Optional[int] = None

    @field_validator("url")
    @classmethod
    def _http_only(cls, v):
        if v and not re.match(r"^https?://", v.strip()):
            raise ValueError("Ссылка должна начинаться с http:// или https://")
        return v.strip() if v else v


class MaterialIn(MaterialFields):
    kind: Kind
    title: str = Field(min_length=1, max_length=255)


class MaterialOut(ORMModel):
    id: uuid.UUID
    kind: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    file: Optional[Attachment] = None
    cover_url: Optional[str] = None
    position: int
    created_at: UTCDateTime


def _check(kind: str, url: Optional[str], file: Optional[dict]) -> None:
    if kind == "link" and not url:
        raise HTTPException(422, "Для ссылки нужен адрес")
    if kind == "file" and not file:
        raise HTTPException(422, "Прикрепите файл")
    # a book may be a file, a link to a shop/library, or just a recommendation with a description


def _check_files(user: User, values: dict, material: Optional[Material] = None) -> None:
    """The file and the cover must be the author's own uploads (or already on this material)"""
    current = [material.cover_url, (material.file or {}).get("url")] if material else []
    if values.get("file"):
        check_url(user, values["file"]["url"], current)
    if "cover_url" in values:
        check_url(user, values["cover_url"], current)


def _own(db: Session, material_id: uuid.UUID, user: User) -> Material:
    material = db.get(Material, material_id)
    if not material or material.author_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Материал не найден")
    return material


@router.get("/api/materials", response_model=list[MaterialOut])
def list_materials(author: str, db: Session = Depends(get_db)):
    owner = db.scalar(select(User).where(User.username == author.lower(), User.is_hidden.is_(False)))
    if not owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Автор не найден")
    return db.scalars(
        select(Material).where(Material.author_id == owner.id).order_by(Material.position, Material.created_at.desc())
    ).all()


@router.post("/api/materials", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
def create_material(data: MaterialIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    values = data.model_dump(exclude_none=True, mode="json")
    _check_files(user, values)
    _check(data.kind, values.get("url"), values.get("file"))
    material = Material(author_id=user.id, **values)
    db.add(material)
    db.commit()
    return material


@router.patch("/api/materials/{material_id}", response_model=MaterialOut)
def update_material(material_id: uuid.UUID, data: MaterialFields, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    material = _own(db, material_id, user)
    values = data.model_dump(exclude_unset=True, mode="json")
    _check_files(user, values, material)
    old_file = (material.file or {}).get("url")
    old_cover = material.cover_url
    for field, value in values.items():
        setattr(material, field, value)
    _check(material.kind, material.url, material.file)
    if "file" in values and old_file != (material.file or {}).get("url"):
        delete_own(user, storage.key_from_url(old_file))
    if "cover_url" in values and old_cover != material.cover_url:
        delete_own(user, storage.key_from_url(old_cover))
    db.commit()
    return material


@router.delete("/api/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    material = _own(db, material_id, user)
    delete_own(user, storage.key_from_url((material.file or {}).get("url")))
    delete_own(user, storage.key_from_url(material.cover_url))
    db.delete(material)
    db.commit()
