from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import RowMapping
from sqlalchemy import text, Sequence
from sqlalchemy.orm import class_mapper
from database.table import Podcast, Episode
from database.APImodels import PodcastCreate, EpisodeCreate
import uuid
from typing import List, Optional


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
        delete_map_points_query = text("""
            DELETE FROM episode_map_points
            WHERE episode_id IN (
                SELECT episode_id FROM episodes WHERE podcast_id = :podcast_id
            )
        """)
        await self.db_session.execute(delete_map_points_query, {"podcast_id": podcast_id})

        delete_episodes_query = text("DELETE FROM episodes WHERE podcast_id = :podcast_id")
        await self.db_session.execute(delete_episodes_query, {"podcast_id": podcast_id})

        delete_podcast_query = text("DELETE FROM podcasts WHERE podcast_id = :podcast_id RETURNING podcast_id")
        result = await self.db_session.execute(delete_podcast_query, {"podcast_id": podcast_id})
        await self.db_session.commit()
        return result.first() is not None

class EpisodeDAL:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_episode(self, episode_data: EpisodeCreate) -> Episode:
        episode_dict = episode_data.model_dump()

        new_episode = Episode(**episode_dict)
        self.db_session.add(new_episode)
        await self.db_session.flush()
        return new_episode

    async def get_episodes(
        self,
        skip: int = 0,
        limit: int = 20,
        podcast_id: Optional[uuid.UUID] = None,
    ) -> Sequence[RowMapping]:
        conditions = []
        params = {"skip": skip, "limit": limit}

        if podcast_id is not None:
            conditions.append("podcast_id = :podcast_id")
            params["podcast_id"] = podcast_id

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = text(f"""
            SELECT * FROM episodes
            {where_clause}
            ORDER BY pub_date DESC NULLS LAST, episode_id
            OFFSET :skip
            LIMIT :limit
        """)
        result = await self.db_session.execute(query, params)
        return result.mappings().all()

    async def get_episode_by_id(self, episode_id: uuid.UUID) -> RowMapping | None:
        query = text("SELECT * FROM episodes WHERE episode_id = :episode_id")
        result = await self.db_session.execute(query, {"episode_id": episode_id})
        return result.mappings().first()

    async def get_episodes_by_podcast(self, podcast_id: uuid.UUID) -> Sequence[RowMapping]:
        query = text("SELECT * FROM episodes WHERE podcast_id = :podcast_id ORDER BY episode_id")
        result = await self.db_session.execute(query, {"podcast_id": podcast_id})
        return result.mappings().all()

    async def delete_episode(self, episode_id: uuid.UUID) -> bool:
        delete_map_point_query = text("DELETE FROM episode_map_points WHERE episode_id = :episode_id")
        await self.db_session.execute(delete_map_point_query, {"episode_id": episode_id})

        query = text("DELETE FROM episodes WHERE episode_id = :episode_id RETURNING episode_id")
        result = await self.db_session.execute(query, {"episode_id": episode_id})
        await self.db_session.commit()
        return result.first() is not None

    async def delete_episodes_by_podcast(self, podcast_id: uuid.UUID) -> int:
        delete_map_points_query = text("""
            DELETE FROM episode_map_points
            WHERE episode_id IN (
                SELECT episode_id FROM episodes WHERE podcast_id = :podcast_id
            )
        """)
        await self.db_session.execute(delete_map_points_query, {"podcast_id": podcast_id})

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


class EpisodeMapPointDAL:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_points_in_viewport(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        limit: int = 5000,
    ) -> Sequence[RowMapping]:
        query = text("""
            SELECT
                episode_id,
                umap_x AS x,
                umap_y AS y,
                dominant_topic
            FROM episode_map_points
            WHERE umap_x BETWEEN :min_x AND :max_x
              AND umap_y BETWEEN :min_y AND :max_y
            ORDER BY episode_id
            LIMIT :limit
        """)
        result = await self.db_session.execute(
            query,
            {
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
                "limit": limit,
            },
        )
        return result.mappings().all()

    async def get_points_in_viewport_grouped_by_year(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
    ) -> Sequence[RowMapping]:
        query = text("""
            SELECT
                emp.episode_id,
                emp.umap_x AS x,
                emp.umap_y AS y,
                emp.dominant_topic,
                CAST(SUBSTRING(e.pub_date FROM '(\d{4})') AS INTEGER) AS year
            FROM episode_map_points emp
            INNER JOIN episodes e ON e.episode_id = emp.episode_id
            WHERE emp.umap_x BETWEEN :min_x AND :max_x
              AND emp.umap_y BETWEEN :min_y AND :max_y
              AND SUBSTRING(e.pub_date FROM '(\d{4})') IS NOT NULL
            ORDER BY year, emp.episode_id
        """)
        result = await self.db_session.execute(
            query,
            {
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
            },
        )
        return result.mappings().all()

    async def get_hover_details(self, episode_id: uuid.UUID) -> RowMapping | None:
        query = text("""
            SELECT
                e.episode_id,
                e.title,
                e.description,
                p.title AS podcast_title,
                emp.dominant_topic,
                emp.topic_scores_json
            FROM episodes e
            INNER JOIN podcasts p ON p.podcast_id = e.podcast_id
            LEFT JOIN episode_map_points emp ON emp.episode_id = e.episode_id
            WHERE e.episode_id = :episode_id
        """)
        result = await self.db_session.execute(query, {"episode_id": episode_id})
        return result.mappings().first()
