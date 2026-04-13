import json
import uuid
from typing import List, Optional, Union

from pydantic import BaseModel, Field


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
    yandex_id: Optional[str] = None
    pub_date: Optional[str] = None


class PodcastCreate(PodcastFields):
    title: str


class EpisodeCreate(EpisodeFields):
    title: str
    duration: int
    podcast_id: uuid.UUID


class ShowPodcast(PodcastFields):
    podcast_id: uuid.UUID
    episodes: Optional[List["ShowEpisode"]] = None

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


class BatchEpisodeCreate(BaseModel):
    episodes: List[EpisodeCreate]


class ViewportRequest(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    limit: int = Field(5000, ge=1, le=20000)

    @property
    def min_x(self) -> float:
        return min(self.x1, self.x2)

    @property
    def max_x(self) -> float:
        return max(self.x1, self.x2)

    @property
    def min_y(self) -> float:
        return min(self.y1, self.y2)

    @property
    def max_y(self) -> float:
        return max(self.y1, self.y2)


class ViewportPoint(BaseModel):
    episode_id: uuid.UUID
    x: float
    y: float
    dominant_topic: str


class TopicScore(BaseModel):
    topic: str
    weight: float


class EpisodeHoverResponse(BaseModel):
    episode_id: uuid.UUID
    title: str
    description: Optional[str] = None
    podcast_title: str
    dominant_topic: Optional[str] = None
    top_3_topics: List[TopicScore]


def extract_top_topics(topic_scores_json: Optional[Union[str, dict]], limit: int = 3) -> List[TopicScore]:
    if not topic_scores_json:
        return []

    if isinstance(topic_scores_json, dict):
        topic_scores_json = json.dumps(topic_scores_json)

    try:
        topic_scores = json.loads(topic_scores_json)
    except json.JSONDecodeError:
        return []

    if not isinstance(topic_scores, dict):
        return []

    ranked_topics = []
    for topic, weight in topic_scores.items():
        if weight is None:
            continue
        try:
            numeric_weight = float(weight)
        except (TypeError, ValueError):
            continue
        if numeric_weight <= 0:
            continue
        ranked_topics.append((str(topic), numeric_weight))

    ranked_topics.sort(key=lambda item: item[1], reverse=True)

    return [TopicScore(topic=topic, weight=weight) for topic, weight in ranked_topics[:limit]]