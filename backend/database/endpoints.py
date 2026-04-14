"""api endpoints for podcasts, episodes, and map-related views."""

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
    # keep local development simple by creating missing tables on startup.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@podcast_router.post("/", response_model=ShowPodcast, status_code=status.HTTP_201_CREATED)
# create a new podcast record.
async def create_podcast(body: PodcastCreate) -> ShowPodcast:
    async with async_session() as session:
        async with session.begin():
            podcast_dal = PodcastDAL(session)

            if body.yandex_id:
                # reject duplicate imports before attempting the insert.
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
# return one podcast by its internal id.
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
# list podcasts with optional pagination or yandex id filtering.
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
# partially update podcast fields.
async def update_podcast(
        podcast_id: uuid.UUID,
        update_data: PodcastUpdate
) -> ShowPodcast:
    async with async_session() as session:
        async with session.begin():
            podcast_dal = PodcastDAL(session)

            # skip unset fields so patch semantics stay partial.
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
# delete a podcast together with its episodes and map data.
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


@episode_router.post("/", response_model=ShowEpisode, status_code=status.HTTP_201_CREATED)
# create a single episode.
async def create_episode(body: EpisodeCreate) -> ShowEpisode:
    async with async_session() as session:
        async with session.begin():
            if body.yandex_id:
                # imports rely on yandex ids being unique across episodes.
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


@episode_router.get("/", response_model=List[ShowEpisode])
# list episodes with optional pagination and podcast filtering.
async def get_episodes(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(20, ge=1, le=500, description="Number of records to return"),
        podcast_id: Optional[uuid.UUID] = Query(None, description="Filter by podcast ID"),
) -> List[ShowEpisode]:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            episodes = await episode_dal.get_episodes(
                skip=skip,
                limit=limit,
                podcast_id=podcast_id,
            )

            return [ShowEpisode(**episode) for episode in episodes]


@episode_router.get("/podcast/{podcast_id}", response_model=List[ShowEpisode])
# return all episodes that belong to one podcast.
async def get_episodes_by_podcast(podcast_id: uuid.UUID) -> List[ShowEpisode]:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            episodes = await episode_dal.get_episodes_by_podcast(podcast_id)

            return [ShowEpisode(**episode) for episode in episodes]


@episode_router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
# delete one episode and its related map point.
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
# delete every episode for a podcast together with map points.
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
# search episodes by title or description.
async def search_episodes(
        q: str = Query(..., min_length=1, description="Search term")
) -> List[ShowEpisode]:
    async with async_session() as session:
        async with session.begin():
            episode_dal = EpisodeDAL(session)
            episodes = await episode_dal.search_episodes(q)

            return [ShowEpisode(**episode) for episode in episodes]


@episode_router.get("/stats/year-topics", response_model=List[YearTopicStats])
# return global counts grouped as year -> topic -> count.
async def get_episode_counts_by_year_and_topic() -> List[YearTopicStats]:
    async with async_session() as session:
        async with session.begin():
            point_dal = EpisodeMapPointDAL(session)
            rows = await point_dal.get_episode_counts_by_year_and_topic()

            # shape flat sql aggregates into a year-first payload for the frontend.
            grouped_rows: dict[int, list[TopicCount]] = {}
            for row in rows:
                grouped_rows.setdefault(row["year"], []).append(
                    TopicCount(topic=row["topic"], count=row["count"])
                )

            return [
                YearTopicStats(year=year, topics=topics)
                for year, topics in grouped_rows.items()
            ]


@episode_router.post("/viewport/year-topics", response_model=List[YearTopicStats])
# return visible map stats grouped as year -> topic -> count.
async def get_episode_counts_in_viewport_by_year_and_topic(body: ViewportRequest) -> List[YearTopicStats]:
    async with async_session() as session:
        async with session.begin():
            point_dal = EpisodeMapPointDAL(session)
            rows = await point_dal.get_episode_counts_in_viewport_by_year_and_topic(
                min_x=body.min_x,
                max_x=body.max_x,
                min_y=body.min_y,
                max_y=body.max_y,
            )

            # keep the viewport endpoint aligned with the global stats shape.
            grouped_rows: dict[int, list[TopicCount]] = {}
            for row in rows:
                grouped_rows.setdefault(row["year"], []).append(
                    TopicCount(topic=row["topic"], count=row["count"])
                )

            return [
                YearTopicStats(year=year, topics=topics)
                for year, topics in grouped_rows.items()
            ]


@episode_router.post("/viewport", response_model=List[ViewportPoint])
# return raw map points inside the requested viewport.
async def get_points_in_viewport(body: ViewportRequest) -> List[ViewportPoint]:
    async with async_session() as session:
        async with session.begin():
            point_dal = EpisodeMapPointDAL(session)
            points = await point_dal.get_points_in_viewport(
                min_x=body.min_x,
                max_x=body.max_x,
                min_y=body.min_y,
                max_y=body.max_y,
                limit=body.limit,
            )

            return [ViewportPoint(**point) for point in points]


@episode_router.post("/viewport/years", response_model=List[ViewportYearGroup])
# return map points grouped by year for timeline rendering.
async def get_points_in_viewport_by_year(body: ViewportRequest) -> List[ViewportYearGroup]:
    async with async_session() as session:
        async with session.begin():
            point_dal = EpisodeMapPointDAL(session)
            points = await point_dal.get_points_in_viewport_grouped_by_year(
                min_x=body.min_x,
                max_x=body.max_x,
                min_y=body.min_y,
                max_y=body.max_y,
            )

            # preserve raw point coordinates while splitting them for a timeline view.
            grouped_points: dict[int, list[ViewportPoint]] = {}
            for point in points:
                year = point["year"]
                grouped_points.setdefault(year, []).append(
                    ViewportPoint(
                        episode_id=point["episode_id"],
                        x=point["x"],
                        y=point["y"],
                        dominant_topic=point["dominant_topic"],
                    )
                )

            return [
                ViewportYearGroup(year=year, episodes=episodes)
                for year, episodes in sorted(grouped_points.items())
            ]


@episode_router.get("/{episode_id}/hover", response_model=EpisodeHoverResponse)
# return hover card data for one episode on the map.
async def get_episode_hover(episode_id: uuid.UUID) -> EpisodeHoverResponse:
    async with async_session() as session:
        async with session.begin():
            point_dal = EpisodeMapPointDAL(session)
            episode = await point_dal.get_hover_details(episode_id)

            if not episode:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Episode with id {episode_id} not found"
                )

            return EpisodeHoverResponse(
                episode_id=episode["episode_id"],
                title=episode["title"],
                description=episode["description"],
                podcast_title=episode["podcast_title"],
                dominant_topic=episode["dominant_topic"],
                top_3_topics=extract_top_topics(episode["topic_scores_json"]),
            )


@episode_router.get("/{episode_id}", response_model=ShowEpisode)
# return one episode by its internal id.
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


@episode_router.post("/batch", status_code=status.HTTP_207_MULTI_STATUS)
# import many episodes in one request and report created, skipped, and failed rows.
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
                    # isolate each insert so one bad row does not poison the whole batch.
                    async with session.begin_nested():
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
