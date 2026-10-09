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
NAME_FILE = Path(__file__).parent / "player_team_seasons.csv"

# --------------------------------------------------
# CUSTOM DESIGN
# --------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #101318;
        color: #FFFFFF;
    }

    /* Improve text contrast throughout the app */
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp li,
    [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"],
    [data-testid="stCaptionContainer"] {
        color: #FFFFFF;
    }

    [data-testid="stHeader"] {
        background-color: #101318;
    }

    [data-testid="stSidebar"] {
        background-color: #171B22;
    }

    h1, h2, h3, h4 {
        color: #FFFFFF;
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
        color: #D0D0D0;
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
        color: #FFFFFF;
    }

    div[data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    div[data-testid="stTabs"] button {
        font-weight: 700;
        color: #FFFFFF;
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
        color: #D0D0D0;
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

    names = pd.read_csv(NAME_FILE, low_memory=False)

    # Make player IDs consistent between the two files.
    data["player_id"] = data["player_id"].astype("string").str.strip()
    names["player_id"] = names["player_id"].astype("string").str.strip()

    # Clean the name mapping.
    names = names.dropna(subset=["player_id", "player"])

    names["player"] = names["player"].astype(str).str.strip()
    names = names[names["player"] != ""]

    # Each player ID should map to one display name.
    name_lookup = (
        names.drop_duplicates("player_id")
        .set_index("player_id")["player"]
    )

    # Add names to every player-season record.
    data["player_name"] = data["player_id"].map(name_lookup)
    data["player_name"] = data["player_name"].fillna("Unknown player")

        # Compatibility aliases for the existing app interface.
    column_map = {
        "GamesPlayed": "G",
        "Points": "PTS",
        "Rebounds": "TRB",
        "Assists": "AST",
        "Steals": "STL",
        "Blocks": "BLK",
        "Turnovers": "TOV",
        "Minutes": "MP",
    }

    for source, target in column_map.items():
        if source in data.columns:
            data[target] = data[source]

    return data


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    '<div class="brand">BRADBALL / BASKETBALL RESEARCH</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="hero-title">The game is bigger<br>than '
    '<span class="accent">the stars.</span></div>',
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

if not NAME_FILE.exists():
    st.error(
        "Player-name database not found. Make sure "
        "`player_team_seasons.csv` is in the same repository folder as `app.py`."
    )
    st.stop()

try:
    df = load_data()
except Exception as error:
    st.error(f"Unable to load the databases: {error}")
    st.stop()

required_columns = ["player_id", "player_name"]

if not all(column in df.columns for column in required_columns):
    st.error("The database is missing a required player ID or name column.")
    st.stop()

# One display label per player ID.
player_lookup = (
    df[["player_id", "player_name"]]
    .dropna(subset=["player_id"])
    .drop_duplicates("player_id")
    .copy()
)

player_lookup["player_label"] = (
    player_lookup["player_name"].astype(str)
    + " ("
    + player_lookup["player_id"].astype(str)
    + ")"
)

player_lookup = player_lookup.sort_values(
    "player_name",
    key=lambda column: column.str.lower()
)

player_options = dict(
    zip(player_lookup["player_label"], player_lookup["player_id"])
)

player_labels = list(player_options.keys())

# --------------------------------------------------
# DATABASE OVERVIEW
# --------------------------------------------------

overview1, overview2, overview3 = st.columns(3)

overview1.metric("PLAYER-SEASONS", f"{len(df):,}")
overview2.metric("UNIQUE PLAYERS", f"{df['player_id'].nunique():,}")
overview3.metric("STAT COLUMNS", f"{len(df.columns):,}")

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

    selected_label = st.selectbox(
        "Choose a player",
        player_labels,
        key="explorer_player",
    )

    selected_id = player_options[selected_label]

    player_df = df[df["player_id"] == selected_id].copy()

    if "Season" in player_df.columns:
        player_df = player_df.sort_values("Season")

    st.markdown(f"### {player_df['player_name'].iloc[0]}")

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

    metric_columns[2].metric("Seasons", f"{len(player_df)}")

    st.markdown("#### Season history")



        preferred_stats = [
        "Season", "Age", "Tm",
        "GamesPlayed", "Minutes", "SecondsPlayed",

        # Traditional statistics
        "Points", "Rebounds", "Assists",
        "Steals", "Blocks", "Turnovers",
        "PlusMinus",

        # Shooting
        "FG2M", "FG2A", "FG3M", "FG3A",
        "FtPoints", "AtRimFGM", "AtRimFGA",
        "ShortMidRangeFGM", "ShortMidRangeFGA",
        "LongMidRangeFGM", "LongMidRangeFGA",
        "Corner3FGM", "Corner3FGA", "Arc3FGA",

        # Passing and shot creation
        "PtsAssisted2s", "PtsUnassisted2s",
        "PtsAssisted3s", "PtsUnassisted3s",
        "TwoPtAssists", "ThreePtAssists",

        # Rebounding
        "OffRebounds", "DefRebounds",

        # Possessions and turnovers
        "OffPoss", "DefPoss", "TotalPoss",
        "LiveBallTurnovers", "BadPassTurnovers",
        "LostBallTurnovers",
    ]
    

    visible_stats = [
        column for column in preferred_stats
        if column in player_df.columns
    ]

    if "Season" in player_df.columns and not player_df.empty:
        seasons = player_df["Season"].astype(str).tolist()

        selected_season = st.selectbox(
            "Choose a season for the full statistical breakdown",
            seasons,
            key="selected_season"
        )

        season_details = player_df[
            player_df["Season"].astype(str) == selected_season
        ].copy()

        st.markdown(f"### {selected_season} — Season Statistics")

        # Show the selected season's stats in a readable table.
        if not season_details.empty:
            st.dataframe(
                season_details[visible_stats],
                use_container_width=True,
                hide_index=True
            )

            # Highlight some key statistics when available.
            key_stats = [
                ("Points", "PTS"),
                ("Rebounds", "TRB"),
                ("Assists", "AST"),
                ("Games", "G"),
                ("Minutes", "MP"),
            ]

            available_stats = [
                (label, column)
                for label, column in key_stats
                if column in season_details.columns
            ]

            if available_stats:
                st.markdown("#### Key statistics")
                stat_columns = st.columns(len(available_stats))

                for column, (label, stat) in zip(
                    stat_columns, available_stats
                ):
                    value = pd.to_numeric(
                        season_details[stat], errors="coerce"
                    ).iloc[0]

                    display_value = (
                        f"{value:,.1f}" if pd.notna(value) else "—"
                    )

                    column.metric(label, display_value)

    else:
        st.info("Season information is not available for this player.")

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
        first_label = st.selectbox(
            "First player",
            player_labels,
            key="compare_first"
        )

    first_id = player_options[first_label]

    alternative_labels = [
        label for label in player_labels
        if player_options[label] != first_id
    ]

    with right:
        second_label = st.selectbox(
            "Second player",
            alternative_labels,
            key="compare_second"
        )

    second_id = player_options[second_label]

    first_df = df[df["player_id"] == first_id].copy()
    second_df = df[df["player_id"] == second_id].copy()

    stats = [
        "Season", "Age", "Tm", "G", "MP", "PTS",
        "TRB", "AST", "STL", "BLK", "TOV",
        "FG%", "3P%", "FT%", "PER", "WS", "VORP"
    ]

    first_cols = [column for column in stats if column in first_df.columns]
    second_cols = [column for column in stats if column in second_df.columns]

    first_name, second_name = st.columns(2)

    with first_name:
        st.markdown(f"#### {first_df['player_name'].iloc[0]}")
        st.dataframe(
            first_df[first_cols],
            use_container_width=True,
            hide_index=True
        )

    with second_name:
        st.markdown(f"#### {second_df['player_name'].iloc[0]}")
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
