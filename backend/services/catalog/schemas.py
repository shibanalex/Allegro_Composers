import re
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from allegro_common import enums
from allegro_common.schemas import ORMModel, UserBrief, UTCDateTime

YOUTUBE_ID = re.compile(r"(?:youtu\.be/|v=|embed/|shorts/)([\w-]{11})")


class Marker(ORMModel):
    page_number: int = Field(ge=1)
    timestamp_seconds: float = Field(ge=0)


class MeasureMarker(ORMModel):
    measure_number: int = Field(ge=1)
    timestamp_seconds: float = Field(ge=0)


class OpusFields(BaseModel):
    """Editable fields; every one optional so the same model serves PATCH"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=255)
    instrumentation: Optional[str] = Field(None, max_length=255)
    ensemble: Optional[str] = None
    form: Optional[str] = None
    key_signature: Optional[str] = Field(None, max_length=40)
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    tags: Optional[list[str]] = None
    description_md: Optional[str] = Field(None, max_length=50_000)
    cover_url: Optional[str] = Field(None, max_length=512)
    audio_type: Optional[Literal["none", "youtube", "hosted_file"]] = None
    audio_source: Optional[str] = Field(None, max_length=512)
    audio_duration_seconds: Optional[float] = Field(None, ge=0)
    score_file_key: Optional[str] = Field(None, max_length=512)
    score_page_count: Optional[int] = Field(None, ge=1, le=2000)
    score_access: Optional[Literal["free", "view_only", "paid"]] = None
    musicxml_file_key: Optional[str] = Field(None, max_length=512)
    audio_offset_seconds: Optional[float] = Field(None, ge=0)
    status: Optional[Literal["published", "draft", "unlisted"]] = None

    @field_validator("ensemble")
    @classmethod
    def _ensemble(cls, v):
        if v is not None and v not in enums.ENSEMBLES:
            raise ValueError(f"Допустимо: {', '.join(enums.ENSEMBLES)}")
        return v

    @field_validator("form")
    @classmethod
    def _form(cls, v):
        if v is not None and v not in enums.FORMS:
            raise ValueError(f"Допустимо: {', '.join(enums.FORMS)}")
        return v

    @field_validator("tags")
    @classmethod
    def _tags(cls, v):
        if v is None:
            return v
        seen, out = set(), []
        for tag in (t.strip().lower() for t in v):
            if tag and tag not in seen:
                seen.add(tag)
                out.append(tag[:40])
        return out[:20]


class OpusCreate(OpusFields):
    title: str = Field(min_length=1, max_length=255)
    ensemble: str
    form: str
    # PDF page-turn markers; empty = derive them from the MusicXML page layout when possible
    markers: list[Marker] = Field([], max_length=2000)
    measure_markers: list[MeasureMarker] = Field([], max_length=20_000)


class OpusUpdate(OpusFields):
    # None = keep the current mode; [] = derive from MusicXML; a list = set by hand
    markers: Optional[list[Marker]] = Field(None, max_length=2000)
    measure_markers: Optional[list[MeasureMarker]] = Field(None, max_length=20_000)


class OpusOut(ORMModel):
    id: uuid.UUID
    slug: str
    title: str
    subtitle: Optional[str] = None
    instrumentation: Optional[str] = None
    ensemble: str
    form: str
    key_signature: Optional[str] = None
    difficulty: Optional[int] = None
    year: Optional[int] = None
    tags: list[str] = []
    description_md: Optional[str] = None
    cover_url: Optional[str] = None
    audio_type: str
    audio_source: Optional[str] = None
    audio_url: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    score_url: Optional[str] = None
    score_page_count: Optional[int] = None
    score_access: str
    musicxml_url: Optional[str] = None
    audio_offset_seconds: float = 0
    auto_page_markers: bool = False
    status: str
    play_count: int
    created_at: UTCDateTime
    author: UserBrief
    markers: list[Marker] = []
    measure_markers: list[MeasureMarker] = []
    critique_count: int = 0


class OpusPage(BaseModel):
    items: list[OpusOut]
    total: int


class CollectionIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    opus_ids: list[uuid.UUID] = []


class CollectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    opus_ids: Optional[list[uuid.UUID]] = None


class CollectionOut(ORMModel):
    id: uuid.UUID
    slug: str
    title: str
    description: Optional[str] = None
    year: Optional[int] = None
    created_at: UTCDateTime
    author: UserBrief
    opuses: list[OpusOut]


class Facet(BaseModel):
    value: str
    label: str
    count: int


class Facets(BaseModel):
    ensembles: list[Facet]
    forms: list[Facet]
    keys: list[Facet]
    difficulty: list[Facet]
    tags: list[Facet]


class SearchComposer(UserBrief):
    bio: Optional[str] = None


class SearchOpus(BaseModel):
    slug: str
    title: str
    subtitle: Optional[str] = None
    author: UserBrief
    snippet: Optional[str] = None  # the words found in the description


class SearchPost(BaseModel):
    slug: str
    title: str
    kind: str
    author: UserBrief
    created_at: UTCDateTime
    snippet: str = ""  # the words found in the text (blog posts are often untitled)


class SearchResult(BaseModel):
    composers: list[SearchComposer]
    opuses: list[SearchOpus]
    posts: list[SearchPost]
    tags: list[str]
    words: list[str] = []  # the stems searched for, to highlight them
