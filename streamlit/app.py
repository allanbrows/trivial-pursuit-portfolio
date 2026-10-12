import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Trivial Pursuit - Benchmark IA",
    page_icon="🧠",
    layout="wide",
)


# ============================================================
# CHEMIN DU PROJET ET DUCKDB
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "trivial_pursuit.duckdb"
)


# ============================================================
# CONNEXION DUCKDB
# ============================================================

@st.cache_resource
def get_connection():
    return duckdb.connect(
        str(DB_PATH),
        read_only=True,
    )


con = get_connection()


# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================

@st.cache_data
def load_model_comparison():
    return con.execute(
        """
        SELECT *
        FROM main.mart_model_comparison
        """
    ).df()


@st.cache_data
def load_category():
    return con.execute(
        """
        SELECT *
        FROM main.mart_accuracy_category
        """
    ).df()


@st.cache_data
def load_difficulty():
    return con.execute(
        """
        SELECT *
        FROM main.mart_accuracy_difficulty
        """
    ).df()


@st.cache_data
def load_response_time():
    return con.execute(
        """
        SELECT *
        FROM main.mart_response_time
        """
    ).df()


# ============================================================
# CHARGEMENT
# ============================================================

comparison = load_model_comparison()
category = load_category()
difficulty = load_difficulty()
response_time = load_response_time()


# ============================================================
# TITRE
# ============================================================

st.title("🧠 Trivial Pursuit — Benchmark des modèles IA")

st.markdown(
    """
    ### Benchmark de modèles de langage locaux

    Ce dashboard présente les résultats du benchmark réalisé
    sur les questions de culture générale provenant d'Open Trivia Database.

    **Modèles évalués :**
    - 🟢 Gemma 3 4B
    - 🔵 LLaMA 3.2 3B

    Les résultats sont stockés dans **DuckDB** et produits par **dbt**.
    """
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Filtres")


# ---------- FILTRE MODÈLE ----------

available_models = sorted(
    comparison["model"].dropna().unique()
)

selected_models = st.sidebar.multiselect(
    "Modèles",
    options=available_models,
    default=available_models,
)


# ---------- FILTRE DIFFICULTÉ ----------

available_difficulties = sorted(
    difficulty["difficulty"].dropna().unique()
)

selected_difficulties = st.sidebar.multiselect(
    "Difficulté",
    options=available_difficulties,
    default=available_difficulties,
)


# ============================================================
# APPLICATION DES FILTRES
# ============================================================

# -------------------------
# Comparaison globale
# -------------------------

filtered_comparison = comparison[
    comparison["model"].isin(selected_models)
].copy()


# -------------------------
# Catégories
# -------------------------

filtered_category = category[
    category["model"].isin(selected_models)
].copy()


# -------------------------
# Difficulté
# -------------------------

filtered_difficulty = difficulty[
    difficulty["model"].isin(selected_models)
].copy()

filtered_difficulty = filtered_difficulty[
    filtered_difficulty["difficulty"].isin(
        selected_difficulties
    )
].copy()


# -------------------------
# Temps de réponse
# -------------------------

filtered_response = response_time[
    response_time["model"].isin(selected_models)
].copy()


# ============================================================
# MESSAGE SI AUCUN MODÈLE
# ============================================================

if len(selected_models) == 0:

    st.warning(
        "Veuillez sélectionner au moins un modèle dans la barre latérale."
    )

    st.stop()


# ============================================================
# VUE D'ENSEMBLE
# ============================================================

st.header("📊 Vue d'ensemble")


if not filtered_comparison.empty:

    # Meilleure accuracy
    best_accuracy_row = filtered_comparison.loc[
        filtered_comparison["accuracy"].idxmax()
    ]

    # Modèle le plus rapide
    fastest_model_row = filtered_comparison.loc[
        filtered_comparison["average_response_time"].idxmin()
    ]

    # Nombre de questions
    total_questions = int(
        filtered_comparison["questions"].max()
    )

    # Nombre de modèles
    number_models = len(
        filtered_comparison
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Questions benchmarkées",
            f"{total_questions:,}".replace(",", " "),
        )

    with col2:

        st.metric(
            "Modèles",
            number_models,
        )

    with col3:

        st.metric(
            "Meilleure accuracy",
            f"{best_accuracy_row['accuracy']:.2f}%",
        )

    with col4:

        st.metric(
            "Modèle le plus précis",
            best_accuracy_row["model"],
        )


# ============================================================
# COMPARAISON GLOBALE
# ============================================================

st.header("🏆 Comparaison des modèles")


display_comparison = filtered_comparison[
    [
        "model",
        "questions",
        "correct",
        "incorrect",
        "accuracy",
        "average_response_time",
        "median_response_time",
    ]
].copy()


display_comparison.columns = [
    "Modèle",
    "Questions",
    "Correctes",
    "Incorrectes",
    "Accuracy (%)",
    "Temps moyen (s)",
    "Temps médian (s)",
]


st.dataframe(
    display_comparison,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# GRAPHIQUE ACCURACY
# ============================================================

col1, col2 = st.columns(2)


with col1:

    st.subheader("🎯 Accuracy globale")

    fig_accuracy = px.bar(
        filtered_comparison,
        x="model",
        y="accuracy",
        text="accuracy",
        labels={
            "model": "Modèle",
            "accuracy": "Accuracy (%)",
        },
        title="Accuracy globale des modèles",
    )

    fig_accuracy.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
    )

    fig_accuracy.update_layout(
        yaxis_range=[
            0,
            min(
                100,
                float(
                    filtered_comparison["accuracy"].max()
                ) + 15,
            ),
        ]
    )

    st.plotly_chart(
        fig_accuracy,
        use_container_width=True,
    )


# ============================================================
# GRAPHIQUE TEMPS
# ============================================================

with col2:

    st.subheader("⚡ Temps de réponse")

    fig_time = px.bar(
        filtered_comparison,
        x="model",
        y="average_response_time",
        text="average_response_time",
        labels={
            "model": "Modèle",
            "average_response_time": "Temps moyen (secondes)",
        },
        title="Temps de réponse moyen",
    )

    fig_time.update_traces(
        texttemplate="%{text:.2f} s",
        textposition="outside",
    )

    st.plotly_chart(
        fig_time,
        use_container_width=True,
    )


# ============================================================
# PERFORMANCE PAR DIFFICULTÉ
# ============================================================

st.header("🎯 Performance selon la difficulté")


if not filtered_difficulty.empty:

    fig_difficulty = px.bar(
        filtered_difficulty,
        x="difficulty",
        y="accuracy",
        color="model",
        barmode="group",
        text="accuracy",
        labels={
            "difficulty": "Difficulté",
            "accuracy": "Accuracy (%)",
            "model": "Modèle",
        },
        title="Accuracy par niveau de difficulté",
    )

    fig_difficulty.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
    )

    st.plotly_chart(
        fig_difficulty,
        use_container_width=True,
    )

else:

    st.info(
        "Aucune donnée disponible pour les difficultés sélectionnées."
    )


# ============================================================
# PERFORMANCE PAR CATÉGORIE
# ============================================================

st.header("📚 Performance par catégorie")


if not filtered_category.empty:

    categories = sorted(
        filtered_category["category"]
        .dropna()
        .unique()
    )

    selected_category = st.selectbox(
        "Choisir une catégorie",
        categories,
    )

    category_detail = filtered_category[
        filtered_category["category"]
        == selected_category
    ].copy()


    fig_category_detail = px.bar(
        category_detail,
        x="model",
        y="accuracy",
        color="model",
        text="accuracy",
        labels={
            "model": "Modèle",
            "accuracy": "Accuracy (%)",
        },
        title=f"Accuracy — {selected_category}",
    )


    fig_category_detail.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
    )


    st.plotly_chart(
        fig_category_detail,
        use_container_width=True,
    )


else:

    st.info(
        "Aucune donnée disponible pour les modèles sélectionnés."
    )


# ============================================================
# MEILLEURES CATÉGORIES
# ============================================================

st.subheader("📈 Meilleures performances par catégorie")


if not filtered_category.empty:

    top_categories = (
        filtered_category
        .sort_values(
            "accuracy",
            ascending=False,
        )
        .head(15)
    )


    fig_top = px.bar(
        top_categories,
        x="accuracy",
        y="category",
        color="model",
        orientation="h",
        labels={
            "accuracy": "Accuracy (%)",
            "category": "Catégorie",
            "model": "Modèle",
        },
        title="Top 15 des performances par catégorie",
    )


    st.plotly_chart(
        fig_top,
        use_container_width=True,
    )


# ============================================================
# TEMPS DE RÉPONSE
# ============================================================

st.header("⏱️ Analyse des temps de réponse")


display_time = filtered_response.copy()


display_time.columns = [
    "Modèle",
    "Questions",
    "Temps moyen (s)",
    "Temps médian (s)",
    "Temps minimum (s)",
    "Temps maximum (s)",
    "Écart-type (s)",
]


st.dataframe(
    display_time,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# SYNTHÈSE AUTOMATIQUE
# ============================================================

st.header("📝 Synthèse du benchmark")


if len(filtered_comparison) >= 1:

    best_accuracy_model = filtered_comparison.loc[
        filtered_comparison["accuracy"].idxmax(),
        "model",
    ]

    best_accuracy_value = filtered_comparison[
        "accuracy"
    ].max()


    fastest_model_name = filtered_comparison.loc[
        filtered_comparison[
            "average_response_time"
        ].idxmin(),
        "model",
    ]

    fastest_time = filtered_comparison[
        "average_response_time"
    ].min()


    st.success(
        f"""
        🏆 **Modèle le plus précis : {best_accuracy_model}**

        Accuracy : **{best_accuracy_value:.2f}%**

        ⚡ **Modèle le plus rapide : {fastest_model_name}**

        Temps de réponse moyen :
        **{fastest_time:.2f} secondes**
        """
    )


# ============================================================
# INFORMATIONS SUR LE PROJET
# ============================================================

st.divider()

st.subheader("🏗️ Architecture du projet")

st.code(
    """
Open Trivia Database
        ↓
     BRONZE
 questions_raw.csv
        ↓
     SILVER
 questions_clean.parquet
        ↓
      Ollama
 ┌───────────────┐
 │ Gemma 3 4B   │
 │ LLaMA 3.2 3B │
 └───────────────┘
        ↓
 Silver enrichie
        ↓
       dbt
        ↓
    DuckDB GOLD
        ↓
    STREAMLIT
    Dashboard
""",
    language="text",
)


st.caption(
    "Projet M1 Data Engineering & IA — Benchmark Trivial Pursuit"
)

st.caption(
    "Données : Open Trivia Database | "
    "LLM locaux : Ollama | "
    "Transformation : dbt | "
    "Stockage analytique : DuckDB"
)