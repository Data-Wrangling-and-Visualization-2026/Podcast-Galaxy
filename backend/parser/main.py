import httpx
import asyncio
import random
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_album_ids_from_file(filename: str) -> List[int]:
    ids = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        ids.append(int(line))
                    except ValueError:
                        logger.warning(f"Skipping invalid line: {line}")
        logger.info(f"Loaded {len(ids)} album IDs from {filename}")
    except FileNotFoundError:
        logger.error(f"File {filename} not found.")
    return ids


async def fetch_with_delay(client: httpx.AsyncClient, url: str, delay_between_requests: float) -> Dict[str, Any]:

    jitter = random.uniform(0.8, 1.2)
    actual_delay = delay_between_requests * jitter

    logger.info(f"Waiting {actual_delay:.1f}s before request...")
    await asyncio.sleep(actual_delay)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9',
        'Referer': 'https://music.yandex.ru/',
    }

    resp = await client.get(url, headers=headers)

    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 302:
        logger.error(f"Got captcha (302) for {url}. Need to increase delay between requests.")
        raise Exception("Captcha triggered - need longer delay between requests")
    else:
        resp.raise_for_status()
        return resp.json()


async def import_yandex_album(
        album_id: int,
        base_url: str,
        timeout: float,
        batch_size: int = 50,
        delay_between_requests: float = 2.0
) -> Dict[str, Any]:
    logger.info(f"Starting import of album {album_id} from Yandex Music")

    yandex_url = f"https://api.music.yandex.ru/albums/{album_id}/with-tracks"

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            logger.info(f"Requesting data from {yandex_url}")
            data = await fetch_with_delay(client, yandex_url, delay_between_requests)

            if "result" not in data:
                raise ValueError("Response does not contain 'result' field")

            album_data = data["result"]
            logger.info(f"Received data for album: {album_data.get('title')}")

    except Exception as e:
        logger.error(f"Failed to fetch from Yandex Music: {e}")
        return {
            "status": "error",
            "yandex_album_id": album_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

    podcast_payload = {
        "title": album_data["title"],
        "age_restriction": 18 if album_data.get("contentWarning") == "explicit" else None,
        "likes_count": album_data.get("likesCount", 0),
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

            if podcast_resp.status_code == 409:
                logger.info(f"Podcast already exists, searching by yandex_id...")
                podcast_id = await get_podcast_id_by_yandex_id(base_url, str(album_data["id"]))
                if not podcast_id:
                    raise Exception("Podcast exists but couldn't find ID")
            else:
                podcast_resp.raise_for_status()
                created_podcast = podcast_resp.json()
                podcast_id = created_podcast["podcast_id"]
                logger.info(f"Podcast created with ID: {podcast_id}")
    except Exception as e:
        logger.error(f"Failed to create podcast: {e}")
        return {
            "status": "error",
            "yandex_album_id": album_id,
            "error": f"Podcast creation failed: {e}",
            "timestamp": datetime.now().isoformat()
        }

    all_episodes = []
    volumes = album_data.get("volumes", [])
    total_episodes = sum(len(volume) for volume in volumes)

    for volume in volumes:
        for track in volume:
            episode_payload = {
                "title": track["title"],
                "duration": track.get("durationMs", 0) // 1000,
                "podcast_id": podcast_id,
                "description": track.get("shortDescription") or track.get("description"),
                "category": None,
                "yandex_id": str(track["id"]),
                "pub_date": track.get("pubDate"),
            }
            episode_payload = {k: v for k, v in episode_payload.items() if v is not None}
            all_episodes.append(episode_payload)

    logger.info(f"Collected {len(all_episodes)} episodes for import")

    episodes_created = 0
    episodes_skipped = 0
    episodes_failed = 0

    for i in range(0, len(all_episodes), batch_size):
        batch = all_episodes[i:i + batch_size]
        logger.info(
            f"Sending batch {i // batch_size + 1}/{(len(all_episodes) - 1) // batch_size + 1} ({len(batch)} episodes)")

        try:
            async with httpx.AsyncClient(timeout=timeout * 2) as client:
                batch_resp = await client.post(
                    f"{base_url}/episode/batch",
                    json={"episodes": batch}
                )

                if batch_resp.status_code == 207:
                    result = batch_resp.json()
                    episodes_created += result.get("created", 0)
                    episodes_skipped += result.get("skipped", 0)
                    episodes_failed += result.get("failed", 0)

                    logger.info(f"Batch result: {result.get('created', 0)} created, "
                                f"{result.get('skipped', 0)} skipped, {result.get('failed', 0)} failed")

                elif batch_resp.status_code == 409:
                    episodes_skipped += len(batch)
                    logger.info(f"All {len(batch)} episodes in batch already exist")
                else:
                    logger.warning("Batch endpoint not available, falling back to individual requests")
                    for episode in batch:
                        try:
                            async with httpx.AsyncClient(timeout=timeout) as client:
                                ep_resp = await client.post(
                                    f"{base_url}/episode/",
                                    json=episode
                                )
                                if ep_resp.status_code == 201:
                                    episodes_created += 1
                                elif ep_resp.status_code == 409:
                                    episodes_skipped += 1
                                else:
                                    episodes_failed += 1
                        except Exception:
                            episodes_failed += 1

        except Exception as e:
            logger.error(f"Batch request failed: {e}, falling back to individual requests")
            for episode in batch:
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        ep_resp = await client.post(
                            f"{base_url}/episode/",
                            json=episode
                        )
                        if ep_resp.status_code == 201:
                            episodes_created += 1
                        elif ep_resp.status_code == 409:
                            episodes_skipped += 1
                        else:
                            episodes_failed += 1
                except Exception:
                    episodes_failed += 1

        await asyncio.sleep(0.5)

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


async def get_podcast_id_by_yandex_id(base_url: str, yandex_id: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{base_url}/podcast/",
                params={"yandex_id": yandex_id}
            )
            if resp.status_code == 200:
                podcasts = resp.json()
                if podcasts:
                    return podcasts[0]["podcast_id"]
    except:
        pass
    return None


async def import_multiple_albums(
        album_ids: List[int],
        base_url: str,
        timeout: float = 30.0,
        batch_size: int = 50,
        delay_between_requests: float = 5.0
) -> List[Dict[str, Any]]:
    logger.info(f"Starting batch import of {len(album_ids)} albums (delay {delay_between_requests}s between requests)")

    results = []
    for idx, album_id in enumerate(album_ids, 1):
        result = await import_yandex_album(
            album_id=album_id,
            base_url=base_url,
            timeout=timeout,
            batch_size=batch_size,
            delay_between_requests=delay_between_requests
        )
        results.append(result)

        if result.get("status") == "success":
            logger.info(f"Progress: {idx}/{len(album_ids)} completed successfully")
        else:
            logger.info(f"Progress: {idx}/{len(album_ids)} failed")

        # If we got a captcha, increase delay for future requests
        if "captcha" in result.get("error", "").lower():
            delay_between_requests *= 1.001
            logger.info(f"Captcha detected, increasing delay to {delay_between_requests:.1f}s")

    success_count = sum(1 for r in results if r.get("status") == "success")
    logger.info(f"Batch import completed: {success_count}/{len(album_ids)} successful")

    return results


async def main():
    filename = "album_ids_53_categories_20260320_015824.txt"
    album_ids = read_album_ids_from_file(filename)

    base_url = "http://localhost:8000"
    timeout = 30.0
    batch_size = 50
    delay_between_requests = 2.0

    results = await import_multiple_albums(
        album_ids=album_ids,
        base_url=base_url,
        timeout=timeout,
        batch_size=batch_size,
        delay_between_requests=delay_between_requests
    )

    successful = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "error"]

    print("\n" + "=" * 50)
    print(f"Total albums: {len(album_ids)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    if successful:
        total_episodes = sum(r.get("total_episodes", 0) for r in successful)
        imported_episodes = sum(r.get("episodes_imported", 0) for r in successful)
        print(f"Total episodes across all podcasts: {total_episodes}")
        print(f"Imported episodes: {imported_episodes}")
    if failed:
        print("\nFailed albums:")
        for f in failed:
            print(f"  ID {f['yandex_album_id']}: {f.get('error', 'Unknown error')}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())