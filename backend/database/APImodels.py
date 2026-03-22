import uuid
from pydantic import BaseModel, Field
from typing import Optional, List


class PodcastFields(BaseModel):
    title: Optional[str] = None
    age_restriction: Optional[int] = Field(None, ge=0, le=21)
    likes_count: Optional[int] = Field(0, ge=0)
    yandex_id: Optional[str] = None
    track_count: Optional[int] = None


class EpisodeFields(BaseModel):
    title: Optional[str] = None
    duration: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    category: Optional[str] = None
    yandex_id: Optional[str] = None
    pub_date: Optional[str] = None


class TunedModel(BaseModel):
    class Config:
        from_attributes = True


class PodcastCreate(PodcastFields):
    title: str


class EpisodeCreate(EpisodeFields):
    title: str
    duration: int
    podcast_id: uuid.UUID


class ShowPodcast(PodcastFields):
    podcast_id: uuid.UUID
    episodes: Optional[List['ShowEpisode']] = None

    class Config:
        from_attributes = True


class ShowEpisode(EpisodeFields):
    episode_id: uuid.UUID
    podcast_id: uuid.UUID
    podcast: Optional[ShowPodcast] = None

    class Config:
        from_attributes = True


class PodcastUpdate(BaseModel):
    title: Optional[str] = None
    age_restriction: Optional[int] = Field(None, ge=0, le=21)
    likes_count: Optional[int] = Field(None, ge=0)


class EpisodeUpdate(BaseModel):
    title: Optional[str] = None
    duration: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    category: Optional[str] = None


class PodcastCategoryUpdate(BaseModel):
    podcast_id: uuid.UUID
    category: str


class EpisodeCategoryUpdate(BaseModel):
    episode_id: uuid.UUID
    category: str


class EpisodeCategoryBatchUpdate(BaseModel):
    updates: List[EpisodeCategoryUpdate]


class PodcastCategoryBatchUpdate(BaseModel):
    updates: List[PodcastCategoryUpdate]


class BatchEpisodeCreate(BaseModel):
    episodes: List[EpisodeCreate]