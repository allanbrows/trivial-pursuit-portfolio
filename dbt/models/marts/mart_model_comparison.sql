SELECT
    model,
    COUNT(*) AS questions,
    SUM(CASE WHEN ai_correct THEN 1 ELSE 0 END) AS correct,
    SUM(CASE WHEN NOT ai_correct THEN 1 ELSE 0 END) AS incorrect,
    ROUND(
        100.0 * SUM(CASE WHEN ai_correct THEN 1 ELSE 0 END)
        / COUNT(*),
        2
    ) AS accuracy,
    ROUND(AVG(response_time), 3) AS average_response_time,
    ROUND(MEDIAN(response_time), 3) AS median_response_time,
    ROUND(MIN(response_time), 3) AS min_response_time,
    ROUND(MAX(response_time), 3) AS max_response_time
FROM {{ ref('int_model_results') }}
GROUP BY model
ORDER BY accuracy DESC
