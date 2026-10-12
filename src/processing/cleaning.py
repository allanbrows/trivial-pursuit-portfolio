import pandas as pd
import html
import re
from pathlib import Path


# --------------------------------------------------
# CHEMINS
# --------------------------------------------------

INPUT_FILE = Path("data/bronze/questions_raw.csv")
OUTPUT_FILE = Path("data/silver/questions_clean.parquet")


# --------------------------------------------------
# FONCTION DE NETTOYAGE DES TEXTES
# --------------------------------------------------

def clean_text(value):
    """
    Nettoie une valeur textuelle provenant d'OpenTDB.
    """

    # Si la valeur est vide
    if pd.isna(value):
        return ""

    # Transformer la valeur en texte
    value = str(value)

    # Décoder les entités HTML
    # Exemple :
    # &amp;   -> &
    # &quot;  -> "
    # &#039;  -> '
    value = html.unescape(value)

    # Remplacer plusieurs espaces par un seul
    value = re.sub(r"\s+", " ", value)

    # Supprimer les espaces au début et à la fin
    value = value.strip()

    return value


# --------------------------------------------------
# PROGRAMME PRINCIPAL
# --------------------------------------------------

def main():

    print("======================================")
    print("   NETTOYAGE BRONZE -> SILVER")
    print("======================================")

    # 1. Vérifier que le fichier Bronze existe
    if not INPUT_FILE.exists():
        print(f"ERREUR : fichier introuvable : {INPUT_FILE}")
        return

    # 2. Lire le fichier CSV
    print("\nLecture du fichier Bronze...")

    df = pd.read_csv(INPUT_FILE)

    print(f"Nombre de lignes initiales : {len(df)}")
    print(f"Colonnes : {list(df.columns)}")

    # --------------------------------------------------
    # 3. Vérification des colonnes
    # --------------------------------------------------

    expected_columns = [
        "type",
        "difficulty",
        "category",
        "question",
        "correct_answer",
        "incorrect_answers",
    ]

    missing_columns = [
        column
        for column in expected_columns
        if column not in df.columns
    ]

    if missing_columns:
        print("\nERREUR : colonnes manquantes :")
        print(missing_columns)
        return

    # --------------------------------------------------
    # 4. Nettoyage des colonnes textuelles
    # --------------------------------------------------

    print("\nNettoyage des données...")

    text_columns = [
        "type",
        "difficulty",
        "category",
        "question",
        "correct_answer",
        "incorrect_answers",
    ]

    for column in text_columns:
        df[column] = df[column].apply(clean_text)

    # --------------------------------------------------
    # 5. Suppression des questions vides
    # --------------------------------------------------

    before_empty = len(df)

    df = df[df["question"] != ""]

    removed_empty = before_empty - len(df)

    print(f"Questions vides supprimées : {removed_empty}")

    # --------------------------------------------------
    # 6. Suppression des doublons
    # --------------------------------------------------

    before_duplicates = len(df)

    df = df.drop_duplicates(
        subset=["question"],
        keep="first"
    )

    removed_duplicates = before_duplicates - len(df)

    print(f"Doublons supprimés : {removed_duplicates}")

    # --------------------------------------------------
    # 7. Vérification des valeurs manquantes
    # --------------------------------------------------

    print("\nValeurs manquantes :")

    missing_values = df[expected_columns].isna().sum()

    print(missing_values)

    # --------------------------------------------------
    # 8. Réinitialiser les index
    # --------------------------------------------------

    df = df.reset_index(drop=True)

    # --------------------------------------------------
    # 9. Créer le dossier Silver
    # --------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------
    # 10. Sauvegarder en Parquet
    # --------------------------------------------------

    print("\nSauvegarde du fichier Silver...")

    df.to_parquet(
        OUTPUT_FILE,
        index=False,
        engine="pyarrow"
    )

    # --------------------------------------------------
    # 11. Résumé final
    # --------------------------------------------------

    print("\n======================================")
    print("       SILVER CRÉÉE AVEC SUCCÈS")
    print("======================================")

    print(f"Fichier : {OUTPUT_FILE}")
    print(f"Nombre de lignes : {len(df)}")
    print(f"Nombre de colonnes : {len(df.columns)}")

    print("\nColonnes Silver :")

    for column in df.columns:
        print(f" - {column}")


# --------------------------------------------------
# POINT D'ENTRÉE
# --------------------------------------------------

if __name__ == "__main__":
    main()