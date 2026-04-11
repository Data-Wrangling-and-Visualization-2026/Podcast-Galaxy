# скрипт помогающий привести файл с пропущенными/неверно определенными эпизодами в файл с нужной структурой для повторного анализа вручную через ллм

import csv
from pathlib import Path

INPUT_FILE = Path("invalid_classified.csv")
OUTPUT_FILE = Path("invalid_classified_clean.csv")

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

idx_episode_id = header.index("episode_id")
idx_title = header.index("title")
idx_description = header.index("description")

with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["episode_id", "title", "description"])

    for row in rows:
        if len(row) > max(idx_episode_id, idx_title, idx_description):
            writer.writerow([
                row[idx_episode_id],
                row[idx_title],
                row[idx_description]
            ])
