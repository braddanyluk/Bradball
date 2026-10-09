
import streamlit as st
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="BradBall | Basketball Analytics",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_FILE = Path(__file__).parent / "player_seasons.csv.gz"

# --------------------------------------------------
# CUSTOM DESIGN
# --------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #101318;
        color: #F1F3F5;
    }

    [data-testid="stHeader"] {
        background-color: #101318;
    }

    [data-testid="stSidebar"] {
        background-color: #171B22;
    }

    h1, h2, h3 {
        color: #F5F5F5;
        letter-spacing: -0.5px;
    }

    .brand {
        font-size: 15px;
        font-weight: 800;
        letter-spacing: 4px;
        color: #FF8A3D;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .hero-title {
        font-size: clamp(38px, 6vw, 60px);
        font-weight: 850;
        letter-spacing: -2px;
        line-height: 1.05;
        margin: 0;
        color: #FFFFFF;
    }

    .hero-subtitle {
        font-size: 17px;
        color: #A8B0BD;
        margin-top: 12px;
        margin-bottom: 22px;
    }

    .accent {
        color: #FF8A3D;
    }

    .section-label {
        color: #FF8A3D;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    div[data-testid="stMetric"] {
        background: #191E27;
        border: 1px solid #2A303B;
        border-radius: 12px;
        padding: 18px;
    }

    div[data-testid="stMetricLabel"] {
        color: #A8B0BD;
    }

    div[data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    div[data-testid="stTabs"] button {
        font-weight: 700;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #FF8A3D;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #2A303B;
        border-radius: 10px;
        overflow: hidden;
    }

    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    .footer {
        border-top: 1px solid #2A303B;
        margin-top: 35px;
        padding-top: 18px;
        color: #87909E;
        font-size: 12px;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# DATA LOADING
# --------------------------------------------------

@st.cache_data
def load_data():
    data = pd.read_csv(
        DATA_FILE,
        compression="gzip",
        low_memory=False
    )

    # Normalize IDs so searches work consistently.
    if "player_id" in data.columns:
        data["player_id"] = data["player_id"].astype("string")

    return data


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown('<div class="brand">BRADBALL / BASKETBALL RESEARCH</div>',
            unsafe_allow_html=True)

st.markdown(
    '<div class="hero-title">The game is bigger<br>than <span class="accent">the stars.</span></div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="hero-subtitle">'
    'Players. Skills. Roles. Interactions. The things that make teams work.'
    '</div>',
    unsafe_allow_html=True
)

st.divider()

# --------------------------------------------------
# LOAD AND VALIDATE DATABASE
# --------------------------------------------------

if not DATA_FILE.exists():
    st.error(
        "Player database not found. Make sure "
        "`player_seasons.csv.gz` is in the same repository folder as `app.py`."
    )
    st.stop()

try:
    df = load_data()
except Exception as error:
    st.error(f"Unable to load the player database: {error}")
    st.stop()

if "player_id" not in df.columns:
    st.error("The dataset is missing the required player_id column.")
    st.stop()

player_ids = sorted(df["player_id"].dropna().unique().tolist())

# --------------------------------------------------
# DATABASE OVERVIEW
# --------------------------------------------------

overview1, overview2, overview3 = st.columns(3)

overview1.metric(
    "PLAYER-SEASONS",
    f"{len(df):,}"
)

overview2.metric(
    "UNIQUE PLAYERS",
    f"{df['player_id'].nunique():,}"
)

overview3.metric(
    "STAT COLUMNS",
    f"{len(df.columns):,}"
)

st.write("")

# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------

players_tab, compare_tab, lab_tab = st.tabs([
    "🏀  Player Explorer",
    "⚖️  Compare",
    "🧪  Data Lab",
])

# --------------------------------------------------
# PLAYER EXPLORER
# --------------------------------------------------

with players_tab:
    st.markdown(
        '<div class="section-label">01 / Player Explorer</div>',
        unsafe_allow_html=True
    )

    st.header("Explore a career")

    st.write(
        "Examine a player's seasons, production, and development over time."
    )

    selected_id = st.selectbox(
        "Player ID",
        player_ids,
        key="explorer_player",
        help="We'll replace this with player-name search when we connect the name mapping."
    )

    player_df = df[df["player_id"] == selected_id].copy()

    if "Season" in player_df.columns:
        player_df = player_df.sort_values("Season")

    # Useful career overview metrics.
    metric_columns = st.columns(3)

    if "G" in player_df.columns:
        games = pd.to_numeric(player_df["G"], errors="coerce").sum()
        metric_columns[0].metric(
            "Games recorded",
            f"{games:,.0f}" if pd.notna(games) else "—"
        )

    if "PTS" in player_df.columns:
        points = pd.to_numeric(player_df["PTS"], errors="coerce")
        metric_columns[1].metric(
            "Average listed points",
            f"{points.mean():.1f}" if points.notna().any() else "—"
        )

    metric_columns[2].metric(
        "Seasons",
        f"{len(player_df)}"
    )

    st.markdown("#### Season history")

    preferred_stats = [
        "Season", "Age", "Tm", "G", "GS", "MP",
        "PTS", "TRB", "AST", "STL", "BLK", "TOV",
        "FG%", "3P%", "FT%", "PER", "WS", "VORP"
    ]

    visible_stats = [
        column for column in preferred_stats
        if column in player_df.columns
    ]

    if visible_stats:
        st.dataframe(
            player_df[visible_stats],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.dataframe(
            player_df,
            use_container_width=True,
            hide_index=True
        )

    if "Season" in player_df.columns and "PTS" in player_df.columns:
        st.markdown("#### Scoring across seasons")

        chart_df = player_df[["Season", "PTS"]].copy()
        chart_df["PTS"] = pd.to_numeric(
            chart_df["PTS"], errors="coerce"
        )
        chart_df = chart_df.dropna(subset=["PTS"])

        if not chart_df.empty:
            st.line_chart(
                chart_df.set_index("Season")["PTS"],
                use_container_width=True
            )

# --------------------------------------------------
# PLAYER COMPARISON
# --------------------------------------------------

with compare_tab:
    st.markdown(
        '<div class="section-label">02 / Player Comparison</div>',
        unsafe_allow_html=True
    )

    st.header("Compare player seasons")

    st.write(
        "Put two players' statistical records side by side. "
        "This is a descriptive comparison, not a measure of overall value."
    )

    left, right = st.columns(2)

    with left:
        first_id = st.selectbox(
            "First player ID",
            player_ids,
            key="compare_first"
        )

    alternative_ids = [pid for pid in player_ids if pid != first_id]

    with right:
        second_id = st.selectbox(
            "Second player ID",
            alternative_ids,
            key="compare_second"
        )

    first_df = df[df["player_id"] == first_id].copy()
    second_df = df[df["player_id"] == second_id].copy()

    stats = [
        "Season", "Age", "Tm", "G", "MP", "PTS",
        "TRB", "AST", "STL", "BLK", "TOV",
        "FG%", "3P%", "FT%", "PER", "WS", "VORP"
    ]

    first_cols = [c for c in stats if c in first_df.columns]
    second_cols = [c for c in stats if c in second_df.columns]

    first_name, second_name = st.columns(2)

    with first_name:
        st.markdown("#### Player A")
        st.caption(f"ID: {first_id}")
        st.dataframe(
            first_df[first_cols],
            use_container_width=True,
            hide_index=True
        )

    with second_name:
        st.markdown("#### Player B")
        st.caption(f"ID: {second_id}")
        st.dataframe(
            second_df[second_cols],
            use_container_width=True,
            hide_index=True
        )

# --------------------------------------------------
# DATA LAB
# --------------------------------------------------

with lab_tab:
    st.markdown(
        '<div class="section-label">03 / Data Lab</div>',
        unsafe_allow_html=True
    )

    st.header("Inspect the evidence")

    st.write(
        "Check what the database contains before drawing conclusions."
    )

    st.markdown("#### Database structure")

    structure1, structure2 = st.columns(2)

    structure1.metric("Rows", f"{len(df):,}")
    structure2.metric("Columns", f"{len(df.columns):,}")

    st.markdown("#### Available variables")

    st.dataframe(
        pd.DataFrame({"Column": df.columns.astype(str)}),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("#### Sample records")

    st.dataframe(
        df.head(20),
        use_container_width=True,
        hide_index=True
    )

st.markdown(
    '<div class="footer">'
    'BRADBALL &nbsp; / &nbsp; DATA BEFORE ASSUMPTIONS &nbsp; / &nbsp; '
    'FIT, CONTEXT & INTERACTION'
    '</div>',
    unsafe_allow_html=True
)

