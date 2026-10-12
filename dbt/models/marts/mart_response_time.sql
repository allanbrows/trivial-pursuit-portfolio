SELECT
    model,
    COUNT(*) AS questions,
    ROUND(AVG(response_time), 3) AS average_response_time,
    ROUND(MEDIAN(response_time), 3) AS median_response_time,
    ROUND(MIN(response_time), 3) AS min_response_time,
    ROUND(MAX(response_time), 3) AS max_response_time,
    ROUND(
        STDDEV_SAMP(response_time),
        3
    ) AS std_response_time
FROM {{ ref('int_model_results') }}
GROUP BY model
ORDER BY average_response_time
