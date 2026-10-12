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
FROM read_parquet('data/silver/questions_enriched_gemma3_4b.parquet')
