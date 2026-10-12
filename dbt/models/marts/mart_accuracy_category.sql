SELECT
    model,
    category,
    COUNT(*) AS questions,
    SUM(CASE WHEN ai_correct THEN 1 ELSE 0 END) AS correct,
    ROUND(
        100.0 * SUM(CASE WHEN ai_correct THEN 1 ELSE 0 END)
        / COUNT(*),
        2
    ) AS accuracy,
    ROUND(AVG(response_time), 3) AS average_response_time
FROM {{ ref('int_model_results') }}
GROUP BY
    model,
    category
ORDER BY
    model,
    accuracy DESC
