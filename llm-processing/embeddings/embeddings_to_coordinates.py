import pandas as pd
import numpy as np
import umap
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import seaborn as sns
from sklearn.preprocessing import normalize

df = pd.read_csv('../clean_ready_data/all_classified_clean.csv')

episode_ids = df['episode_id'].values
topic_names = [col for col in df.columns if col != 'episode_id']

X = df[topic_names].values.astype(np.float32)

row_sums = X.sum(axis=1, keepdims=True)
row_sums[row_sums == 0] = 1
X = X / row_sums * 100

# UMAP этап, используем:
# n_neighbors: 25 — хороший баланс между локальной и глобальной структурой
# min_dist: 0.15 — чем больше точек, тем меньше можно ставить min_dist
# metric='cosine' — обязательно для вероятностных векторов

reducer = umap.UMAP(
    n_components=2,
    n_neighbors=25,
    min_dist=0.15,
    metric='cosine',
    random_state=42,
    verbose=True
)

embeddings_2d = reducer.fit_transform(X)

#этап определения доминирующей темы

dominant_idx = np.argmax(X, axis=1)
dominant_topic_names = [topic_names[i] for i in dominant_idx]
dominant_weight = np.max(X, axis=1)

#строим заранее графики, чтобы посмотреть как расположены темы
colors_20 = plt.cm.tab20.colors
colors_20b = plt.cm.tab20b.colors
all_colors = list(colors_20) + list(colors_20b[:2])

if len(all_colors) < len(topic_names):
    all_colors = [plt.cm.hsv(i / len(topic_names)) for i in range(len(topic_names))]

topic_color_map = {topic: all_colors[i] for i, topic in enumerate(topic_names)}
point_colors = [topic_color_map[topic_names[i]] for i in dominant_idx]

#график со всеми точками
fig, ax = plt.subplots(figsize=(20, 16))
sizes = 3 + (dominant_weight / 100) * 12

scatter = ax.scatter(
    embeddings_2d[:, 0],
    embeddings_2d[:, 1],
    c=point_colors,
    s=sizes,
    alpha=0.6,
    edgecolors='none'
)

ax.set_title('Semantic Map of Podcast Episodes\nColored by Dominant Topic',
             fontsize=16, pad=20)
ax.set_xlabel('UMAP Dimension 1', fontsize=12)
ax.set_ylabel('UMAP Dimension 2', fontsize=12)
ax.grid(True, alpha=0.3)

used_topics = set(dominant_topic_names)
legend_patches = []
for topic in sorted(used_topics):
    if topic in topic_color_map:
        patch = mpatches.Patch(color=topic_color_map[topic], label=topic, alpha=0.8)
        legend_patches.append(patch)

ax.legend(handles=legend_patches,
          loc='upper left',
          bbox_to_anchor=(1.02, 1),
          fontsize=8,
          ncol=2 if len(used_topics) > 15 else 1)

plt.tight_layout()
plt.savefig('semantic_map_all_episodes.png', dpi=150, bbox_inches='tight')
plt.show()

# центроиды тем вычисляем, чтобы показать на графике и потом использовать для визуализации (опционально)
topic_centroids = []
topic_counts = []

for i, topic in enumerate(topic_names):
    weights = X[:, i]
    threshold = max(30, np.percentile(weights[weights > 0], 80) if np.any(weights > 0) else 100)
    mask = weights > threshold

    if mask.sum() >= 3:
        centroid = np.average(embeddings_2d[mask], axis=0, weights=weights[mask])
        topic_centroids.append(centroid)
        topic_counts.append((topic, mask.sum()))
    else:
        mask2 = weights > 0
        if mask2.sum() >= 1:
            centroid = np.average(embeddings_2d[mask2], axis=0, weights=weights[mask2])
            topic_centroids.append(centroid)
            topic_counts.append((topic, mask2.sum()))
        else:
            topic_centroids.append([np.nan, np.nan])
            topic_counts.append((topic, 0))

topic_centroids = np.array(topic_centroids)

fig4, ax4 = plt.subplots(figsize=(20, 16))

ax4.scatter(
    embeddings_2d[:, 0],
    embeddings_2d[:, 1],
    c='lightgray',
    s=2,
    alpha=0.2
)

for i, topic in enumerate(topic_names):
    if not np.isnan(topic_centroids[i, 0]):
        ax4.scatter(
            topic_centroids[i, 0],
            topic_centroids[i, 1],
            c=[topic_color_map[topic]],
            s=200,
            marker='X',
            edgecolors='black',
            linewidths=1.5,
            zorder=10
        )
        ax4.annotate(
            topic,
            (topic_centroids[i, 0], topic_centroids[i, 1]),
            fontsize=9,
            ha='center',
            va='bottom',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
            zorder=11
        )

ax4.set_title('Topic Centroids in Episode Semantic Space\n(X marks where each topic "lives")', fontsize=16)
ax4.set_xlabel('UMAP Dimension 1', fontsize=12)
ax4.set_ylabel('UMAP Dimension 2', fontsize=12)
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('semantic_map_centroids.png', dpi=150, bbox_inches='tight')
plt.show()

# сохраняем координаты центроидов в отдельный файл для базы данных
centroids_df = pd.DataFrame({
    'topic': topic_names,
    'centroid_x': topic_centroids[:, 0],
    'centroid_y': topic_centroids[:, 1],
    'num_episodes_high_weight': [cnt for _, cnt in topic_counts]
})

centroids_df.to_csv('topic_centroids.csv', index=False)

# сохраняем координаты полученные через UMAP
results_df = pd.DataFrame({
    'episode_id': episode_ids,
    'umap_x': embeddings_2d[:, 0],
    'umap_y': embeddings_2d[:, 1],
    'dominant_topic': dominant_topic_names,
    'dominant_weight': dominant_weight
})

for i, topic in enumerate(topic_names):
    results_df[topic] = X[:, i]

results_df.to_csv('podcast_umap_2d_results.csv', index=False)
