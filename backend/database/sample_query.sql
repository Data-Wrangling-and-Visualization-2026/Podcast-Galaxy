CREATE TABLE IF NOT EXISTS sampled_episodes (
    episode_id UUID,
    yandex_id VARCHAR(255),
    title TEXT,
    description TEXT,
    duration INTEGER,
    podcast_id UUID,
    pub_date VARCHAR,
    category VARCHAR(255),
    popularity_group INTEGER,
    duration_bucket VARCHAR(20),
    sample_weight FLOAT
);

-- Step 1: Assign a popularity group to each podcast (5 groups)
WITH podcast_with_percentile AS (
    SELECT
        podcast_id,
        likes_count,
        NTILE(5) OVER (ORDER BY likes_count) AS popularity_group
    FROM podcasts
    WHERE likes_count IS NOT NULL
),

-- Step 2: For each podcast, take NO MORE THAN 20 random episodes
limited_episodes AS (
    SELECT
        e.*,
        p.likes_count,
        p.popularity_group,
        ROW_NUMBER() OVER (
            PARTITION BY e.podcast_id
            ORDER BY RANDOM()
        ) AS row_num_in_podcast
    FROM episodes e
    INNER JOIN podcast_with_percentile p ON e.podcast_id = p.podcast_id
),
filtered_episodes AS (
    SELECT *
    FROM limited_episodes
    WHERE row_num_in_podcast <= 20
),

-- Step 3: Add duration groups (4 groups)
episodes_with_buckets AS (
    SELECT
        *,
        CASE
            WHEN duration < 15 * 60 THEN 'short'
            WHEN duration < 45 * 60 THEN 'medium'
            WHEN duration < 90 * 60 THEN 'long'
            ELSE 'very_long'
        END AS duration_bucket
    FROM filtered_episodes
    WHERE duration IS NOT NULL AND duration > 0
),

-- Step 4: Determine how many to take from each stratum
strata_counts AS (
    SELECT
        popularity_group,
        duration_bucket,
        COUNT(*) AS available_episodes,
        LEAST(COUNT(*), 2250) AS target_to_take
    FROM episodes_with_buckets
    GROUP BY popularity_group, duration_bucket
),

-- Step 5: Randomly number the episodes within each stratum
sampled_episodes_prepared AS (
    SELECT
        e.*,
        ROW_NUMBER() OVER (
            PARTITION BY e.popularity_group, e.duration_bucket
            ORDER BY RANDOM()
        ) AS row_num_in_stratum,
        sc.target_to_take
    FROM episodes_with_buckets e
    INNER JOIN strata_counts sc
        ON e.popularity_group = sc.popularity_group
        AND e.duration_bucket = sc.duration_bucket
)

INSERT INTO sampled_episodes (
    episode_id,
    yandex_id,
    title,
    description,
    duration,
    podcast_id,
    pub_date,
    category,
    popularity_group,
    duration_bucket,
    sample_weight
)
SELECT
    episode_id,
    yandex_id,
    title,
    description,
    duration,
    podcast_id,
    pub_date,
    category,
    popularity_group,
    duration_bucket,
    (COUNT(*) OVER (PARTITION BY popularity_group, duration_bucket))::FLOAT / target_to_take AS sample_weight
FROM sampled_episodes_prepared
WHERE row_num_in_stratum <= target_to_take
ORDER BY popularity_group, duration_bucket;