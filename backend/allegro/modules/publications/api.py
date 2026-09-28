"""HTTP layer of the publications module: blog posts, articles, news; members' materials"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.modules.accounts.deps import get_current_user, get_optional_user
from allegro.modules.publications import service
from allegro.modules.publications.schemas import (
    Kind, MaterialFields, MaterialIn, MaterialOut, PostCreate, PostFields, PostOut, PostPage,
)

router = APIRouter(tags=["publications"])


@router.get("/api/posts", response_model=PostPage)
def list_posts(
    kind: Optional[list[Kind]] = Query(None),
    author: Optional[str] = None,
    opus: Optional[str] = None,
    mine: bool = False,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """«Блоги» (kind=note) and «Статьи и обзоры» (kind=article) of all members, one member's posts, the news"""
    posts, total = service.list_posts(db, user, kinds=kind, author=author, opus=opus, mine=mine, limit=limit, offset=offset)
    return PostPage(items=service.posts_out(db, posts), total=total)


@router.get("/api/posts/{slug}", response_model=PostOut)
def get_post(slug: str, user=Depends(get_optional_user), db: Session = Depends(get_db)):
    return service.posts_out(db, [service.read_post(db, slug, user)])[0]


@router.post("/api/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.posts_out(db, [service.create_post(db, user, data)])[0]


@router.patch("/api/posts/{slug}", response_model=PostOut)
def update_post(slug: str, data: PostFields, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.posts_out(db, [service.update_post(db, user, slug, data)])[0]


@router.delete("/api/posts/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(slug: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_post(db, user, slug)


# ---------------------------------------------------------------- materials

@router.get("/api/materials", response_model=list[MaterialOut])
def list_materials(author: str, db: Session = Depends(get_db)):
    return service.list_materials(db, author)


@router.post("/api/materials", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
def create_material(data: MaterialIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.create_material(db, user, data)


@router.patch("/api/materials/{material_id}", response_model=MaterialOut)
def update_material(material_id: uuid.UUID, data: MaterialFields, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.update_material(db, user, material_id, data)


@router.delete("/api/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_material(db, user, material_id)
