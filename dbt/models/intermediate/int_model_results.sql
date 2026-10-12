SELECT
    type,
    difficulty,
    category,
    question,
    correct_answer,
    incorrect_answers,
    ai_answer,
    ai_correct,
    response_time,
    model,
    prompt,
    ai_raw_response,
    correct_label
FROM {{ ref('stg_gemma') }}

UNION ALL

SELECT
    type,
    difficulty,
    category,
    question,
    correct_answer,
    incorrect_answers,
    ai_answer,
    ai_correct,
    response_time,
    model,
    prompt,
    ai_raw_response,
    correct_label
FROM {{ ref('stg_llama') }}
