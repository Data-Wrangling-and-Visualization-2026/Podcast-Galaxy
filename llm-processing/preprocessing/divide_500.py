# делим выборку на файлы по 500 эпизодов (для удобства отправки в ллм)
import pandas as pd
import os

file_path = '../sampled_episodes.csv'
chunk_size = 500
base_name = os.path.splitext(file_path)[0]

df = pd.read_csv(file_path)

for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i + chunk_size]
    output_file = f'{base_name}_part_{i//chunk_size + 1}.csv'
    chunk.to_csv(output_file, index=False)
