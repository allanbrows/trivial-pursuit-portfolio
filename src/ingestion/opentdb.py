import requests
import pandas as pd
import os
import time


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "https://opentdb.com/api.php"
TOKEN_URL = "https://opentdb.com/api_token.php"

BATCH_SIZE = 50
WAIT_TIME = 5

OUTPUT_FILE = "data/bronze/questions_raw.csv"


# ============================================================
# 1. CRÉER LE TOKEN
# ============================================================

print("Création du token OpenTDB...")

token_response = requests.get(
    TOKEN_URL,
    params={"command": "request"},
    timeout=30
)

token_response.raise_for_status()

token_data = token_response.json()

if token_data["response_code"] != 0:
    raise Exception(
        f"Erreur lors de la création du token : "
        f"{token_data['response_code']}"
    )

token = token_data["token"]

print("Token créé avec succès.")


# ============================================================
# 2. PRÉPARER LE DOSSIER
# ============================================================

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)


# ============================================================
# 3. COLLECTE PAR LOTS DE 50
# ============================================================

all_questions = []

lot = 0

while True:

    lot += 1

    print()
    print("=" * 60)
    print(f"LOT {lot}")
    print("=" * 60)

    params = {
        "amount": BATCH_SIZE,
        "token": token
    }

    try:

        response = requests.get(
            API_URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as e:

        print("Erreur réseau :", e)
        print("Nouvelle tentative dans 5 secondes...")

        time.sleep(WAIT_TIME)

        lot -= 1

        continue


    response_code = data["response_code"]

    print("Code OpenTDB :", response_code)


    # ========================================================
    # CODE 0 : QUESTIONS RÉCUPÉRÉES
    # ========================================================

    if response_code == 0:

        questions = data["results"]

        print(
            f"Questions reçues : {len(questions)}"
        )

        all_questions.extend(questions)


    # ========================================================
    # CODE 1 : PLUS DE QUESTIONS DISPONIBLES
    # ========================================================

    elif response_code == 1:

        print()
        print("OpenTDB n'a plus suffisamment de questions.")
        break


    # ========================================================
    # CODE 4 : TOKEN ÉPUISÉ
    # ========================================================

    elif response_code == 4:

        print("Token épuisé.")
        print("Création d'un nouveau token...")

        token_response = requests.get(
            TOKEN_URL,
            params={"command": "request"},
            timeout=30
        )

        token_response.raise_for_status()

        token_data = token_response.json()

        if token_data["response_code"] != 0:
            raise Exception(
                "Impossible de créer un nouveau token."
            )

        token = token_data["token"]

        print("Nouveau token créé.")

        lot -= 1

        continue


    # ========================================================
    # AUTRE CODE
    # ========================================================

    else:

        print(
            f"Code OpenTDB inattendu : {response_code}"
        )

        break


    # ========================================================
    # 4. SUPPRESSION DES DOUBLONS
    # ========================================================

    df = pd.DataFrame(all_questions)

    df = df.drop_duplicates(
        subset=["question"]
    )


    # ========================================================
    # 5. SAUVEGARDE APRÈS CHAQUE LOT
    # ========================================================

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8"
    )

    print(
        f"Total unique : {len(df)}"
    )

    print(
        f"Sauvegarde : {OUTPUT_FILE}"
    )


    # ========================================================
    # 6. ATTENDRE 5 SECONDES
    # ========================================================

    print(
        f"Attente de {WAIT_TIME} secondes..."
    )

    time.sleep(WAIT_TIME)


# ============================================================
# 7. BILAN FINAL
# ============================================================

print()
print("=" * 60)
print("COLLECTE TERMINÉE")
print("=" * 60)

final_df = pd.DataFrame(all_questions)

raw_count = len(final_df)

unique_df = final_df.drop_duplicates(
    subset=["question"]
)

unique_count = len(unique_df)

duplicate_count = raw_count - unique_count

print(f"Questions récupérées : {raw_count}")
print(f"Questions uniques    : {unique_count}")
print(f"Doublons détectés    : {duplicate_count}")

print()
print(f"Fichier final : {OUTPUT_FILE}")