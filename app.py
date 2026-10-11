import re

import numpy as np
import pandas as pd
import streamlit as st
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
        position: sticky;
        top: 0;
        z-index: 999;
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

    data["player_id"] = data["player_id"].astype("string").str.strip()
    names["player_id"] = names["player_id"].astype("string").str.strip()

    names = names.dropna(subset=["player_id", "player"])

    names["player"] = names["player"].astype(str).str.strip()
    names = names[names["player"] != ""]

    name_lookup = (
        names.drop_duplicates("player_id")
        .set_index("player_id")["player"]
    )

    data["player_name"] = data["player_id"].map(name_lookup)
    data["player_name"] = data["player_name"].fillna("Unknown player")

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

    # Per-100 stats using half of total possessions.
    if "TotalPoss" in data.columns:
        total_possessions = pd.to_numeric(
            data["TotalPoss"], errors="coerce"
        )
        denominator = total_possessions / 2

        excluded_stats = {
            "Season", "Age", "Tm", "Player", "player_name",
            "player_id", "PlayerId", "GamesPlayed",
            "Minutes", "SecondsPlayed", "TotalPoss",
            "OffPoss", "DefPoss",
        }

        for column in data.columns:
            if column in excluded_stats or column.endswith("/100"):
                continue

            if not pd.api.types.is_numeric_dtype(data[column]):
                continue

            name_lower = column.lower()
            if any(term in name_lower for term in [
                "pct", "percent", "percentage", "rate",
                "ratio", "share", "usage",
            ]):
                continue

            values = pd.to_numeric(data[column], errors="coerce")
            data[f"{column}/100"] = (
                values.div(denominator).mul(100)
            ).where(denominator > 0).round(2)

    return data


# --------------------------------------------------
# ANALYSIS HELPERS
# --------------------------------------------------

def weighted_corr(x, y, w):
    """Weighted Pearson correlation. Returns NaN if undefined."""
    x = pd.to_numeric(x, errors="coerce")
    y = pd.to_numeric(y, errors="coerce")
    w = pd.to_numeric(w, errors="coerce")

    ok = x.notna() & y.notna() & w.notna() & (w > 0)
    x, y, w = x[ok].astype(float), y[ok].astype(float), w[ok].astype(float)

    if len(x) < 3 or w.sum() <= 0:
        return float("nan")

    mx = (w * x).sum() / w.sum()
    my = (w * y).sum() / w.sum()
    dx, dy = x - mx, y - my

    vx = (w * dx.pow(2)).sum() / w.sum()
    vy = (w * dy.pow(2)).sum() / w.sum()

    if vx <= 0 or vy <= 0:
        return float("nan")

    return float(((w * dx * dy).sum() / w.sum()) / (vx * vy) ** 0.5)


def within_group_z(data, groups):
    """Z-score every column within each group (e.g. each season).

    This stops league-wide trends (like the rise of the three-pointer)
    from creating fake relationships across eras.
    """
    grouped = data.groupby(groups)
    mean = grouped.transform("mean")
    std = grouped.transform("std")
    z = (data - mean) / std
    return z.replace([np.inf, -np.inf], np.nan)


def is_rate_column(name):
    """True for per-100 stats, percentages, shares and other rates."""
    lowered = name.lower()
    return (
        name.endswith("/100")
        or "%" in name
        or any(term in lowered for term in [
            "pct", "percent", "rate", "ratio", "share", "usage",
        ])
    )


def stat_stem(name):
    """Rough 'family' of a stat so FG3M and FG3A count as the same thing."""
    s = name.replace("/100", "").lower()
    s = re.sub(r"(?<=\d)[ma]$|fg[ma]$", "", s)
    for token in ("made", "attempts", "pct"):
        s = s.replace(token, "")
    return s.strip("_ ")


def is_near_duplicate(a, b):
    """Hide pairs like FG3M vs FG3A that are related by definition."""
    sa, sb = stat_stem(a), stat_stem(b)
    if not sa or not sb:
        return False
    return sa == sb or sa.startswith(sb) or sb.startswith(sa)


@st.cache_data(show_spinner="Calculating statistical relationships...")
def calculate_relationships(data, weight_values, hide_duplicates):
    corr = data.corr(min_periods=30)

    valid = data.notna().astype("int32")
    sample_sizes = valid.T.dot(valid)

    columns = np.array(data.columns)
    rows, cols = np.triu_indices(len(columns), k=1)

    relationships = pd.DataFrame({
        "Statistic A": columns[rows],
        "Statistic B": columns[cols],
        "Correlation": corr.values[rows, cols],
        "Player-seasons": sample_sizes.values[rows, cols],
    })

    relationships = relationships.dropna(subset=["Correlation"])
    relationships = relationships[relationships["Player-seasons"] >= 30]

    if hide_duplicates and not relationships.empty:
        keep = [
            not is_near_duplicate(a, b)
            for a, b in zip(
                relationships["Statistic A"],
                relationships["Statistic B"],
            )
        ]
        relationships = relationships[keep]

    relationships = relationships.reset_index(drop=True)
    relationships["Minutes-weighted"] = np.nan

    if weight_values is not None and not relationships.empty:
        candidates = relationships.assign(
            abs_r=relationships["Correlation"].abs()
        ).nlargest(200, "abs_r")

        for idx, row in candidates.iterrows():
            relationships.loc[idx, "Minutes-weighted"] = weighted_corr(
                data[row["Statistic A"]],
                data[row["Statistic B"]],
                weight_values,
            )

    return relationships


@st.cache_data(show_spinner="Building team-season table...")
def build_team_seasons(data):
    """Sum player-seasons into team-seasons and derive team-level metrics.

    Team possessions are approximated as (sum of every player's offensive
    possessions) / 5, since five players are on the floor at once.
    """
    if "Tm" not in data.columns or "Season" not in data.columns:
        return pd.DataFrame()

    d = data.copy()

    # Drop combined rows for traded players so nobody is double counted.
    is_combined = (
        d["Tm"].astype(str).str.upper().str.match(r"^(TOT|\dTM)$")
    )
    d = d[~is_combined]

    sum_columns = [
        "Points", "FG2M", "FG2A", "FG3M", "FG3A", "FtPoints",
        "AtRimFGM", "AtRimFGA", "ShortMidRangeFGA", "LongMidRangeFGA",
        "Corner3FGA", "Arc3FGA", "Turnovers", "OffRebounds",
        "Assists", "OffPoss",
    ]
    sum_columns = [c for c in sum_columns if c in d.columns]

    if not sum_columns:
        return pd.DataFrame()

    d[sum_columns] = d[sum_columns].apply(pd.to_numeric, errors="coerce")

    t = d.groupby(["Season", "Tm"], as_index=False)[sum_columns].sum()

    def has(*cols):
        return all(c in t.columns for c in cols)

    if has("FG2A", "FG3A"):
        t["FGA"] = t["FG2A"] + t["FG3A"]
    if has("OffPoss"):
        t["TeamPoss"] = t["OffPoss"] / 5

    out = t[["Season", "Tm"]].copy()

    def safe_div(num, den):
        return (num / den).where(den > 0)

    if has("FG3A", "FGA"):
        out["3PA share of shots"] = safe_div(t["FG3A"], t["FGA"])
    if has("AtRimFGA", "FGA"):
        out["Rim share of shots"] = safe_div(t["AtRimFGA"], t["FGA"])
    if has("ShortMidRangeFGA", "LongMidRangeFGA", "FGA"):
        out["Mid-range share of shots"] = safe_div(
            t["ShortMidRangeFGA"] + t["LongMidRangeFGA"], t["FGA"]
        )
    if has("Corner3FGA", "FG3A"):
        out["Corner share of 3PA"] = safe_div(t["Corner3FGA"], t["FG3A"])
    if has("FG3M", "FG3A"):
        out["3P%"] = safe_div(t["FG3M"], t["FG3A"])
    if has("AtRimFGM", "AtRimFGA"):
        out["Rim FG%"] = safe_div(t["AtRimFGM"], t["AtRimFGA"])

    if has("TeamPoss"):
        per100 = {
            "Points": "Points per 100 poss",
            "Turnovers": "Turnovers per 100 poss",
            "OffRebounds": "Off. rebounds per 100 poss",
            "Assists": "Assists per 100 poss",
            "FtPoints": "Free-throw points per 100 poss",
        }
        for source, label in per100.items():
            if source in t.columns:
                out[label] = safe_div(t[source], t["TeamPoss"]) * 100

    return out


def render_relationship(frame, x_col, y_col, weights=None, unit="rows"):
    """Metrics + scatterplot + caveat for any two columns of `frame`."""
    pair = frame[[x_col, y_col]].dropna()

    x, y = pair[x_col], pair[y_col]
    ordinary_r = x.corr(y)

    weighted_r = float("nan")
    if weights is not None:
        weighted_r = weighted_corr(x, y, weights.loc[pair.index])

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Correlation",
        f"{ordinary_r:+.3f}" if pd.notna(ordinary_r) else "—",
    )
    if weights is not None:
        c2.metric(
            "Minutes-weighted correlation",
            f"{weighted_r:+.3f}" if pd.notna(weighted_r) else "—",
        )
    c3.metric("Sample size", f"{len(pair):,} {unit}")

    st.scatter_chart(pair, x=x_col, y=y_col, use_container_width=True)

    st.caption(
        "Correlations range from -1 to +1. Positive means the statistics "
        "tend to rise together; negative means an inverse relationship. "
        "A relationship is not proof of cause."
    )


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

players_tab, compare_tab, lab_tab, team_tab = st.tabs([
    "🏀 Player Explorer",
    "⚖️ Compare",
    "🧪 Data Lab",
    "🏟️ Team Lab",
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

        "Points", "Rebounds", "Assists",
        "Steals", "Blocks", "Turnovers",
        "PlusMinus",

        "FG2M", "FG2A", "FG3M", "FG3A",
        "FtPoints", "AtRimFGM", "AtRimFGA",
        "ShortMidRangeFGM", "ShortMidRangeFGA",
        "LongMidRangeFGM", "LongMidRangeFGA",
        "Corner3FGM", "Corner3FGA", "Arc3FGA",

        "PtsAssisted2s", "PtsUnassisted2s",
        "PtsAssisted3s", "PtsUnassisted3s",
        "TwoPtAssists", "ThreePtAssists",

        "OffRebounds", "DefRebounds",

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

        if not season_details.empty:
            games = pd.to_numeric(
                season_details["GamesPlayed"], errors="coerce"
            )

            for stat in ["Points", "Rebounds", "Assists", "Steals",
                         "Blocks", "Turnovers"]:
                if stat in season_details.columns:
                    season_details[f"{stat}PerGame"] = (
                        pd.to_numeric(season_details[stat], errors="coerce")
                        / games
                    ).where(games > 0).round(1)

            visible_stats = [
                column for column in preferred_stats
                if column in season_details.columns
            ] + [
                f"{stat}PerGame"
                for stat in ["Points", "Rebounds", "Assists", "Steals",
                             "Blocks", "Turnovers"]
                if f"{stat}PerGame" in season_details.columns
            ]

            st.dataframe(
                season_details[visible_stats],
                use_container_width=True,
                hide_index=True
            )

            with st.expander(
                "🔬 Explore All Available Stats",
                expanded=False
            ):
                st.write(
                    "Explore the full statistical profile for this player-season."
                )

                raw_data = season_details.copy()

                duplicate_aliases = [
                    "G", "PTS", "TRB", "AST",
                    "STL", "BLK", "TOV", "MP"
                ]

                raw_data = raw_data.drop(
                    columns=[
                        col for col in duplicate_aliases
                        if col in raw_data.columns
                    ],
                    errors="ignore"
                )
                raw_data = raw_data[
                    sorted(raw_data.columns, key=str.lower)
                ]

                raw_data = raw_data.drop(
                    columns=[
                        col for col in raw_data.columns
                        if col.endswith("PerGame")
                    ],
                    errors="ignore"
                )

                search_term = st.text_input(
                    "🔎 Search statistics",
                    placeholder="Try: turnover, assist, rim, possession...",
                    key="raw_data_search"
                )

                if search_term.strip():
                    matching_columns = [
                        col for col in raw_data.columns
                        if search_term.lower() in str(col).lower()
                    ]
                    raw_data = raw_data[matching_columns]

                if len(raw_data.columns) == 0:
                    st.info("No statistics matched that search.")
                else:
                    st.caption(
                        f"Showing {len(raw_data.columns)} statistics"
                    )

                    stat_columns = st.columns(3)

                    for index, column in enumerate(raw_data.columns):
                        value = raw_data[column].iloc[0]

                        if pd.isna(value):
                            display_value = "—"
                        elif isinstance(value, (int, float)):
                            display_value = (
                                f"{value:,.2f}".rstrip("0").rstrip(".")
                            )
                        else:
                            display_value = str(value)

                        with stat_columns[index % 3]:
                            with st.container(border=True):
                                st.caption(str(column))
                                st.markdown(f"### {display_value}")

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
# DATA LAB (player-season relationships)
# --------------------------------------------------

with lab_tab:
    st.markdown(
        '<div class="section-label">03 / Data Lab</div>',
        unsafe_allow_html=True
    )

    st.header("Relationship Explorer")

    st.write(
        "Discover which statistical characteristics tend to move "
        "together across player-seasons."
    )

    # ---- Controls ----
    f1, f2, f3, f4 = st.columns(4)

    with f1:
        rates_only = st.checkbox(
            "Rates only (per-100, %, shares)",
            value=True,
            help="Raw totals mostly measure playing time, so they "
                 "correlate with each other for boring reasons.",
        )
    with f2:
        within_season = st.checkbox(
            "Compare within each season",
            value=True,
            help="Converts each stat to a z-score inside its own season, "
                 "so league-wide trends don't create fake relationships.",
        )
    with f3:
        hide_duplicates = st.checkbox(
            "Hide near-duplicate pairs",
            value=True,
            help="Hides pairs like FG3M vs FG3A that are linked by definition.",
        )
    with f4:
        min_minutes = st.slider(
            "Minimum minutes",
            min_value=0,
            max_value=2000,
            value=300,
            step=50,
            help="Set to 0 to include everyone.",
        )

    # ---- Minutes column (for filter and weighting) ----
    if "Minutes" in df.columns:
        minutes = pd.to_numeric(df["Minutes"], errors="coerce")
    elif "SecondsPlayed" in df.columns:
        minutes = pd.to_numeric(df["SecondsPlayed"], errors="coerce") / 60
    else:
        minutes = None

    if minutes is not None:
        lab_mask = minutes.fillna(0) >= min_minutes
    else:
        lab_mask = pd.Series(True, index=df.index)

    lab_df = df[lab_mask]
    lab_weights = minutes[lab_mask] if minutes is not None else None

    # ---- Choose columns ----
    excluded_names = {
        "player_id", "player_name", "player", "season",
        "age", "year", "rank", "number", "jersey",
        "team", "tm", "gamesplayed", "g",
        "minutes", "secondsplayed", "mp",
        "totalposs", "offposs", "defposs",
    }
    alias_columns = {
        "PTS", "TRB", "AST", "STL", "BLK", "TOV", "MP", "G",
    }

    numeric_data = pd.DataFrame(index=lab_df.index)

    for column in lab_df.columns:
        if column.lower() in excluded_names or column in alias_columns:
            continue
        if column.endswith("PerGame"):
            continue
        if rates_only and not is_rate_column(column):
            continue

        values = pd.to_numeric(lab_df[column], errors="coerce")

        if values.notna().sum() < 30:
            continue
        if values.nunique(dropna=True) < 2:
            continue

        numeric_data[column] = values

    if within_season and "Season" in lab_df.columns and len(numeric_data.columns):
        numeric_data = within_group_z(numeric_data, lab_df["Season"])

    if len(numeric_data.columns) < 2 or len(numeric_data) < 30:
        st.warning(
            "Not enough data with these settings. Try lowering the "
            "minimum minutes or turning off 'Rates only'."
        )

    else:
        relationships = calculate_relationships(
            numeric_data,
            lab_weights,
            hide_duplicates,
        )

        if relationships.empty:
            st.warning("No valid relationships could be calculated.")

        else:
            st.caption(
                f"Analyzed {len(numeric_data.columns)} statistics across "
                f"{len(numeric_data):,} player-seasons. Minutes-weighted "
                "results are calculated for the 200 strongest ordinary "
                "relationships."
            )

            ranking_choice = st.radio(
                "Explore relationships",
                [
                    "Strongest positive",
                    "Strongest negative",
                    "Weakest relationships",
                ],
                horizontal=True,
                key="relationship_ranking",
            )

            if ranking_choice == "Strongest positive":
                ranked = relationships.sort_values(
                    "Correlation", ascending=False
                )
            elif ranking_choice == "Strongest negative":
                ranked = relationships.sort_values(
                    "Correlation", ascending=True
                )
            else:
                ranked = relationships.assign(
                    abs_r=relationships["Correlation"].abs()
                ).sort_values("abs_r")

            st.dataframe(
                ranked.head(20)[
                    [
                        "Statistic A",
                        "Statistic B",
                        "Correlation",
                        "Minutes-weighted",
                        "Player-seasons",
                    ]
                ].style.format({
                    "Correlation": "{:+.3f}",
                    "Minutes-weighted": "{:+.3f}",
                }),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("#### Investigate a relationship")

            available_stats = sorted(
                numeric_data.columns,
                key=str.lower,
            )

            first_stat, second_stat = st.columns(2)

            with first_stat:
                selected_x = st.selectbox(
                    "First statistic",
                    available_stats,
                    key="relationship_x",
                )

            with second_stat:
                selected_y = st.selectbox(
                    "Second statistic",
                    [col for col in available_stats if col != selected_x],
                    key="relationship_y",
                )

            render_relationship(
                numeric_data,
                selected_x,
                selected_y,
                weights=lab_weights,
                unit="player-seasons",
            )

            st.info(
                "Research note: players contribute multiple seasons, so "
                "observations are not independent. Player-level "
                "relationships also reflect position (guards shoot threes, "
                "centers shoot at the rim). For questions about how a "
                "team plays, use the Team Lab."
            )

# --------------------------------------------------
# TEAM LAB (team-season relationships)
# --------------------------------------------------

with team_tab:
    st.markdown(
        '<div class="section-label">04 / Team Lab</div>',
        unsafe_allow_html=True
    )

    st.header("How teams play")

    st.write(
        "Each dot is one team in one season. Use this for questions about "
        "style, like whether shooting more threes goes with more shots at "
        "the rim."
    )

    teams = build_team_seasons(df)

    if teams.empty:
        st.warning(
            "Couldn't build team seasons. This needs `Season` and `Tm` "
            "columns plus shot-zone and possession columns."
        )
    else:
        metric_names = [
            c for c in teams.columns if c not in ("Season", "Tm")
        ]

        team_z = st.checkbox(
            "Compare within each season",
            value=True,
            key="team_within_season",
            help="Measures each team against the league average of its "
                 "own season, which removes era trends.",
        )

        if team_z:
            team_values = within_group_z(
                teams[metric_names], teams["Season"]
            )
        else:
            team_values = teams[metric_names].copy()

        tx, ty = st.columns(2)

        default_x = (
            metric_names.index("3PA share of shots")
            if "3PA share of shots" in metric_names else 0
        )

        with tx:
            team_x = st.selectbox(
                "First statistic",
                metric_names,
                index=default_x,
                key="team_x",
            )

        y_options = [m for m in metric_names if m != team_x]
        default_y = (
            y_options.index("Rim share of shots")
            if "Rim share of shots" in y_options else 0
        )

        with ty:
            team_y = st.selectbox(
                "Second statistic",
                y_options,
                index=default_y,
                key="team_y",
            )

        render_relationship(team_values, team_x, team_y, unit="team-seasons")

        with st.expander("See the team-season table"):
            st.dataframe(
                teams.round(3),
                use_container_width=True,
                hide_index=True,
            )

        st.caption(
            "Team possessions are estimated from player data (the sum of "
            "each player's offensive possessions divided by 5), so "
            "per-100 numbers are approximate."
        )

st.markdown(
    '<div class="footer">'
    'BRADBALL &nbsp; / &nbsp; DATA BEFORE ASSUMPTIONS &nbsp; / &nbsp; '
    'FIT, CONTEXT & INTERACTION'
    '</div>',
    unsafe_allow_html=True
)
