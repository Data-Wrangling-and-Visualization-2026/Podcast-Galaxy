# код для повторного прогона утерянных в первый раз данных через ллм

from openai import OpenAI
import csv
from pathlib import Path
import json
from datetime import datetime
import math
import time
import re
import httpx

API_KEY = API_KEY_DEEPSEEK
INPUT_DIR = Path("../input_csv")
OUTPUT_FILE = Path("../clean_ready_data/all_classified.csv")
PROGRESS_FILE = Path("progress_lost.json")
LOST_EPISODES_FILE = Path("lost_episodes_new.csv")

# проверенные на тестах оптимальные настройки для размера входящего запроса и настроек для ответа ллм
EPISODES_PER_CHUNK = 59
MAX_TOKENS = 8000
TEMPERATURE = 0.1
DELAY_BETWEEN_CHUNKS = 1

# промпт для ллм
SYSTEM_PROMPT = """Ты — эксперт по семантической классификации подкастов.

Твоя задача — классифицировать эпизоды строго по 22 категориям.

Входной формат: CSV с колонками episode_id, title, description

Категории (строго в этом порядке):
1. politics
2. science
3. tech
4. entertainment
5. art
6. education
7. tourism
8. economics
9. law
10. ecology
11. style
12. BBC
13. sports
14. psychology
15. religion
16. architecture
17. medicine 
18. business 
19. food 
20. history
21. relationship 
22. family 

ПРАВИЛА (ОБЯЗАТЕЛЬНЫ К ВЫПОЛНЕНИЮ):

1. Для КАЖДОГО эпизода сумма процентов по всем 22 категориям должна быть РОВНО 100.
2. Если эпизод полностью относится к одной категории — ставь 100 в неё и 0 в остальные.
3. Если эпизод относится к нескольким — распределяй проценты пропорционально важности.
4. Используй ТОЛЬКО латиницу и цифры. ЗАПРЕЩЕНЫ русские, китайские и другие символы.
5. ЗАПРЕЩЕНЫ пояснения, комментарии, текст "вот результат", "конец" — ТОЛЬКО CSV.
6. Каждая категория — целое число от 0 до 100.

Формат ответа (первая строка — заголовок):
episode_id,politics,science,tech,entertainment,art,education,tourism,economics,law,ecology,style,BBC,sports,psychology,religion,architecture,medicine,business,food,history,relationship,family

ПРИМЕР правильного ответа (НЕ копируй эти цифры, только формат!):
12e03d57-3d51-4c92-9fb9-1bf35fd0a70f,0,0,0,95,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0,0,0,0

Проверь себя: сумма должна быть 100.

Отвечай ТОЛЬКО CSV. Без пояснений. Без markdown. Без китайских символов."""

# вспомогательные функции
def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_chunks": [], "total_episodes": 0, "lost_episodes": []}


def save_progress(processed_chunks, total_episodes, lost_episodes):
    progress = {
        "processed_chunks": processed_chunks,
        "total_episodes": total_episodes,
        "lost_episodes": lost_episodes,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def save_lost_episodes(lost_episodes):
    if not lost_episodes:
        return
    header = ["episode_id", "title", "description", "source_file"]
    with open(LOST_EPISODES_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(lost_episodes)


def split_csv(file_path, episodes_per_chunk):
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    total = len(rows)
    num_chunks = math.ceil(total / episodes_per_chunk)

    chunks = []
    for i in range(num_chunks):
        start = i * episodes_per_chunk
        end = min(start + episodes_per_chunk, total)
        chunk_rows = rows[start:end]
        chunks.append({
            "rows": chunk_rows,
            "start": start + 1,
            "end": end
        })

    return header, chunks, total, rows


def chunk_to_csv_string(header, chunk_rows):
    csv_string = ','.join(header) + '\n'
    for row in chunk_rows:
        escaped_row = []
        for cell in row:
            if not cell:
                escaped_row.append('')
            elif ',' in cell or '\n' in cell or '"' in cell:
                cell = cell.replace('"', '""')
                escaped_row.append(f'"{cell}"')
            else:
                escaped_row.append(cell)
        csv_string += ','.join(escaped_row) + '\n'
    return csv_string


def validate_classification_line(line, episode_id):
    if re.search(r'[\u4e00-\u9fff]', line):
        return False, "китайские символы"

    parts = line.strip().split(',')

    if len(parts) != 23:
        return False, f"неверное кол-во колонок: {len(parts)}"

    if parts[0] != episode_id:
        return False, f"неверный ID: {parts[0]}"

    try:
        scores = [int(x) for x in parts[1:]]
    except ValueError:
        return False, "категории не числа"

    if sum(scores) != 100:
        return False, f"сумма {sum(scores)} != 100"

    if any(s < 0 or s > 100 for s in scores):
        return False, "значения вне диапазона 0-100"

    return True, "OK"


def classify_chunk(client, chunk_csv, num_episodes, original_rows, source_file):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # ← используем chat
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chunk_csv}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )

        result = response.choices[0].message.content
        usage = response.usage

        lines = result.strip().split('\n')

        if lines and "episode_id" in lines[0].lower():
            data_lines = lines[1:]
        else:
            data_lines = lines

        valid_lines = []
        lost = []

        for i, line in enumerate(data_lines):
            if i >= len(original_rows):
                break

            original_row = original_rows[i]
            ep_id = original_row[0]

            is_valid, reason = validate_classification_line(line, ep_id)

            if is_valid:
                valid_lines.append(line)
            else:
                lost.append([ep_id, original_row[1], original_row[2], source_file])
                print(f"Потерян {ep_id}: {reason}")

        returned_ids = set()
        for line in valid_lines:
            returned_ids.add(line.split(',')[0])

        for row in original_rows:
            ep_id = row[0]
            if ep_id not in returned_ids:
                if [ep_id, row[1], row[2], source_file] not in lost:
                    lost.append([ep_id, row[1], row[2], source_file])

        return {
            "success": True,
            "data_lines": valid_lines,
            "lost": lost,
            "expected": num_episodes,
            "actual": len(valid_lines),
            "tokens": {
                "input": usage.prompt_tokens,
                "output": usage.completion_tokens
            }
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "insufficient" in error_msg or "balance" in error_msg:
            return {"success": False, "error": "INSUFFICIENT_BALANCE", "lost": []}
        return {"success": False, "error": str(e), "lost": original_rows}

def write_header_if_needed():
    if not OUTPUT_FILE.exists() or OUTPUT_FILE.stat().st_size == 0:
        header = "episode_id,politics,science,tech,entertainment,art,education,tourism,economics,law,ecology,style,BBC,sports,psychology,religion,architecture,medicine,business,food,history,relationship,family\n"
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(header)

def append_to_output(data_lines):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        for line in data_lines:
            if line.strip():
                f.write(line.strip() + '\n')

def main():
    write_header_if_needed()

    http_client = httpx.Client(verify=False)
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com", http_client=http_client)

    print("Подключение...")
    try:
        client.models.list()
        print("Подключился")
    except Exception as e:
        print(f"Ошибка: {e}")
        return

    progress = load_progress()
    processed_chunks = set(progress.get("processed_chunks", []))
    total_episodes = progress.get("total_episodes", 0)
    all_lost_episodes = progress.get("lost_episodes", [])

    if processed_chunks:
        print(f"Обработано чанков: {len(processed_chunks)}")
        print(f"Всего эпизодов: {total_episodes}")
        print(f"Потеряно: {len(all_lost_episodes)}")

    csv_files = sorted(INPUT_DIR.glob("sampled_episodes_part_*.csv"))

    all_chunks = []
    for file_path in csv_files:
        header, chunks, total, all_rows = split_csv(file_path, EPISODES_PER_CHUNK)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_path.stem}_chunk_{i + 1}"
            csv_string = chunk_to_csv_string(header, chunk["rows"])
            all_chunks.append({
                "chunk_id": chunk_id,
                "csv_string": csv_string,
                "num_episodes": len(chunk["rows"]),
                "rows": chunk["rows"],
                "source_file": file_path.name
            })

    to_process = [ch for ch in all_chunks if ch["chunk_id"] not in processed_chunks]

    if not to_process:
        save_lost_episodes(all_lost_episodes)
        return
    balance_exhausted = False

    for i, chunk in enumerate(to_process, 1):
        if balance_exhausted:
            break

        result = classify_chunk(
            client,
            chunk["csv_string"],
            chunk["chunk_id"],
            chunk["num_episodes"],
            chunk["rows"]
        )

        if result["success"]:
            append_to_output(result["data_lines"])
            processed_chunks.add(chunk["chunk_id"])
            total_episodes += len(result["data_lines"])

            if result["lost"]:
                all_lost_episodes.extend(result["lost"])
                print(f"Потеряно: {len(result['lost'])} эпизодов")

            save_progress(list(processed_chunks), total_episodes, all_lost_episodes)

            print(f"Всего эпизодов: {total_episodes} | Потеряно: {len(all_lost_episodes)}")

        else:
            if result.get("error") == "INSUFFICIENT_BALANCE":
                print(f"Деньги на счету закончились")
                balance_exhausted = True
            else:
                print(f"Ошибка: {result.get('error')}")
                if result.get("lost"):
                    all_lost_episodes.extend(result["lost"])
                save_progress(list(processed_chunks), total_episodes, all_lost_episodes)

        time.sleep(DELAY_BETWEEN_CHUNKS)

    save_lost_episodes(all_lost_episodes)

    print(f"Всего эпизодов: {total_episodes}")
    print(f"Потеряно эпизодов: {len(all_lost_episodes)}")

if __name__ == "__main__":
    main()