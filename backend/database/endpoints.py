from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from database.settings import settings
from database.DAL import *
from database.APImodels import *
from database.table import Base
from typing import List, Optional
import uuid

engine = create_async_engine(settings.real_database_url, future=True, echo=True)

async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

app = FastAPI(title="Podcast App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

podcast_router = APIRouter()
episode_router = APIRouter()


@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@podcast_router.post("/", response_model=ShowPodcast, status_code=status.HTTP_201_CREATED)
async def create_podcast(body: PodcastCreate) -> ShowPodcast:
    async with async_session() as session:
        async with session.begin():
            podcast_dal = PodcastDAL(session)

            if body.yandex_id:
                existing = await session.execute(
                    text("SELECT * FROM podcasts WHERE yandex_id = :yandex_id"),
                    {"yandex_id": body.yandex_id}
                )
                existing_podcast = existing.mappings().first()
                if existing_podcast:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Podcast with yandex_id {body.yandex_id} already exists"
                    )

            podcast = await podcast_dal.create_podcast(body)

            podcast_dict = model_to_dict(podcast)
            return ShowPodcast(**podcast_dict)


@podcast_router.get("/{podcast_id}", response_model=ShowPodcast)
async def get_podcast_by_id(podcast_id: uuid.UUID) -> ShowPodcast:
    async with async_session() as session:
        async with session.begin():
            podcast_dal = PodcastDAL(session)
            podcast = await podcast_dal.get_podcast_by_id(podcast_id)

            if not podcast:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Podcast with id {podcast_id} not found"
                )

            return ShowPodcast(**podcast)


@podcast_router.get("/", response_model=List[ShowPodcast])
async def get_podcasts(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
        yandex_id: Optional[str] = Query(None, description="Filter by Yandex ID")
) -> List[ShowPodcast]:
    async with async_session() as session:
        async with session.begin():
            if yandex_id:
                query = text("""
                    SELECT * FROM podcasts 
                    WHERE yandex_id = :yandex_id
                """)
                result = await session.execute(query, {"yandex_id": yandex_id})
                podcast = result.mappings().first()
                return [ShowPodcast(**podcast)] if podcast else []
            else:
                podcast_dal = PodcastDAL(session)
                podcasts = await podcast_dal.get_podcasts_from_n(skip, limit)
                return [ShowPodcast(**podcast) for podcast in podcasts]


@podcast_router.patch("/{podcast_id}", response_model=ShowPodcast)
async def update_podcast(
        podcast_id: uuid.UUID,
        update_data: PodcastUpdate
) -> ShowPodcast:
    async with async_session() as session:
        async with session.begin():
            podcast_dal = PodcastDAL(session)

            update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}

            if not update_dict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid fields to update"
                )

            updated_podcast = await podcast_dal.update_podcast(podcast_id, update_dict)

            if not updated_podcast:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Podcast with id {podcast_id} not found"
                )

            return ShowPodcast(**updated_podcast)


@podcast_router.delete("/{podcast_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_podcast(podcast_id: uuid.UUID):
    async with async_session() as session:
        async with session.begin():
            podcast_dal = PodcastDAL(session)
            deleted = await podcast_dal.delete_podcast(podcast_id)

            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Podcast with id {podcast_id} not found"
                )

            return None


@podcast_router.patch("/{podcast_id}/category", response_model=ShowPodcast)
async def update_podcast_category(
        podcast_id: uuid.UUID,
        category_update: PodcastCategoryUpdate
) -> ShowPodcast:
    async with async_session() as session:
        async with session.begin():
            podcast_dal = PodcastDAL(session)
            updated_podcast = await podcast_dal.update_podcast_category(
                podcast_id,
                category_update.category
            )

            if not updated_podcast:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Podcast with id {podcast_id} not found"
                )

            return ShowPodcast(**updated_podcast)


@episode_router.post("/", response_model=ShowEpisode, status_code=status.HTTP_201_CREATED)
async def create_episode(body: EpisodeCreate) -> ShowEpisode:
    async with async_session() as session:
        async with session.begin():
            if body.yandex_id:
                existing = await session.execute(
                    text("SELECT episode_id FROM episodes WHERE yandex_id = :yandex_id"),
                    {"yandex_id": body.yandex_id}
                )
                if existing.first():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Episode with yandex_id {body.yandex_id} already exists"
                    )

            episode_dal = EpisodeDAL(session)
            episode = await episode_dal.create_episode(body)

            episode_dict = model_to_dict(episode)
            return ShowEpisode(**episode_dict)


@episode_router.get("/{episode_id}", response_model=ShowEpisode)
async def get_episode_by_id(episode_id: uuid.UUID) -> ShowEpisode:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            episode = await episode_dal.get_episode_by_id(episode_id)

            if not episode:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Episode with id {episode_id} not found"
                )

            return ShowEpisode(**episode)


@episode_router.get("/podcast/{podcast_id}", response_model=List[ShowEpisode])
async def get_episodes_by_podcast(podcast_id: uuid.UUID) -> List[ShowEpisode]:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            episodes = await episode_dal.get_episodes_by_podcast(podcast_id)

            return [ShowEpisode(**episode) for episode in episodes]


@episode_router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(episode_id: uuid.UUID):
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            deleted = await episode_dal.delete_episode(episode_id)

            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Episode with id {episode_id} not found"
                )

            return None


@episode_router.delete("/podcast/{podcast_id}/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_podcast_episodes(podcast_id: uuid.UUID):
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            deleted_count = await episode_dal.delete_episodes_by_podcast(podcast_id)

            if deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No episodes found for podcast with id {podcast_id}"
                )

            return None


@episode_router.get("/search/", response_model=List[ShowEpisode])
async def search_episodes(
        q: str = Query(..., min_length=1, description="Search term")
) -> List[ShowEpisode]:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            episodes = await episode_dal.search_episodes(q)

            return [ShowEpisode(**episode) for episode in episodes]


@episode_router.patch("/{episode_id}/category", response_model=ShowEpisode)
async def update_episode_category(
        episode_id: uuid.UUID,
        category_update: EpisodeCategoryUpdate
) -> ShowEpisode:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            updated_episode = await episode_dal.update_episode_category(
                episode_id,
                category_update.category
            )

            if not updated_episode:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Episode with id {episode_id} not found"
                )

            return ShowEpisode(**updated_episode)


@episode_router.post("/categories/batch-update", response_model=dict)
async def batch_update_episode_categories(batch_update: EpisodeCategoryBatchUpdate) -> dict:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            updates_list = [update.model_dump() for update in batch_update.updates]
            updated_count = await episode_dal.update_episodes_categories_batch(updates_list)

            return {
                "total": len(batch_update.updates),
                "updated": updated_count,
                "message": f"Successfully updated {updated_count} out of {len(batch_update.updates)} episodes"
            }


@episode_router.get("/uncategorized/", response_model=List[ShowEpisode])
async def get_uncategorized_episodes(
        limit: int = Query(100, ge=1, le=500, description="Maximum number of episodes to return")
) -> List[ShowEpisode]:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            episodes = await episode_dal.get_episodes_without_category(limit)

            return [ShowEpisode(**episode) for episode in episodes]


@episode_router.post("/batch", status_code=status.HTTP_207_MULTI_STATUS)
async def create_episodes_batch(batch: BatchEpisodeCreate):
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)

            results = {
                "created": 0,
                "skipped": 0,
                "failed": 0,
                "details": []
            }

            for episode_data in batch.episodes:
                try:
                    existing = await session.execute(
                        text("SELECT episode_id FROM episodes WHERE yandex_id = :yandex_id"),
                        {"yandex_id": episode_data.yandex_id}
                    )

                    if existing.first():
                        results["skipped"] += 1
                        results["details"].append({
                            "yandex_id": episode_data.yandex_id,
                            "status": "skipped",
                            "reason": "already_exists"
                        })
                        continue

                    episode = await episode_dal.create_episode(episode_data)
                    results["created"] += 1
                    results["details"].append({
                        "yandex_id": episode_data.yandex_id,
                        "episode_id": str(episode.episode_id),
                        "status": "created"
                    })

                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "yandex_id": episode_data.yandex_id,
                        "status": "failed",
                        "reason": str(e)
                    })

            return results


main_api_router = APIRouter()

main_api_router.include_router(podcast_router, prefix="/podcast", tags=["podcast"])
main_api_router.include_router(episode_router, prefix="/episode", tags=["episode"])
app.include_router(main_api_router)