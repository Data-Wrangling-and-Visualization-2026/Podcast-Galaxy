"""sqlalchemy table definitions for podcasts, episodes, and map points."""

from sqlalchemy import Column, String, Integer, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


class Podcast(Base):
    __tablename__ = "podcasts"

    podcast_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    yandex_id = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=False)
    age_restriction = Column(Integer, nullable=True)
    likes_count = Column(Integer, default=0)
    track_count = Column(Integer, nullable=True)

    episodes = relationship("Episode", back_populates="podcast", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"

    episode_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    yandex_id = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    duration = Column(Integer, nullable=False)
    podcast_id = Column(UUID(as_uuid=True), ForeignKey("podcasts.podcast_id"), nullable=False)
    # pub_date stays as a string because imported source data is not fully normalized.
    pub_date = Column(String, nullable=True)

    podcast = relationship("Podcast", back_populates="episodes")
    map_point = relationship(
        "EpisodeMapPoint",
        back_populates="episode",
        cascade="all, delete-orphan",
        uselist=False,
    )


class EpisodeMapPoint(Base):
    __tablename__ = "episode_map_points"

    episode_id = Column(UUID(as_uuid=True), ForeignKey("episodes.episode_id"), primary_key=True)
    umap_x = Column(Float, nullable=False, index=True)
    umap_y = Column(Float, nullable=False, index=True)
    dominant_topic = Column(String, nullable=False)
    dominant_weight = Column(Float, nullable=True)
    # store the full topic distribution so hover cards can show more than the dominant topic.
    topic_scores_json = Column(Text, nullable=False)

    episode = relationship("Episode", back_populates="map_point")
