from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


class Podcast(Base):
    __tablename__ = "podcasts"

    podcast_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    age_restriction = Column(Integer, nullable=True)
    likes_count = Column(Integer, default=0)
    category = Column(String, nullable=True)

    episodes = relationship("Episode", back_populates="podcast", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"

    episode_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    podcast_id = Column(UUID(as_uuid=True), ForeignKey("podcasts.podcast_id"), nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)

    podcast = relationship("Podcast", back_populates="episodes")