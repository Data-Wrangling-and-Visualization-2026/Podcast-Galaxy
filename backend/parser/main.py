import httpx
import asyncio
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def import_yandex_album(
        album_id: int,
        base_url: str,
        timeout: float
) -> Dict[str, Any]:
    logger.info(f"Starting import of album {album_id} from Yandex Music")

    yandex_url = f"https://api.music.yandex.ru/albums/{album_id}/with-tracks"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"Requesting data from {yandex_url}")
            resp = await client.get(yandex_url)
            resp.raise_for_status()
            data = resp.json()

            if "result" not in data:
                raise ValueError("Response does not contain 'result' field")

            album_data = data["result"]
            logger.info(f"Received data for album: {album_data.get('title')}")

    except httpx.TimeoutException:
        logger.error(f"Timeout when requesting Yandex Music for album {album_id}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} when requesting Yandex Music")
        raise
    except Exception as e:
        logger.error(f"Unexpected error when requesting Yandex Music: {e}")
        raise

    podcast_payload = {
        "title": album_data["title"],
        "description": None,
        "age_restriction": 18 if album_data.get("contentWarning") == "explicit" else None,
        "likes_count": album_data.get("likesCount", 0),
        "category": album_data.get("genre"),
        "yandex_id": str(album_data["id"]),
        "track_count": album_data.get("trackCount"),
    }

    podcast_payload = {k: v for k, v in podcast_payload.items() if v is not None}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"Creating podcast: {podcast_payload['title']}")
            podcast_resp = await client.post(
                f"{base_url}/podcast/",
                json=podcast_payload
            )
            podcast_resp.raise_for_status()
            created_podcast = podcast_resp.json()
            podcast_id = created_podcast["podcast_id"]
            logger.info(f"Podcast created with ID: {podcast_id}")
    except Exception as e:
        logger.error(f"Failed to create podcast: {e}")
        raise

    episodes_created = 0
    episodes_failed = 0
    episodes_skipped = 0

    volumes = album_data.get("volumes", [])
    total_episodes = sum(len(volume) for volume in volumes)

    logger.info(f"Starting import of {total_episodes} episodes")

    for volume_idx, volume in enumerate(volumes):
        for track_idx, track in enumerate(volume):
            try:
                episode_payload = {
                    "title": track["title"],
                    "duration": track.get("durationMs", 0) // 1000,  # convert to seconds
                    "podcast_id": podcast_id,
                    "description": track.get("shortDescription") or track.get("description"),
                    "category": None,
                    "yandex_id": str(track["id"]),
                    "pub_date": track.get("pubDate"),
                }

                episode_payload = {k: v for k, v in episode_payload.items() if v is not None}

                async with httpx.AsyncClient(timeout=timeout) as client:
                    ep_resp = await client.post(
                        f"{base_url}/episode/",
                        json=episode_payload
                    )

                    if ep_resp.status_code == 201:
                        episodes_created += 1
                        if episodes_created % 10 == 0:
                            logger.info(f"Imported {episodes_created}/{total_episodes} episodes")
                    elif ep_resp.status_code == 409:
                        episodes_skipped += 1
                    else:
                        episodes_failed += 1
                        logger.warning(f"Failed to import episode {track['title']}: {ep_resp.status_code}")

            except Exception as e:
                episodes_failed += 1
                logger.error(f"Error importing episode {track.get('title', 'Unknown')}: {e}")

    result = {
        "status": "success",
        "podcast_id": str(podcast_id),
        "podcast_title": album_data["title"],
        "total_episodes": total_episodes,
        "episodes_imported": episodes_created,
        "episodes_skipped": episodes_skipped,
        "episodes_failed": episodes_failed,
        "yandex_album_id": album_id,
        "timestamp": datetime.now().isoformat()
    }

    logger.info(f"Import completed: {episodes_created}/{total_episodes} episodes imported")
    return result


async def import_multiple_albums(
        album_ids: List[int],
        base_url: str,
        timeout: float = 30.0,
        max_concurrent: int = 3
) -> List[Dict[str, Any]]:
    logger.info(f"Starting batch import of {len(album_ids)} albums")

    semaphore = asyncio.Semaphore(max_concurrent)

    async def import_with_semaphore(album_id: int) -> Dict[str, Any]:
        async with semaphore:
            try:
                return await import_yandex_album(
                    album_id=album_id,
                    base_url=base_url,
                    timeout=timeout
                )
            except Exception as e:
                logger.error(f"Failed to import album {album_id}: {e}")
                return {
                    "status": "error",
                    "yandex_album_id": album_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

    tasks = [import_with_semaphore(album_id) for album_id in album_ids]
    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r.get("status") == "success")
    logger.info(f"Batch import completed: {success_count}/{len(album_ids)} successful")

    return results


async def get_album_info(album_id: int) -> Dict[str, Any]:
    yandex_url = f"https://api.music.yandex.ru/albums/{album_id}/with-tracks"

    async with httpx.AsyncClient() as client:
        resp = await client.get(yandex_url)
        resp.raise_for_status()
        data = resp.json()

        if "result" not in data:
            raise ValueError("Response does not contain 'result' field")

        album_data = data["result"]

        return {
            "id": album_data["id"],
            "title": album_data["title"],
            "artist": album_data.get("artists", [{}])[0].get("name") if album_data.get("artists") else None,
            "track_count": album_data.get("trackCount"),
            "genre": album_data.get("genre"),
            "likes_count": album_data.get("likesCount"),
            "content_warning": album_data.get("contentWarning"),
            "available": album_data.get("available", True)
        }


async def main():
    try:
        result = await import_yandex_album(
            album_id=24956069,
            base_url="http://localhost:8000",
            timeout=30.0
        )
        print(f"Import result: {result}")
    except Exception as e:
        print(f"Import failed: {e}")

    try:
        info = await get_album_info(24956069)
        print(f"Album info: {info}")
    except Exception as e:
        print(f"Failed to get album info: {e}")


if __name__ == "__main__":
    asyncio.run(main())