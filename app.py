import html
import re
import zlib

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

    .headshot {
        position: relative;
        flex: 0 0 auto;
        overflow: hidden;
        border-radius: 12px;
        background: linear-gradient(160deg, #232A36 0%, #171B22 100%);
        border: 1px solid #2A303B;
        border-bottom: 3px solid #FF8A3D;
    }

    /* Shown when there is no picture, or while it loads. */
    .headshot-initials {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 850;
        letter-spacing: 2px;
        color: #3A4352;
    }

    .headshot img {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: contain;
        object-position: center bottom;
    }

    .player-card {
        display: flex;
        align-items: center;
        gap: 22px;
        background: #191E27;
        border: 1px solid #2A303B;
        border-radius: 14px;
        padding: 14px 24px 14px 14px;
        margin: 6px 0 16px 0;
    }

    .player-card-name {
        font-size: clamp(24px, 4vw, 34px);
        font-weight: 850;
        letter-spacing: -1px;
        line-height: 1.1;
        color: #FFFFFF;
    }

    .player-card-sub {
        font-size: 14px;
        color: #D0D0D0;
        margin-top: 6px;
    }

    .mini-player {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 4px 0 10px 0;
    }

    .mini-player-name {
        font-weight: 700;
        font-size: 14px;
        color: #FFFFFF;
        line-height: 1.2;
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
# PLAYER PICTURES
# --------------------------------------------------

HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png"


def headshot_url(player_id):
    """NBA.com headshot for a stats.nba.com player ID, or None."""
    text = str(player_id).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return HEADSHOT_URL.format(player_id=text) if text.isdigit() else None


def name_initials(name):
    parts = [p for p in re.split(r"[\s.\-]+", str(name)) if p]
    letters = [p[0] for p in parts[:2]]
    return "".join(letters).upper() or "?"


def avatar_html(player_id, name, width=190):
    """A headshot with an initials badge behind it.

    If NBA.com has no picture for this player (or the link is blocked),
    the image simply doesn't draw and the initials show instead.
    """
    height = round(width * 190 / 260)
    url = headshot_url(player_id)
    image = (
        f'<img src="{url}" alt="" loading="lazy" '
        f'referrerpolicy="no-referrer">'
        if url else ""
    )
    return (
        f'<div class="headshot" style="width:{width}px;height:{height}px;">'
        f'<div class="headshot-initials" '
        f'style="font-size:{round(width * 0.22)}px;">'
        f'{html.escape(name_initials(name))}</div>{image}</div>'
    )


def player_card_html(player_id, name, subtitle=""):
    return (
        '<div class="player-card">'
        + avatar_html(player_id, name, 190)
        + '<div><div class="player-card-name">'
        + html.escape(str(name))
        + '</div><div class="player-card-sub">'
        + html.escape(subtitle)
        + "</div></div></div>"
    )


def mini_player_html(player_id, name, subtitle=""):
    return (
        '<div class="mini-player">'
        + avatar_html(player_id, name, 84)
        + '<div><div class="mini-player-name">'
        + html.escape(str(name))
        + '</div><div class="player-card-sub" style="margin-top:2px;">'
        + html.escape(subtitle)
        + "</div></div></div>"
    )


def career_summary(player_rows):
    """'1998-99 to 2015-16 · 18 seasons · LAL, MIA' for a player."""
    parts = []
    if "Season" in player_rows.columns and len(player_rows):
        seasons = player_rows["Season"].astype(str)
        first, last = seasons.min(), seasons.max()
        parts.append(first if first == last else f"{first} to {last}")
        parts.append(f"{seasons.nunique()} seasons")
    if "Tm" in player_rows.columns:
        teams = [
            t for t in player_rows["Tm"].astype(str).unique()
            if not re.match(r"^(TOT|\dTM)$", t.upper()) and t != "nan"
        ]
        if teams:
            shown = ", ".join(teams[:4])
            parts.append(shown + ("..." if len(teams) > 4 else ""))
    return " · ".join(parts)


# --------------------------------------------------
# DATA LOADING
# --------------------------------------------------

@st.cache_resource
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

    # Recognize common alternate names for the team and season columns.
    def rename_to(target, candidates):
        if target in data.columns:
            return
        lowered = {c.lower(): c for c in data.columns}
        for candidate in candidates:
            if candidate.lower() in lowered:
                data[target] = data[lowered[candidate.lower()]]
                return

    rename_to("Tm", ["Team", "TeamAbbreviation", "team_abbreviation",
                      "TeamAbbr", "Team_Abbreviation", "TeamName", "Squad"])
    rename_to("Season", ["Year", "SeasonYear", "season_year"])

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

    # Keep the full dataset, but use compact storage for the many numeric columns.
    # Float32 is sufficient for these displayed and modeled statistics.
    for column in data.select_dtypes(include=["integer"]).columns:
        data[column] = pd.to_numeric(data[column], downcast="integer")
    for column in data.select_dtypes(include=["floating"]).columns:
        data[column] = pd.to_numeric(data[column], downcast="float")

    # These labels repeat across player-seasons; categorical storage avoids
    # keeping a separate copy of each string in every row.
    for column in ("player_id", "player_name"):
        if column in data.columns:
            data[column] = data[column].astype("category")

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


STAT_GROUP_ORDER = [
    "Scoring & shooting", "Shot locations", "Shot creation", "Playmaking",
    "Rebounding", "Defense", "Turnovers", "Free throws & fouls", "Other",
]

# First match wins, so order matters (e.g. DefRebounds -> Rebounding).
STAT_GROUP_RULES = [
    ("Turnovers", ["turnover"]),
    ("Rebounding", ["reb"]),
    ("Free throws & fouls", ["freethrow", "ftpoint", "foul"]),
    ("Shot locations", ["rim", "mid", "corner", "arc", "putback", "heave"]),
    ("Shot creation", ["assisted"]),
    ("Playmaking", ["assist"]),
    ("Defense", ["steal", "block", "charge", "deflect"]),
    ("Scoring & shooting", ["fg", "point", "pts", "efg", "pct", "usage"]),
]


def stat_group(name):
    """Sort a column into a rough category by keywords in its name."""
    lowered = name.lower()
    for group, keywords in STAT_GROUP_RULES:
        if any(k in lowered for k in keywords):
            return group
    return "Other"


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


# Era boundaries use the season's starting year (2019-20 counts as 2019).
ERAS = [
    ("Before 1996: Early era", 1900, 1995),
    ("1996-2003: Hand-check era", 1996, 2003),
    ("2004-2012: Hand-check removed", 2004, 2012),
    ("2013-2017: Three-point revolution", 2013, 2017),
    ("2018-present: Modern spacing", 2018, 2100),
]


def season_start_year(season):
    match = re.search(r"(\d{4})", str(season))
    return int(match.group(1)) if match else np.nan


def era_for_year(year):
    if pd.isna(year):
        return None
    for label, low, high in ERAS:
        if low <= year <= high:
            return label
    return None


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
        "AtRimFGM", "AtRimFGA",
        "ShortMidRangeFGM", "ShortMidRangeFGA",
        "LongMidRangeFGM", "LongMidRangeFGA",
        "Corner3FGM", "Corner3FGA", "Arc3FGM", "Arc3FGA",
        "PtsAssisted2s", "PtsAssisted3s",
        "Turnovers", "LiveBallTurnovers",
        "OffRebounds", "DefRebounds",
        "Assists", "Steals", "Blocks", "PlusMinus", "OffPoss",
    ]
    sum_columns = [c for c in sum_columns if c in d.columns]

    if not sum_columns:
        return pd.DataFrame()

    d[sum_columns] = d[sum_columns].apply(pd.to_numeric, errors="coerce")

    t = d.groupby(["Season", "Tm"], as_index=False)[sum_columns].sum()

    def has(*cols):
        return all(c in t.columns for c in cols)

    def safe_div(num, den):
        return (num / den).where(den > 0)

    if has("FG2A", "FG3A"):
        t["FGA"] = t["FG2A"] + t["FG3A"]
    if has("OffPoss"):
        t["TeamPoss"] = t["OffPoss"] / 5

    out = t[["Season", "Tm"]].copy()

    # ---- Shot selection ----
    if has("FG3A", "FGA"):
        out["3PA share of shots"] = safe_div(t["FG3A"], t["FGA"])
    if has("AtRimFGA", "FGA"):
        out["Rim share of shots"] = safe_div(t["AtRimFGA"], t["FGA"])
    if has("ShortMidRangeFGA", "LongMidRangeFGA", "FGA"):
        out["Mid-range share of shots"] = safe_div(
            t["ShortMidRangeFGA"] + t["LongMidRangeFGA"], t["FGA"]
        )
    if has("LongMidRangeFGA", "FGA"):
        out["Long mid-range share of shots"] = safe_div(
            t["LongMidRangeFGA"], t["FGA"]
        )
    if has("Corner3FGA", "FG3A"):
        out["Corner share of 3PA"] = safe_div(t["Corner3FGA"], t["FG3A"])

    # ---- Shot-making ----
    if has("FG3M", "FG3A"):
        out["3P%"] = safe_div(t["FG3M"], t["FG3A"])
    if has("AtRimFGM", "AtRimFGA"):
        out["Rim FG%"] = safe_div(t["AtRimFGM"], t["AtRimFGA"])
    if has("FG2M", "FG3M", "FGA"):
        out["eFG%"] = safe_div(t["FG2M"] + 1.5 * t["FG3M"], t["FGA"])

    # ---- Shot quality vs. shot-making ----
    # Expected points per shot if the team shot league-average from each
    # zone that season. Separates "good shots" from "making shots".
    if "Arc3FGA" in t.columns and "Arc3FGM" not in t.columns:
        if has("FG3M", "Corner3FGM"):
            t["Arc3FGM"] = t["FG3M"] - t["Corner3FGM"]

    zones = [
        ("AtRimFGA", "AtRimFGM", 2),
        ("ShortMidRangeFGA", "ShortMidRangeFGM", 2),
        ("LongMidRangeFGA", "LongMidRangeFGM", 2),
        ("Corner3FGA", "Corner3FGM", 3),
        ("Arc3FGA", "Arc3FGM", 3),
    ]
    if all(has(att, made) for att, made, _ in zones):
        zone_cols = [c for att, made, _ in zones for c in (att, made)]
        league = t.groupby("Season")[zone_cols].transform("sum")

        zone_att = sum(t[att] for att, _, _ in zones)
        expected = sum(
            t[att] * (value * league[made] / league[att])
            for att, made, value in zones
        )
        actual = sum(t[made] * value for _, made, value in zones)

        out["Shot quality (expected pts/shot)"] = safe_div(expected, zone_att)
        out["Shot-making vs expected (pts/shot)"] = (
            safe_div(actual, zone_att) - safe_div(expected, zone_att)
        )

    # ---- Offense extras ----
    if has("Points", "FGA"):
        out["Points per shot (incl. FTs)"] = safe_div(t["Points"], t["FGA"])
    if has("FtPoints", "FGA"):
        out["Free-throw points per shot"] = safe_div(t["FtPoints"], t["FGA"])
    if has("PtsAssisted2s", "PtsAssisted3s", "FG2M", "FG3M"):
        out["Assisted share of FG points"] = safe_div(
            t["PtsAssisted2s"] + t["PtsAssisted3s"],
            2 * t["FG2M"] + 3 * t["FG3M"],
        )
    if has("LiveBallTurnovers", "Turnovers"):
        out["Live-ball share of turnovers"] = safe_div(
            t["LiveBallTurnovers"], t["Turnovers"]
        )

    # ---- Per 100 possessions ----
    if has("TeamPoss"):
        per100 = {
            "Points": "Points per 100 poss",
            "Turnovers": "Turnovers per 100 poss",
            "OffRebounds": "Off. rebounds per 100 poss",
            "DefRebounds": "Def. rebounds per 100 poss",
            "Assists": "Assists per 100 poss",
            "FtPoints": "Free-throw points per 100 poss",
            "Steals": "Steals per 100 poss",
            "Blocks": "Blocks per 100 poss",
        }
        for source, label in per100.items():
            if source in t.columns:
                out[label] = safe_div(t[source], t["TeamPoss"]) * 100

    # ---- Results (approximate) ----
    # On-court plus-minus summed over players counts each point margin
    # five times, so divide by 5 to get the team margin.
    if has("PlusMinus", "TeamPoss"):
        margin = t["PlusMinus"] / 5
        out["Net rating (approx.)"] = safe_div(margin, t["TeamPoss"]) * 100
        if has("Points"):
            out["Points allowed per 100 poss (approx.)"] = (
                safe_div(t["Points"] - margin, t["TeamPoss"]) * 100
            )

    # ---- Era label ----
    era_map = {
        s: era_for_year(season_start_year(s)) for s in out["Season"].unique()
    }
    out["Era"] = out["Season"].map(era_map)

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
# TEAM BUILDER HELPERS
# --------------------------------------------------

BUILDER_MIN_MINUTES = 500   # players below this don't define "league average"
BUILDER_ALPHAS = [1, 10, 30, 100, 300, 1000, 3000, 10000]


def _num(data, column):
    return pd.to_numeric(data[column], errors="coerce")


def _p100(data, column):
    poss = _num(data, "TotalPoss") / 2
    return (_num(data, column) / poss * 100).where(poss > 0)


def _ratio(num, den, min_den):
    return (num / den).where(den >= min_den)


def _per100_feature(column):
    return lambda d: _p100(d, column)


def _minutes(data):
    if "Minutes" in data.columns:
        return _num(data, "Minutes")
    if "SecondsPlayed" in data.columns:
        return _num(data, "SecondsPlayed") / 60
    return None


# (label, columns it needs, how to compute it)
BUILDER_FEATURES = [
    ("3-pt attempts /100", ["FG3A"], _per100_feature("FG3A")),
    ("3P%", ["FG3M", "FG3A"],
     lambda d: _ratio(_num(d, "FG3M"), _num(d, "FG3A"), 50)),
    ("Rim attempts /100", ["AtRimFGA"], _per100_feature("AtRimFGA")),
    ("Rim FG%", ["AtRimFGM", "AtRimFGA"],
     lambda d: _ratio(_num(d, "AtRimFGM"), _num(d, "AtRimFGA"), 50)),
    ("Mid-range attempts /100", ["ShortMidRangeFGA", "LongMidRangeFGA"],
     lambda d: _p100(d, "ShortMidRangeFGA") + _p100(d, "LongMidRangeFGA")),
    # These location and creation signals are optional: older player files
    # simply omit them, while newer tracking exports can provide them.
    ("Corner 3 attempts /100", ["Corner3FGA"], _per100_feature("Corner3FGA")),
    ("Arc 3 attempts /100", ["Arc3FGA"], _per100_feature("Arc3FGA")),
    ("Unassisted scoring /100", ["PtsUnassisted2s", "PtsUnassisted3s"],
     lambda d: _p100(d, "PtsUnassisted2s") + _p100(d, "PtsUnassisted3s")),
    ("Shot quality", ["ShotQualityAvg"], lambda d: _num(d, "ShotQualityAvg")),
    ("Corner 3 accuracy", ["Corner3FGM", "Corner3FGA"],
     lambda d: _ratio(_num(d, "Corner3FGM"), _num(d, "Corner3FGA"), 20)),
    ("Arc 3 accuracy", ["Arc3FGM", "Arc3FGA"],
     lambda d: _ratio(_num(d, "Arc3FGM"), _num(d, "Arc3FGA"), 20)),
    ("eFG%", ["FG2M", "FG3M", "FG2A", "FG3A"],
     lambda d: _ratio(
         _num(d, "FG2M") + 1.5 * _num(d, "FG3M"),
         _num(d, "FG2A") + _num(d, "FG3A"),
         100,
     )),
    ("Free-throw points /100", ["FtPoints"], _per100_feature("FtPoints")),
    ("Assists /100", ["Assists"], _per100_feature("Assists")),
    ("Turnovers /100", ["Turnovers"], _per100_feature("Turnovers")),
    ("Off. rebounds /100", ["OffRebounds"], _per100_feature("OffRebounds")),
    ("Def. rebounds /100", ["DefRebounds"], _per100_feature("DefRebounds")),
    ("Steals /100", ["Steals"], _per100_feature("Steals")),
    ("Blocks /100", ["Blocks"], _per100_feature("Blocks")),
    ("Assisted share of FG points",
     ["PtsAssisted2s", "PtsAssisted3s", "FG2M", "FG3M"],
     lambda d: _ratio(
         _num(d, "PtsAssisted2s") + _num(d, "PtsAssisted3s"),
         2 * _num(d, "FG2M") + 3 * _num(d, "FG3M"),
         50,
     )),
]


# Resources a team only has so much of. Five players can't each keep
# their own full share of the shots, assists or rebounds.
POOL_DEFS = [
    ("Shot attempts",
     ["3-pt attempts /100", "Rim attempts /100", "Mid-range attempts /100"]),
    ("Free-throw points", ["Free-throw points /100"]),
    ("Assists", ["Assists /100"]),
    ("Turnovers", ["Turnovers /100"]),
    ("Offensive rebounds", ["Off. rebounds /100"]),
    ("Defensive rebounds", ["Def. rebounds /100"]),
    ("Steals", ["Steals /100"]),
    ("Blocks", ["Blocks /100"]),
]


# Capabilities where the best (or worst) player on the floor matters more
# than the average: does anyone pass, shoot, protect the rim?
ROLE_FEATURES = [
    ("Best passer", "Assists /100", "max"),
    ("Best 3-pt volume", "3-pt attempts /100", "max"),
    ("Spacing floor (lowest 3-pt volume)", "3-pt attempts /100", "min"),
    ("Best rim protector", "Blocks /100", "max"),
    ("Best rim attacker", "Rim attempts /100", "max"),
    ("Best rebounder", "Def. rebounds /100", "max"),
]

BUILDER_BOOTSTRAPS = 150
BUILDER_PAIR_AXES = 8


def _fit_builder_pair_axes(z, feature_cols, n_axes=BUILDER_PAIR_AXES):
    """Compress player skills into a small, stable space for pair modeling."""
    values = z[feature_cols].to_numpy(dtype=np.float32, copy=False)
    if len(values) < 2 or not feature_cols:
        return np.zeros((len(feature_cols), 0), dtype=np.float32), []
    covariance = (values.T @ values) / max(len(values), 1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1][:min(n_axes, len(feature_cols))]
    axes = eigenvectors[:, order].astype(np.float32)
    # Keep signs deterministic so labels and cached outputs don't flip.
    for column in range(axes.shape[1]):
        pivot = int(np.argmax(np.abs(axes[:, column])))
        if axes[pivot, column] < 0:
            axes[:, column] *= -1
    labels = []
    for column in range(axes.shape[1]):
        loadings = axes[:, column]
        top = np.argsort(np.abs(loadings))[::-1][:3]
        labels.append(
            f"Skill axis {column + 1} (" + ", ".join(
                ("+" if loadings[i] >= 0 else "−") + str(feature_cols[i])
                for i in top
            ) + ")"
        )
    return axes, labels


def _builder_pair_interactions(projected):
    """Sum symmetric skill-fit products over the ten player pairs.

    `projected` has shape (lineups, 5, skill_axes). Unlike products of a
    lineup average, these features only multiply skills across two different
    players, so they directly represent pair fit.
    """
    projected = np.asarray(projected, dtype=np.float32)
    n_rows, n_players, n_axes = projected.shape
    rows, cols = np.triu_indices(n_axes)
    output = np.zeros((n_rows, len(rows)), dtype=np.float32)
    pair_count = 0
    for i in range(n_players):
        for j in range(i + 1, n_players):
            left, right = projected[:, i, :], projected[:, j, :]
            output += left[:, rows] * right[:, cols]
            off_diagonal = rows != cols
            output[:, off_diagonal] += (
                left[:, cols[off_diagonal]] * right[:, rows[off_diagonal]]
            )
            pair_count += 1
    if pair_count:
        output /= pair_count
    return output


def _builder_pair_columns(axis_labels):
    return [
        f"Pair fit: {axis_labels[a]} × {axis_labels[b]}"
        for a, b in zip(*np.triu_indices(len(axis_labels)))
    ]


def role_values(z_rows):
    """Best or worst player on the floor for each capability (z-scores)."""
    values = {}
    for label, feature, how in ROLE_FEATURES:
        if feature in z_rows.columns:
            column = z_rows[feature]
            values[label] = column.max() if how == "max" else column.min()
    return pd.Series(values, dtype=float)


def _player_feature_z(data):
    """Each player-season's stats, measured against that season's league.

    A z-score of +1 means one standard deviation above the average
    qualified player of that season. This makes players from different
    eras comparable, so lineups can mix eras.

    Returns (z-scores, raw values, season means, season standard deviations).
    """
    minutes = _minutes(data)
    needed = ["Season", "TotalPoss"]
    blank = pd.DataFrame(index=data.index)

    if minutes is None or any(c not in data.columns for c in needed):
        return blank, blank, pd.DataFrame(), pd.DataFrame()

    raw = pd.DataFrame(
        {
            label: fn(data)
            for label, required, fn in BUILDER_FEATURES
            if all(c in data.columns for c in required)
        },
        index=data.index,
    )
    if raw.empty:
        return raw, raw, pd.DataFrame(), pd.DataFrame()

    qualified = minutes >= BUILDER_MIN_MINUTES
    seasons = data["Season"]
    ref = raw[qualified]
    mean = ref.groupby(seasons[qualified]).mean()
    std = ref.groupby(seasons[qualified]).std()

    def align(table):
        return pd.DataFrame(
            table.reindex(seasons.values).to_numpy(),
            index=data.index,
            columns=table.columns,
        )

    z = (raw - align(mean)) / align(std).replace(0, np.nan)
    return z.clip(-3.5, 3.5).fillna(0), raw, mean, std


@st.cache_resource(show_spinner="Building lineup profiles...")
def builder_tables(data):
    """Player z-scores, a 'core five' profile per team-season, and the
    historical limits on shared resources."""
    z, raw, mean_table, std_table = _player_feature_z(data)

    if z.shape[1] < 6 or "Tm" not in data.columns:
        return z, pd.DataFrame(), {}

    minutes = _minutes(data)
    d = data[["Season", "Tm", "player_name"]].copy()
    d["_min"] = minutes
    d = d[~d["Tm"].astype(str).str.upper().str.match(r"^(TOT|\dTM)$")]
    d = d[d["_min"] > 0]
    d = d.sort_values(["Season", "Tm", "_min"], ascending=[True, True, False])

    top = d.groupby(["Season", "Tm"]).head(5)
    keys = [top["Season"], top["Tm"]]

    profile = z.loc[top.index].groupby(keys).mean()

    zt = z.loc[top.index]
    for label, feature, how in ROLE_FEATURES:
        if feature in zt.columns:
            grouped = zt[feature].groupby(keys)
            profile[label] = grouped.max() if how == "max" else grouped.min()
    profile["Core five"] = top.groupby(["Season", "Tm"])["player_name"].agg(
        lambda s: ", ".join(s.astype(str))
    )
    sizes = top.groupby(["Season", "Tm"]).size()
    profile["_n"] = sizes
    profile = profile[profile["_n"] == 5].drop(columns="_n").reset_index()

    # How much of each shared resource has any real top five ever used?
    full_cores = sizes[sizes == 5].index
    pool_defs, caps = [], {}
    for name, members in POOL_DEFS:
        members = [m for m in members if m in raw.columns]
        if not members:
            continue
        totals = (
            raw.loc[top.index, members].sum(axis=1).groupby(keys).sum()
        )
        totals = totals.loc[totals.index.isin(full_cores)].dropna()
        if len(totals) < 30:
            continue
        pool_defs.append((name, members))
        caps[name] = {
            "cap": float(np.percentile(totals, 99)),
            "typical": float(np.median(totals)),
        }

    cores = {
        key: list(group.index)
        for key, group in top.groupby(["Season", "Tm"])
        if len(group) == 5
    }

    # Learn compact skill axes once, then preserve player-to-player products
    # for each historical core. These features are trained from the actual
    # five-man outcomes in Team Builder.
    pair_axes, pair_axis_labels = _fit_builder_pair_axes(z, list(z.columns))
    pair_cols = _builder_pair_columns(pair_axis_labels)
    if pair_cols:
        projected = z[list(z.columns)].to_numpy(dtype=np.float32) @ pair_axes
        profile_keys = list(zip(profile["Season"], profile["Tm"]))
        core_rows = np.asarray([cores[key] for key in profile_keys], dtype=int)
        profile_pair_values = _builder_pair_interactions(projected[core_rows])
        for i, column in enumerate(pair_cols):
            profile[column] = profile_pair_values[:, i]

    pools = {
        "cores": cores,
        "raw": raw,
        "mean": mean_table,
        "std": std_table,
        "defs": pool_defs,
        "caps": caps,
        "interaction_axes": pair_axes,
        "interaction_axis_labels": pair_axis_labels,
        "interaction_cols": pair_cols,
    }
    return z, profile, pools


def apply_pool_limits(data, zfeat, pools, rows, feature_cols):
    """Shrink every player's slice when the five together want more of a
    shared resource than any real top five has ever had.

    Returns the adjusted z-scores and a report of what was scaled.
    """
    z = zfeat.loc[rows, feature_cols].copy()
    raw = pools["raw"].loc[rows]
    seasons = data.loc[rows, "Season"].to_numpy()
    report = []

    for name, members in pools["defs"]:
        wanted = float(raw[members].sum().sum())
        cap = pools["caps"][name]["cap"]
        typical = pools["caps"][name]["typical"]
        factor = min(1.0, cap / wanted) if wanted > 0 else 1.0

        report.append({
            "Resource": name,
            "Five players would use": wanted,
            "Typical top five": typical,
            "Observed 99th pct cap": cap,
            "Everyone scaled to": factor,
        })

        if factor < 1.0:
            for member in members:
                mean = pools["mean"][member].reindex(seasons).to_numpy(float)
                std = pools["std"][member].reindex(seasons).to_numpy(float)
                std = np.where(std == 0, np.nan, std)
                scaled = raw[member].to_numpy(float) * factor
                z[member] = np.nan_to_num(
                    np.clip((scaled - mean) / std, -3.5, 3.5)
                )

    return z, report


def _design(features, interactions):
    """Build additive features, optionally with pairwise products and squares."""
    columns = list(features.columns)
    if not interactions:
        return features.copy()

    base = features.to_numpy(dtype=np.float32, copy=False)
    n_rows, n_features = base.shape
    n_products = n_features * (n_features + 1) // 2
    values = np.empty((n_rows, n_features + n_products), dtype=np.float32)
    values[:, :n_features] = base
    names = list(columns)
    index = n_features
    for i, a in enumerate(columns):
        for j in range(i, n_features):
            b = columns[j]
            values[:, index] = base[:, i] * base[:, j]
            names.append(f"{a} (squared)" if i == j else f"{a} × {b}")
            index += 1
    return pd.DataFrame(values, columns=names, index=features.index)


def _builder_design(features, interactions, interaction_cols=(),
                    interaction_values=None, interaction_frame=None):
    """Build the compact Team Builder design matrix.

    Keep the broad quadratic interactions among lineup summaries, and append
    explicit player-pair skill features when available.
    """
    if not interactions or not interaction_cols:
        return _design(features, interactions)
    design = _design(features, True)
    if interaction_frame is not None:
        extra = interaction_frame.loc[:, list(interaction_cols)].reset_index(drop=True)
    else:
        extra = pd.DataFrame(
            [interaction_values], columns=interaction_cols,
            index=features.index,
        )
    return pd.concat([design, extra], axis=1)

def _ridge_fit(X, y, alpha, w=None):
    if w is None:
        mu = X.mean(axis=0)
        sd = X.std(axis=0)
        sd[sd == 0] = 1.0
        Z = (X - mu) / sd
        y_mean = y.mean()
        coef = np.linalg.solve(
            Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y_mean)
        )
        return mu, sd, y_mean, coef

    # Weighted version: rows with more minutes count for more.
    w = w / w.mean()
    total = w.sum()
    mu = (X * w[:, None]).sum(axis=0) / total
    sd = np.sqrt((w[:, None] * (X - mu) ** 2).sum(axis=0) / total)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    y_mean = float((w * y).sum() / total)
    coef = np.linalg.solve(
        Z.T @ (Z * w[:, None]) + alpha * np.eye(Z.shape[1]),
        Z.T @ (w * (y - y_mean)),
    )
    return mu, sd, y_mean, coef


def _ridge_predict(model, X):
    mu, sd, y_mean, coef = model
    return ((X - mu) / sd) @ coef + y_mean


def _boot_predict(boot, X):
    """Predictions from every bootstrap model for one lineup (1 x p)."""
    return (
        ((X - boot["mu"]) / boot["sd"]) * boot["coef"]
    ).sum(axis=1) + boot["ym"]


def _weighted_percentile(values, weights, q):
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cumulative = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q / 100.0, cumulative, v))


def _season_stats(X, y, w, season_index, n_seasons):
    """Per-season sums needed to fit a weighted ridge without revisiting rows."""
    p = X.shape[1]
    S0 = np.zeros(n_seasons)
    S1 = np.zeros((n_seasons, p))
    S2 = np.zeros((n_seasons, p, p))
    T1 = np.zeros(n_seasons)
    T2 = np.zeros((n_seasons, p))
    for s in range(n_seasons):
        rows = season_index == s
        Xs, ys, ws = X[rows], y[rows], w[rows]
        S0[s] = ws.sum()
        S1[s] = ws @ Xs
        S2[s] = Xs.T @ (Xs * ws[:, None])
        T1[s] = ws @ ys
        T2[s] = Xs.T @ (ws * ys)
    return S0, S1, S2, T1, T2


def _ridge_from_stats(stats, counts, alpha):
    """Weighted ridge from per-season sums (counts say how often each season is used)."""
    S0s, S1s, S2s, T1s, T2s = stats
    S0 = float(counts @ S0s)
    S1 = counts @ S1s
    S2 = np.tensordot(counts, S2s, axes=1)
    T1 = float(counts @ T1s)
    T2 = counts @ T2s

    mu = S1 / S0
    sd = np.sqrt(np.maximum(np.diag(S2) / S0 - mu ** 2, 0.0))
    sd[sd == 0] = 1.0
    y_mean = T1 / S0
    centered = S2 - np.outer(S1, mu) - np.outer(mu, S1) + S0 * np.outer(mu, mu)
    cross = T2 - mu * T1 - S1 * y_mean + S0 * mu * y_mean
    A = centered / np.outer(sd, sd) + alpha * np.eye(len(mu))
    coef = np.linalg.solve(A, cross / sd)
    return mu, sd, y_mean, coef


def _fit_variant_blocked(X, y, w, season_index, season_fold, k, alphas):
    """Cross-validate, fit and bootstrap one model using per-season sums.

    Fast enough for tens of thousands of lineups. The uncertainty refits
    resample whole seasons, which is also more honest than resampling
    lineups, since lineups in a season share opponents and context.
    """
    n_seasons = len(season_fold)
    stats = _season_stats(X, y, w, season_index, n_seasons)
    row_fold = season_fold[season_index]

    best = None
    fold_counts = [(season_fold != f).astype(float) for f in range(k)]
    for alpha in alphas:
        oof = np.zeros(len(y))
        for f in range(k):
            model = _ridge_from_stats(stats, fold_counts[f], alpha)
            test = row_fold == f
            oof[test] = _ridge_predict(model, X[test])
        sse = float((w * (y - oof) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, alpha, oof)
    sse, alpha, oof = best

    model = _ridge_from_stats(stats, np.ones(n_seasons), alpha)
    rng = np.random.default_rng(0)
    fits = [
        _ridge_from_stats(
            stats,
            rng.multinomial(n_seasons, np.full(n_seasons, 1.0 / n_seasons)).astype(float),
            alpha,
        )
        for _ in range(BUILDER_BOOTSTRAPS)
    ]
    boot = {
        "mu": np.array([f[0] for f in fits]),
        "sd": np.array([f[1] for f in fits]),
        "ym": np.array([f[2] for f in fits]),
        "coef": np.array([f[3] for f in fits]),
    }
    return alpha, sse, oof, model, boot


@st.cache_resource(show_spinner="Fitting the model across seasons...")
def fit_builder_models(_profiles, feature_cols, target_col, weight_col=None,
                       carry_cols=(), interaction_cols=(), cache_key=()):
    """Fit additive and interaction models, scored on held-out groups.

    Seasons are split into folds, and each fold is predicted by a model
    that never saw those seasons. That out-of-sample score is the honest
    measure of whether the model actually understands anything.

    With a weight column (real lineups), rows count in proportion to their
    minutes, since ratings from more minutes are less noisy.
    """
    data = _profiles.dropna(subset=[target_col]).reset_index(drop=True)
    y = data[target_col].to_numpy(float)
    interaction_support = None
    if interaction_cols:
        pair_values = data[list(interaction_cols)].to_numpy(dtype=float)
        interaction_support = {
            "lo": np.percentile(pair_values, 1, axis=0),
            "hi": np.percentile(pair_values, 99, axis=0),
        }

    weights = None
    if weight_col is not None:
        weights = data[weight_col].to_numpy(float)
        weights = weights / weights.mean()
    w_all = weights if weights is not None else np.ones(len(y))

    seasons = data["Season"].astype(str).to_numpy()
    unique_seasons = sorted(set(seasons))
    # When five-man lineups are available, keep every appearance of the same
    # five players in one fold. This tests whether skill profiles generalize
    # to combinations the model did not train on, rather than letting the
    # same lineup reappear in another season's training rows.
    if "LineupKey" in data.columns:
        groups = data["LineupKey"].fillna("").astype(str).to_numpy()
        unique_groups = sorted(set(groups))
    else:
        groups = seasons
        unique_groups = unique_seasons
    k = min(5, len(unique_groups))
    fold_of = {group: i % k for i, group in enumerate(unique_groups)}
    folds = np.array([fold_of[group] for group in groups])

    season_index = np.array([unique_seasons.index(s) for s in seasons]) if len(unique_seasons) < 200 else None
    # This vector is used only by the season-blocked fast path, where groups
    # are seasons. Lineup-key folds use the ordinary grouped fit below.
    season_fold = np.array([i % min(5, len(unique_seasons))
                            for i, _ in enumerate(unique_seasons)])
    blocked = (weights is not None and len(unique_seasons) >= 8
               and "LineupKey" not in data.columns)

    y_bar = float((w_all * y).sum() / w_all.sum())
    total_ss = float((w_all * (y - y_bar) ** 2).sum())
    alphas = (
        BUILDER_ALPHAS if weights is None
        else [a * len(y) / 500.0 for a in BUILDER_ALPHAS]
    )

    def subset(array, index):
        return None if array is None else array[index]

    results = {}
    for name, interactions in (("additive", False), ("interact", True)):
        design = _builder_design(
            data[feature_cols], interactions, interaction_cols,
            interaction_frame=data if interactions and interaction_cols else None,
        )
        X = design.to_numpy(dtype=np.float32, copy=False)

        if blocked:
            alpha, sse, oof, model, boot = _fit_variant_blocked(
                X, y, weights, season_index, season_fold, k, alphas
            )
        else:
            best = None
            for alpha in alphas:
                oof = np.zeros(len(y))
                for fold in range(k):
                    train, test = folds != fold, folds == fold
                    model = _ridge_fit(X[train], y[train], alpha, subset(weights, train))
                    oof[test] = _ridge_predict(model, X[test])
                sse = float((w_all * (y - oof) ** 2).sum())
                if best is None or sse < best[0]:
                    best = (sse, alpha, oof)

            sse, alpha, oof = best
            model = _ridge_fit(X, y, alpha, weights)

            # Resample whole seasons when possible because lineup rows from
            # one season share opponents and environment. Small datasets fall
            # back to row resampling.
            rng = np.random.default_rng(0)
            if weights is not None and len(unique_seasons) >= 8 and season_index is not None:
                stats = _season_stats(X, y, weights, season_index, len(unique_seasons))
                fits = [
                    _ridge_from_stats(
                        stats,
                        rng.multinomial(
                            len(unique_seasons),
                            np.full(len(unique_seasons), 1.0 / len(unique_seasons)),
                        ).astype(float),
                        alpha,
                    )
                    for _ in range(BUILDER_BOOTSTRAPS)
                ]
            else:
                fits = [
                    _ridge_fit(X[idx], y[idx], alpha, subset(weights, idx))
                    for idx in (rng.integers(0, len(y), len(y))
                                for _ in range(BUILDER_BOOTSTRAPS))
                ]
            boot = {
                "mu": np.array([f[0] for f in fits]),
                "sd": np.array([f[1] for f in fits]),
                "ym": np.array([f[2] for f in fits]),
                "coef": np.array([f[3] for f in fits]),
            }

        # Separate forward-in-time check: train only on earlier seasons,
        # purge exact five-player groups that recur in the future block, and
        # choose regularization using the earlier data alone.
        future_eval = None
        n_future = max(1, int(np.ceil(len(unique_seasons) * 0.2)))
        if len(unique_seasons) >= 4:
            future_seasons = set(unique_seasons[-n_future:])
            future_test = np.isin(seasons, list(future_seasons))
            future_train = ~future_test
            if "LineupKey" in data.columns and future_test.any():
                held_groups = set(groups[future_test])
                future_train &= ~np.isin(groups, list(held_groups))
            train_seasons = set(seasons[future_train])
            if future_test.any() and len(train_seasons) >= 2 and future_train.sum() >= 100:
                train_groups = groups[future_train]
                inner_groups = sorted(set(train_groups))
                inner_k = min(3, len(inner_groups))
                inner_fold_of = {g: i % inner_k for i, g in enumerate(inner_groups)}
                inner_folds = np.array([inner_fold_of[g] for g in train_groups])
                train_rows = np.flatnonzero(future_train)
                inner_weights = w_all[future_train]
                inner_model_weights = subset(weights, future_train)
                best_future = None
                for candidate_alpha in alphas:
                    inner_sse = 0.0
                    for inner_fold in range(inner_k):
                        fit_local = inner_folds != inner_fold
                        val_local = inner_folds == inner_fold
                        if not fit_local.any() or not val_local.any():
                            continue
                        inner_model = _ridge_fit(
                            X[train_rows[fit_local]], y[train_rows[fit_local]],
                            candidate_alpha,
                            (inner_model_weights[fit_local]
                             if inner_model_weights is not None else None),
                        )
                        inner_pred = _ridge_predict(
                            inner_model, X[train_rows[val_local]]
                        )
                        inner_sse += float(
                            (inner_weights[val_local]
                             * (y[train_rows[val_local]] - inner_pred) ** 2).sum()
                        )
                    if best_future is None or inner_sse < best_future[0]:
                        best_future = (inner_sse, candidate_alpha)
                future_alpha = best_future[1] if best_future else alpha
                future_model = _ridge_fit(
                    X[future_train], y[future_train], future_alpha,
                    subset(weights, future_train),
                )
                future_pred = _ridge_predict(future_model, X[future_test])
                future_weights = w_all[future_test]
                future_mean = float(
                    (w_all[future_train] * y[future_train]).sum()
                    / w_all[future_train].sum()
                )
                future_ss = float(
                    (future_weights * (y[future_test] - future_mean) ** 2).sum()
                )
                future_sse = float(
                    (future_weights * (y[future_test] - future_pred) ** 2).sum()
                )
                future_eval = {
                    "r2": 1 - future_sse / future_ss if future_ss > 0 else np.nan,
                    "rmse": float(np.sqrt(future_sse / future_weights.sum())),
                    "seasons": sorted(future_seasons),
                    "n": int(future_test.sum()),
                }

        results[name] = {
            "boot": boot,
            "alpha": alpha,
            "r2": 1 - sse / total_ss,
            "rmse": float(np.sqrt(sse / w_all.sum())),
            "oof": oof,
            "fitted": _ridge_predict(model, X),
            "model": model,
            "columns": list(design.columns),
            "future": future_eval,
        }
        del design, X

    # What do real historical groups look like? Used by the guardrails.
    F = data[feature_cols].to_numpy(float)
    if weights is None:
        center = F.mean(axis=0)
        cov = np.cov(F, rowvar=False) + 1e-6 * np.eye(F.shape[1])
        lo, hi = np.percentile(F, 1, axis=0), np.percentile(F, 99, axis=0)
    else:
        center = (weights[:, None] * F).sum(axis=0) / weights.sum()
        centered_w = F - center
        cov = (weights[:, None] * centered_w).T @ centered_w / weights.sum()
        cov = cov + 1e-6 * np.eye(F.shape[1])
        lo = np.array([_weighted_percentile(F[:, j], weights, 1) for j in range(F.shape[1])])
        hi = np.array([_weighted_percentile(F[:, j], weights, 99) for j in range(F.shape[1])])
    inverse = np.linalg.inv(cov)
    centered = F - center
    results["support"] = {
        "mu": center,
        "inv": inverse,
        "d2": np.einsum("ij,jk,ik->i", centered, inverse, centered),
        "lo": lo,
        "hi": hi,
        "w": weights,
    }

    # Best and worst real results to compare against (ignoring tiny samples).
    reference_rows = np.ones(len(y), dtype=bool)
    if "Minutes" in data.columns:
        big = data["Minutes"].to_numpy(float) >= 200
        if big.sum() >= 30:
            reference_rows = big
    results["reference"] = (
        float(y[reference_rows].max()), float(y[reference_rows].min())
    )

    keep = ["Season", "Tm", "Era", "Core five"] + [
        c for c in carry_cols if c in data.columns
    ]
    results["data"] = data[keep].assign(actual=y)
    if weight_col is not None:
        results["data"]["weight"] = data[weight_col].to_numpy(float)
    results["interaction_cols"] = list(interaction_cols)
    results["interaction_support"] = interaction_support
    return results


def render_team_builder(df, player_labels, player_options):
    """The Team Builder tab: a model learned from historical teams."""
    st.markdown(
        '<div class="section-label">04 / Team Builder</div>',
        unsafe_allow_html=True
    )
    st.header("Build a lineup")

    st.write(
        "Choose five players to estimate how they might perform together. "
        "The estimate is learned from real player and lineup data."
    )

    with st.expander("How the estimate works"):
        st.markdown(
            "- Player stats are compared with others from the same season, "
            "so players from different eras can be combined.\n"
            "- The model learns from real five-player lineups and checks its "
            "estimates on lineups it did not learn from.\n"
            "- It looks at each player's skills and how those skills may fit "
            "together.\n"
            "- Lineups with more playing time provide stronger evidence.\n"
            "- Estimates are less certain for combinations unlike the ones "
            "in the data.\n"
            "- The data cannot capture everything, such as coaching, "
            "matchups, injuries, or every defensive role."
        )

    zfeat, profiles, pools = builder_tables(df)
    if zfeat.shape[1] < 6:
        st.warning(
            "Not enough of the needed stat columns to build lineup "
            "profiles (need minutes, TotalPoss, and shot/box-score stats)."
        )
        return

    base_cols = list(zfeat.columns)
    with st.expander("What player stats are included?"):
        st.write(
            "The app uses the available stats below. If a stat is missing "
            "from the data, it is skipped. Current stats: "
            + (", ".join(base_cols) if base_cols else "none found")
            + "."
        )
        st.caption(
            "The feature list includes optional shot-location, shot-quality, "
            "and unassisted-scoring measures when those columns exist in the "
            "player data."
        )

    # ---- Real five-man lineups, if the files are present ----
    lineup_data, lineup_problem, lineup_info = None, None, None
    lineup_load_report = {}
    if any(path.exists() for path in LINEUP_FILES):
        try:
            loaded, loaded_report = load_lineups()
            if loaded is None:
                lineup_problem = (
                    "; ".join(loaded_report["problems"])
                    + " (Data Lab, then Lineup Lab, shows what's in the files.)"
                )
            else:
                lineup_data = loaded
                lineup_load_report = loaded_report
        except Exception as error:
            lineup_problem = f"The lineup files couldn't be used: {error}"

    use_lineups = False
    if lineup_data is not None:
        data_basis = st.radio(
            "Learn from",
            ["Real five-man lineups (recommended)", "Team results (older method)"],
            index=0,
            horizontal=True,
            key="builder_data_basis",
            help="Real lineups are exactly what this tool predicts: five "
                 "players on the floor together. The older method learns "
                 "from whole teams and has to estimate the bench's effect.",
        )
        use_lineups = data_basis.startswith("Real")
    elif lineup_problem:
        st.caption(lineup_problem)

    # ---- Targets ----
    targets = {}
    teams = None
    if use_lineups:
        for label, (column, sign_) in LINEUP_TARGET_COLUMNS.items():
            if lineup_data[column].notna().any():
                targets[label] = (column, sign_)
    else:
        teams = build_team_seasons(df)
        if teams.empty:
            st.warning("The Team Lab needs to work first (Season and Tm columns).")
            return
        if profiles.empty:
            st.warning(
                "Not enough of the needed stat columns to build lineup "
                "profiles (need minutes, TotalPoss, and shot/box-score stats)."
            )
            return
        if "Net rating (approx.)" in teams.columns:
            targets["Net rating"] = ("Net rating (approx.)", 1)
        if "Points per 100 poss" in teams.columns:
            targets["Offense (points scored per 100)"] = (
                "Points per 100 poss", 1
            )
        if "Points allowed per 100 poss (approx.)" in teams.columns:
            targets["Defense (points prevented per 100)"] = (
                "Points allowed per 100 poss (approx.)", -1
            )

    if not targets:
        st.warning("No results columns available to learn from.")
        return

    target_label = st.radio(
            "What should the estimate focus on?",
        list(targets.keys()),
        horizontal=True,
        key="builder_target",
    )
    source_col, sign = targets[target_label]

    if use_lineups:
        training, _, pools, lineup_info = build_lineup_training(
            df, lineup_data, zfeat, pools, tuple(base_cols), _lineup_cache_key()
        )
        lineup_info["source_rows_raw"] = lineup_load_report.get("rows_raw")
        lineup_info["source_rows_clean"] = lineup_load_report.get("rows_clean")
        lineup_info["source_duplicates_removed"] = lineup_load_report.get(
            "duplicates_removed", 0
        )
        if training is None:
            st.warning(lineup_info.get("reason", "Couldn't build profiles from the lineups."))
            return

        merged = training.copy()
        # A short lineup sample is less stable than a long one. Shrink its
        # observed deviation toward league average before fitting; minute
        # weights still let the larger samples carry more information.
        reliability = merged["Minutes"] / (
            merged["Minutes"] + LINEUP_TARGET_PRIOR_MINUTES
        )
        merged["_target"] = sign * merged[source_col] * reliability
        feature_cols = base_cols + [
            label for label, _, _ in ROLE_FEATURES if label in merged.columns
        ]
        usable = int(merged["_target"].notna().sum())
        if usable < 500 or merged["Season"].nunique() < 3:
            st.warning(
                f"Only {usable} usable lineups across "
                f"{merged['Season'].nunique()} seasons. That's too few to "
                "fit a trustworthy model."
            )
            return
        results = fit_builder_models(
            merged, feature_cols, "_target", "weight", ("Team", "Minutes"),
            interaction_cols=tuple(pools.get("interaction_cols", ())),
            cache_key=(_lineup_cache_key(), target_label, tuple(feature_cols)),
        )
    else:
        feature_cols = [
            c for c in profiles.columns
            if c not in ("Season", "Tm", "Core five")
            and c not in pools.get("interaction_cols", ())
        ]
        merged = profiles.merge(
            teams[["Season", "Tm", "Era", source_col]],
            on=["Season", "Tm"],
            how="left",
        )
        merged["_target"] = sign * (
            merged[source_col]
            - merged.groupby("Season")[source_col].transform("mean")
        )

        if "Net rating" in target_label:
            season_means = teams.groupby("Season")["Net rating (approx.)"].mean()
            if season_means.abs().max() > 2:
                st.warning(
                    "Net rating should average about 0 in every season, but "
                    f"some seasons are off by up to {season_means.abs().max():.1f}. "
                    "That suggests PlusMinus or the possession estimate isn't "
                    "what I assumed. Treat net-rating results with suspicion, "
                    "or try the Offense target."
                )

        usable = merged["_target"].notna().sum()
        if usable < 100 or merged["Season"].nunique() < 3:
            st.warning(
                f"Only {usable} usable team-seasons across "
                f"{merged['Season'].nunique()} seasons. That's too few to "
                "fit a trustworthy model."
            )
            return

        results = fit_builder_models(
            merged, feature_cols, "_target",
            interaction_cols=tuple(pools.get("interaction_cols", ())),
            cache_key=(_lineup_cache_key(), target_label, tuple(feature_cols)),
        )

    additive, interact = results["additive"], results["interact"]

    # ---- Optional pair chemistry layer (extra memory and computation) ----
    pair_layer, pair_problem = None, None
    enable_pair_layer = False
    if PAIR_FILE.exists():
        enable_pair_layer = st.checkbox(
            "Load pair chemistry (uses extra memory)",
            value=False,
            key="builder_enable_pair_layer",
            help="The core lineup model works without this optional layer. "
                 "Turn it on to include learned pair effects.",
        )
    if PAIR_FILE.exists() and enable_pair_layer:
        try:
            pair_data, _ = load_pairs()
            if pair_data is None:
                pair_problem = "The pair file could not be read."
            else:
                pair_layer = run_pair_layer(
                    pair_data, zfeat, df, pools, results, target_label, base_cols
                )
        except Exception as error:
            pair_problem = f"Pair data could not be used: {error}"

    # ---- Model report card ----
    st.markdown("#### How reliable are its estimates?")

    gain = interact["r2"] - additive["r2"]
    if use_lineups:
        m1, m2, m3 = st.columns(3)
        m1.metric("Skill-fit model", f"{interact['r2']:.1%} of differences explained")
        m2.metric("Typical error on new lineups", f"about ±{interact['rmse']:.1f} pts/100")
        m3.metric(
            "Skills added together",
            f"{additive['r2']:.1%} of differences explained",
            delta=f"{gain:+.1%} with skill fit",
        )
        st.caption(
            "“Differences explained” compares the model with guessing the "
            "average lineup. It is not the percent of predictions that are "
            "correct. The typical error is an average, not a guaranteed range. "
            "Short-minute ratings are pulled toward league average before fitting."
        )
        if additive.get("future") and interact.get("future"):
            future_add, future_pair = additive["future"], interact["future"]
            seasons = future_pair["seasons"]
            season_span = (
                f"{seasons[0]} through {seasons[-1]}"
                if len(seasons) > 1 else (seasons[0] if seasons else "not available")
            )
            with st.expander("Does it carry over to newer seasons?"):
                st.write(
                    f"Trained on earlier seasons and checked on {season_span}. "
                    "Any exact five-player lineup repeated across the split was "
                    "removed from training."
                )
                st.write(
                    f"With skill interactions: {future_pair['r2']:.1%} R², "
                    f"about ±{future_pair['rmse']:.1f} pts/100 typical miss. "
                    f"Sum-of-parts baseline: {future_add['r2']:.1%} R² "
                    f"(about ±{future_add['rmse']:.1f} pts/100)."
                )
        st.caption(
            f"Training used {usable:,} lineup records with matched player stats "
            f"and at least {LINEUP_MODEL_MIN_MINUTES} minutes, out of "
            f"{lineup_info['lineups']:,} cleaned records "
            f"({lineup_info['matched']:,} matched to player seasons). "
            f"Those training records total {lineup_info['training_minutes']:,.0f} minutes. "
            "Each record summarizes a five-player group, not one possession "
            "or play."
        )
        with st.expander("How much lineup data made it into training?"):
            raw_rows = lineup_info.get("source_rows_raw")
            raw_count = (
                f"{raw_rows:,} rows across the source files"
                if raw_rows is not None else "source row count unavailable"
            )
            cleaned_rows = lineup_info.get("source_rows_clean") or lineup_info["lineups"]
            matched_rows = lineup_info["matched"]
            fit_rows = int(usable)
            st.write(f"**Read from files:** {raw_count}.")
            st.write(
                f"**After parsing and removing duplicate/invalid rows:** "
                f"{cleaned_rows:,}."
            )
            st.write(
                f"**Matched to all five players' season stats:** "
                f"{matched_rows:,} of {lineup_info['lineups']:,} cleaned records "
                f"({matched_rows / max(lineup_info['lineups'], 1):.1%})."
            )
            st.write(
                f"**Passed the {LINEUP_MODEL_MIN_MINUTES}-minute cutoff:** "
                f"{lineup_info.get('training_lineups', 0):,} records; "
                f"{lineup_info.get('training_combinations', 0):,} distinct "
                f"five-player combinations. The target rating was available "
                f"for {fit_rows:,} of them."
            )
            st.caption(
                "So the headline training count is not the number of raw file "
                "rows or possessions. This breakdown shows whether most rows "
                "were removed by parsing, player-season matching, or the "
                "minimum-minutes rule."
            )
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Skills added together", f"{additive['r2']:.1%} explained")
        m2.metric("With player skill fit", f"{interact['r2']:.1%} explained")
        m3.metric(
            "Typical error: skills / skill fit",
            f"±{additive['rmse']:.1f} / ±{interact['rmse']:.1f} pts/100",
            help="Root mean squared prediction error on held-out data. "
                 "These are outcome errors, not uncertainty bands for one lineup.",
        )

    if gain > 0.01:
        generalization_group = "unseen lineups" if use_lineups else "held-out seasons"
        st.success(
            f"The skill-interaction model improved the main held-out score "
            f"by {gain:.1%} points. This is evidence of added signal for "
            f"{generalization_group}; check the future-season details below too."
        )
        default_model = 1
    else:
        st.info(
            "The skill-interaction model didn't clearly improve predictions "
            f"on {('unseen lineups' if use_lineups else 'held-out seasons')}. "
            "It remains the selected estimate so the app "
            "can show what the learned player-pair skill fit predicts, but "
            "the backtest says that signal is not yet reliable."
        )
        # This app's purpose is to estimate skill fit, so keep that model
        # selected by default and report its validation score openly.
        default_model = 1

    if use_lineups:
        with st.expander("How did the older team-based method do on real lineups?"):
            check = legacy_scale_check(
                df, zfeat, profiles, merged, feature_cols, target_label
            )
            if check is None:
                st.write("Couldn't run the comparison (it needs the team-level data).")
            else:
                k1, k2, k3 = st.columns(3)
                k1.metric(
                    "Its predictions needed scaling by",
                    f"{check['slope']:.2f}x",
                    help="How much the old team-based predictions would have "
                         "to be multiplied by to match what real lineups did.",
                )
                k2.metric(
                    "My bench-dilution guess was",
                    "—" if check["guess"] is None else f"{check['guess']:.2f}x",
                )
                k3.metric("Correlation with real lineups", f"{check['corr']:.2f}")
                st.caption(
                    "The old method learned from whole teams and divided out "
                    "the bench's share of minutes. If the first number is "
                    "close to the second, that guess was about right. If "
                    "not, the real lineups are correcting it."
                )
    else:
        st.caption(
            "R² is the share of variation in held-out team results explained "
            "compared with predicting the weighted average. It is not the "
            "percentage of teams predicted correctly. Real basketball has "
            "many factors this model cannot see."
        )

    use_pair_layer = False
    blend_history = False
    if pair_layer is not None and pair_layer.get("ok"):
        bt = pair_layer["backtest"]
        st.markdown("#### Pair chemistry layer")
        if "r2_with" in bt:
            p1, p2, p3 = st.columns(3)
            p1.metric("Without pair layer", f"{bt['r2_without']:.1%}")
            p2.metric("With pair layer", f"{bt['r2_with']:.1%}")
            p3.metric(
                "How much shows up",
                f"{bt['lam']:.2f}x",
                help="Summed pair chemistry is multiplied by this. 1.0 would "
                     "mean it shows up in results at full strength.",
            )
            if bt["helps"]:
                st.success(
                    f"Adding pair chemistry improved predictions from "
                    f"{bt['r2_without']:.1%} to {bt['r2_with']:.1%}, with "
                    "every pair scored by a model that never saw that pair's "
                    f"own results. About {bt['lam']:.0%} of the summed "
                    "chemistry shows up in results, so it's scaled by that."
                )
            else:
                st.info(
                    "Adding pair chemistry did not clearly improve "
                    "predictions, so it's off by default. Every pair is "
                    "scored by a model that never saw that pair's own "
                    "results, so this is a fair test: skill fit alone may "
                    "not add much here, or the player stats may not capture "
                    "what drives it."
                )
            use_pair_layer = st.checkbox(
                "Add pair chemistry to predictions",
                value=bool(bt["helps"]),
                key=f"builder_pair_layer_{target_label}",
            )
            if use_pair_layer:
                blend_history = st.checkbox(
                    "Also let each pair's real history raise or lower its score "
                    "(hindsight)",
                    value=False,
                    key=f"builder_pair_history_{target_label}",
                    help="Off by default. With it on, a duo that happened to "
                         "do well together gets a bonus for it, even if "
                         "their skills wouldn't predict that.",
                )
        else:
            st.caption(
                "Not enough overlapping team-seasons to backtest the pair "
                "layer, so it's left off."
            )
    elif pair_layer is not None:
        st.caption(
            "Pair chemistry layer unavailable: "
            + pair_layer.get("reason", "the pair model couldn't be fit.")
        )
    elif pair_problem:
        st.caption(pair_problem)

    model_choice = st.radio(
        "How should player skills be combined?",
        ["Add skills together", "Include how skills fit together"],
        index=default_model,
        horizontal=True,
        key="builder_model_pairfit_v2",
    )
    st.caption(
        "The player-pair model learns whether combinations of skills across "
        "different players raise or lower a lineup's result. It is selected "
        "by default because that is the purpose of this tool; the score above "
        "shows how it generalizes to held-out data."
    )

    chosen_key = (
        "additive" if model_choice == "Add skills together" else "interact"
    )
    chosen = results[chosen_key]

    if use_pair_layer and chosen_key == "interact":
        st.caption(
            "The player-pair skill model remains active. The optional pair "
            "history layer is added separately and is evaluated after the "
            "skill-interaction model."
        )

    # ---- Calibration: is the model too cautious? ----
    cal = calibration_summary(
        results["data"]["actual"], chosen["oof"], results["data"].get("weight")
    )
    with st.expander("Is the model too cautious? (calibration check)"):
        if np.isnan(cal["slope"]):
            st.write("Not enough data to check.")
        else:
            st.write(
                f"On seasons it never saw, when the model predicted +1.0, "
                f"teams actually averaged {cal['slope']:+.2f}."
            )
            st.dataframe(
                cal["table"].style.format(
                    {"Predicted": "{:+.1f}", "Actual": "{:+.1f}", "Rows": "{:.0f}"}
                ),
                use_container_width=True,
            )
            if cal["slope"] >= 1.15:
                st.info(
                    "Predictions look compressed: the best-looking teams did "
                    "better than predicted and the worst did worse. That's "
                    "typical of a cautious model, and 'Stretch predictions' "
                    "below corrects for it."
                )
            elif cal["slope"] <= 0.9:
                st.info(
                    "Predictions look too bold: real results were less "
                    "extreme than predicted. Stretching would make that worse."
                )
            else:
                st.success("Predictions line up well with what happened.")

    calibrate = st.checkbox(
        "Stretch predictions to match history",
        value=False,
        key="builder_calibrate",
        help="Applies the calibration slope above to the skills "
             "prediction. Only worth turning on if the check shows "
             "predictions are compressed.",
    )

    # The model learns from whole teams, whose benches dilute the five best
    # players. A lineup is the five on the floor together, so that dilution
    # is divided back out.
    core_share = None if use_lineups else top_five_minute_share(df)
    basis_scale = (1.0 / core_share) if core_share else 1.0
    calib_scale = cal["scale"] if (calibrate and not np.isnan(cal["slope"])) else 1.0
    if use_lineups:
        st.caption(
            "Ratings are for these five on the floor together, learned "
            "directly from real five-man lineups, so no bench adjustment "
            "is needed."
        )
    else:
        st.caption(
            f"Ratings are for these five on the floor together. The model "
            f"learns from whole teams, where the top five play about "
            f"{core_share:.0%} of the minutes, so the bench's dilution is "
            f"divided out ({basis_scale:.2f}x). That's an estimate."
            if core_share else
            "Ratings are for these five on the floor together. The bench's "
            "dilution couldn't be estimated from this data, so none is "
            "removed."
        )

    mode_col1, mode_col2 = st.columns(2)
    with mode_col1:
        guardrail_mode = st.radio(
            "Unusual lineups",
            ["Extrapolate and show the uncertainty",
             "Strict: cap at the best and worst real results"],
            index=0,
            key="builder_guardrails",
            help="The first option lets the model say a group beats every "
                 "real result, with a range showing how unsure it is. The "
                 "second keeps results inside what has actually happened.",
        )
    with mode_col2:
        limit_pools = st.checkbox(
            "Limit unusually high combined stats",
            value=False,
            key="builder_pools",
            help="An optional safeguard that lowers a combined stat if it is "
                 "far above what appeared in real lineups. It is not a "
                 "teammate-specific skill interaction.",
        )
    strict = guardrail_mode.startswith("Strict")

    # ---- Pick five players ----
    st.markdown("#### Pick five players")

    minutes = _minutes(df)
    selected_rows = []
    slots = st.columns(5)

    for i, slot in enumerate(slots):
        with slot:
            player_label = st.selectbox(
                f"Player {i + 1}",
                ["— choose —"] + player_labels,
                key=f"bld_player_{i}",
            )

            if player_label == "— choose —":
                selected_rows.append(None)
                continue

            player_id = player_options[player_label]
            rows = df[df["player_id"] == player_id].sort_values("Season")

            st.markdown(
                mini_player_html(
                    player_id,
                    rows["player_name"].iloc[0],
                    career_summary(rows),
                ),
                unsafe_allow_html=True,
            )

            row_labels = {}
            for idx, row in rows.iterrows():
                team_text = f" ({row['Tm']})" if "Tm" in rows.columns else ""
                row_labels[f"{row['Season']}{team_text}"] = idx

            keys = list(row_labels.keys())
            default_index = 0
            if minutes is not None:
                best_idx = minutes.loc[rows.index].idxmax()
                for position, key in enumerate(keys):
                    if row_labels[key] == best_idx:
                        default_index = position

            season_label = st.selectbox(
                "Season",
                keys,
                index=default_index,
                key=f"bld_season_{i}_{player_id}",
            )
            selected_rows.append(row_labels[season_label])

    if any(r is None for r in selected_rows):
        st.info("Choose all five players to see a prediction.")
    elif len(set(selected_rows)) < 5:
        st.warning("The same player-season appears more than once.")
    else:
        if limit_pools:
            lineup_z, pool_report = apply_pool_limits(
                df, zfeat, pools, selected_rows, base_cols
            )
        else:
            lineup_z, pool_report = zfeat.loc[selected_rows, base_cols], []

        lineup = (
            pd.concat([lineup_z.mean(axis=0), role_values(lineup_z)])
            .reindex(feature_cols)
            .fillna(0)
        )
        support = results["support"]
        raw_vec = lineup.to_numpy(float)
        interaction_cols = results.get("interaction_cols", [])
        interaction_axes = pools.get("interaction_axes")
        pair_interaction_vec = np.zeros(len(interaction_cols), dtype=np.float32)
        if (interaction_cols and interaction_axes is not None
                and interaction_axes.shape[1]):
            projected_players = (
                lineup_z[base_cols].to_numpy(dtype=np.float32) @ interaction_axes
            )[None, :, :]
            pair_interaction_vec = _builder_pair_interactions(projected_players)[0]
            if strict and results.get("interaction_support") is not None:
                pair_support = results["interaction_support"]
                pair_interaction_vec = np.clip(
                    pair_interaction_vec, pair_support["lo"], pair_support["hi"]
                )

        # How far is this group from anything that ever actually played?
        centered = raw_vec - support["mu"]
        lineup_d2 = float(centered @ support["inv"] @ centered)
        below = (support["d2"] < lineup_d2).astype(float)
        unusual_pct = float(
            (np.average(below, weights=support["w"]) if support.get("w") is not None
             else below.mean()) * 100
        )
        beyond_history = lineup_d2 > float(support["d2"].max())

        # Keep the skill-interaction model active for unusual lineups too.
        # Strict mode clips its inputs; otherwise uncertainty reflects the
        # extrapolation rather than silently removing the interaction signal.
        active_key, active = chosen_key, chosen

        outside = []
        for i, feature in enumerate(feature_cols):
            if raw_vec[i] > support["hi"][i] + 1e-9:
                outside.append((feature, raw_vec[i], support["hi"][i],
                                raw_vec[i] - support["hi"][i]))
            elif raw_vec[i] < support["lo"][i] - 1e-9:
                outside.append((feature, raw_vec[i], support["lo"][i],
                                support["lo"][i] - raw_vec[i]))

        def model_output(vector, pair_values=None):
            feature_row = pd.DataFrame([vector], columns=feature_cols)
            row = _builder_design(
                feature_row, active_key == "interact", interaction_cols,
                interaction_values=(pair_interaction_vec if pair_values is None
                                    else pair_values),
            )
            row = row[active["columns"]]
            values = row.to_numpy(float)
            return values, float(_ridge_predict(active["model"], values)[0])

        pair_table, synergy_effect = None, 0.0
        if use_pair_layer:
            pair_table = lineup_pair_synergy(
                df, zfeat, pair_layer, selected_rows, base_cols,
                use_history=blend_history,
            )
            synergy_effect = float(
                pair_layer["backtest"]["lam"] * pair_table["Used"].sum()
            )

        best_seen, worst_seen = results["reference"]
        _, unadjusted_prediction = model_output(raw_vec)

        trust = 1.0
        capped_by_history = False

        if strict:
            # Keep inputs inside history, shrink if far outside, and cap.
            X, prediction = model_output(np.clip(raw_vec, support["lo"], support["hi"]))
            if beyond_history:
                trust = float(np.sqrt(support["d2"].max() / lineup_d2))
            prediction *= trust * calib_scale
            prediction += synergy_effect
            if prediction > best_seen:
                prediction, capped_by_history = best_seen, True
            elif prediction < worst_seen:
                prediction, capped_by_history = worst_seen, True
        else:
            X, prediction = model_output(raw_vec)
            prediction *= calib_scale
            prediction += synergy_effect

        # Everything above is on the model's native, whole-team basis.
        prediction_team = prediction
        prediction = prediction_team * basis_scale

        # Uncertainty: resampled-history models disagree more the further
        # the lineup is from anything real. Add ordinary prediction noise.
        boot_predictions = _boot_predict(active["boot"], X)
        boot_spread = float(boot_predictions.std())
        error_used = (
            pair_layer["backtest"]["rmse_with"]
            if use_pair_layer and "rmse_with" in pair_layer["backtest"]
            else active["rmse"]
        )
        total_spread = float(np.sqrt(boot_spread ** 2 + error_used ** 2))
        total_spread *= basis_scale * max(1.0, calib_scale)
        low = prediction - 1.28 * total_spread
        high = prediction + 1.28 * total_spread

        model_mu, model_sd, _, coef = active["model"]
        contributions = pd.Series(
            ((X[0] - model_mu) / model_sd) * coef * trust * calib_scale * basis_scale,
            index=active["columns"],
        )
        if use_pair_layer:
            contributions["Pair chemistry (10 pairs)"] = synergy_effect * basis_scale

        if beyond_history:
            unusual_label = "Unlike any in history"
        elif unusual_pct >= 99:
            unusual_label = "Extreme"
        elif unusual_pct >= 90:
            unusual_label = "Very unusual"
        elif unusual_pct >= 70:
            unusual_label = "Unusual"
        else:
            unusual_label = "Typical"

        r1, r2, r3 = st.columns(3)
        r1.metric(
            f"Predicted {target_label.split(' (')[0].lower()}",
            f"{prediction:+.1f} per 100",
            help="These five on the floor together, relative to an "
                 "average team of the same season.",
        )
        r2.metric(
            "Approx. 80% model range",
            "Capped" if capped_by_history else f"{low:+.1f} to {high:+.1f}",
            help="Combines held-out prediction error with variation across "
                 "season-resampled fits, then uses a normal-error multiplier. "
                 "It has not been calibrated to contain 80% of future lineup "
                 "results. A wide range means the estimate is weak.",
        )
        r3.metric(
            "How unusual is this group?",
            unusual_label,
            help=f"More unusual than {unusual_pct:.0f}% of real "
                 "historical cores.",
        )

        if active_key == "interact" and unusual_pct >= 99:
            st.caption(
                "The skill-interaction model remains active for this unusual "
                "group. Treat the prediction cautiously; strict mode clips "
                "the interaction inputs to the training range."
            )

        if high - low >= 20:
            st.warning(
                "This model range is wide enough that the prediction does "
                "not reliably distinguish a strong lineup from a weak one. "
                "Treat the point estimate as exploratory."
            )

        if use_lineups:
            st.caption(
                f"For scale: the best real lineup in the data (200+ minutes) "
                f"was {best_seen:+.1f} and the worst was {worst_seen:+.1f}."
            )
        else:
            st.caption(
                f"For scale: the best real team in the data works out to "
                f"{best_seen * basis_scale:+.1f} on a five-on-the-floor basis, "
                f"and the worst to {worst_seen * basis_scale:+.1f}."
            )

        scaled_any = any(r["Everyone scaled to"] < 0.98 for r in pool_report)

        if scaled_any:
            st.markdown("#### Historical volume caps")
            st.write(
                "The five players' season per-100 rates add up above the "
                "historical cap for these categories. The app proportionally "
                "reduces every player's rate in each affected category. "
                "This is a conservative heuristic based on summed rates, "
                "not a measured teammate effect. Turn it off above to see "
                "the prediction without these caps."
            )
            pool_table = pd.DataFrame(pool_report)
            shown = pool_table[pool_table["Everyone scaled to"] < 0.98]
            st.dataframe(
                shown.style.format({
                    "Five players would use": "{:.1f}",
                    "Typical top five": "{:.1f}",
                    "Observed 99th pct cap": "{:.1f}",
                    "Everyone scaled to": "{:.0%}",
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "The cap is usually the 99th percentile of summed player "
                "rates in historical lineups; if there are too few such "
                "lineups, the team top-five distribution is used. It does "
                "not establish that blocks, steals, or rebounds actually "
                "fall by this amount when these specific players share the "
                "floor. Percentages such as 3P% are not capped."
            )
        elif pool_report:
            with st.expander("Historical volume caps (nothing needed scaling)"):
                st.dataframe(
                    pd.DataFrame(pool_report).style.format({
                        "Five players would use": "{:.1f}",
                        "Typical top five": "{:.1f}",
                        "Observed 99th pct cap": "{:.1f}",
                        "Everyone scaled to": "{:.0%}",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

        if strict and capped_by_history:
            st.warning(
                "Strict mode: the model's number went beyond every real "
                f"team in the data (best: {best_seen:+.1f}, worst: "
                f"{worst_seen:+.1f}), so it is shown capped. Switch to "
                "'Extrapolate' to see the uncapped estimate and its range."
            )
        elif not strict and beyond_history:
            st.info(
                "No group in the data looks like this one, so the model is "
                "extrapolating. It can still be useful here because it "
                "builds the answer from capabilities that real teams did "
                "or didn't have, but the range above is the honest answer, "
                "not the single number. A wide range means 'unknown', not "
                "'bad'."
            )
        elif not strict and prediction_team > best_seen:
            st.info(
                f"This beats the best real result in the data "
                f"({best_seen:+.1f}). Check the range and the drivers "
                "below before trusting it."
            )
        elif unusual_pct >= 99:
            st.warning(
                "This group is more extreme than 99% of real historical "
                "cores. Treat the prediction as shaky."
            )

        if strict and (outside or abs(unadjusted_prediction - prediction) > 0.05):
            st.caption(
                f"Raw model output was {unadjusted_prediction:+.1f}. "
                f"Strict mode limited it to {prediction:+.1f}."
            )

        if outside:
            with st.expander(
                f"{len(outside)} measures are beyond anything in the data"
            ):
                outside_table = pd.DataFrame(
                    outside,
                    columns=["Measure", "This group", "Historical limit",
                             "Beyond by"],
                ).sort_values("Beyond by", ascending=False)
                st.dataframe(
                    outside_table.round(2),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(
                    "Values are standard deviations vs. the league. The "
                    "historical limit is the 1st/99th percentile of real "
                    "top-five groups. "
                    + ("Strict mode only shows the model values up to that "
                       "limit." if strict else
                       "These values are passed to the model as they are.")
                )

        names = []
        for idx in selected_rows:
            row = df.loc[idx]
            names.append(f"{row['player_name']} {row['Season']}")

        if use_pair_layer and pair_table is not None:
            st.markdown("#### Pair chemistry")
            st.write(
                "Ten pairs share the floor in a lineup. 'Skills predict' is "
                "how well each pair's skills fit together, beyond how good "
                "each player is on his own, scored by a model that never saw "
                "that pair's own results. 'Real history' is how the pair "
                "actually deviated from its parts, shown for context."
            )
            shown_pairs = pair_table.assign(
                **{"Shared minutes": pair_table["Shared minutes"].round(0)}
            )
            st.dataframe(
                shown_pairs.style.format({
                    "Skills predict": "{:+.2f}",
                    "Shared minutes": "{:.0f}",
                    "Real history": "{:+.2f}",
                    "Used": "{:+.2f}",
                }, na_rep="—"),
                use_container_width=True,
                hide_index=True,
            )

            best_pair = pair_table.loc[pair_table["Used"].idxmax()]
            worst_pair = pair_table.loc[pair_table["Used"].idxmin()]
            st.caption(
                f"Best fit: {best_pair['Pair']} ({best_pair['Used']:+.2f}). "
                f"Worst fit: {worst_pair['Pair']} ({worst_pair['Used']:+.2f}). "
                f"Total chemistry across the 10 pairs: "
                f"{pair_table['Used'].sum():+.2f}, scaled by "
                f"{pair_layer['backtest']['lam']:.2f} to {synergy_effect:+.2f} "
                "per 100 in the prediction. "
                + ("Each pair's real history was blended in."
                   if blend_history else
                   "Real history is shown but not used.")
            )

        if lineup_data is not None:
            hist_column, hist_sign = LINEUP_TARGET_COLUMNS[target_label]
            same_five = lineup_history(
                lineup_data, [df.loc[r, "player_id"] for r in selected_rows]
            )
            st.markdown("#### Has this exact five played together?")
            if same_five.empty:
                st.caption(
                    "Not in the lineup data. These five never shared the "
                    "floor (or only did so outside the downloaded top "
                    "players), so the estimate rests on skills alone."
                )
            else:
                minutes_together = float(same_five["Minutes"].sum())
                observed = float(
                    hist_sign * (same_five[hist_column] * same_five["Minutes"]).sum()
                    / minutes_together
                )
                trust_history = minutes_together / (minutes_together + LINEUP_SHRINK_MINUTES)
                blended_history = trust_history * observed + (1 - trust_history) * prediction
                h1, h2, h3 = st.columns(3)
                h1.metric("What actually happened", f"{observed:+.1f}",
                          help="Minutes-weighted, relative to a league-average team.")
                h2.metric("Minutes together", f"{minutes_together:,.0f}")
                h3.metric("Estimate if history were blended in", f"{blended_history:+.1f}",
                          help="For comparison only. It is not part of the "
                               "prediction above, which doesn't use this "
                               "lineup's own results. Leans on history more "
                               "as minutes grow.")
                st.dataframe(
                    same_five[["Season", "Team", "Minutes", "Sample", "NetRtg", "OffRtg", "DefRtg"]]
                    .rename(columns={"NetRtg": "Net", "OffRtg": "Off", "DefRtg": "Def"})
                    .style.format({"Minutes": "{:.0f}", "Net": "{:+.1f}",
                                   "Off": "{:.1f}", "Def": "{:.1f}"}, na_rep="—"),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(
                    "Five-man results are noisy, so the blend trusts them "
                    "slowly. "
                    + ("The model was trained on lineups like this one, so "
                       "agreement here isn't an independent test."
                       if use_lineups else "")
                )

        # ---- How this number was built ----
        def model_for(key, vector, pair_values=None):
            info = results[key]
            row = _builder_design(
                pd.DataFrame([vector], columns=feature_cols), key == "interact",
                interaction_cols,
                interaction_values=(pair_interaction_vec if pair_values is None
                                    else pair_values),
            )
            row = row[info["columns"]]
            return float(_ridge_predict(info["model"], row.to_numpy(float))[0])

        unscaled_z = zfeat.loc[selected_rows, base_cols]
        vec_unscaled = (
            pd.concat([unscaled_z.mean(axis=0), role_values(unscaled_z)])
            .reindex(feature_cols).fillna(0).to_numpy(float)
        )
        pair_unscaled = pair_interaction_vec
        if interaction_cols and interaction_axes is not None and interaction_axes.shape[1]:
            pair_unscaled = _builder_pair_interactions(
                (unscaled_z.to_numpy(dtype=np.float32) @ interaction_axes)[None, :, :]
            )[0]
        skills_only = model_for("additive", vec_unscaled)
        active_unscaled = model_for(active_key, vec_unscaled, pair_unscaled)
        active_limited = model_for(active_key, raw_vec, pair_interaction_vec)

        stage_rows = [
            ("Individual skills (sum of parts)", skills_only,
             "What the five can do, added up, vs. an average team."),
            ("Skill interactions, including player-pair fit",
             active_unscaled - skills_only,
             "Credit or penalty learned from how skills combine across the five players."),
            ("Historical volume caps", active_limited - active_unscaled,
             "Proportional adjustment to summed per-100 rates; heuristic, "
             "not a measured teammate effect."),
            ("Stretching to match history", (calib_scale - 1.0) * active_limited,
             "Calibration correction, if switched on."),
            ("Pair chemistry", synergy_effect,
             "How the ten pairs' skills fit, if switched on."),
        ]
        stage_rows.append((
            "Guardrails", prediction_team - sum(v for _, v, _ in stage_rows),
            "Strict-mode clipping, shrinking or capping, if any."
        ))
        stage_rows.append((
            "Bench dilution removed", prediction - prediction_team,
            "Converts a whole-team result into five players on the floor "
            "together."
        ))

        steps = pd.DataFrame(stage_rows, columns=["Step", "Effect", "What it means"])
        steps = steps[(steps["Effect"].abs() >= 0.005) | (steps.index == 0)].copy()
        steps["Running total"] = steps["Effect"].cumsum()

        st.markdown("#### How this number was built")
        st.dataframe(
            steps[["Step", "Effect", "Running total", "What it means"]]
            .style.format({"Effect": "{:+.2f}", "Running total": "{:+.2f}"}),
            use_container_width=True,
            hide_index=True,
        )
        st.bar_chart(steps.set_index("Step")["Effect"], use_container_width=True)
        st.caption(
            f"Starts at a league-average team (0) and ends at the "
            f"prediction ({prediction:+.2f})."
        )

        player_effects = []
        for k in range(5):
            swapped = lineup_z.copy()
            swapped.iloc[k] = 0.0     # a league-average player in his place
            vec = (
                pd.concat([swapped.mean(axis=0), role_values(swapped)])
                .reindex(feature_cols).fillna(0).to_numpy(float)
            )
            player_effects.append(
                (model_for(active_key, raw_vec, pair_interaction_vec)
                 - model_for(
                     active_key,
                     vec,
                     _builder_pair_interactions(
                         (swapped[base_cols].to_numpy(dtype=np.float32) @ interaction_axes)[None, :, :]
                     )[0] if interaction_cols and interaction_axes is not None
                     and interaction_axes.shape[1] else pair_interaction_vec,
                 ))
                * calib_scale * basis_scale
            )

        contribution_table = pd.DataFrame({
            "Player": names,
            "Contribution (skills only)": player_effects,
        }).sort_values("Contribution (skills only)", ascending=False)
        st.markdown("#### Each player's contribution")
        st.dataframe(
            contribution_table.style.format({"Contribution (skills only)": "{:+.2f}"}),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "How much each player adds compared with swapping in a "
            "league-average player and leaving the other four alone. These "
            "won't add up exactly to the total, because skills interact and "
            "the five share the same shots and rebounds. Pair chemistry is "
            "shown separately."
        )

        st.markdown("#### What drives this prediction")

        top_drivers = contributions.reindex(
            contributions.abs().sort_values(ascending=False).index
        ).head(10)
        driver_table = pd.DataFrame({
            "Factor": top_drivers.index,
            "Effect (pts/100)": top_drivers.values.round(2),
            "Type": [
                "Pair data" if f.startswith("Pair chemistry")
                else "Interaction" if ("×" in f or "squared" in f)
                else "Skill"
                for f in top_drivers.index
            ],
        })
        st.dataframe(driver_table, use_container_width=True, hide_index=True)

        st.caption(
            "Positive effects raise the prediction. Rows marked "
            "'Interaction' are stacking terms: they exist only when skills "
            "combine."
        )

        with st.expander(
            "Lineup profile (z-scores vs. each player's season, after "
            "sharing limits)"
        ):
            profile_table = lineup_z.T.round(2)
            profile_table.columns = names
            profile_table["Lineup average"] = lineup.round(2)
            st.dataframe(profile_table, use_container_width=True)
            st.caption(
                "+1.0 means one standard deviation above the average "
                "qualified player of that season."
            )

    # ---- What the model values ----
    with st.expander("What the model values (sum-of-parts weights)"):
        mu, sd, _, coef = additive["model"]
        weights = pd.DataFrame({
            "Skill": additive["columns"],
            "Weight": coef,
        })
        weights["Weight"] = weights["Weight"].round(3)
        weights = weights.sort_values("Weight", ascending=False)
        st.dataframe(weights, use_container_width=True, hide_index=True)
        st.caption(
            "Weights are per standard deviation of the group's average "
            "profile. Many skills overlap (more threes and fewer mid-range "
            "shots tend to go together), so don't read any single weight "
            "as that skill's isolated effect."
        )

    # ---- Over- and under-performers ----
    with st.expander(
        ("Lineups" if use_lineups else "Teams")
        + " that beat or missed their parts (synergy candidates)"
    ):
        history = results["data"].copy()
        history["predicted"] = chosen["oof"]
        history["difference"] = history["actual"] - history["predicted"]

        eras_present = [
            label for label, _, _ in ERAS
            if label in set(history["Era"].dropna())
        ]
        era_pick = st.multiselect(
            "Eras",
            eras_present,
            default=eras_present,
            key="builder_eras",
        )
        history = history[history["Era"].isin(era_pick)]

        shown_columns = (
            ["Season", "Team", "Core five", "Minutes", "actual", "predicted", "difference"]
            if use_lineups else
            ["Season", "Tm", "Core five", "actual", "predicted", "difference"]
        )
        view = history[shown_columns].rename(columns={
            "actual": "Actual",
            "predicted": "Predicted (unseen)",
            "difference": "Beat prediction by",
        })

        formats = {
            "Actual": "{:+.1f}",
            "Predicted (unseen)": "{:+.1f}",
            "Beat prediction by": "{:+.1f}",
            "Minutes": "{:.0f}",
        }
        if use_lineups:
            view = view[view["Minutes"] >= LINEUP_CAP_MIN_MINUTES]

        st.markdown("**Beat their parts the most**")
        st.dataframe(
            view.nlargest(10, "Beat prediction by").style.format(formats),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("**Fell short of their parts the most**")
        st.dataframe(
            view.nsmallest(10, "Beat prediction by").style.format(formats),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Predictions here come from models that never saw that season. "
            "A big gap can mean synergy, coaching, health, depth, or "
            "things this data can't see, so treat it as a place to start "
            "looking, not a verdict."
        )


# --------------------------------------------------
# PAIR LAB HELPERS
# --------------------------------------------------

PAIR_FILE = Path(__file__).parent / "player_pair_seasons.csv.gz"

PAIR_RATES = ["OffRtg", "DefRtg", "NetRtg"]
PAIR_PCTS = ["Fg3Pct", "Fg2Pct", "OppFg3Pct", "OppFg2Pct"]

# Small samples are pulled toward the team baseline: with this many
# shared minutes, half of a pair's difference from baseline is kept.
PAIR_SHRINK_MINUTES = 400

PAIR_SAMPLE_LABELS = [
    "⚪ No shared minutes",
    "🔴 Very low (<50 min)",
    "🟠 Low (50-199 min)",
    "🟡 Moderate (200-499 min)",
    "🟢 Solid (500+ min)",
]


def pair_sample_label(minutes):
    """Evidence tier for a Series (or single number) of shared minutes."""
    scalar = np.isscalar(minutes)
    m = pd.to_numeric(pd.Series([minutes] if scalar else minutes), errors="coerce")
    m = m.fillna(0)
    labels = np.select(
        [m <= 0, m < 50, m < 200, m < 500],
        PAIR_SAMPLE_LABELS[:4],
        default=PAIR_SAMPLE_LABELS[4],
    )
    return labels[0] if scalar else pd.Series(labels, index=m.index)


def _clean_id(series):
    return (
        series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    )


def _read_name_lookup():
    """Same player_id -> name mapping the rest of the app uses."""
    try:
        names = pd.read_csv(NAME_FILE, low_memory=False)
        names["player_id"] = _clean_id(names["player_id"])
        names = names.dropna(subset=["player_id", "player"])
        names["player"] = names["player"].astype(str).str.strip()
        names = names[names["player"] != ""]
        return names.drop_duplicates("player_id").set_index("player_id")["player"]
    except Exception:
        return pd.Series(dtype="string")


@st.cache_data(show_spinner="Loading player-pair data...", max_entries=1)
def load_pairs():
    """Load and clean the pair file. Returns (data, report).

    Nothing here assumes the file is tidy: units and scales are detected,
    and everything unusual is recorded in the report for the Data checks tab.
    """
    report = {"notes": [], "problems": []}

    raw = pd.read_csv(
        PAIR_FILE,
        compression="gzip",
        dtype={"Player1Id": "string", "Player2Id": "string", "TeamId": "string"},
        low_memory=False,
    )
    raw.columns = [str(c).strip() for c in raw.columns]
    report["rows_raw"] = len(raw)
    report["columns"] = list(raw.columns)

    required = ["Season", "Player1Id", "Player2Id", "Minutes"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        report["problems"].append(f"Missing required columns: {', '.join(missing)}")
        return None, report

    d = raw.copy()
    d["Player1Id"] = _clean_id(d["Player1Id"])
    d["Player2Id"] = _clean_id(d["Player2Id"])
    d["Season"] = d["Season"].astype("string").str.strip()

    if "TeamId" in d.columns:
        d["TeamId"] = _clean_id(d["TeamId"])
    else:
        d["TeamId"] = pd.NA
        report["notes"].append("No TeamId column; teams are identified by name.")
    if "Team" not in d.columns:
        d["Team"] = d["TeamId"]
        report["notes"].append("No Team column; using TeamId as the team label.")
    d["Team"] = d["Team"].astype("string").str.strip()
    if "SeasonType" not in d.columns:
        d["SeasonType"] = "Regular Season"
        report["notes"].append("No SeasonType column; assuming regular season.")
    d["SeasonType"] = d["SeasonType"].astype("string").str.strip()

    for column in ["Minutes"] + PAIR_RATES + PAIR_PCTS:
        if column in d.columns:
            d[column] = pd.to_numeric(d[column], errors="coerce", downcast="float")
        else:
            d[column] = np.nan
            report["notes"].append(f"Column {column} not in file; left blank.")

    # Drop rows we can't interpret as a pair of two different players.
    bad = (
        d["Player1Id"].isna() | d["Player2Id"].isna()
        | (d["Player1Id"] == d["Player2Id"])
        | d["Season"].isna() | d["Team"].isna()
    )
    report["unusable_rows"] = int(bad.sum())
    d = d[~bad].copy()

    # Minutes: detect seconds vs minutes.
    positive = d.loc[d["Minutes"] > 0, "Minutes"]
    if len(positive) and positive.quantile(0.99) > 5000:
        d["Minutes"] = d["Minutes"] / 60
        report["notes"].append(
            "Minutes looked like seconds (99th percentile above 5,000), "
            "so they were divided by 60."
        )
    elif len(positive):
        report["notes"].append(
            "Minutes treated as minutes "
            f"(median {positive.median():.0f}, max {positive.max():.0f})."
        )

    # Zero-minute rows: their ratings are placeholders, not performance.
    zero = d["Minutes"].fillna(0) <= 0
    report["zero_minute_rows"] = int(zero.sum())
    nonblank = d.loc[zero, PAIR_RATES + PAIR_PCTS].fillna(0).ne(0).any(axis=1)
    report["zero_minute_with_values"] = int(nonblank.sum())
    d.loc[zero, PAIR_RATES + PAIR_PCTS] = np.nan

    # Net rating: fill in from offense and defense if needed; sanity check.
    off_def = d["OffRtg"].notna() & d["DefRtg"].notna()
    if d["NetRtg"].notna().sum() == 0 and off_def.any():
        d["NetRtg"] = d["OffRtg"] - d["DefRtg"]
        report["notes"].append("NetRtg was empty; computed as OffRtg - DefRtg.")
    both = off_def & d["NetRtg"].notna()
    if both.any():
        mismatch = ((d.loc[both, "NetRtg"] - (d.loc[both, "OffRtg"] - d.loc[both, "DefRtg"])).abs() > 0.6).mean()
        report["net_mismatch_share"] = float(mismatch)

    # Shooting percentages: fractions or percents?
    for column in PAIR_PCTS:
        positive_pct = d.loc[d[column] > 0, column]
        if len(positive_pct) and positive_pct.quantile(0.99) <= 1.5:
            d[column] = d[column] * 100
            report["notes"].append(f"{column} was a fraction (0-1); converted to percent.")
        d.loc[d[column] > 100, column] = np.nan
        # An exact 0% on a tiny sample almost always means "no attempts".
        suspect = (d[column] == 0) & (d["Minutes"] < 100)
        report[f"{column}_zero_blanked"] = int(suspect.sum())
        d.loc[suspect, column] = np.nan

    # One row per pair: put the two IDs in a fixed order, drop mirrors.
    first, second = d["Player1Id"], d["Player2Id"]
    swap = first > second
    d["PlayerA"] = first.where(~swap, second).astype(str)
    d["PlayerB"] = second.where(~swap, first).astype(str)
    for column in ["Season", "Team", "SeasonType"]:
        d[column] = d[column].astype(str)

    team_key = "TeamId" if d["TeamId"].notna().any() else "Team"
    keys = ["Season", "SeasonType", team_key, "PlayerA", "PlayerB"]
    before = len(d)
    d = d.sort_values("Minutes", ascending=False).drop_duplicates(keys)
    report["duplicates_removed"] = before - len(d)

    # Names, using the same mapping as the rest of the app.
    lookup = _read_name_lookup()
    d["NameA"] = d["PlayerA"].map(lookup)
    d["NameB"] = d["PlayerB"].map(lookup)
    report["name_coverage"] = float(
        (d["NameA"].notna() & d["NameB"].notna()).mean()
    ) if len(d) else 0.0
    d["NameA"] = d["NameA"].fillna("Player " + d["PlayerA"])
    d["NameB"] = d["NameB"].fillna("Player " + d["PlayerB"])

    # Team baselines (minutes-weighted over that team's pairs).
    group = ["Season", "SeasonType", "Team"]
    valid = d["Minutes"] > 0
    for rating, label in (("NetRtg", "BaseNet"), ("OffRtg", "BaseOff"), ("DefRtg", "BaseDef")):
        ok = valid & d[rating].notna()
        tmp = d.loc[ok, group + ["Minutes", rating]].copy()
        tmp["_w"] = tmp[rating] * tmp["Minutes"]
        agg = tmp.groupby(group).agg(_w=("_w", "sum"), _m=("Minutes", "sum"))
        agg[label] = agg["_w"] / agg["_m"]
        d = d.merge(agg[[label]].reset_index(), on=group, how="left")

    d["NetVsTeam"] = d["NetRtg"] - d["BaseNet"]
    d["Shrunk"] = d["NetVsTeam"] * d["Minutes"] / (d["Minutes"] + PAIR_SHRINK_MINUTES)
    d["Sample"] = pair_sample_label(d["Minutes"])

    d = d.reset_index(drop=True)
    report["rows_clean"] = len(d)
    return d, report


def _weighted(group, column):
    weights = group["Minutes"].clip(lower=0)
    ok = group[column].notna() & (weights > 0)
    if not ok.any() or weights[ok].sum() <= 0:
        return np.nan
    return float((group.loc[ok, column] * weights[ok]).sum() / weights[ok].sum())


def pair_by_season(history):
    """One row per season for a pair (minutes-weighted if traded mid-season)."""
    rows = []
    for season, group in history.groupby("Season"):
        row = {
            "Season": season,
            "Team": ", ".join(sorted(group["Team"].unique())),
            "Minutes": float(group["Minutes"].clip(lower=0).sum()),
        }
        for column in PAIR_RATES + PAIR_PCTS:
            row[column] = _weighted(group, column)
        rows.append(row)
    table = pd.DataFrame(rows).sort_values("Season").reset_index(drop=True)
    table["Sample"] = pair_sample_label(table["Minutes"])
    return table


def _pair_skill_context(df, pid_a, pid_b, name_a, name_b, season):
    """Each player's skill profile (z-scores vs. that season's league)."""
    zfeat, _, _ = builder_tables(df)
    if zfeat.empty or "Season" not in df.columns:
        return None

    minutes = _minutes(df)
    if name_a == name_b:
        name_b = name_b + " (2)"

    columns = {}
    for pid, name in ((pid_a, name_a), (pid_b, name_b)):
        rows = df.index[
            (df["player_id"].astype(str) == pid)
            & (df["Season"].astype(str) == season)
        ]
        if len(rows) == 0:
            continue
        best = minutes.loc[rows].idxmax() if minutes is not None else rows[0]
        columns[name] = zfeat.loc[best]

    if not columns:
        return None
    table = pd.DataFrame(columns)
    if len(columns) == 2:
        table["Pair average"] = table.mean(axis=1)
    return table


def _show_pair_metrics(row):
    minutes = float(row["Minutes"])
    st.markdown(f"**Evidence:** {row['Sample']}")

    if minutes <= 0:
        st.warning(
            "This pair is listed but never shared the floor, so its ratings "
            "are blank. A blank is not a zero: there's no performance to "
            "report."
        )
        return

    if minutes < 200:
        st.warning(
            f"Only {minutes:.0f} shared minutes. Ratings from samples this "
            "small swing a lot, so treat them as noise unless other seasons "
            "agree."
        )

    def number(value, fmt):
        return "—" if pd.isna(value) else fmt.format(value)

    def delta(value, base):
        if pd.isna(value) or pd.isna(base):
            return None
        return f"{value - base:+.1f} vs team"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Shared minutes", f"{minutes:,.0f}")
    c2.metric("Net rating", number(row["NetRtg"], "{:+.1f}"),
              delta(row["NetRtg"], row["BaseNet"]))
    c3.metric("Offensive rating", number(row["OffRtg"], "{:.1f}"),
              delta(row["OffRtg"], row["BaseOff"]))
    c4.metric("Defensive rating", number(row["DefRtg"], "{:.1f}"),
              delta(row["DefRtg"], row["BaseDef"]), delta_color="inverse")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("3P%", number(row["Fg3Pct"], "{:.1f}%"))
    s2.metric("2P%", number(row["Fg2Pct"], "{:.1f}%"))
    s3.metric("Opponent 3P%", number(row["OppFg3Pct"], "{:.1f}%"))
    s4.metric("Opponent 2P%", number(row["OppFg2Pct"], "{:.1f}%"))

    if pd.notna(row["NetVsTeam"]):
        st.caption(
            f"Net rating vs. the team's baseline: {row['NetVsTeam']:+.1f} raw, "
            f"{row['Shrunk']:+.1f} after adjusting for sample size. "
            "The baseline is the team's minutes-weighted average across all "
            "its pairs that season."
        )


def _pair_lookup(pairs, df):
    types = sorted(pairs["SeasonType"].unique())
    default_type = types.index("Regular Season") if "Regular Season" in types else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        season_type = st.selectbox("Season type", types, index=default_type, key="pair_type")
    typed = pairs[pairs["SeasonType"] == season_type]

    seasons = sorted(typed["Season"].unique(), reverse=True)
    if not seasons:
        st.info("No data for that season type.")
        return
    with c2:
        season = st.selectbox("Season", seasons, key="pair_season")
    in_season = typed[typed["Season"] == season]

    teams = sorted(in_season["Team"].unique())
    with c3:
        team = st.selectbox("Team", teams, key="pair_team")
    sub = in_season[in_season["Team"] == team]

    # Players on this team-season, with unambiguous labels.
    names = {**dict(zip(sub["PlayerA"], sub["NameA"])),
             **dict(zip(sub["PlayerB"], sub["NameB"]))}
    name_counts = pd.Series(list(names.values())).value_counts()
    label_of = {
        pid: (name if name_counts[name] == 1 else f"{name} ({pid})")
        for pid, name in names.items()
    }
    player_ids = sorted(names, key=lambda p: label_of[p].lower())

    p1_label = st.selectbox(
        "First player (type to search)",
        [label_of[p] for p in player_ids],
        key=f"pair_p1_{season_type}_{season}_{team}",
    )
    p1 = next(p for p in player_ids if label_of[p] == p1_label)

    # Partners with a record first (most shared minutes first), then the rest.
    mine = sub[(sub["PlayerA"] == p1) | (sub["PlayerB"] == p1)].copy()
    mine["Partner"] = np.where(mine["PlayerA"] == p1, mine["PlayerB"], mine["PlayerA"])
    shared = mine.groupby("Partner")["Minutes"].sum().sort_values(ascending=False)

    options, option_to_id = [], {}
    for partner, minutes in shared.items():
        text = (f"{label_of[partner]} · {minutes:.0f} min together"
                if minutes > 0 else f"{label_of[partner]} · listed, 0 min")
        options.append(text)
        option_to_id[text] = partner
    for pid in player_ids:
        if pid != p1 and pid not in shared.index:
            text = f"{label_of[pid]} · no shared record"
            options.append(text)
            option_to_id[text] = pid

    if not options:
        st.info("This player has no teammates in the data for that team-season.")
        return

    p2_text = st.selectbox(
        "Second player (partners sorted by shared minutes)",
        options,
        key=f"pair_p2_{season_type}_{season}_{team}_{p1}",
    )
    p2 = option_to_id[p2_text]
    lo, hi = sorted([p1, p2])

    st.markdown(f"### {label_of[p1]} + {label_of[p2]}")
    record = sub[(sub["PlayerA"] == lo) & (sub["PlayerB"] == hi)]

    if record.empty:
        st.info(
            "No record for this pair with this team in this season. That "
            "means they have no data together here (they likely never "
            "shared the floor). It is not a rating of zero."
        )
    else:
        _show_pair_metrics(record.iloc[0])

    st.caption(
        "These are descriptive numbers. Minutes, the other three players on "
        "the floor, opponents and sample size all shape them, so they don't "
        "prove two players make each other better."
    )

    # ---- Across seasons ----
    st.markdown("#### This pair across seasons")
    history = pairs[
        (pairs["PlayerA"] == lo) & (pairs["PlayerB"] == hi)
        & (pairs["SeasonType"] == season_type)
    ]

    if history.empty:
        st.caption("This pair has no record in any season for this season type.")
    else:
        by_season = pair_by_season(history)
        if len(by_season) < 2:
            st.caption(
                "Only one season on record for this pair, so there's no "
                "trend to compare."
            )
        st.dataframe(
            by_season[["Season", "Team", "Minutes", "Sample", "NetRtg", "OffRtg",
                       "DefRtg", "Fg3Pct", "Fg2Pct", "OppFg3Pct", "OppFg2Pct"]]
            .rename(columns={"NetRtg": "Net", "OffRtg": "Off", "DefRtg": "Def",
                             "Fg3Pct": "3P%", "Fg2Pct": "2P%",
                             "OppFg3Pct": "Opp 3P%", "OppFg2Pct": "Opp 2P%"})
            .style.format({"Minutes": "{:.0f}", "Net": "{:+.1f}", "Off": "{:.1f}",
                           "Def": "{:.1f}", "3P%": "{:.1f}", "2P%": "{:.1f}",
                           "Opp 3P%": "{:.1f}", "Opp 2P%": "{:.1f}"}, na_rep="—"),
            use_container_width=True,
            hide_index=True,
        )

        if len(by_season) >= 2:
            floor = st.slider(
                "Chart only seasons with at least this many shared minutes",
                min_value=0, max_value=1000, value=100, step=25,
                key="pair_chart_floor",
            )
            plotted = by_season[by_season["Minutes"] >= max(floor, 1)]
            if len(plotted) >= 2:
                chart = plotted.set_index("Season")[["NetRtg", "OffRtg", "DefRtg"]]
                st.line_chart(chart, use_container_width=True)
            else:
                st.caption("Fewer than two seasons clear that minutes bar, so there's nothing to chart.")

    # ---- Skill context ----
    if st.checkbox("Show each player's skill profile for this season",
                   value=False, key="pair_skills"):
        try:
            context = _pair_skill_context(
                df, p1, p2, names[p1], names[p2], season
            )
        except Exception as error:
            context = None
            st.caption(f"Couldn't build skill profiles: {error}")
        if context is None:
            st.caption(
                "No matching player-stat rows for those players in this "
                "season, so no skill profile to show."
            )
        else:
            st.dataframe(context.round(2), use_container_width=True)
            st.caption(
                "Standard deviations vs. the league that season (+1 is one "
                "above average). Use it to ask what each player brings, "
                "not as an explanation of the pair's rating."
            )


def _pair_explorer(pairs):
    types = sorted(pairs["SeasonType"].unique())
    default_type = types.index("Regular Season") if "Regular Season" in types else 0

    f1, f2 = st.columns(2)
    with f1:
        season_type = st.selectbox("Season type", types, index=default_type, key="pe_type")
    all_seasons = sorted(pairs.loc[pairs["SeasonType"] == season_type, "Season"].unique())
    if not all_seasons:
        st.info("No data for that season type.")
        return
    with f2:
        if len(all_seasons) > 1:
            start, end = st.select_slider(
                "Seasons", options=all_seasons,
                value=(all_seasons[0], all_seasons[-1]), key="pe_seasons",
            )
        else:
            start = end = all_seasons[0]

    g1, g2, g3 = st.columns(3)
    with g1:
        chosen_teams = st.multiselect("Teams (blank = all)", sorted(pairs["Team"].unique()), key="pe_teams")
    with g2:
        query = st.text_input("Player name contains", key="pe_query")
    with g3:
        min_minutes = st.slider("Minimum shared minutes", 0, 2000, 200, 25, key="pe_min")

    sort_options = {
        "Net vs team, sample-adjusted (recommended)": ("Shrunk", False),
        "Net rating": ("NetRtg", False),
        "Net vs team (raw)": ("NetVsTeam", False),
        "Offensive rating": ("OffRtg", False),
        "Defensive rating (lower is better)": ("DefRtg", True),
        "Shared minutes": ("Minutes", False),
        "3P%": ("Fg3Pct", False),
        "2P%": ("Fg2Pct", False),
        "Opponent 3P% (lower is better)": ("OppFg3Pct", True),
        "Opponent 2P% (lower is better)": ("OppFg2Pct", True),
    }
    h1, h2, h3 = st.columns(3)
    with h1:
        sort_label = st.selectbox("Sort by", list(sort_options.keys()), key="pe_sort")
    with h2:
        direction = st.radio("Order", ["Best first", "Worst first"], horizontal=True, key="pe_dir")
    with h3:
        rows_to_show = st.select_slider("Rows to show", options=[25, 50, 100, 250], value=50, key="pe_rows")

    f = pairs[
        (pairs["SeasonType"] == season_type)
        & pairs["Season"].between(start, end)
        & (pairs["Minutes"] > 0)
        & (pairs["Minutes"] >= min_minutes)
    ]
    if chosen_teams:
        f = f[f["Team"].isin(chosen_teams)]
    if query.strip():
        q = query.strip()
        f = f[
            f["NameA"].str.contains(q, case=False, na=False, regex=False)
            | f["NameB"].str.contains(q, case=False, na=False, regex=False)
        ]

    if f.empty:
        st.info("No pairs match those filters. Try lowering the minimum minutes.")
        return

    column, best_is_low = sort_options[sort_label]
    ascending = best_is_low if direction == "Best first" else not best_is_low
    ranked = f.dropna(subset=[column]).sort_values(column, ascending=ascending)

    st.caption(
        f"{len(ranked):,} pair-seasons match. "
        f"{(ranked['Minutes'] < 500).mean():.0%} of them have fewer than 500 shared minutes. "
        "Pairs with no shared minutes are left out."
    )

    view = ranked.head(rows_to_show)[[
        "NameA", "NameB", "Season", "Team", "Minutes", "Sample", "NetRtg",
        "NetVsTeam", "Shrunk", "OffRtg", "DefRtg", "Fg3Pct", "Fg2Pct",
        "OppFg3Pct", "OppFg2Pct",
    ]].rename(columns={
        "NameA": "Player 1", "NameB": "Player 2", "NetRtg": "Net",
        "NetVsTeam": "Net vs team", "Shrunk": "Adjusted vs team",
        "OffRtg": "Off", "DefRtg": "Def", "Fg3Pct": "3P%", "Fg2Pct": "2P%",
        "OppFg3Pct": "Opp 3P%", "OppFg2Pct": "Opp 2P%",
    })
    st.dataframe(
        view.style.format({
            "Minutes": "{:.0f}", "Net": "{:+.1f}", "Net vs team": "{:+.1f}",
            "Adjusted vs team": "{:+.1f}", "Off": "{:.1f}", "Def": "{:.1f}",
            "3P%": "{:.1f}", "2P%": "{:.1f}", "Opp 3P%": "{:.1f}", "Opp 2P%": "{:.1f}",
        }, na_rep="—"),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "'Adjusted vs team' pulls small samples toward the team's baseline, "
        "so a hot 80-minute pair doesn't outrank a proven 1,500-minute one. "
        "Look for pairs that stay good across seasons and teammates."
    )


def _pair_checks(pairs, report):
    st.write("What the pair file actually contains, and what was cleaned.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows in file", f"{report['rows_raw']:,}")
    m2.metric("Rows after cleaning", f"{report['rows_clean']:,}")
    m3.metric("Seasons", f"{pairs['Season'].nunique()}")
    m4.metric("Teams", f"{pairs['Team'].nunique()}")

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("Zero-minute rows", f"{report['zero_minute_rows']:,}")
    n2.metric("...that had non-zero values", f"{report['zero_minute_with_values']:,}",
              help="These were blanked, not treated as performance.")
    n3.metric("Mirror duplicates removed", f"{report['duplicates_removed']:,}")
    n4.metric("Players with a known name", f"{report['name_coverage']:.0%}")

    for problem in report["problems"]:
        st.error(problem)
    for note in report["notes"]:
        st.caption(note)
    if report.get("net_mismatch_share", 0) > 0.02:
        st.warning(
            f"{report['net_mismatch_share']:.0%} of rows have a NetRtg that "
            "doesn't equal OffRtg minus DefRtg (beyond rounding). Worth a look."
        )
    blanked = {c: report.get(f"{c}_zero_blanked", 0) for c in PAIR_PCTS}
    if any(blanked.values()):
        st.caption(
            "Exact 0% shooting on under 100 shared minutes was blanked as "
            "'probably no attempts': "
            + ", ".join(f"{c} {n:,}" for c, n in blanked.items())
        )

    st.markdown("#### Evidence tiers")
    tiers = (pairs["Sample"].value_counts()
             .reindex(PAIR_SAMPLE_LABELS).fillna(0).astype(int).rename("Pair-seasons"))
    st.dataframe(tiers.reset_index().rename(columns={"index": "Tier", "Sample": "Tier"}),
                 use_container_width=True, hide_index=True)

    st.markdown("#### Coverage by season")
    coverage = pairs.groupby(["SeasonType", "Season"]).agg(
        Pairs=("Minutes", "size"),
        Teams=("Team", "nunique"),
        Median_minutes=("Minutes", "median"),
    ).reset_index()
    st.dataframe(coverage.round(1), use_container_width=True, hide_index=True)

    st.markdown("#### Value ranges")
    numeric = pairs[["Minutes"] + PAIR_RATES + PAIR_PCTS]
    st.dataframe(numeric.describe().T.round(2), use_container_width=True)


def render_pair_lab(df):
    """Pair Lab: how two-player combinations have performed."""
    st.subheader("Pair Lab")
    st.write(
        "How two-player combinations performed while sharing the floor. "
        "Good for noticing things worth investigating, not for declaring "
        "that two players make each other better."
    )

    if not PAIR_FILE.exists():
        st.info(
            "Pair data not found. Put `player_pair_seasons.csv.gz` in the "
            "same folder as `app.py`."
        )
        return

    try:
        pairs, report = load_pairs()
    except Exception as error:
        st.error(f"Unable to load the pair data: {error}")
        return

    if pairs is None:
        st.error("; ".join(report["problems"]))
        return

    look_tab, explore_tab, combo_tab, checks_tab = st.tabs(
        ["Look up a pair", "Explore pairs", "Skill combinations", "Data checks"]
    )
    with look_tab:
        _pair_lookup(pairs, df)
    with explore_tab:
        _pair_explorer(pairs)
    with combo_tab:
        _pair_skill_combos(pairs, df)
    with checks_tab:
        _pair_checks(pairs, report)


# --------------------------------------------------
# PAIR SYNERGY LAYER
# --------------------------------------------------
# A pair's net rating (relative to its team) is mostly explained by how good
# each player is. What's left over is how the pair did beyond its parts.
#
# The model learns which SHAPES of skill profile fit together: a symmetric
# compatibility matrix M over the skills, so chemistry(A, B) = zA' M zB. It
# never sees player IDs or teams, so two players who never met are scored
# exactly like any other pair. Outcomes are the training signal (the only place
# "what fits" can be learned), but every pair in a lineup is scored by a model
# that never saw that pair's own results, and the model is validated on pairs
# and players it was never shown.

PAIR_MODEL_MIN_MINUTES = 100       # pairs below this are too noisy to learn from
PAIR_PLAYER_RIDGE = 100.0          # shrinkage on each player-season's own effect
PAIR_MODEL_ALPHAS = [10, 100, 1_000, 10_000, 100_000]
PAIR_FOLDS = 5                      # ways to hold out pairs and players
PAIR_RANKS = [1, 2, 3, 4, 6, 8]     # skill axes to try (plus all of them)
PAIR_EVIDENCE_MINUTES = 600        # shared minutes at which observed results get half the weight
PAIR_MIN_SKILL_MATCH = 0.5         # need this share of pair rows matched to player stats

# builder target -> (pair column, team baseline column, sign so + is good)
PAIR_TARGETS = {
    "Net rating": ("NetRtg", "BaseNet", 1),
    "Offense (points scored per 100)": ("OffRtg", "BaseOff", 1),
    "Defense (points prevented per 100)": ("DefRtg", "BaseDef", -1),
}


def _pair_cache_key():
    """Changes when a data file changes, so cached fits refresh."""
    stamps = []
    for path in (PAIR_FILE, DATA_FILE, NAME_FILE):
        try:
            stamps.append(path.stat().st_mtime)
        except Exception:
            stamps.append(0.0)
    return tuple(stamps)


def _skill_row_lookup(data):
    """'playerid|season' -> the row of that player's main stats that season."""
    minutes = _minutes(data)
    frame = pd.DataFrame(
        {
            "key": data["player_id"].astype(str) + "|" + data["Season"].astype(str),
            "m": minutes.fillna(0) if minutes is not None else 0.0,
        },
        index=data.index,
    )
    best = frame.sort_values("m", ascending=False).drop_duplicates("key")
    return pd.Series(best.index.to_numpy(), index=best["key"].to_numpy())


def _fold_of_key(key, folds=PAIR_FOLDS):
    """A stable fold for a name (same answer every run, unlike hash())."""
    return zlib.crc32(str(key).encode("utf-8")) % folds


def _pair_key(a, b):
    a, b = str(a), str(b)
    return f"{a}|{b}" if a <= b else f"{b}|{a}"


def _pair_feature_names(features):
    count = len(features)
    rows, cols = np.triu_indices(count, k=1)
    names = [f"Both high on {f} (or both low)" for f in features]
    names += [f"One has {features[i]}, the other has {features[j]}"
              for i, j in zip(rows, cols)]
    return names


def _pair_features(za, zb):
    """The ways one player's skills can pair with the other's.

    Every term is a product of one skill from each player, written so the
    answer doesn't depend on which is called A and which B. A fitted weight
    on each term is one entry of a symmetric skill-compatibility matrix.
    """
    count = za.shape[1]
    rows, cols = np.triu_indices(count, k=1)
    return np.hstack([
        za * zb,                                                 # same skill, both
        za[:, rows] * zb[:, cols] + za[:, cols] * zb[:, rows],   # different skills
    ])


def _geometry_matrix(weights, count):
    """Weights on the pair features -> symmetric compatibility matrix M."""
    M = np.zeros((count, count))
    M[np.diag_indices(count)] = weights[:count]
    rows, cols = np.triu_indices(count, k=1)
    M[rows, cols] = weights[count:]
    M[cols, rows] = weights[count:]
    return M


def _weights_from_matrix(M):
    rows, cols = np.triu_indices(M.shape[0], k=1)
    return np.concatenate([np.diag(M), M[rows, cols]])


def _truncate_geometry(M, rank):
    """Keep only the `rank` strongest axes of the compatibility matrix."""
    if rank is None or rank >= M.shape[0]:
        return M
    values, vectors = np.linalg.eigh(M)
    keep = np.argsort(-np.abs(values))[:rank]
    return (vectors[:, keep] * values[keep]) @ vectors[:, keep].T


def _bilinear(za, zb, M):
    """chemistry(A, B) = zA' M zB, for many pairs at once."""
    return ((za @ M) * zb).sum(axis=1)


def _geometry_axes(M, features, top=3):
    """The axes of skill space the compatibility matrix is built from.

    Along an axis, a pair's chemistry is (strength) x (A's score) x (B's
    score). A positive strength rewards players who sit on the same side;
    a negative strength rewards players on opposite sides (complements).
    """
    values, vectors = np.linalg.eigh(M)
    axes = []
    for index in np.argsort(-np.abs(values)):
        if abs(values[index]) < 1e-9:
            continue
        vector = vectors[:, index]
        if vector[np.argmax(np.abs(vector))] < 0:
            vector = -vector
        order = np.argsort(-vector)
        axes.append({
            "value": float(values[index]),
            "strength": float(abs(values[index])),
            "kind": "complement" if values[index] < 0 else "reinforce",
            "high": [features[i] for i in order[:top] if vector[i] > 0.15],
            "low": [features[i] for i in order[::-1][:top] if vector[i] < -0.15],
        })
    return axes


def _pair_residuals(pairs):
    """Strip out each player-season's own effect, leaving pair-specific deviation.

    Within every team-season, a pair's net rating (vs. team) is modeled as
    player A's effect + player B's effect. The residual is how far the pair
    landed from that.
    """
    residual = pd.Series(np.nan, index=pairs.index)
    for _, group in pairs.groupby(["Season", "Team"]):
        players = pd.unique(pd.concat([group["PlayerA"], group["PlayerB"]]))
        position = {p: i for i, p in enumerate(players)}
        n, k = len(group), len(players)
        design = np.zeros((n, k))
        design[np.arange(n), group["PlayerA"].map(position).to_numpy()] = 1.0
        design[np.arange(n), group["PlayerB"].map(position).to_numpy()] = 1.0
        w = group["Minutes"].to_numpy(float)
        y = group["y"].to_numpy(float)
        gram = design.T @ (design * w[:, None]) + PAIR_PLAYER_RIDGE * np.eye(k)
        beta = np.linalg.solve(gram, design.T @ (w * y))
        residual.loc[group.index] = y - design @ beta
    return residual


def _fit_pair_geometry(pairs, za, zb):
    """Learn a skill-compatibility matrix, validated three ways.

    The three scores answer different questions:
      season  - new seasons, but the same players and pairs (flatters it)
      pair    - a pair it never saw, though it saw each player with others
      player  - two players it never saw at all (the real test of geometry)
    Settings are chosen on the strictest test that has enough data, so the
    model is rewarded for generalizing to strangers, not for memorizing.
    """
    count = za.shape[1]
    X = _pair_features(za, zb)
    y = pairs["e"].to_numpy(float)
    minutes = pairs["Minutes"].to_numpy(float)
    w = minutes / minutes.mean()
    total_w = w.sum()

    mu = (X * w[:, None]).sum(axis=0) / total_w
    sd = np.sqrt((((X - mu) ** 2) * w[:, None]).sum(axis=0) / total_w)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd

    id_a, id_b = pairs["PlayerA"].to_numpy(), pairs["PlayerB"].to_numpy()
    seasons = pairs["Season"].to_numpy()

    unique_seasons = sorted(set(seasons))
    k_season = min(PAIR_FOLDS, len(unique_seasons))
    season_fold_of = {s: i % k_season for i, s in enumerate(unique_seasons)}
    season_fold = np.array([season_fold_of[s] for s in seasons])
    pair_fold = np.array([_fold_of_key(_pair_key(a, b)) for a, b in zip(id_a, id_b)])
    player_fold_of = {p: _fold_of_key(p) for p in set(id_a) | set(id_b)}
    fold_a = np.array([player_fold_of[p] for p in id_a])
    fold_b = np.array([player_fold_of[p] for p in id_b])

    schemes = {
        "season": [(season_fold != f, season_fold == f) for f in range(k_season)]
        if k_season >= 2 else [],
        "pair": [(pair_fold != f, pair_fold == f) for f in range(PAIR_FOLDS)],
        "player": [((fold_a != f) & (fold_b != f), (fold_a == f) & (fold_b == f))
                   for f in range(PAIR_FOLDS)],
    }

    def stats(train):
        Zt, yt, wt = Z[train], y[train], w[train]
        wsum = wt.sum()
        zbar = (wt[:, None] * Zt).sum(axis=0) / wsum
        y_mean = (wt * yt).sum() / wsum
        Zc = Zt - zbar
        return Zc.T @ (Zc * wt[:, None]), Zc.T @ (wt * (yt - y_mean))

    scheme_stats = {
        name: [stats(tr) if tr.sum() >= 200 and te.sum() >= 50 else None
               for tr, te in folds]
        for name, folds in schemes.items()
    }

    def matrix_for(A, b, alpha, rank):
        coef = np.linalg.solve(A + alpha * np.eye(A.shape[0]), b)
        return _truncate_geometry(_geometry_matrix(coef / sd, count), rank)

    def centered_offset(M, train):
        return float((w[train] * _bilinear(za[train], zb[train], M)).sum() / w[train].sum())

    def evaluate(name, alpha, rank):
        oof = np.full(len(y), np.nan)
        for f, (train, test) in enumerate(schemes[name]):
            entry = scheme_stats[name][f]
            if entry is None:
                continue
            M = matrix_for(entry[0], entry[1], alpha, rank)
            oof[test] = _bilinear(za[test], zb[test], M) - centered_offset(M, train)
        tested = ~np.isnan(oof)
        sse = float((w[tested] * (y[tested] - oof[tested]) ** 2).sum())
        sst = float((w[tested] * y[tested] ** 2).sum())
        return sse, sst, oof

    # Choose settings on the strictest test that has enough data.
    chosen_scheme = "player"
    if sum(e is not None for e in scheme_stats["player"]) < 3:
        chosen_scheme = "pair"

    best = None
    for alpha in PAIR_MODEL_ALPHAS:
        sse, sst, _ = evaluate(chosen_scheme, alpha, None)
        if best is None or sse < best[0]:
            best = (sse, sst, alpha)
    _, sst_chosen, alpha = best

    rank_scores = {}
    for rank in PAIR_RANKS + [None]:
        rank_scores[rank], _, _ = evaluate(chosen_scheme, alpha, rank)
    best_sse = min(rank_scores.values())
    rank = None
    for candidate in PAIR_RANKS + [None]:
        # Prefer the simplest geometry that's within a hair of the best.
        if rank_scores[candidate] <= best_sse + 0.002 * sst_chosen:
            rank = candidate
            break

    validation = {"rank": rank, "alpha": alpha, "chosen_on": chosen_scheme}
    solid = pairs["Minutes"].to_numpy(float) >= 500
    for name in ("season", "pair", "player"):
        if not schemes[name]:
            validation[name] = float("nan")
            continue
        sse, sst, oof = evaluate(name, alpha, rank)
        validation[name] = 1 - sse / sst if sst > 0 else float("nan")
        validation[f"{name}_rows"] = int((~np.isnan(oof)).sum())
        if name == "player":
            ok = solid & ~np.isnan(oof)
            s_sst = float((w[ok] * y[ok] ** 2).sum())
            validation["player_solid"] = (
                1 - float((w[ok] * (y[ok] - oof[ok]) ** 2).sum()) / s_sst if s_sst > 0 else float("nan")
            )

    # Final model on everything, plus one model per pair-fold. A pair in a
    # lineup is later scored by the model that never saw that pair's results.
    everything = np.ones(len(y), dtype=bool)
    A_all, b_all = stats(everything)
    M_raw = matrix_for(A_all, b_all, alpha, None)
    M_full = _truncate_geometry(M_raw, rank)
    full = {"M": M_full, "b": -centered_offset(M_full, everything)}

    pair_models = []
    for f, (train, _) in enumerate(schemes["pair"]):
        entry = scheme_stats["pair"][f]
        if entry is None:
            pair_models.append(full)
            continue
        M_f = matrix_for(entry[0], entry[1], alpha, rank)
        pair_models.append({"M": M_f, "b": -centered_offset(M_f, train)})

    # Do the patterns hold up in two independent halves of the seasons?
    order = {s: i for i, s in enumerate(unique_seasons)}
    first_half = np.array([order[s] % 2 == 0 for s in seasons])
    halves = None
    if first_half.sum() >= 200 and (~first_half).sum() >= 200:
        h1, h2 = stats(first_half), stats(~first_half)
        halves = (
            matrix_for(h1[0], h1[1], alpha, None),
            matrix_for(h2[0], h2[1], alpha, None),
        )

    return {
        "alpha": alpha,
        "rank": rank,
        "n": len(y),
        "n_seasons": len(unique_seasons),
        "n_players": len(player_fold_of),
        "validation": validation,
        "full": full,
        "pair_models": pair_models,
        "M_raw": M_raw,
        "halves": halves,
    }


def _pair_predict(model, za, zb, fold=None):
    """Expected pair-specific deviation (net rating points per 100).

    With a fold, uses the model trained without that fold's pairs.
    """
    entry = model["full"] if fold is None else model["pair_models"][fold]
    return _bilinear(za, zb, entry["M"]) + entry["b"]


@st.cache_data(show_spinner="Learning pair chemistry from the pair data...")
def fit_pair_synergy(_pairs, _zfeat, _row_of, base_cols, target_label, cache_key):
    """Learn which skill shapes make a pair beat (or miss) what its two
    players' individual quality predicts."""
    rating, base, sign = PAIR_TARGETS[target_label]
    out = {"ok": False, "target": target_label}

    types = list(_pairs["SeasonType"].unique())
    season_type = "Regular Season" if "Regular Season" in types else types[0]
    out["season_type"] = season_type

    pool = _pairs[
        (_pairs["SeasonType"] == season_type)
        & (_pairs["Minutes"] >= PAIR_MODEL_MIN_MINUTES)
        & _pairs[rating].notna()
        & _pairs[base].notna()
    ][["Season", "Team", "PlayerA", "PlayerB", "Minutes", rating, base]].copy()
    out["n_pairs"] = len(pool)

    if len(pool) < 500:
        out["reason"] = (
            f"Only {len(pool)} pair-seasons have at least "
            f"{PAIR_MODEL_MIN_MINUTES} shared minutes. That's too few to learn from."
        )
        return out

    pool["y"] = sign * (pool[rating] - pool[base])
    pool["e"] = _pair_residuals(pool)

    # Real pair history is kept for display only. Scoring never uses it
    # unless the user asks.
    out["evidence"] = pool[["Season", "PlayerA", "PlayerB", "Minutes", "e"]].copy()

    pool["rowA"] = (pool["PlayerA"] + "|" + pool["Season"]).map(_row_of)
    pool["rowB"] = (pool["PlayerB"] + "|" + pool["Season"]).map(_row_of)
    matched = pool["rowA"].notna() & pool["rowB"].notna()
    out["match_rate"] = float(matched.mean())

    if out["match_rate"] < PAIR_MIN_SKILL_MATCH or matched.sum() < 500:
        out["reason"] = (
            f"Only {out['match_rate']:.0%} of pair rows could be matched to "
            "player stats. The player IDs or season labels probably differ "
            "between the two files."
        )
        return out

    pool = pool[matched]
    za = _zfeat.loc[pool["rowA"].astype(int).to_numpy(), list(base_cols)].to_numpy(float)
    zb = _zfeat.loc[pool["rowB"].astype(int).to_numpy(), list(base_cols)].to_numpy(float)

    out.update(_fit_pair_geometry(pool, za, zb))
    out["feature_names"] = _pair_feature_names(list(base_cols))
    out["base_cols"] = list(base_cols)
    out["axes"] = _geometry_axes(out["full"]["M"], list(base_cols))
    out["ok"] = True
    return out


@st.cache_data(show_spinner=False)
def pair_layer_backtest(_model, _zfeat, _cores, _builder, _ids, base_cols, target_label, cache_key):
    """Does adding pair chemistry help predict results?

    For each historical team (or real lineup), sum the expected chemistry of
    its five main players' 10 pairs, then see how well that explains what the
    skill-interaction model got wrong. Every pair is scored by a model that never
    saw that pair's own results, in any season, so a duo can't earn credit for
    having already proved itself. Rows are weighted by minutes when the data
    has weights.
    """
    data = _builder["data"]
    baseline_model = _builder.get("interact", _builder["additive"])
    oof_add = np.asarray(baseline_model["oof"], float)
    actual = data["actual"].to_numpy(float)
    weights = (
        data["weight"].to_numpy(float) if "weight" in data.columns
        else np.ones(len(data))
    )
    rows_i, rows_j = np.triu_indices(5, k=1)

    out = {"n": 0, "helps": False, "lam": 0.0, "held_out": "each pair's own history"}
    core_rows = [_cores.get(key) for key in zip(data["Season"], data["Tm"])]
    valid = np.array([r is not None and len(r) == 5 for r in core_rows])
    if valid.sum() < 100:
        return out

    valid_index = np.where(valid)[0]
    rows = np.array([core_rows[i] for i in valid_index])
    positions = _zfeat.index.get_indexer(rows.ravel()).reshape(rows.shape)
    z = _zfeat[list(base_cols)].to_numpy(float)[positions]   # rows x 5 x skills
    ids = np.asarray(_ids)[positions]                        # rows x 5 player ids

    total = np.zeros(len(valid_index))
    for i, j in zip(rows_i, rows_j):
        folds = np.array([
            _fold_of_key(_pair_key(a, b)) for a, b in zip(ids[:, i], ids[:, j])
        ])
        for fold in np.unique(folds):
            chosen = folds == fold
            total[chosen] += _pair_predict(
                _model, z[chosen, i, :], z[chosen, j, :], int(fold)
            )
    summed = np.full(len(data), np.nan)
    summed[valid_index] = total

    ok = ~np.isnan(summed)
    out["n"] = int(ok.sum())
    if ok.sum() < 100 or np.nanstd(summed) == 0:
        return out

    s, y, base = summed[ok], actual[ok], oof_add[ok]
    w = weights[ok] / weights[ok].mean()
    miss = y - base

    denom = float((w * s ** 2).sum())
    lam_raw = float((w * s * miss).sum() / denom)
    resid = miss - lam_raw * s
    se = float(np.sqrt((w * resid ** 2).sum() / max(len(s) - 1, 1) / denom))

    # Cross-fit the strength so the score isn't flattering itself.
    seasons = data["Season"].to_numpy()[ok].astype(str)
    unique = sorted(set(seasons))
    k = min(5, len(unique))
    fold_of = {x_: i % k for i, x_ in enumerate(unique)}
    folds = np.array([fold_of[x_] for x_ in seasons])
    adjustment = np.zeros(len(s))
    for f in range(k):
        test = folds == f
        train = ~test
        d_train = float((w[train] * s[train] ** 2).sum())
        lam_f = (
            float(np.clip((w[train] * s[train] * miss[train]).sum() / d_train, 0, 1.5))
            if d_train > 0 else 0.0
        )
        adjustment[test] = lam_f * s[test]

    y_bar = float((w * y).sum() / w.sum())
    total_ss = float((w * (y - y_bar) ** 2).sum())
    r2_without = 1 - float((w * (y - base) ** 2).sum()) / total_ss
    r2_with = 1 - float((w * (y - base - adjustment) ** 2).sum()) / total_ss

    lam = float(np.clip(lam_raw, 0, 1.5))
    out.update({
        "lam": lam,
        "lam_raw": lam_raw,
        "se": se,
        "r2_without": r2_without,
        "r2_with": r2_with,
        "rmse_without": float(np.sqrt((w * (y - base) ** 2).sum() / w.sum())),
        "rmse_with": float(np.sqrt((w * (y - base - adjustment) ** 2).sum() / w.sum())),
        "corr": weighted_corr(pd.Series(s), pd.Series(miss), pd.Series(w)),
        "helps": bool((r2_with - r2_without) > 0.003 and lam_raw > 0.1),
    })
    return out


def run_pair_layer(pairs, zfeat, data, pools, results, target_label, base_cols):
    """Fit the pair model and backtest it against the Builder's results."""
    key = _pair_cache_key()
    model = fit_pair_synergy(
        pairs, zfeat, _skill_row_lookup(data), tuple(base_cols), target_label, key
    )
    if not model.get("ok"):
        return model
    ids = data["player_id"].astype(str).reindex(zfeat.index).to_numpy()
    backtest = pair_layer_backtest(
        model, zfeat, pools.get("cores", {}), results, ids,
        tuple(base_cols), target_label, key,
    )
    return {**model, "backtest": backtest}


def lineup_pair_synergy(data, zfeat, model, rows, base_cols, use_history=False):
    """Skill-based chemistry for the 10 pairs in a lineup.

    Each pair is scored by the model that never saw that pair's own results.
    Real history is shown for context. It only changes the number used when
    use_history is on, because letting a duo's past results raise its score
    is exactly the hindsight this layer is meant to avoid.
    """
    ids = [str(data.loc[r, "player_id"]) for r in rows]
    seasons = [str(data.loc[r, "Season"]) for r in rows]
    labels = [f"{data.loc[r, 'player_name']} {data.loc[r, 'Season']}" for r in rows]

    z = zfeat.loc[rows, list(base_cols)].to_numpy(float)
    ii, jj = np.triu_indices(5, k=1)
    expected = np.array([
        float(_pair_predict(
            model, z[a:a + 1], z[b:b + 1], _fold_of_key(_pair_key(ids[a], ids[b]))
        )[0])
        for a, b in zip(ii, jj)
    ])

    evidence = model["evidence"]
    relevant = evidence[
        evidence["PlayerA"].isin(ids) & evidence["PlayerB"].isin(ids)
    ]

    records = []
    for n, (a, b) in enumerate(zip(ii, jj)):
        low_id, high_id = sorted([ids[a], ids[b]])
        history = relevant[
            (relevant["PlayerA"] == low_id) & (relevant["PlayerB"] == high_id)
        ]

        kind, minutes, observed = "Never seen together", 0.0, np.nan
        if len(history):
            same = (
                history[history["Season"] == seasons[a]]
                if seasons[a] == seasons[b] else history.iloc[0:0]
            )
            used, kind = (same, "Same season") if len(same) else (history, "Other seasons")
            minutes = float(used["Minutes"].sum())
            if minutes > 0:
                observed = float((used["e"] * used["Minutes"]).sum() / minutes)

        value = float(expected[n])
        if use_history and pd.notna(observed):
            weight = minutes / (minutes + PAIR_EVIDENCE_MINUTES)
            value = weight * observed + (1 - weight) * value
        records.append({
            "Pair": f"{labels[a]} + {labels[b]}",
            "Skills predict": float(expected[n]),
            "Seen together": kind,
            "Shared minutes": minutes,
            "Real history": observed,
            "Used": float(value),
        })
    return pd.DataFrame(records)


def _pair_skill_combos(pairs, data):
    """Pair Lab tab: the skill geometry behind pair chemistry."""
    zfeat, _, _ = builder_tables(data)
    if zfeat.empty or "Season" not in data.columns:
        st.info("This needs the player stats (minutes, possessions and shot data).")
        return

    target_label = st.selectbox(
        "What to explain", list(PAIR_TARGETS.keys()), key="pair_combo_target"
    )
    base_cols = tuple(zfeat.columns)
    model = fit_pair_synergy(
        pairs, zfeat, _skill_row_lookup(data), base_cols, target_label,
        _pair_cache_key(),
    )

    if not model.get("ok"):
        st.warning(model.get("reason", "Couldn't fit the pair model."))
        return

    validation = model["validation"]

    def percent(value):
        return "—" if pd.isna(value) else f"{value:.1%}"

    st.markdown("#### Do skills alone predict chemistry?")
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Same players, new seasons", percent(validation["season"]),
        help="The model has seen these players and pairs in other seasons. "
             "This is the easiest test and the least convincing.",
    )
    c2.metric(
        "A pair it never saw", percent(validation["pair"]),
        help="The model never saw this pair's results in any season, though "
             "it saw each player with other teammates.",
    )
    c3.metric(
        "Players it never saw", percent(validation["player"]),
        help="Neither player appeared in training at all. This is the real "
             "test that the model learned skill geometry, not people.",
    )
    st.caption(
        f"Learned from {model['n']:,} pair-seasons and {model['n_players']:,} "
        f"players, using {'all axes' if model['rank'] is None else str(model['rank']) + ' skill axes'}. "
        "If the three scores are close, the model is learning geometry. If "
        "the first is much higher than the last, part of it is memorizing "
        "specific players."
    )

    if pd.notna(validation["player"]) and validation["player"] <= 0.001:
        st.info(
            "Skills alone don't predict chemistry for players the model "
            "hasn't seen. At this level of detail, pair results look mostly "
            "like the sum of the two players, so the axes and patterns below "
            "shouldn't be trusted."
        )

    st.markdown("#### The axes of skill fit")
    axes = model.get("axes", [])[:6]
    if axes:
        rows = []
        for number, axis in enumerate(axes, start=1):
            high = ", ".join(axis["high"]) or "—"
            low = ", ".join(axis["low"]) or "—"
            rows.append({
                "Axis": f"Axis {number}",
                "Rewards": "Opposites (complements)" if axis["kind"] == "complement"
                           else "Alike (both on the same side)",
                "Strength": axis["strength"],
                "High end": high,
                "Low end": low,
            })
        st.dataframe(
            pd.DataFrame(rows).style.format({"Strength": "{:.3f}"}),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Each axis is a blend of skills. Along a 'complements' axis, a "
            "pair does best when one player is at the high end and the other "
            "at the low end, and worst when both sit on the same side "
            "(redundancy). Along an 'alike' axis it's the reverse."
        )

    st.markdown("#### Individual skill pairings")
    weights = _weights_from_matrix(model["M_raw"])
    table = pd.DataFrame({"Pattern": model["feature_names"], "Weight": weights})
    if model["halves"] is not None:
        half1, half2 = (_weights_from_matrix(m) for m in model["halves"])
        table["First half"], table["Second half"] = half1, half2
        floor = 0.02
        table["Holds in both halves"] = (
            (np.sign(half1) == np.sign(half2))
            & (np.abs(half1) > floor) & (np.abs(half2) > floor)
        )
    else:
        table["Holds in both halves"] = False

    only_stable = st.checkbox(
        "Only patterns that hold in both halves of the seasons",
        value=True, key="pair_combo_stable",
    )
    shown = table[table["Holds in both halves"]] if only_stable else table
    shown = shown.reindex(shown["Weight"].abs().sort_values(ascending=False).index).head(25)

    if shown.empty:
        st.info("No single pairing was stable across both halves of the seasons.")
        return

    st.dataframe(
        shown.assign(Direction=np.where(shown["Weight"] > 0, "Helps", "Hurts"))
        [["Pattern", "Direction", "Weight", "Holds in both halves"]]
        .style.format({"Weight": "{:+.3f}"}),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Weight is the change in a pair's net rating (per 100 possessions) "
        "for a one-standard-deviation move in that pairing. 'One has X, the "
        "other has Y' means either player may hold either skill. These are "
        "patterns in past data, not guarantees."
    )


# --------------------------------------------------
# BUILDER TRANSPARENCY HELPERS
# --------------------------------------------------

def top_five_minute_share(data):
    """Typical share of a team's player-minutes taken by its five busiest players.

    The Builder learns from team results, and the bench plays the rest of the
    minutes. So a team built around five players is diluted by its bench in a
    way a five-man unit (all five on the floor together) is not.
    """
    minutes = _minutes(data)
    if minutes is None or "Tm" not in data.columns or "Season" not in data.columns:
        return None

    d = pd.DataFrame({
        "Season": data["Season"].astype(str),
        "Tm": data["Tm"].astype(str),
        "m": minutes,
    }).dropna()
    d = d[~d["Tm"].str.upper().str.match(r"^(TOT|\dTM)$") & (d["m"] > 0)]
    if d.empty:
        return None

    groups = d.groupby(["Season", "Tm"])
    d["rank"] = groups["m"].rank(ascending=False, method="first")
    top = d[d["rank"] <= 5].groupby(["Season", "Tm"])["m"].sum()
    total = groups["m"].sum()
    count = groups["m"].size()

    share = (top / total)[count >= 8].dropna()
    if len(share) < 10:
        return None
    return float(np.clip(share.median(), 0.45, 0.95))


def calibration_summary(actual, predicted, weights=None):
    """Does the model's out-of-sample prediction run too cautious or too bold?"""
    actual = np.asarray(actual, float)
    predicted = np.asarray(predicted, float)
    w = np.ones(len(actual)) if weights is None else np.asarray(weights, float)
    ok = ~(np.isnan(actual) | np.isnan(predicted) | np.isnan(w))
    actual, predicted, w = actual[ok], predicted[ok], w[ok]

    out = {"slope": float("nan"), "scale": 1.0, "table": pd.DataFrame()}
    if len(actual) < 50:
        return out
    w = w / w.mean()
    mp = (w * predicted).sum() / w.sum()
    ma = (w * actual).sum() / w.sum()
    variance = float((w * (predicted - mp) ** 2).sum() / w.sum())
    if variance == 0:
        return out

    slope = float((w * (predicted - mp) * (actual - ma)).sum() / w.sum() / variance)
    out["slope"] = slope
    out["scale"] = float(np.clip(slope, 0.8, 1.6))

    bins = pd.qcut(predicted, 5, duplicates="drop")
    table = pd.DataFrame({"bin": bins, "p": predicted, "a": actual, "w": w})
    table["pw"], table["aw"] = table["p"] * table["w"], table["a"] * table["w"]
    grouped = table.groupby("bin", observed=True)
    summary = pd.DataFrame({
        "Predicted": grouped["pw"].sum() / grouped["w"].sum(),
        "Actual": grouped["aw"].sum() / grouped["w"].sum(),
        "Rows": grouped["p"].size(),
    }).reset_index(drop=True)
    summary.index = [
        f"Group {i + 1}" + (" (lowest)" if i == 0 else " (highest)" if i == len(summary) - 1 else "")
        for i in range(len(summary))
    ]
    out["table"] = summary
    return out


# --------------------------------------------------
# --------------------------------------------------
# LINEUP DATA (real five-man lineups)
# --------------------------------------------------

LINEUP_FILE_NAMES = [
    "5man_lineups_2000_2009.csv.gz",
    "5man_lineups_2009_2017.csv.gz",
    "5man_lineups_2018_2026.csv.gz",
]
LINEUP_FILES = [Path(__file__).parent / name for name in LINEUP_FILE_NAMES]

LINEUP_RATES = ["OffRtg", "DefRtg", "NetRtg"]
LINEUP_PCTS = ["Fg3Pct", "Fg2Pct", "OppFg3Pct", "OppFg2Pct"]

# builder target -> (centered lineup column, sign so + is good)
LINEUP_TARGET_COLUMNS = {
    "Net rating": ("NetC", 1),
    "Offense (points scored per 100)": ("OffC", 1),
    "Defense (points prevented per 100)": ("DefC", -1),
}

LINEUP_MODEL_MIN_MINUTES = 40     # lineups below this are too noisy to train on
LINEUP_WEIGHT_CAP = 800           # no single lineup counts for more than this
LINEUP_SHRINK_MINUTES = 800       # Lineup Lab's historical display shrinkage
LINEUP_TARGET_PRIOR_MINUTES = 200 # Team Builder target reliability prior
LINEUP_CAP_MIN_MINUTES = 200      # lineups used to set "most ever" resource limits

LINEUP_SAMPLE_LABELS = [
    "⚪ No minutes",
    "🔴 Very low (<25 min)",
    "🟠 Low (25-99 min)",
    "🟡 Moderate (100-299 min)",
    "🟢 Solid (300+ min)",
]


def lineup_sample_label(minutes):
    scalar = np.isscalar(minutes)
    m = pd.to_numeric(pd.Series([minutes] if scalar else minutes), errors="coerce").fillna(0)
    labels = np.select(
        [m <= 0, m < 25, m < 100, m < 300],
        LINEUP_SAMPLE_LABELS[:4],
        default=LINEUP_SAMPLE_LABELS[4],
    )
    return labels[0] if scalar else pd.Series(labels, index=m.index)


def _lineup_cache_key():
    stamps = []
    for path in list(LINEUP_FILES) + [DATA_FILE, NAME_FILE, PAIR_FILE]:
        try:
            stamps.append(path.stat().st_mtime)
        except Exception:
            stamps.append(0.0)
    return tuple(stamps)


# Other names the same columns often go by (matched ignoring case and spaces).
_LINEUP_ALIASES = {
    "Season": ["season", "seasonyear", "season_year"],
    "SeasonType": ["seasontype", "season_type"],
    "Team": ["team", "teamabbreviation", "team_abbreviation", "teamabbr", "tm", "teamname"],
    "TeamId": ["teamid", "team_id"],
    "Minutes": ["minutes", "min", "mins", "minutesplayed", "minutes_played"],
    "OffRtg": ["offrtg", "off_rtg", "offrating", "off_rating", "ortg", "offensiverating", "onoffrtg"],
    "DefRtg": ["defrtg", "def_rtg", "defrating", "def_rating", "drtg", "defensiverating", "ondefrtg"],
    "NetRtg": ["netrtg", "net_rtg", "netrating", "net_rating", "nrtg"],
    "Fg3Pct": ["fg3pct", "fg3_pct", "fg3%", "3p%", "threepct"],
    "Fg2Pct": ["fg2pct", "fg2_pct", "fg2%", "2p%"],
    "OppFg3Pct": ["oppfg3pct", "opp_fg3pct", "oppfg3%", "opp3p%"],
    "OppFg2Pct": ["oppfg2pct", "opp_fg2pct", "oppfg2%", "opp2p%"],
}

_LINEUP_ID_HINTS = {
    "lineupid", "lineupids", "lineup", "groupid", "playerids",
    "players", "rowid", "on",
}


def _apply_lineup_aliases(d):
    lowered = {}
    for column in d.columns:
        lowered.setdefault(str(column).lower().replace(" ", ""), column)
    renames = {}
    for canonical, options in _LINEUP_ALIASES.items():
        if canonical in d.columns:
            continue
        for option in options:
            original = lowered.get(option)
            if original is not None and original not in renames and original not in _LINEUP_ALIASES:
                renames[original] = canonical
                break
    return d.rename(columns=renames) if renames else d


def _extract_lineup_ids(d):
    """Find the five player IDs wherever the file keeps them.

    Handles five separate columns, or one column that holds all five (for
    example 'On:123,456,...' or '123-456-...'). Returns (ids, description);
    ids has one row per row of d, with blanks where there weren't five.
    """
    explicit = [f"Player{i}Id" for i in range(1, 6)]
    if all(c in d.columns for c in explicit):
        return d[explicit].apply(_clean_id), "Player1Id..Player5Id"

    # Five separate columns under other names.
    lowered = {str(c).lower().replace("_", "").replace(" ", ""): c for c in d.columns}
    for pattern in ("player{i}id", "player{i}", "p{i}id", "p{i}", "playerid{i}"):
        wanted = [pattern.format(i=i) for i in range(1, 6)]
        if all(w in lowered for w in wanted):
            columns = [lowered[w] for w in wanted]
            sample = d[columns].head(300).astype(str)
            if sample.apply(lambda s: s.str.fullmatch(r"\d+(\.0)?")).all().all():
                return d[columns].apply(_clean_id), ", ".join(columns)

    # One column holding all five.
    best = None
    for column in d.columns:
        if column == "_file":
            continue
        values = d[column].dropna().astype(str).head(2000)
        if values.empty:
            continue
        tokens = values.str.findall(r"\d+")
        five = (
            tokens.map(len).eq(5)
            & values.str.contains(r"\D")
            & tokens.map(lambda t: all(len(x) >= 2 for x in t))
        )
        share = float(five.mean())
        if share < 0.3:
            continue
        hinted = str(column).lower().replace("_", "").replace(" ", "") in _LINEUP_ID_HINTS
        # An ID column is mostly digits; a column of names is mostly letters.
        letters = float(
            (values.str.count(r"[A-Za-z]") / values.str.len().clip(lower=1)).mean()
        )
        score = (round(share, 2), hinted, -round(letters, 2))
        if best is None or score > best[0]:
            best = (score, column)

    if best is None:
        return None, None

    column = best[1]
    tokens = d[column].astype(str).str.findall(r"\d+")
    keep = tokens.map(len) == 5
    ids = pd.DataFrame(tokens[keep].tolist(), index=d.index[keep]).reindex(d.index)
    return ids.apply(_clean_id), f"the '{column}' column"


@st.cache_resource(show_spinner="Loading five-man lineup data...")
def load_lineups():
    """Combine and clean the lineup files. Returns (data, report).

    Nothing here assumes the files are tidy or non-overlapping: schema, units
    and scales are detected, and everything unusual goes in the report.
    """
    report = {"notes": [], "problems": [], "files": []}

    frames = []
    for path in LINEUP_FILES:
        if not path.exists():
            report["files"].append((path.name, None))
            continue
        # Read the header first, then load only columns consumed by Team
        # Builder and Lineup Lab. These exports can contain hundreds of
        # unused tracking columns, which are expensive to inflate in memory.
        header = pd.read_csv(path, compression="gzip", nrows=0).columns
        canonical_needed = {
            "Season", "SeasonType", "Team", "TeamId", "Minutes",
            *LINEUP_RATES, *LINEUP_PCTS,
            "Points", "OpponentPoints", "OffPoss", "DefPoss",
        }
        accepted = set()
        for canonical in canonical_needed:
            accepted.add(canonical.lower().replace(" ", ""))
            for alias in _LINEUP_ALIASES.get(canonical, []):
                accepted.add(alias.lower().replace(" ", ""))
        id_columns = []
        for column in header:
            norm = str(column).lower().replace(" ", "").replace("_", "")
            if (re.fullmatch(r"(?:player[1-5]id|player[1-5]|p[1-5]id|p[1-5]|playerid[1-5])", norm)
                    or norm in {hint.replace("_", "") for hint in _LINEUP_ID_HINTS}):
                id_columns.append(column)
        selected = [
            c for c in header
            if str(c).lower().replace(" ", "") in accepted or c in id_columns
        ]
        # Unknown single-column lineup ID formats still need to be detected;
        # keep the old robust read as a fallback for those uncommon schemas.
        usecols = selected if id_columns else None
        part = pd.read_csv(
            path, compression="gzip", low_memory=False,
            usecols=usecols,
        )
        part.columns = [str(c).strip() for c in part.columns]
        part["_file"] = path.name
        frames.append(part)
        report["files"].append((path.name, len(part)))

    if not frames:
        report["problems"].append("None of the lineup files were found.")
        return None, report

    d = pd.concat(frames, ignore_index=True, copy=False)
    frames.clear()
    del part
    report["rows_raw"] = len(d)

    d = _apply_lineup_aliases(d)
    report["columns"] = [c for c in d.columns if c != "_file"]
    report["head"] = d.head(3).drop(columns=["_file"])

    # ---- the five players ----
    ids, how = _extract_lineup_ids(d)
    if ids is None:
        report["problems"].append(
            "Couldn't find the five player IDs in the lineup files. The "
            "columns are: " + ", ".join(report["columns"]) + ". Open "
            "'What's in the files' below and send it to Claude."
        )
        return None, report
    report["notes"].append(f"Players were read from {how}.")

    missing = [c for c in ("Season", "Minutes") if c not in d.columns]
    if "Team" not in d.columns and "TeamId" not in d.columns:
        missing.append("Team or TeamId")
    if missing:
        report["problems"].append(
            "The lineup files are missing: " + ", ".join(missing) + ". "
            "The columns are: " + ", ".join(report["columns"]) + "."
        )
        return None, report

    # Keep only columns used by the builder and Lineup Lab. The raw column
    # names and sample rows are already saved in the diagnostic report above.
    needed_columns = {"Season", "SeasonType", "Team", "TeamId", "Minutes", "_file"}
    needed_columns.update(LINEUP_RATES)
    needed_columns.update(LINEUP_PCTS)
    needed_columns.update(["Points", "OpponentPoints", "OffPoss", "DefPoss"])
    d = d[[c for c in d.columns if c in needed_columns]]

    # ---- identity columns ----
    d["Season"] = d["Season"].astype("string").str.strip()
    d["SeasonType"] = (
        d["SeasonType"].astype("string").str.strip()
        if "SeasonType" in d.columns else "Regular Season"
    )
    if "TeamId" in d.columns:
        d["TeamId"] = _clean_id(d["TeamId"])
    if "Team" not in d.columns:
        d["Team"] = d["TeamId"]
    if "TeamId" not in d.columns:
        d["TeamId"] = d["Team"].astype("string")
    d["Team"] = d["Team"].astype("string").str.strip()

    rating_inputs = ["Points", "OpponentPoints", "OffPoss", "DefPoss"]
    for column in ["Minutes"] + LINEUP_RATES + LINEUP_PCTS + rating_inputs:
        if column in d.columns:
            d[column] = pd.to_numeric(d[column], errors="coerce", downcast="float")

    if "OffRtg" not in d.columns or d["OffRtg"].notna().sum() == 0:
        d["OffRtg"] = np.nan
    if "Points" in d.columns and "OffPoss" in d.columns:
        derived = 100 * d["Points"] / d["OffPoss"].where(d["OffPoss"] > 0)
        d["OffRtg"] = d["OffRtg"].fillna(derived)
        report["notes"].append("OffRtg filled from Points per 100 offensive possessions where missing.")
    elif d["OffRtg"].isna().all():
        report["notes"].append("OffRtg could not be derived; Points or OffPoss is missing.")

    if "DefRtg" not in d.columns or d["DefRtg"].notna().sum() == 0:
        d["DefRtg"] = np.nan
    if "OpponentPoints" in d.columns and "DefPoss" in d.columns:
        derived = 100 * d["OpponentPoints"] / d["DefPoss"].where(d["DefPoss"] > 0)
        d["DefRtg"] = d["DefRtg"].fillna(derived)
        report["notes"].append("DefRtg filled from OpponentPoints per 100 defensive possessions where missing.")
    elif d["DefRtg"].isna().all():
        report["notes"].append("DefRtg could not be derived; OpponentPoints or DefPoss is missing.")

    if "NetRtg" not in d.columns or d["NetRtg"].notna().sum() == 0:
        d["NetRtg"] = np.nan
    derived_net = d["OffRtg"] - d["DefRtg"]
    if d["NetRtg"].isna().any() and d[["OffRtg", "DefRtg"]].notna().all(axis=1).any():
        d["NetRtg"] = d["NetRtg"].fillna(derived_net)
        report["notes"].append("NetRtg filled as OffRtg minus DefRtg where missing.")

    for column in LINEUP_PCTS:
        if column not in d.columns:
            d[column] = np.nan
            report["notes"].append(f"Column {column} not in the files; left blank.")

    d = d.drop(columns=rating_inputs, errors="ignore")

    # ---- keep rows with five distinct players ----
    ok = ids.notna().all(axis=1) & d["Season"].notna() & d["Team"].notna()
    report["unusable_rows"] = int((~ok).sum())
    d, ids = d[ok].copy(), ids[ok]
    sorted_ids = np.sort(ids.astype(str).to_numpy(), axis=1)
    distinct = (sorted_ids[:, 1:] != sorted_ids[:, :-1]).all(axis=1)
    report["not_five_distinct"] = int((~distinct).sum())
    d, sorted_ids = d[distinct].copy(), sorted_ids[distinct]

    for i in range(5):
        d[f"Player{i + 1}Id"] = sorted_ids[:, i]
    d["LineupKey"] = ["-".join(row) for row in sorted_ids]

    # ---- minutes ----
    positive = d.loc[d["Minutes"] > 0, "Minutes"]
    if len(positive) and positive.quantile(0.99) > 6000:
        d["Minutes"] = d["Minutes"] / 60
        report["notes"].append("Minutes looked like seconds, so they were divided by 60.")
    elif len(positive):
        report["notes"].append(
            f"Minutes treated as minutes (median {positive.median():.0f}, "
            f"max {positive.max():.0f})."
        )
    empty = d["Minutes"].fillna(0) <= 0
    report["zero_minute_rows"] = int(empty.sum())
    d = d[~empty].copy()

    # ---- ratings and percentages ----
    off_def = d["OffRtg"].notna() & d["DefRtg"].notna()
    if d["NetRtg"].notna().sum() == 0 and off_def.any():
        d["NetRtg"] = d["OffRtg"] - d["DefRtg"]
        report["notes"].append("NetRtg was empty; computed as OffRtg - DefRtg.")
    both = off_def & d["NetRtg"].notna()
    if both.any():
        report["net_mismatch_share"] = float(
            ((d.loc[both, "NetRtg"] - (d.loc[both, "OffRtg"] - d.loc[both, "DefRtg"])).abs() > 0.6).mean()
        )
    for column in LINEUP_PCTS:
        pos = d.loc[d[column] > 0, column]
        if len(pos) and pos.quantile(0.99) <= 1.5:
            d[column] = d[column] * 100
            report["notes"].append(f"{column} was a fraction (0-1); converted to percent.")
        d.loc[d[column] > 100, column] = np.nan
        suspect = (d[column] == 0) & (d["Minutes"] < 25)
        d.loc[suspect, column] = np.nan

    for column in ["Season", "Team", "SeasonType", "TeamId"]:
        d[column] = d[column].astype(str)

    # ---- the files overlap at the boundaries: keep one copy ----
    files_per_season = d.groupby("Season")["_file"].nunique()
    report["overlap_seasons"] = sorted(files_per_season[files_per_season > 1].index.tolist())
    before = len(d)
    d = d.sort_values("Minutes", ascending=False).drop_duplicates(
        ["Season", "SeasonType", "TeamId", "LineupKey"]
    )
    report["duplicates_removed"] = before - len(d)

    # ---- names ----
    lookup = _read_name_lookup()
    name_columns = []
    known = pd.Series(True, index=d.index)
    for i in range(1, 6):
        mapped = d[f"Player{i}Id"].map(lookup)
        known &= mapped.notna()
        d[f"Name{i}"] = mapped.fillna("Player " + d[f"Player{i}Id"])
        name_columns.append(f"Name{i}")
    d["Names"] = d[name_columns].agg(", ".join, axis=1)
    report["name_coverage"] = float(known.mean()) if len(d) else 0.0

    # ---- league and team baselines (minutes-weighted) ----
    def weighted_mean(frame, by, column):
        ok = frame[column].notna()
        part = frame.loc[ok]
        w = part["Minutes"]
        total = (part[column] * w).groupby([part[b] for b in by]).sum()
        return (total / w.groupby([part[b] for b in by]).sum()).rename("_m")

    for rating, label in (("NetRtg", "Net"), ("OffRtg", "Off"), ("DefRtg", "Def")):
        league = weighted_mean(d, ["Season", "SeasonType"], rating).reset_index()
        league = league.rename(columns={"_m": f"League{label}"})
        d = d.merge(league, on=["Season", "SeasonType"], how="left")
        d[f"{label}C"] = d[rating] - d[f"League{label}"]   # relative to league average

        team = weighted_mean(d, ["Season", "SeasonType", "Team"], rating).reset_index()
        team = team.rename(columns={"_m": f"Base{label}"})
        d = d.merge(team, on=["Season", "SeasonType", "Team"], how="left")

    d["NetVsTeam"] = d["NetRtg"] - d["BaseNet"]
    d["Shrunk"] = d["NetVsTeam"] * d["Minutes"] / (d["Minutes"] + LINEUP_SHRINK_MINUTES)
    d["Sample"] = lineup_sample_label(d["Minutes"])

    d = d.drop(columns=["_file"]).reset_index(drop=True)
    report["rows_clean"] = len(d)
    return d, report


def _lineup_avatars(row):
    """Five small headshots for one lineup row."""
    columns = st.columns(5)
    for i, column in enumerate(columns, start=1):
        with column:
            st.markdown(
                mini_player_html(row[f"Player{i}Id"], row[f"Name{i}"], ""),
                unsafe_allow_html=True,
            )


def _show_lineup_metrics(row):
    minutes = float(row["Minutes"])
    st.markdown(f"**Evidence:** {row['Sample']}")
    if minutes < 100:
        st.warning(
            f"Only {minutes:.0f} minutes together. Five-man ratings from "
            "samples this small are mostly noise."
        )

    def number(value, fmt):
        return "—" if pd.isna(value) else fmt.format(value)

    def delta(value, base):
        if pd.isna(value) or pd.isna(base):
            return None
        return f"{value - base:+.1f} vs team"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Minutes together", f"{minutes:,.0f}")
    c2.metric("Net rating", number(row["NetRtg"], "{:+.1f}"), delta(row["NetRtg"], row["BaseNet"]))
    c3.metric("Offensive rating", number(row["OffRtg"], "{:.1f}"), delta(row["OffRtg"], row["BaseOff"]))
    c4.metric("Defensive rating", number(row["DefRtg"], "{:.1f}"),
              delta(row["DefRtg"], row["BaseDef"]), delta_color="inverse")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("3P%", number(row["Fg3Pct"], "{:.1f}%"))
    s2.metric("2P%", number(row["Fg2Pct"], "{:.1f}%"))
    s3.metric("Opponent 3P%", number(row["OppFg3Pct"], "{:.1f}%"))
    s4.metric("Opponent 2P%", number(row["OppFg2Pct"], "{:.1f}%"))

    if pd.notna(row["NetVsTeam"]):
        st.caption(
            f"Net rating vs. the team's baseline: {row['NetVsTeam']:+.1f} raw, "
            f"{row['Shrunk']:+.1f} after adjusting for sample size. The "
            "baseline is the team's minutes-weighted average across the "
            "lineups in the data."
        )


_LINEUP_TABLE_COLUMNS = ["Names", "Season", "Team", "Minutes", "Sample", "NetRtg",
                         "NetVsTeam", "Shrunk", "OffRtg", "DefRtg", "Fg3Pct",
                         "Fg2Pct", "OppFg3Pct", "OppFg2Pct"]
_LINEUP_TABLE_NAMES = {
    "Names": "Lineup", "NetRtg": "Net", "NetVsTeam": "Net vs team",
    "Shrunk": "Adjusted vs team", "OffRtg": "Off", "DefRtg": "Def",
    "Fg3Pct": "3P%", "Fg2Pct": "2P%", "OppFg3Pct": "Opp 3P%", "OppFg2Pct": "Opp 2P%",
}
_LINEUP_TABLE_FORMATS = {
    "Minutes": "{:.0f}", "Net": "{:+.1f}", "Net vs team": "{:+.1f}",
    "Adjusted vs team": "{:+.1f}", "Off": "{:.1f}", "Def": "{:.1f}",
    "3P%": "{:.1f}", "2P%": "{:.1f}", "Opp 3P%": "{:.1f}", "Opp 2P%": "{:.1f}",
}


def _lineup_table(frame):
    view = frame[_LINEUP_TABLE_COLUMNS].rename(columns=_LINEUP_TABLE_NAMES)
    st.dataframe(
        view.style.format(_LINEUP_TABLE_FORMATS, na_rep="—"),
        use_container_width=True,
        hide_index=True,
    )


def _lineup_lookup(lineups):
    types = sorted(lineups["SeasonType"].unique())
    default_type = types.index("Regular Season") if "Regular Season" in types else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        season_type = st.selectbox("Season type", types, index=default_type, key="ll_type")
    typed = lineups[lineups["SeasonType"] == season_type]
    seasons = sorted(typed["Season"].unique(), reverse=True)
    if not seasons:
        st.info("No lineups for that season type.")
        return
    with c2:
        season = st.selectbox("Season", seasons, key="ll_season")
    in_season = typed[typed["Season"] == season]
    teams = sorted(in_season["Team"].unique())
    with c3:
        team = st.selectbox("Team", teams, key="ll_team")

    sub = in_season[in_season["Team"] == team].sort_values("Minutes", ascending=False)
    st.caption(
        f"{len(sub):,} lineups, {sub['Minutes'].sum():,.0f} minutes captured "
        "(a full regular season is roughly 3,900 team minutes; lineups "
        "outside the downloaded top players aren't included)."
    )
    _lineup_table(sub.head(40))

    st.markdown("#### Inspect a lineup")
    top = sub.head(25).reset_index(drop=True)
    labels = [f"{row.Names} · {row.Minutes:.0f} min" for row in top.itertuples()]
    choice = st.selectbox("Lineup", labels, key=f"ll_pick_{season_type}_{season}_{team}")
    row = top.iloc[labels.index(choice)]
    _lineup_avatars(row)
    _show_lineup_metrics(row)
    st.caption(
        "Descriptive only. A lineup's rating also reflects its opponents, "
        "who it played with and against, and luck, and five-man samples are "
        "small."
    )


def _lineup_explorer(lineups):
    types = sorted(lineups["SeasonType"].unique())
    default_type = types.index("Regular Season") if "Regular Season" in types else 0

    f1, f2 = st.columns(2)
    with f1:
        season_type = st.selectbox("Season type", types, index=default_type, key="le_type")
    all_seasons = sorted(lineups.loc[lineups["SeasonType"] == season_type, "Season"].unique())
    if not all_seasons:
        st.info("No lineups for that season type.")
        return
    with f2:
        if len(all_seasons) > 1:
            start, end = st.select_slider(
                "Seasons", options=all_seasons,
                value=(all_seasons[0], all_seasons[-1]), key="le_seasons",
            )
        else:
            start = end = all_seasons[0]

    g1, g2, g3 = st.columns(3)
    with g1:
        chosen_teams = st.multiselect("Teams (blank = all)", sorted(lineups["Team"].unique()), key="le_teams")
    with g2:
        query = st.text_input("Any player name contains", key="le_query")
    with g3:
        min_minutes = st.slider("Minimum minutes together", 0, 1500, 150, 25, key="le_min")

    sort_options = {
        "Net vs team, sample-adjusted (recommended)": ("Shrunk", False),
        "Net rating": ("NetRtg", False),
        "Net vs team (raw)": ("NetVsTeam", False),
        "Offensive rating": ("OffRtg", False),
        "Defensive rating (lower is better)": ("DefRtg", True),
        "Minutes together": ("Minutes", False),
        "3P%": ("Fg3Pct", False),
        "2P%": ("Fg2Pct", False),
    }
    h1, h2, h3 = st.columns(3)
    with h1:
        sort_label = st.selectbox("Sort by", list(sort_options.keys()), key="le_sort")
    with h2:
        direction = st.radio("Order", ["Best first", "Worst first"], horizontal=True, key="le_dir")
    with h3:
        rows_to_show = st.select_slider("Rows to show", options=[25, 50, 100, 250], value=50, key="le_rows")

    f = lineups[
        (lineups["SeasonType"] == season_type)
        & lineups["Season"].between(start, end)
        & (lineups["Minutes"] >= max(min_minutes, 1))
    ]
    if chosen_teams:
        f = f[f["Team"].isin(chosen_teams)]
    if query.strip():
        q = query.strip()
        mask = pd.Series(False, index=f.index)
        for i in range(1, 6):
            mask |= f[f"Name{i}"].str.contains(q, case=False, na=False, regex=False)
        f = f[mask]

    if f.empty:
        st.info("No lineups match those filters. Try lowering the minimum minutes.")
        return

    column, best_is_low = sort_options[sort_label]
    ascending = best_is_low if direction == "Best first" else not best_is_low
    ranked = f.dropna(subset=[column]).sort_values(column, ascending=ascending)

    st.caption(
        f"{len(ranked):,} lineups match. "
        f"{(ranked['Minutes'] < 300).mean():.0%} of them have under 300 minutes together."
    )
    _lineup_table(ranked.head(rows_to_show))
    st.caption(
        "'Adjusted vs team' pulls small samples toward the team's baseline "
        "much harder than for pairs, because five-man ratings are far "
        "noisier. Look for lineups that stay good across seasons."
    )


def _lineup_checks(lineups, report):
    st.write("What the lineup files actually contain, and what was cleaned.")

    st.markdown("**Files**")
    for name, rows in report["files"]:
        st.caption(f"{name}: " + ("not found" if rows is None else f"{rows:,} rows"))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows in files", f"{report['rows_raw']:,}")
    m2.metric("Rows after cleaning", f"{report['rows_clean']:,}")
    m3.metric("Seasons", f"{lineups['Season'].nunique()}")
    m4.metric("Distinct lineups", f"{lineups['LineupKey'].nunique():,}")

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("Overlap duplicates removed", f"{report['duplicates_removed']:,}",
              help="The files share boundary seasons.")
    n2.metric("Zero-minute rows dropped", f"{report['zero_minute_rows']:,}")
    n3.metric("Not five distinct players", f"{report['not_five_distinct']:,}")
    n4.metric("Lineups with all names known", f"{report['name_coverage']:.0%}")

    if report.get("overlap_seasons"):
        st.caption("Seasons found in more than one file: " + ", ".join(report["overlap_seasons"]))
    for problem in report["problems"]:
        st.error(problem)
    for note in report["notes"]:
        st.caption(note)
    if report.get("net_mismatch_share", 0) > 0.02:
        st.warning(
            f"{report['net_mismatch_share']:.0%} of rows have a NetRtg that "
            "doesn't equal OffRtg minus DefRtg (beyond rounding)."
        )
    if report.get("columns"):
        with st.expander("Columns found in the files"):
            st.code(", ".join(report["columns"]))

    st.markdown("#### Evidence tiers")
    tiers = (lineups["Sample"].value_counts()
             .reindex(LINEUP_SAMPLE_LABELS).fillna(0).astype(int).rename("Lineups"))
    st.dataframe(tiers.reset_index().rename(columns={"index": "Tier", "Sample": "Tier"}),
                 use_container_width=True, hide_index=True)

    st.markdown("#### Coverage by season")
    per_team = lineups.groupby(["SeasonType", "Season", "TeamId"])["Minutes"].agg(["size", "sum"])
    coverage = per_team.groupby(["SeasonType", "Season"]).agg(
        Teams=("size", "size"),
        Median_lineups_per_team=("size", "median"),
        Median_minutes_per_team=("sum", "median"),
    ).reset_index()
    st.dataframe(coverage.round(0), use_container_width=True, hide_index=True)
    st.caption(
        "Minutes per team well below ~3,900 means lineups involving players "
        "outside the downloaded top group aren't represented."
    )


def _lineup_file_diagnostics():
    """Column names and first rows of each lineup file, straight from disk."""
    for path in LINEUP_FILES:
        if not path.exists():
            st.caption(f"{path.name}: not found")
            continue
        try:
            head = pd.read_csv(path, compression="gzip", dtype=str, nrows=3)
            st.markdown(f"**{path.name}**")
            st.code(", ".join(map(str, head.columns)))
            st.dataframe(head, use_container_width=True, hide_index=True)
        except Exception as error:
            st.caption(f"{path.name}: couldn't be read ({error})")


def render_lineup_lab(df):
    """Lineup Lab: how real five-man lineups performed."""
    st.subheader("Lineup Lab")
    st.write(
        "Real five-man lineups: who played together, for how long, and how "
        "they did. Five-man samples are small and noisy, so this is for "
        "finding things worth a closer look."
    )

    if not any(path.exists() for path in LINEUP_FILES):
        st.info(
            "Lineup files not found. Put " + ", ".join(f"`{n}`" for n in LINEUP_FILE_NAMES)
            + " in the same folder as `app.py`."
        )
        return

    try:
        lineups, report = load_lineups()
    except Exception as error:
        st.error(f"Unable to load the lineup data: {error}")
        return
    if lineups is None:
        st.error("; ".join(report["problems"]))
        with st.expander("What's in the files (send this to Claude)", expanded=True):
            _lineup_file_diagnostics()
        return

    look_tab, explore_tab, checks_tab = st.tabs(
        ["Look up lineups", "Explore lineups", "Data checks"]
    )
    with look_tab:
        _lineup_lookup(lineups)
    with explore_tab:
        _lineup_explorer(lineups)
    with checks_tab:
        _lineup_checks(lineups, report)


# --------------------------------------------------
# LINEUP MODEL INPUTS (used by the Team Builder)
# --------------------------------------------------

@st.cache_resource(show_spinner="Building lineup profiles from real lineups...")
def build_lineup_training(_data, _lineups, _zfeat, _pools, base_cols, cache_key):
    """Skill profile for every real lineup, plus limits on shared resources.

    Returns (training table, cores, pools, report). Each lineup's profile is
    built exactly like a team's core five: the average of its five players'
    skill z-scores, plus the best/worst player on the floor for key roles.
    """
    base_cols = list(base_cols)
    row_of = _skill_row_lookup(_data)
    L = _lineups

    labels = pd.concat(
        [(L[f"Player{i}Id"] + "|" + L["Season"]).map(row_of) for i in range(1, 6)],
        axis=1,
    )
    matched = labels.notna().all(axis=1)
    total_minutes = float(L["Minutes"].sum())
    report = {
        "lineups": len(L),
        "matched": int(matched.sum()),
        "unmatched": int((~matched).sum()),
        "match_rate": float(matched.mean()) if len(L) else 0.0,
        "minutes_match_rate": float(L.loc[matched, "Minutes"].sum() / total_minutes) if total_minutes else 0.0,
        "distinct_combinations": int(L["LineupKey"].nunique()),
    }
    if report["minutes_match_rate"] < 0.5 or matched.sum() < 500:
        report["reason"] = (
            f"Only {report['minutes_match_rate']:.0%} of lineup minutes could be "
            "matched to player stats. Player IDs or season labels probably "
            "differ between the files."
        )
        return None, {}, {}, report

    Lm = L[matched]
    report["matched_below_minute_cutoff"] = int(
        (Lm["Minutes"] < LINEUP_MODEL_MIN_MINUTES).sum()
    )
    R = labels[matched].astype(int).to_numpy()
    zvals = _zfeat[base_cols].to_numpy(dtype=np.float32)
    zpos = _zfeat.index.get_indexer(R.ravel()).reshape(R.shape)

    # Average the five player profiles incrementally. Building the full
    # lineups x 5 x features tensor can use hundreds of MB for large files.
    prof_values = np.zeros((len(R), len(base_cols)), dtype=np.float32)
    for player_slot in range(5):
        prof_values += zvals[zpos[:, player_slot]]
    prof_values /= 5
    prof = pd.DataFrame(prof_values, columns=base_cols)
    interaction_axes = _pools.get("interaction_axes")
    interaction_cols = _pools.get("interaction_cols", [])
    if interaction_axes is not None and interaction_axes.shape[1] and interaction_cols:
        keep_for_model = (Lm["Minutes"] >= LINEUP_MODEL_MIN_MINUTES).to_numpy()
        player_axis_scores = zvals @ interaction_axes
        lineup_axis_scores = player_axis_scores[zpos[keep_for_model]]
        pair_values = _builder_pair_interactions(lineup_axis_scores)
        for i, column in enumerate(interaction_cols):
            prof[column] = np.nan
            prof.loc[keep_for_model, column] = pair_values[:, i]
    feature_index = {c: i for i, c in enumerate(base_cols)}
    for label, feature, how in ROLE_FEATURES:
        if feature in feature_index:
            column = zvals[zpos[:, 0], feature_index[feature]]
            for player_slot in range(1, 5):
                player_values = zvals[zpos[:, player_slot], feature_index[feature]]
                column = np.maximum(column, player_values) if how == "max" else np.minimum(column, player_values)
            prof[label] = column

    prof["Season"] = Lm["Season"].to_numpy()
    prof["Tm"] = (Lm["TeamId"] + ":" + Lm["LineupKey"]).to_numpy()
    prof["LineupKey"] = Lm["LineupKey"].to_numpy()
    prof["Team"] = Lm["Team"].to_numpy()
    prof["Core five"] = Lm["Names"].to_numpy()
    prof["Minutes"] = Lm["Minutes"].to_numpy()
    for column in ("NetC", "OffC", "DefC"):
        prof[column] = Lm[column].to_numpy()
    era_of = {s: era_for_year(season_start_year(s)) for s in prof["Season"].unique()}
    prof["Era"] = prof["Season"].map(era_of)
    prof["weight"] = np.minimum(prof["Minutes"], LINEUP_WEIGHT_CAP)

    # Limits on shared resources, from what real lineups have used.
    raw = _pools["raw"]
    rawpos = raw.index.get_indexer(R.ravel()).reshape(R.shape)
    big = (prof["Minutes"] >= LINEUP_CAP_MIN_MINUTES).to_numpy()
    caps = dict(_pools["caps"])
    for name, members in _pools["defs"]:
        values = raw[members].to_numpy(float)[rawpos]       # lineups x 5 x members
        totals = np.nansum(values, axis=(1, 2))
        if big.sum() >= 30:
            caps[name] = {
                "cap": float(np.percentile(totals[big], 99)),
                "typical": float(np.median(totals[big])),
            }
    pools = {**_pools, "caps": caps}

    keep = (prof["Minutes"] >= LINEUP_MODEL_MIN_MINUTES).to_numpy()
    training = prof[keep].reset_index(drop=True)
    cores = {
        (s, t): rows.tolist()
        for s, t, rows in zip(training["Season"], training["Tm"], R[keep])
    }
    report["training_lineups"] = len(training)
    report["training_combinations"] = int(training["LineupKey"].nunique())
    report["training_minutes"] = float(training["Minutes"].sum())
    return training, cores, {**pools, "cores": cores}, report


def legacy_scale_check(df, zfeat, profiles, training, feature_cols, target_label):
    """How did the older team-based method do on real lineups?

    Fit the old team-level model, apply it to every real lineup, and measure
    how much its predictions would need to be multiplied by to match what the
    lineups actually did. That's an empirical version of the bench-dilution
    guess.
    """
    mapping = {
        "Net rating": ("Net rating (approx.)", 1),
        "Offense (points scored per 100)": ("Points per 100 poss", 1),
        "Defense (points prevented per 100)": ("Points allowed per 100 poss (approx.)", -1),
    }
    teams = build_team_seasons(df)
    source, sign = mapping[target_label]
    if teams.empty or source not in teams.columns or profiles.empty:
        return None

    team_cols = [c for c in profiles.columns if c not in ("Season", "Tm", "Core five")]
    if set(team_cols) - set(training.columns):
        return None

    merged = profiles.merge(teams[["Season", "Tm", "Era", source]], on=["Season", "Tm"], how="left")
    merged["_target"] = sign * (
        merged[source] - merged.groupby("Season")[source].transform("mean")
    )
    if merged["_target"].notna().sum() < 100:
        return None

    fitted = fit_builder_models(
        merged, team_cols, "_target",
        cache_key=(_lineup_cache_key(), "legacy", target_label, tuple(team_cols)),
    )
    predicted = _ridge_predict(
        fitted["additive"]["model"], training[team_cols].to_numpy(float)
    )
    actual = training["_target"].to_numpy(float)
    w = training["weight"].to_numpy(float)

    w = w / w.mean()
    mp, ma = (w * predicted).sum() / w.sum(), (w * actual).sum() / w.sum()
    slope = float((w * (predicted - mp) * (actual - ma)).sum() / (w * (predicted - mp) ** 2).sum())
    corr = weighted_corr(pd.Series(predicted), pd.Series(actual), pd.Series(w))
    share = top_five_minute_share(df)
    return {
        "slope": slope,
        "corr": corr,
        "guess": (1.0 / share) if share else None,
        "n": len(training),
    }


def lineup_history(lineups, player_ids):
    """Every time this exact five has played together."""
    key = "-".join(sorted(str(p) for p in player_ids))
    rows = lineups[lineups["LineupKey"] == key]
    return rows.sort_values("Minutes", ascending=False)



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

selected_page = st.radio(
    "Navigate",
    [
        "🏀 Player Explorer",
        "⚖️ Compare",
        "🧪 Data Lab",
        "🧬 Team Builder",
    ],
    horizontal=True,
    key="main_page",
)

# --------------------------------------------------
# PLAYER EXPLORER
# --------------------------------------------------

if selected_page == "🏀 Player Explorer":
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

    st.markdown(
        player_card_html(
            selected_id,
            player_df["player_name"].iloc[0],
            career_summary(player_df),
        ),
        unsafe_allow_html=True,
    )

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

elif selected_page == "⚖️ Compare":
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
        st.markdown(
            player_card_html(
                first_id,
                first_df["player_name"].iloc[0],
                career_summary(first_df),
            ),
            unsafe_allow_html=True,
        )
        st.dataframe(
            first_df[first_cols],
            use_container_width=True,
            hide_index=True
        )

    with second_name:
        st.markdown(
            player_card_html(
                second_id,
                second_df["player_name"].iloc[0],
                career_summary(second_df),
            ),
            unsafe_allow_html=True,
        )
        st.dataframe(
            second_df[second_cols],
            use_container_width=True,
            hide_index=True
        )

# --------------------------------------------------
# DATA LAB (houses the Player Lab and Team Lab)
# --------------------------------------------------

elif selected_page == "🧪 Data Lab":
    st.markdown(
        '<div class="section-label">03 / Data Lab</div>',
        unsafe_allow_html=True
    )

    st.header("Data Lab")

    st.write(
        "Hunt for patterns in the data. Pick a lab: the Player Lab "
        "looks at what players do, the Team Lab looks at how whole "
        "teams play, the Pair Lab looks at two-player combinations, and "
        "the Lineup Lab looks at real five-man lineups."
    )

    lab_choice = st.selectbox(
        "Choose a lab",
        ["Player Lab", "Team Lab", "Pair Lab", "Lineup Lab"],
        key="lab_choice",
    )

    st.divider()

    if lab_choice == "Player Lab":
        st.subheader("Player Lab")

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

        # ---- Stat groups (narrow the field without losing anything) ----
        group_of = {c: stat_group(c) for c in lab_df.columns}

        selected_groups = st.multiselect(
            "Stat groups to include",
            STAT_GROUP_ORDER,
            default=STAT_GROUP_ORDER,
            help="Categories are guessed from column names. Untick groups "
                 "to focus; 'Other' holds anything that didn't fit.",
        )

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

        numeric_columns = {}

        for column in lab_df.columns:
            if column.lower() in excluded_names or column in alias_columns:
                continue
            if column.endswith("PerGame"):
                continue
            if group_of.get(column) not in selected_groups:
                continue
            if rates_only and not is_rate_column(column):
                continue

            values = pd.to_numeric(lab_df[column], errors="coerce")

            if values.notna().sum() < 30:
                continue
            if values.nunique(dropna=True) < 2:
                continue

            numeric_columns[column] = values

        numeric_data = pd.DataFrame(numeric_columns, index=lab_df.index)

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

                available_stats = sorted(
                    numeric_data.columns,
                    key=str.lower,
                )

                focus_stat = st.selectbox(
                    "Focus on one statistic (optional, type to search)",
                    ["All statistics"] + available_stats,
                    key="lab_focus",
                )

                rows_to_show = st.select_slider(
                    "Rows to show",
                    options=[10, 15, 25, 50],
                    value=15,
                    key="lab_rows",
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

                if focus_stat != "All statistics":
                    ranked = ranked[
                        (ranked["Statistic A"] == focus_stat)
                        | (ranked["Statistic B"] == focus_stat)
                    ]

                st.dataframe(
                    ranked.head(rows_to_show)[
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


    elif lab_choice == "Team Lab":
        st.subheader("Team Lab")

        st.write(
            "Each dot is one team in one season. Use this for questions about "
            "style, like whether shooting more threes goes with more shots at "
            "the rim."
        )

        teams = build_team_seasons(df)

        if teams.empty:
            needed = ["Season", "Tm", "FG3A", "AtRimFGA", "OffPoss"]
            missing = [c for c in needed if c not in df.columns]

            st.warning(
                "Couldn't build team seasons. Missing columns in "
                f"`player_seasons.csv.gz`: {', '.join(missing) or 'none'}."
            )

            with st.expander("Diagnostic info (paste this to Claude)"):
                st.write("**Columns in player_seasons.csv.gz:**")
                st.code(", ".join(map(str, df.columns)))

                try:
                    name_cols = pd.read_csv(NAME_FILE, nrows=3)
                    st.write("**Columns in player_team_seasons.csv:**")
                    st.code(", ".join(map(str, name_cols.columns)))
                    st.write("**First rows of player_team_seasons.csv:**")
                    st.dataframe(name_cols, hide_index=True)
                except Exception as error:
                    st.write(f"Couldn't read the name file: {error}")

                if "Tm" in df.columns:
                    st.write("**Sample team values:**")
                    st.code(", ".join(map(str, df["Tm"].dropna().unique()[:15])))
        else:
            metric_names = [
                c for c in teams.columns if c not in ("Season", "Tm", "Era")
            ]

            # ---- Era filter ----
            present_eras = [
                label for label, _, _ in ERAS
                if label in set(teams["Era"].dropna())
            ]

            selected_eras = st.multiselect(
                "Eras to include",
                present_eras,
                default=present_eras,
                help="Era boundaries use each season's starting year. "
                     "Pick one era to see how a relationship looks in that "
                     "period alone.",
            )

            team_z = st.checkbox(
                "Compare within each season",
                value=True,
                key="team_within_season",
                help="Measures each team against the league average of its "
                     "own season, which removes era trends.",
            )

            # Z-scores are always computed within a season, so filtering by
            # era afterward doesn't change them.
            if team_z:
                team_values = within_group_z(
                    teams[metric_names], teams["Season"]
                )
            else:
                team_values = teams[metric_names].copy()

            era_mask = teams["Era"].isin(selected_eras)

            if not era_mask.any():
                st.info("Select at least one era.")
            else:
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

                render_relationship(
                    team_values[era_mask],
                    team_x,
                    team_y,
                    unit="team-seasons",
                )

                # ---- Same relationship, era by era ----
                st.markdown("#### Does it change by era?")

                era_rows = []
                for label in present_eras:
                    rows = (teams["Era"] == label)
                    pair = team_values.loc[rows, [team_x, team_y]].dropna()
                    if len(pair) >= 10:
                        era_rows.append({
                            "Era": label,
                            "Correlation": pair[team_x].corr(pair[team_y]),
                            "Team-seasons": len(pair),
                        })

                if era_rows:
                    st.dataframe(
                        pd.DataFrame(era_rows).style.format(
                            {"Correlation": "{:+.3f}"}
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.caption(
                        "Eras with fewer than 10 team-seasons are left out. "
                        "Small eras swing a lot, so look for patterns that "
                        "hold across several eras."
                    )
                else:
                    st.caption("Not enough team-seasons per era to compare.")

                # ---- What moves with the first statistic ----
                with st.expander(f"What correlates with “{team_x}”?"):
                    subset = team_values.loc[era_mask, metric_names]
                    related = (
                        subset.corr(min_periods=10)[team_x]
                        .drop(team_x)
                        .dropna()
                        .sort_values(ascending=False)
                    )
                    related_table = related.reset_index()
                    related_table.columns = ["Statistic", "Correlation"]

                    st.dataframe(
                        related_table.style.format({"Correlation": "{:+.3f}"}),
                        use_container_width=True,
                        hide_index=True,
                    )

                with st.expander("See the team-season table"):
                    st.dataframe(
                        teams[era_mask].round(3),
                        use_container_width=True,
                        hide_index=True,
                    )

                st.caption(
                    "Team possessions are estimated from player data (the sum "
                    "of each player's offensive possessions divided by 5), so "
                    "per-100 and net rating numbers are approximate."
                )


    elif lab_choice == "Pair Lab":
        render_pair_lab(df)
    else:
        render_lineup_lab(df)

# --------------------------------------------------
# TEAM BUILDER
# --------------------------------------------------

elif selected_page == "🧬 Team Builder":
    render_team_builder(df, player_labels, player_options)

st.markdown(
    '<div class="footer">'
    'BRADBALL &nbsp; / &nbsp; DATA BEFORE ASSUMPTIONS &nbsp; / &nbsp; '
    'FIT, CONTEXT & INTERACTION'
    '</div>',
    unsafe_allow_html=True
)























