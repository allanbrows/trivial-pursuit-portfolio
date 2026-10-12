import ast
import random
import re
import time
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("data/silver/questions_clean.parquet")

OUTPUT_DIR = Path("data/silver")

# Les deux modèles à comparer
MODELS = [
    "gemma3:4b",
    "llama3.2:3b",
]

# ============================================================
# IMPORTANT :
# None = TOUTES les questions
# ============================================================

N_QUESTIONS = None

# Même seed pour garantir la reproductibilité
RANDOM_SEED = 42

# Sauvegarde toutes les 25 questions
SAVE_EVERY = 25

# API Ollama
OLLAMA_URL = "http://localhost:11434/api/generate"

# Température 0 = comportement déterministe
TEMPERATURE = 0

# Temps maximum pour une requête
TIMEOUT = 120


# ============================================================
# LECTURE DES MAUVAISES RÉPONSES
# ============================================================

def parse_incorrect_answers(value):
    """
    Transforme une chaîne comme :

    ["Paris", "Lyon", "Marseille"]

    en liste Python.
    """

    if isinstance(value, list):
        return value

    if pd.isna(value):
        return []

    try:
        return ast.literal_eval(str(value))
    except Exception:
        return []


# ============================================================
# CONSTRUCTION DES OPTIONS
# ============================================================

def build_options(row, rng):
    """
    Construit les options de réponse.

    Pour une question multiple :
        3 mauvaises réponses + 1 bonne réponse.

    Pour une question boolean :
        True / False.

    Les réponses sont mélangées avec une seed fixe.
    """

    question_type = str(row["type"]).lower()

    correct_answer = str(row["correct_answer"])

    # --------------------------------------------------------
    # Vrai / Faux
    # --------------------------------------------------------

    if question_type == "boolean":

        options = [
            "True",
            "False",
        ]

        rng.shuffle(options)

        labels = ["A", "B"]

    # --------------------------------------------------------
    # QCM
    # --------------------------------------------------------

    else:

        incorrect_answers = parse_incorrect_answers(
            row["incorrect_answers"]
        )

        options = [
            str(answer)
            for answer in incorrect_answers
        ]

        options.append(correct_answer)

        rng.shuffle(options)

        labels = ["A", "B", "C", "D"]

    return labels, options


# ============================================================
# CONSTRUCTION DU PROMPT
# ============================================================

def create_prompt(question, labels, options):

    options_text = "\n".join(
        f"{label}. {option}"
        for label, option in zip(labels, options)
    )

    prompt = f"""
You are answering a general knowledge multiple-choice question.

Question:
{question}

Possible answers:
{options_text}

Choose the correct answer.

IMPORTANT:
- Answer only with the letter corresponding to your choice.
- Do not explain your answer.
- Do not use external search.
- Use only the information contained in the question and the possible answers.

Answer:
""".strip()

    return prompt


# ============================================================
# APPEL À OLLAMA
# ============================================================

def call_ollama(prompt, model):

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
        },
    }

    start_time = time.perf_counter()

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        elapsed = time.perf_counter() - start_time

        answer = data.get("response", "")

        return answer.strip(), elapsed

    except Exception as error:

        elapsed = time.perf_counter() - start_time

        print(
            f"\nERREUR avec {model} : {error}"
        )

        return "", elapsed


# ============================================================
# EXTRACTION DE LA LETTRE
# ============================================================

def extract_answer(response):

    if not response:
        return ""

    text = response.strip().upper()

    # Exemple :
    # B
    # B.
    # Answer: B
    # The answer is B

    match = re.search(
        r"\b([ABCD])\b",
        text,
    )

    if match:
        return match.group(1)

    match = re.match(
        r"^([ABCD])",
        text,
    )

    if match:
        return match.group(1)

    return ""


# ============================================================
# ÉVALUATION
# ============================================================

def evaluate_answer(
    predicted_label,
    labels,
    options,
    correct_answer,
):

    correct_answer = str(correct_answer)

    correct_label = ""

    for label, option in zip(labels, options):

        if str(option) == correct_answer:

            correct_label = label

            break

    is_correct = (
        predicted_label == correct_label
        and correct_label != ""
    )

    return is_correct, correct_label


# ============================================================
# PRÉPARATION DES QUESTIONS
# ============================================================

def prepare_questions(df):

    print("\nPréparation des questions...")

    # --------------------------------------------------------
    # Sélection
    # --------------------------------------------------------

    if N_QUESTIONS is None:

        questions_df = df.copy()

    else:

        if N_QUESTIONS > len(df):

            raise ValueError(
                f"N_QUESTIONS={N_QUESTIONS} "
                f"> nombre disponible={len(df)}"
            )

        questions_df = df.sample(
            n=N_QUESTIONS,
            random_state=RANDOM_SEED,
        ).copy()

    questions_df = questions_df.reset_index(drop=True)

    # --------------------------------------------------------
    # IMPORTANT :
    # On prépare les options UNE SEULE FOIS.
    #
    # Ainsi Gemma et LLaMA reçoivent exactement
    # les mêmes questions et exactement les mêmes options.
    # --------------------------------------------------------

    rng = random.Random(RANDOM_SEED)

    prepared_questions = []

    for index, row in questions_df.iterrows():

        labels, options = build_options(
            row,
            rng,
        )

        prompt = create_prompt(
            row["question"],
            labels,
            options,
        )

        item = row.to_dict()

        item["labels"] = labels
        item["options"] = options
        item["prepared_prompt"] = prompt

        prepared_questions.append(item)

    prepared_df = pd.DataFrame(
        prepared_questions
    )

    print(
        f"Questions préparées : {len(prepared_df)}"
    )

    return prepared_df


# ============================================================
# BENCHMARK D'UN MODÈLE
# ============================================================

def benchmark_model(prepared_df, model):

    print("\n")
    print("=" * 70)
    print(f"          BENCHMARK : {model}")
    print("=" * 70)

    results = []

    # --------------------------------------------------------
    # Fichier de sauvegarde
    # --------------------------------------------------------

    safe_model_name = (
        model
        .replace(":", "_")
        .replace("/", "_")
    )

    output_file = (
        OUTPUT_DIR
        / f"questions_enriched_{safe_model_name}.parquet"
    )

    # --------------------------------------------------------
    # Traitement
    # --------------------------------------------------------

    total_questions = len(prepared_df)

    for index, row in prepared_df.iterrows():

        question_number = index + 1

        print(
            f"\n[{question_number}/{total_questions}]"
        )

        print(
            f"Question : {row['question']}"
        )

        labels = row["labels"]
        options = row["options"]

        # ----------------------------------------------------
        # Affichage des options
        # ----------------------------------------------------

        for label, option in zip(labels, options):

            print(
                f"  {label}. {option}"
            )

        # ----------------------------------------------------
        # Prompt
        # ----------------------------------------------------

        prompt = row["prepared_prompt"]

        # ----------------------------------------------------
        # Appel modèle
        # ----------------------------------------------------

        print(
            f"Interrogation de {model}..."
        )

        raw_answer, response_time = call_ollama(
            prompt,
            model,
        )

        # ----------------------------------------------------
        # Extraction
        # ----------------------------------------------------

        ai_answer = extract_answer(
            raw_answer
        )

        # ----------------------------------------------------
        # Évaluation
        # ----------------------------------------------------

        ai_correct, correct_label = evaluate_answer(
            ai_answer,
            labels,
            options,
            row["correct_answer"],
        )

        # ----------------------------------------------------
        # Affichage
        # ----------------------------------------------------

        print(
            f"Réponse brute : {raw_answer}"
        )

        print(
            f"Réponse extraite : {ai_answer}"
        )

        print(
            f"Bonne réponse : {correct_label}"
        )

        print(
            f"Correct : {ai_correct}"
        )

        print(
            f"Temps : {response_time:.2f} secondes"
        )

        # ----------------------------------------------------
        # Résultat
        # ----------------------------------------------------

        result = {
            "type": row["type"],
            "difficulty": row["difficulty"],
            "category": row["category"],
            "question": row["question"],
            "correct_answer": row["correct_answer"],
            "incorrect_answers": row["incorrect_answers"],

            "ai_answer": ai_answer,
            "ai_correct": ai_correct,
            "response_time": response_time,

            "model": model,

            "prompt": prompt,

            "ai_raw_response": raw_answer,

            "correct_label": correct_label,
        }

        results.append(result)

        # ----------------------------------------------------
        # Sauvegarde progressive
        # ----------------------------------------------------

        if (
            len(results) % SAVE_EVERY == 0
            or len(results) == total_questions
        ):

            temp_df = pd.DataFrame(
                results
            )

            temp_df.to_parquet(
                output_file,
                index=False,
                engine="pyarrow",
            )

            print(
                f"\n>>> Sauvegarde : "
                f"{len(results)}/{total_questions}"
            )

            print(
                f">>> Fichier : {output_file}"
            )

    # --------------------------------------------------------
    # DataFrame final
    # --------------------------------------------------------

    result_df = pd.DataFrame(
        results
    )

    result_df.to_parquet(
        output_file,
        index=False,
        engine="pyarrow",
    )

    # --------------------------------------------------------
    # Statistiques
    # --------------------------------------------------------

    total = len(result_df)

    correct = int(
        result_df["ai_correct"].sum()
    )

    incorrect = total - correct

    accuracy = (
        correct / total * 100
        if total > 0
        else 0
    )

    average_time = (
        result_df["response_time"].mean()
        if total > 0
        else 0
    )

    median_time = (
        result_df["response_time"].median()
        if total > 0
        else 0
    )

    # --------------------------------------------------------
    # Résultats
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print(f"          RÉSULTATS : {model}")
    print("=" * 70)

    print(
        f"Questions : {total}"
    )

    print(
        f"Bonnes réponses : {correct}"
    )

    print(
        f"Erreurs : {incorrect}"
    )

    print(
        f"Accuracy : {accuracy:.2f}%"
    )

    print(
        f"Temps moyen : {average_time:.2f} secondes"
    )

    print(
        f"Temps médian : {median_time:.2f} secondes"
    )

    print(
        f"Fichier : {output_file}"
    )

    print("=" * 70)

    return result_df


# ============================================================
# COMPARAISON DES MODÈLES
# ============================================================

def compare_models(all_results):

    print("\n")
    print("=" * 70)
    print("                 COMPARAISON")
    print("=" * 70)

    comparison = []

    for model, df in all_results.items():

        total = len(df)

        correct = int(
            df["ai_correct"].sum()
        )

        incorrect = total - correct

        accuracy = (
            correct / total * 100
            if total > 0
            else 0
        )

        average_time = (
            df["response_time"].mean()
            if total > 0
            else 0
        )

        median_time = (
            df["response_time"].median()
            if total > 0
            else 0
        )

        comparison.append(
            {
                "model": model,
                "questions": total,
                "correct": correct,
                "incorrect": incorrect,
                "accuracy": accuracy,
                "average_response_time": average_time,
                "median_response_time": median_time,
            }
        )

    comparison_df = pd.DataFrame(
        comparison
    )

    print(
        comparison_df.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Sauvegarde Gold
    # --------------------------------------------------------

    gold_dir = Path("data/gold")

    gold_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    comparison_file = (
        gold_dir
        / "model_comparison.parquet"
    )

    comparison_df.to_parquet(
        comparison_file,
        index=False,
        engine="pyarrow",
    )

    print(
        f"\nComparaison sauvegardée : "
        f"{comparison_file}"
    )

    return comparison_df


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    print("=" * 70)
    print("       TRIVIAL PURSUIT - BENCHMARK COMPLET")
    print("=" * 70)

    # --------------------------------------------------------
    # Vérification fichier Silver
    # --------------------------------------------------------

    if not INPUT_FILE.exists():

        print(
            f"\nERREUR : fichier introuvable : "
            f"{INPUT_FILE}"
        )

        return

    # --------------------------------------------------------
    # Création dossier
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Lecture
    # --------------------------------------------------------

    print(
        "\nLecture du fichier Silver..."
    )

    df = pd.read_parquet(
        INPUT_FILE
    )

    print(
        f"Nombre total de questions : {len(df)}"
    )

    # --------------------------------------------------------
    # Vérification
    # --------------------------------------------------------

    required_columns = [
        "type",
        "difficulty",
        "category",
        "question",
        "correct_answer",
        "incorrect_answers",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        print(
            "\nERREUR : colonnes manquantes :"
        )

        for column in missing_columns:

            print(
                f" - {column}"
            )

        return

    # --------------------------------------------------------
    # Préparation unique
    # --------------------------------------------------------

    prepared_df = prepare_questions(
        df
    )

    # --------------------------------------------------------
    # Benchmark des modèles
    # --------------------------------------------------------

    all_results = {}

    for model in MODELS:

        result_df = benchmark_model(
            prepared_df,
            model,
        )

        all_results[model] = result_df

    # --------------------------------------------------------
    # Comparaison finale
    # --------------------------------------------------------

    compare_models(
        all_results
    )

    # --------------------------------------------------------
    # FIN
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("          BENCHMARK COMPLET TERMINÉ")
    print("=" * 70)

    print(
        "\nFichiers générés :"
    )

    print(
        "data/silver/questions_enriched_gemma3_4b.parquet"
    )

    print(
        "data/silver/questions_enriched_llama3.2_3b.parquet"
    )

    print(
        "data/gold/model_comparison.parquet"
    )


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":
    main()