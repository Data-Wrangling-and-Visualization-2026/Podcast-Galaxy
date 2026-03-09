import pandas as pd
import json
from transformers import pipeline
import torch
import os

categories = [
    "психология и саморазвитие",
    "психотерапия",
    "медицина и здоровье",
    "неврология и мозг",
    "спорт и фитнес",
    "отношения и секс",
    "история",
    "образование",
    "бизнес и предпринимательство",
    "карьера и работа",
    "финансы и инвестиции",
    "маркетинг и продажи",
    "инфобизнес и мошенничество",
    "технологии",
    "искусственный интеллект",
    "кино и сериалы",
    "литература",
    "музыка",
    "юмор",
    "криминал и true crime",
    "детективы и расследования",
    "загадки и мистика",
    "шпионаж и спецслужбы",
    "политика",
    "семья и дети",
    "путешествия",
    "еда и кулинария",
    "мода и красота",
    "дом и интерьер",
    "авто",
    "видеоигры",
    "изучение языков"
]

os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

device = 0 if torch.cuda.is_available() else -1
classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
                      device=device)

with open('test_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data['episodes'])

for i, row in df.iterrows():
    print(f"{i + 1}/{len(df)}")
    text = row.get('description', '')
    title = row.get('title', '')
    full = f"{title}. {text}" if title else text

    result = classifier(full, categories, multi_label=True)

    df.at[i, 'topics'] = ', '.join(result['labels'][:3])
    df.at[i, 'main_topic'] = result['labels'][0]
    df.at[i, 'topic_confidence'] = round(result['scores'][0], 3)
    df.at[i, 'all_scores'] = json.dumps(dict(zip(result['labels'][:10], [round(s, 3) for s in result['scores'][:10]])),
                                        ensure_ascii=False)

df.to_csv('results.csv', index=False, encoding='utf-8-sig')
df.to_json('results.json', orient='records', indent=2, force_ascii=False)