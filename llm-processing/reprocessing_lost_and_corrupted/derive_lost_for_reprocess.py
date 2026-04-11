# код для приведения файла с потерянными эпизодами к нужной структуре для обработки ллм

import csv
from pathlib import Path

LOST_EPISODES_FILE = Path("lost_episodes_new.csv")
SOURCE_CSV_FILE = Path("../sampled_episodes.csv")
OUTPUT_FILE = Path("../input_csv/lost_episodes_to_reprocess2.csv")

lost_episodes = []

with open(LOST_EPISODES_FILE, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if row and len(row) >= 1:
            episode_id = row[0].strip()
            lost_episodes.append(episode_id)

episodes_data = {}

with open(SOURCE_CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)

    idx_episode_id = header.index("episode_id")
    idx_yandex_id = header.index("yandex_id")
    idx_title = header.index("title")
    idx_description = header.index("description")


    for row in reader:
        if len(row) > max(idx_episode_id, idx_yandex_id, idx_title, idx_description):
            episode_id = row[idx_episode_id].strip()
            yandex_id = row[idx_yandex_id].strip()
            title = row[idx_title].strip()
            description = row[idx_description].strip()

            episodes_data[episode_id] = {
                "yandex_id": yandex_id,
                "title": title,
                "description": description
            }

found_count = 0
not_found_count = 0
not_found_ids = []

with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["episode_id", "yandex_id", "title", "description"])

    for ep_id in lost_episodes:
        if ep_id in episodes_data:
            data = episodes_data[ep_id]
            writer.writerow([
                ep_id,
                data["yandex_id"],
                data["title"],
                data["description"]
            ])
            found_count += 1
        else:
            not_found_count += 1
            not_found_ids.append(ep_id)