import asyncio
import uuid
import re
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from settings import settings


class DatabaseCleaner:
    def __init__(self):
        self.engine = create_async_engine(settings.real_database_url, echo=False)
        self.async_session = sessionmaker(
            self    .engine,
            expire_on_commit=False,
            class_=AsyncSession
        )

    def _is_russian_text(self, text: Optional[str]) -> bool:
        if not text or not isinstance(text, str):
            return False

        cleaned_text = re.sub(r'https?://\S+|www\.\S+', '', text)
        cleaned_text = re.sub(r'[^\w\sа-яА-ЯёЁ]', '', cleaned_text)

        if not cleaned_text.strip():
            return False

        russian_chars = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')
        russian_count = sum(1 for char in cleaned_text.lower() if char in russian_chars)
        total_letters = sum(1 for char in cleaned_text if char.isalpha())

        if total_letters == 0:
            return False

        return (russian_count / total_letters) > 0.2

    def _get_year_from_date(self, pub_date) -> Optional[int]:
        if not pub_date:
            return None

        try:
            date_str = str(pub_date)

            year_match = re.search(r'(\d{4})', date_str)
            if year_match:
                return int(year_match.group(1))

            if hasattr(pub_date, 'year'):
                return pub_date.year

        except (ValueError, TypeError, AttributeError):
            pass

        return None

    def _should_delete_episode(self, episode: Dict[str, Any]) -> Tuple[bool, List[str]]:
        title = episode.get('title', '')
        title_cleaned = re.sub(r'[^\w\s]', '', title).strip() if title else ''
        description = episode.get('description', '')
        duration = episode.get('duration')
        pub_date = episode.get('pub_date')

        reasons = []

        if duration is not None and duration < 40:
            reasons.append(f"duration < 40 sec ({duration} sec)")

        year = self._get_year_from_date(pub_date)
        if year is not None and (year < 2015 or year > 2025):
            reasons.append(f"date out of range 2015-2025 ({year})")

        if not description or not description.strip():
            if len(title_cleaned) < 10:
                reasons.append(f"empty description and short title ({len(title_cleaned)} chars)")

        title_is_russian = self._is_russian_text(title)
        desc_is_russian = self._is_russian_text(description)

        if not title_is_russian and not desc_is_russian:
            reasons.append("title and description are not in Russian")

        return len(reasons) > 0, reasons

    async def get_episodes_to_delete_with_details(self, session: AsyncSession, limit: int = 1000) -> List[
        Dict[str, Any]]:
        episodes_to_delete = []

        query = text("""
            SELECT 
                episode_id, 
                title, 
                description, 
                duration,
                pub_date
            FROM episodes 
            WHERE 
                duration < 40
                OR (description IS NULL OR TRIM(description) = '')
                OR (LENGTH(TRIM(title)) < 10)
                OR (pub_date IS NOT NULL AND 
                    (CAST(SUBSTRING(pub_date::text FROM 1 FOR 4) AS INTEGER) < 2015 OR
                     CAST(SUBSTRING(pub_date::text FROM 1 FOR 4) AS INTEGER) > 2025))
            LIMIT :limit
        """)

        result = await session.execute(query, {"limit": limit * 5})
        candidates = result.mappings().all()

        for episode in candidates:
            should_delete, reasons = self._should_delete_episode(dict(episode))
            if should_delete:
                episodes_to_delete.append({
                    'episode_id': episode['episode_id'],
                    'title': episode['title'] or 'No title',
                    'description': episode['description'] or 'No description',
                    'duration': episode['duration'],
                    'pub_date': episode['pub_date'],
                    'reasons': reasons,
                    'title_is_russian': self._is_russian_text(episode['title']),
                    'desc_is_russian': self._is_russian_text(episode['description'])
                })
                if len(episodes_to_delete) >= limit:
                    break

        return episodes_to_delete

    async def get_episodes_to_delete_batch(self, session: AsyncSession, batch_size: int = 10000) -> List[
        Tuple[uuid.UUID, str]]:
        episodes_to_delete = []

        count_query = text("""
            SELECT COUNT(*) as count
            FROM episodes 
            WHERE 
                duration < 40
                OR (description IS NULL OR TRIM(description) = '')
                OR (LENGTH(TRIM(title)) < 10)
                OR (pub_date IS NOT NULL AND 
                    (CAST(SUBSTRING(pub_date::text FROM 1 FOR 4) AS INTEGER) < 2015 OR
                     CAST(SUBSTRING(pub_date::text FROM 1 FOR 4) AS INTEGER) > 2025))
        """)
        result = await session.execute(count_query)
        total_candidates = result.mappings().first()['count']
        print(f"Total candidates to check: {total_candidates:,}")

        offset = 0
        processed = 0
        deleted_candidates = 0

        while True:
            query = text("""
                SELECT 
                    episode_id, 
                    title, 
                    description, 
                    duration,
                    pub_date
                FROM episodes 
                WHERE 
                    duration < 40
                    OR (description IS NULL OR TRIM(description) = '')
                    OR (LENGTH(TRIM(title)) < 10)
                    OR (pub_date IS NOT NULL AND 
                        (CAST(SUBSTRING(pub_date::text FROM 1 FOR 4) AS INTEGER) < 2015 OR
                         CAST(SUBSTRING(pub_date::text FROM 1 FOR 4) AS INTEGER) > 2025))
                LIMIT :limit
                OFFSET :offset
            """)

            result = await session.execute(query, {"limit": batch_size, "offset": offset})
            batch = result.mappings().all()

            if not batch:
                break

            for episode in batch:
                should_delete, _ = self._should_delete_episode(dict(episode))
                if should_delete:
                    episodes_to_delete.append((episode['episode_id'], episode['title']))
                    deleted_candidates += 1

            processed += len(batch)
            print(
                f"Checked {processed:,} of {total_candidates:,} episodes... (found for deletion: {deleted_candidates})")

            offset += batch_size
            await asyncio.sleep(0.1)

        return episodes_to_delete

    async def delete_episodes_batch(self, episode_ids: List[uuid.UUID], batch_size: int = 1000):
        async with self.async_session() as session:
            async with session.begin():
                deleted_count = 0
                total_batches = (len(episode_ids) + batch_size - 1) // batch_size

                for i in range(0, len(episode_ids), batch_size):
                    batch = episode_ids[i:i + batch_size]
                    if batch:
                        batch_str = [str(ep_id) for ep_id in batch]
                        query = text("""
                            DELETE FROM episodes 
                            WHERE episode_id = ANY(:episode_ids)
                            RETURNING episode_id
                        """)
                        result = await session.execute(query, {"episode_ids": batch_str})
                        deleted = result.fetchall()
                        deleted_count += len(deleted)
                        await session.flush()

                        batch_num = i // batch_size + 1
                        print(f"Deleted {len(deleted)} episodes (batch {batch_num}/{total_batches})")

                await session.commit()
                return deleted_count

    async def get_statistics(self, session: AsyncSession) -> dict:
        stats_query = text("""
            SELECT 
                COUNT(*) as total_episodes,
                COUNT(CASE WHEN description IS NULL OR TRIM(description) = '' THEN 1 END) as empty_description,
                COUNT(CASE WHEN LENGTH(TRIM(title)) < 10 THEN 1 END) as short_title,
                COUNT(CASE WHEN duration < 40 THEN 1 END) as short_duration,
                COUNT(CASE 
                    WHEN pub_date IS NOT NULL AND 
                         (CAST(SUBSTRING(pub_date::text FROM 1 FOR 4) AS INTEGER) < 2015 OR
                          CAST(SUBSTRING(pub_date::text FROM 1 FOR 4) AS INTEGER) > 2025)
                    THEN 1 END) as out_of_date_range
            FROM episodes
        """)
        result = await session.execute(stats_query)
        return result.mappings().first()

    async def show_episodes_to_delete(self, session: AsyncSession, limit: int = 1000):
        print("\n" + "=" * 100)
        print(f"FIRST {limit} EPISODES TO DELETE:")
        print("=" * 100)

        episodes = await self.get_episodes_to_delete_with_details(session, limit)

        if not episodes:
            print("No episodes to delete")
            return 0

        for i, ep in enumerate(episodes, 1):
            print(f"\n{i}. id: {ep['episode_id']}")
            print(f"title: {ep['title'][:100]}")
            print(f"duration: {ep['duration']} sec")
            print(f"date: {ep['pub_date']}")
            desc_preview = ep['description'][:150] if len(ep['description']) > 150 else ep['description']
            print(f"description: {desc_preview}")
            print(f"title language: {'RUSSIAN' if ep['title_is_russian'] else 'NOT RUSSIAN'}")
            print(f"description language: {'RUSSIAN' if ep['desc_is_russian'] else 'NOT RUSSIAN'}")
            print(f"deletion reasons:")
            for reason in ep['reasons']:
                print(f"      - {reason}")
            print("-" * 100)

        print(f"\nfound {len(episodes)} of {limit} episodes")
        return len(episodes)

    async def run_cleanup(self, dry_run: bool = True, show_preview: bool = True):
        async with self.async_session() as session:
            async with session.begin():
                print("=" * 80)
                print("STATISTICS BEFORE CLEANUP:")
                stats = await self.get_statistics(session)
                print(f"total episodes: {stats['total_episodes']:,}")
                print(f"empty description: {stats['empty_description']:,}")
                print(f"short title (<10 chars): {stats['short_title']:,}")
                print(f"short duration (<40 sec): {stats['short_duration']:,}")
                print(f"out of date range (2015-2025): {stats['out_of_date_range']:,}")

                print("\n" + "=" * 80)
                print("CHECKING EPISODES FOR DELETION...")

                episodes_to_delete = await self.get_episodes_to_delete_batch(session)

                print("\n" + "=" * 80)
                print(f"FOUND EPISODES TO DELETE: {len(episodes_to_delete):,}")

                if dry_run and show_preview and len(episodes_to_delete) > 0:
                    print("\n" + "=" * 80)
                    print("SHOWING FIRST 1000 EPISODES TO DELETE:")
                    await self.show_episodes_to_delete(session, min(1000, len(episodes_to_delete)))

                if dry_run:
                    print("\n" + "=" * 80)
                    print("DRY RUN MODE: No actual deletion performed")
                    print(f"will delete {len(episodes_to_delete):,} episodes")
                else:
                    if episodes_to_delete:
                        print("\n" + "=" * 80)
                        print("STARTING DELETION...")
                        episode_ids = [ep[0] for ep in episodes_to_delete]
                        deleted_count = await self.delete_episodes_batch(episode_ids)

                        print(f"\nDELETED EPISODES: {deleted_count:,}")

                        stats_after = await self.get_statistics(session)
                        print("\n" + "=" * 80)
                        print("STATISTICS AFTER CLEANUP:")
                        print(f"total episodes: {stats_after['total_episodes']:,}")
                        print(f"empty description: {stats_after['empty_description']:,}")
                        print(f"short title: {stats_after['short_title']:,}")
                        print(f"short duration: {stats_after['short_duration']:,}")

                        print("\n" + "=" * 80)
                        print(f"CLEANUP COMPLETED. Deleted {deleted_count:,} episodes")
                        print(f"remaining episodes: {stats_after['total_episodes']:,}")
                    else:
                        print("no episodes to delete")

        return len(episodes_to_delete) if dry_run else (deleted_count if 'deleted_count' in locals() else 0)

    async def close(self):
        await self.engine.dispose()


async def main():
    cleaner = DatabaseCleaner()
    try:
        print("STARTING DRY RUN...")
        to_delete = await cleaner.run_cleanup(dry_run=True, show_preview=True)

        if to_delete > 0:
            print("\n" + "=" * 80)
            response = input(f"will delete {to_delete:,} episodes. Proceed with actual deletion? (y/n): ")
            if response.lower() == 'y':
                print("\nSTARTING ACTUAL DELETION...")
                await cleaner.run_cleanup(dry_run=False, show_preview=False)
            else:
                print("operation cancelled.")
        else:
            print("\nno episodes to delete.")
    finally:
        await cleaner.close()


if __name__ == "__main__":
    asyncio.run(main())