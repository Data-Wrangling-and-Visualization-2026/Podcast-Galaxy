# чистим файл с конечными данными от ллм: убираем дубликаты, нормализуем проценты, если они не нормализованы, убираем corrupted данные

import csv
from pathlib import Path

CLASSIFIED_FILE = Path("all_classified.csv")
SOURCE_CSV_FILE = Path("../sampled_episodes.csv")
OUTPUT_CLEAN_FILE = Path("all_classified_clean.csv")
INVALID_FILE = Path("invalid_classified.csv")
DUPLICATES_FILE = Path("duplicates_removed.csv")
NORMALIZED_LOG_FILE = Path("normalized_sum.csv")

# нормализуем список оценок так, чтобы их сумма стала равна 100
def normalize_scores(scores):
    old_sum = sum(scores)
    if old_sum == 100:
        return scores, False, old_sum

    if old_sum == 0:
        new_scores = [int(100 / 22) for _ in range(22)]
        remainder = 100 - sum(new_scores)
        for i in range(remainder):
            new_scores[i] += 1
        return new_scores, True, old_sum

    new_scores = [round(s * 100 / old_sum) for s in scores]

    diff = 100 - sum(new_scores)
    if diff != 0:
        indices = sorted(range(len(new_scores)), key=lambda i: new_scores[i], reverse=True)
        for i in indices[:abs(diff)]:
            if diff > 0:
                new_scores[i] += 1
            else:
                new_scores[i] -= 1

    return new_scores, True, old_sum

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
            episodes_data[episode_id] = {
                "yandex_id": row[idx_yandex_id].strip(),
                "title": row[idx_title].strip(),
                "description": row[idx_description].strip()
            }


valid_lines = []  # (episode_id, full_line)
invalid_episodes = []  # (episode_id, yandex_id, title, description, reason)
duplicates_removed = []  # (episode_id, full_line)
normalized_log = []  # (episode_id, old_sum, old_scores, new_scores)
seen_ids = set()

with open(CLASSIFIED_FILE, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    classified_header = next(reader)  # заголовок

    headers = ["episode_id", "politics", "science", "tech", "entertainment", "art", "education",
                       "tourism", "economics", "law", "ecology", "style", "BBC", "sports", "psychology",
                       "religion", "architecture", "medicine", "business", "food", "history", "relationship", "family"]


    for row_num, row in enumerate(reader, 2):
        if not row or len(row) == 0:
            continue

        episode_id = row[0].strip() if len(row) > 0 else ""

        if not episode_id:
            continue

        # проверка на дубликат
        if episode_id in seen_ids:
            duplicates_removed.append([episode_id] + row)
            continue

        # проверка формата: должно быть ровно 23 колонки
        if len(row) != 23:
            invalid_episodes.append([episode_id, "", "", "", f"Неверное кол-во колонок: {len(row)} (должно быть 23)"])
            continue

        # проверка, что все категории — числа
        try:
            scores = [int(x) for x in row[1:23]]
        except ValueError:
            invalid_episodes.append([episode_id, "", "", "", f"Категории не являются числами"])
            continue

        # проверка диапазона 0-100 (до нормализации)
        if any(s < 0 or s > 100 for s in scores):
            invalid_episodes.append([episode_id, "", "", "", f"Значения вне диапазона 0-100"])
            continue

        new_scores, was_normalized, old_sum = normalize_scores(scores)

        if was_normalized:
            normalized_log.append([episode_id, old_sum, scores, new_scores])
            row = [row[0]] + new_scores

        valid_lines.append((episode_id, row))
        seen_ids.add(episode_id)

with open(OUTPUT_CLEAN_FILE, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    for episode_id, row in valid_lines:
        writer.writerow(row)

if duplicates_removed:
    with open(DUPLICATES_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["episode_id", "politics", "science", "tech", "entertainment", "art", "education",
                         "tourism", "economics", "law", "ecology", "style", "BBC", "sports", "psychology",
                         "religion", "architecture", "medicine", "business", "food", "history", "relationship",
                         "family"])
        for row in duplicates_removed:
            writer.writerow(row)

if normalized_log:
    with open(NORMALIZED_LOG_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["episode_id", "old_sum", "old_scores", "new_scores"])
        for item in normalized_log:
            episode_id, old_sum, old_scores, new_scores = item
            writer.writerow([episode_id, old_sum, str(old_scores), str(new_scores)])
