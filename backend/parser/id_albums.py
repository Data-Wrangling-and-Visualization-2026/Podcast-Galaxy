"""collect yandex music album ids for a list of podcast categories."""

import requests
import re
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup


def load_categories_from_file(filename="categories.txt"):
    # read one category slug per line and ignore empty rows.
    categories = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    categories.append(line)
        print(f"Loaded {len(categories)} categories from {filename}")
        return categories
    except FileNotFoundError:
        print(f"File {filename} not found. Please create it with one category per line.")
        return []


def fetch_album_ids_for_categories(category_list):
    if not category_list:
        print("No categories to process.")
        return

    all_album_ids = set()
    session = requests.Session()
    main_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    try:
        # warm up the session to look more like a real browser before category requests.
        session.get('https://music.yandex.ru', headers=main_headers)
        time.sleep(2)
    except Exception as e:
        print(f"Error initializing session: {e}")
        return

    successful_categories = 0
    failed_categories = 0

    for category_slug in category_list:
        print(f"Processing category: {category_slug}")
        url = f"https://music.yandex.ru/non-music/category/{category_slug}/albums"
        category_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://music.yandex.ru/',
        }

        try:
            response = session.get(url, headers=category_headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            ids_found_in_category = 0

            for script in soup.find_all('script'):
                if script.string and 'window.__STATE_SNAPSHOT__' in script.string:
                    text = script.string
                    push_pos = text.find('.push(')
                    if push_pos == -1:
                        continue
                    start = push_pos + 6
                    balance = 0
                    in_string = False
                    escape = False
                    end_pos = -1
                    for i in range(start, len(text)):
                        ch = text[i]
                        if not in_string:
                            if ch == '{':
                                balance += 1
                            elif ch == '}':
                                balance -= 1
                                if balance == 0:
                                    end_pos = i + 1
                                    break
                        if ch == '"' and not escape:
                            in_string = not in_string
                        escape = (ch == '\\' and not escape)

                    if end_pos == -1:
                        continue

                    # extract the embedded state snapshot instead of scraping rendered html.
                    json_str = text[start:end_pos]
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
                    try:
                        albums = data['nonMusic']['albums']['albums']
                        if albums and isinstance(albums, list):
                            for album in albums:
                                if 'id' in album:
                                    all_album_ids.add(album['id'])
                                    ids_found_in_category += 1
                    except KeyError:
                        def find_album_ids(obj):
                            # fallback to a recursive walk when the state shape changes.
                            ids = []
                            if isinstance(obj, dict):
                                if 'id' in obj and isinstance(obj['id'], (int, str)):
                                    if any(key in obj for key in ['type', 'metaType', 'genre', 'trackCount']):
                                        try:
                                            ids.append(int(obj['id']))
                                        except:
                                            pass
                                for value in obj.values():
                                    if isinstance(value, (dict, list)):
                                        ids.extend(find_album_ids(value))
                            elif isinstance(obj, list):
                                for item in obj:
                                    ids.extend(find_album_ids(item))
                            return ids

                        found_ids = find_album_ids(data)
                        for aid in found_ids:
                            all_album_ids.add(aid)
                            ids_found_in_category += 1

            if ids_found_in_category > 0:
                print(f"Found {ids_found_in_category} IDs in this category.")
                successful_categories += 1
            else:
                print(f"No IDs found in this category.")
                failed_categories += 1

        except requests.exceptions.RequestException as e:
            print(f"Error fetching category {category_slug}: {e}")
            failed_categories += 1
        except Exception as e:
            print(f"An unexpected error occurred for {category_slug}: {e}")
            failed_categories += 1

    if not all_album_ids:
        print("No album IDs were found for any of the provided categories.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"album_ids_{len(category_list)}_categories_{timestamp}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        # write sorted ids so repeated runs stay easy to diff.
        for album_id in sorted(all_album_ids):
            f.write(f"{album_id}\n")

    print(f"Success! Total unique album IDs collected: {len(all_album_ids)}")
    print(f"IDs saved to: {filename}")
    print(f"Categories processed: {successful_categories} successful, {failed_categories} failed")


if __name__ == "__main__":
    categories = load_categories_from_file("categories.txt")
    fetch_album_ids_for_categories(categories)
