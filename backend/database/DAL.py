from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import RowMapping
from sqlalchemy import text, Sequence
from sqlalchemy.orm import class_mapper
from database.table import Podcast, Episode
from database.APImodels import PodcastCreate, EpisodeCreate
import uuid
from typing import List


def model_to_dict(model):
    return {c.key: getattr(model, c.key) for c in class_mapper(model.__class__).columns}


class PodcastDAL:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_podcast(self, podcast_data: PodcastCreate) -> Podcast:
        new_podcast = Podcast(**podcast_data.model_dump())
        self.db_session.add(new_podcast)
        await self.db_session.flush()
        return new_podcast

    async def get_podcast_by_id(self, podcast_id: uuid.UUID) -> RowMapping | None:
        query = text("SELECT * FROM podcasts WHERE podcast_id = :podcast_id")
        result = await self.db_session.execute(query, {"podcast_id": podcast_id})
        return result.mappings().first()

    async def get_podcasts_from_n(self, skip: int = 0, limit: int = 20) -> Sequence[RowMapping]:
        """Get podcasts with pagination"""
        query = text("""
            SELECT * FROM podcasts 
            ORDER BY podcast_id 
            OFFSET :skip 
            LIMIT :limit
        """)
        result = await self.db_session.execute(query, {"skip": skip, "limit": limit})
        return result.mappings().all()

    async def update_podcast(self, podcast_id: uuid.UUID, update_data: dict) -> RowMapping | None:
        set_clause = ", ".join([f"{key} = :{key}" for key in update_data.keys()])
        query = text(f"""
            UPDATE podcasts 
            SET {set_clause}
            WHERE podcast_id = :podcast_id 
            RETURNING *
        """)
        params = {"podcast_id": podcast_id, **update_data}
        result = await self.db_session.execute(query, params)
        await self.db_session.commit()
        return result.mappings().first()

    async def delete_podcast(self, podcast_id: uuid.UUID) -> bool:
        query = text("DELETE FROM podcasts WHERE podcast_id = :podcast_id RETURNING podcast_id")
        result = await self.db_session.execute(query, {"podcast_id": podcast_id})
        await self.db_session.commit()
        return result.first() is not None

    async def update_podcast_category(self, podcast_id: uuid.UUID, category: str) -> RowMapping | None:
        query = text("""
            UPDATE podcasts 
            SET category = :category
            WHERE podcast_id = :podcast_id 
            RETURNING *
        """)
        result = await self.db_session.execute(query, {"podcast_id": podcast_id, "category": category})
        await self.db_session.commit()
        return result.mappings().first()


class EpisodeDAL:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_episode(self, episode_data: EpisodeCreate) -> Episode:
        episode_dict = episode_data.model_dump()
        episode_dict.pop('category', None)

        new_episode = Episode(**episode_dict)
        self.db_session.add(new_episode)
        await self.db_session.flush()
        return new_episode

    async def get_episode_by_id(self, episode_id: uuid.UUID) -> RowMapping | None:
        query = text("SELECT * FROM episodes WHERE episode_id = :episode_id")
        result = await self.db_session.execute(query, {"episode_id": episode_id})
        return result.mappings().first()

    async def get_episodes_by_podcast(self, podcast_id: uuid.UUID) -> Sequence[RowMapping]:
        query = text("SELECT * FROM episodes WHERE podcast_id = :podcast_id ORDER BY episode_id")
        result = await self.db_session.execute(query, {"podcast_id": podcast_id})
        return result.mappings().all()

    async def delete_episode(self, episode_id: uuid.UUID) -> bool:
        query = text("DELETE FROM episodes WHERE episode_id = :episode_id RETURNING episode_id")
        result = await self.db_session.execute(query, {"episode_id": episode_id})
        await self.db_session.commit()
        return result.first() is not None

    async def delete_episodes_by_podcast(self, podcast_id: uuid.UUID) -> int:
        query = text("DELETE FROM episodes WHERE podcast_id = :podcast_id RETURNING episode_id")
        result = await self.db_session.execute(query, {"podcast_id": podcast_id})
        await self.db_session.commit()
        return result.rowcount

    async def search_episodes(self, search_term: str) -> Sequence[RowMapping]:
        query = text("""
            SELECT * FROM episodes 
            WHERE title ILIKE :search 
               OR description ILIKE :search
            ORDER BY episode_id
        """)
        result = await self.db_session.execute(query, {"search": f"%{search_term}%"})
        return result.mappings().all()

    async def update_episode_category(self, episode_id: uuid.UUID, category: str) -> RowMapping | None:
        query = text("""
            UPDATE episodes 
            SET category = :category
            WHERE episode_id = :episode_id 
            RETURNING *
        """)
        result = await self.db_session.execute(query, {"episode_id": episode_id, "category": category})
        await self.db_session.commit()
        return result.mappings().first()

    async def update_episodes_categories_batch(self, updates: List[dict]) -> int:
        updated_count = 0
        for update_data in updates:
            result = await self.update_episode_category(
                update_data['episode_id'],
                update_data['category']
            )
            if result:
                updated_count += 1
        return updated_count

    async def get_episodes_without_category(self, limit: int = 100) -> Sequence[RowMapping]:
        query = text("""
            SELECT * FROM episodes 
            WHERE category IS NULL 
            ORDER BY episode_id 
            LIMIT :limit
        """)
        result = await self.db_session.execute(query, {"limit": limit})
        return result.mappings().all()