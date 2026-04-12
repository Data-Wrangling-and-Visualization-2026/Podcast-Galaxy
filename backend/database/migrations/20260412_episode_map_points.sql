ALTER TABLE episodes
DROP COLUMN IF EXISTS category;

CREATE TABLE IF NOT EXISTS episode_map_points (
    episode_id UUID PRIMARY KEY REFERENCES episodes(episode_id) ON DELETE CASCADE,
    umap_x DOUBLE PRECISION NOT NULL,
    umap_y DOUBLE PRECISION NOT NULL,
    dominant_topic VARCHAR(255) NOT NULL,
    dominant_weight DOUBLE PRECISION,
    topic_scores_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_episode_map_points_umap_x ON episode_map_points (umap_x);
CREATE INDEX IF NOT EXISTS idx_episode_map_points_umap_y ON episode_map_points (umap_y);
