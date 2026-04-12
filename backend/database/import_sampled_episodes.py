import asyncio
import csv
import os
import sys
import uuid
from pathlib import Path

import asyncpg


def load_database_url() -> str:
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == "REAL_DATABASE_URL":
                return value.strip()

    database_url = os.environ.get("REAL_DATABASE_URL")
    if database_url:
        return database_url

    raise RuntimeError("REAL_DATABASE_URL not found in backend/database/.env or environment")


def normalize_database_url(database_url: str) -> str:
    prefix = "postgresql+asyncpg://"
    if database_url.startswith(prefix):
        return "postgresql://" + database_url[len(prefix):]
    return database_url


async def import_csv(csv_path: Path) -> None:
    connection = await asyncpg.connect(normalize_database_url(load_database_url()))
    inserted = 0
    skipped = 0
    processed = 0
    progress_step = 5000

    try:
        async with connection.transaction():
            with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    episode_id = uuid.UUID(row["episode_id"])
                    podcast_id = uuid.UUID(row["podcast_id"])
                    yandex_id = (row.get("yandex_id") or "").strip() or None
                    description = row.get("description")
                    description = description if description not in ("", "NULL") else None
                    pub_date = row.get("pub_date")
                    pub_date = pub_date if pub_date not in ("", "NULL") else None

                    result = await connection.fetchval(
                        """
                        INSERT INTO episodes (
                            episode_id,
                            yandex_id,
                            title,
                            description,
                            duration,
                            podcast_id,
                            pub_date
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (episode_id) DO NOTHING
                        RETURNING episode_id
                        """,
                        episode_id,
                        yandex_id,
                        row["title"],
                        description,
                        int(row["duration"]),
                        podcast_id,
                        pub_date,
                    )

                    processed += 1
                    if result is None:
                        skipped += 1
                    else:
                        inserted += 1

                    if processed % progress_step == 0:
                        print(
                            f"Processed: {processed} | Inserted: {inserted} | Skipped: {skipped}",
                            flush=True,
                        )
    finally:
        await connection.close()

    print(f"Processed: {processed}")
    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")


def main() -> None:
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "sampled_episodes.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    asyncio.run(import_csv(csv_path))


if __name__ == "__main__":
    main()
