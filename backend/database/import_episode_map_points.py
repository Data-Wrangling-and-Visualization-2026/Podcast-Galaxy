import asyncio
import csv
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from settings import settings


KNOWN_COLUMNS = {
    "episode_id",
    "umap_x",
    "umap_y",
    "dominant_topic",
    "dominant_weight",
}


def build_topic_scores(row: dict[str, str]) -> str:
    topic_scores: dict[str, float] = {}
    for key, value in row.items():
        if key in KNOWN_COLUMNS:
            continue
        try:
            topic_scores[key] = float(value or 0)
        except ValueError:
            topic_scores[key] = 0.0
    return json.dumps(topic_scores, ensure_ascii=False)


async def import_csv(csv_path: Path) -> None:
    engine = create_async_engine(settings.real_database_url, future=True, echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    inserted = 0

    async with async_session() as session:
        async with session.begin():
            with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    episode_id = uuid.UUID(row["episode_id"])
                    topic_scores_json = build_topic_scores(row)

                    await session.execute(
                        text("""
                            INSERT INTO episode_map_points (
                                episode_id,
                                umap_x,
                                umap_y,
                                dominant_topic,
                                dominant_weight,
                                topic_scores_json
                            )
                            VALUES (
                                :episode_id,
                                :umap_x,
                                :umap_y,
                                :dominant_topic,
                                :dominant_weight,
                                :topic_scores_json
                            )
                            ON CONFLICT (episode_id) DO UPDATE
                            SET umap_x = EXCLUDED.umap_x,
                                umap_y = EXCLUDED.umap_y,
                                dominant_topic = EXCLUDED.dominant_topic,
                                dominant_weight = EXCLUDED.dominant_weight,
                                topic_scores_json = EXCLUDED.topic_scores_json
                        """),
                        {
                            "episode_id": episode_id,
                            "umap_x": float(row["umap_x"]),
                            "umap_y": float(row["umap_y"]),
                            "dominant_topic": row["dominant_topic"],
                            "dominant_weight": float(row["dominant_weight"] or 0),
                            "topic_scores_json": topic_scores_json,
                        },
                    )
                    inserted += 1

        await session.commit()

    await engine.dispose()
    print(f"Imported {inserted} rows from {csv_path}")


def main() -> None:
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "podcast_umap_2d_results.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    asyncio.run(import_csv(csv_path))


if __name__ == "__main__":
    main()
