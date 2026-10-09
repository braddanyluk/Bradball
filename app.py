import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="BradBall",
    page_icon="🏀",
    layout="wide"
)

st.title("🏀 BradBall")
st.subheader("Basketball is more than individual statistics.")

st.write(
    "BradBall is a basketball research project focused on player skills, "
    "roles, interactions, and team performance."
)

st.divider()

st.header("Player Explorer")

st.write(
    "Our first step is building a searchable interface for player statistics. "
    "We'll connect your existing basketball database next."
)

player_name = st.text_input(
    "Search for a player",
    placeholder="Enter a player name or ID"
)

if player_name:
    st.info(
        f"Search for '{player_name}' will become available when we connect "
        "the player database."
    )

st.divider()

st.header("Teammate Fit")

st.write(
    "Explore how combinations of players perform together and apart."
)

st.info(
    "WOWY data integration is coming next. We'll use your existing "
    "combination statistics rather than inventing results."
)

st.divider()

st.caption(
    "BradBall | Researching basketball through data, context, and interaction."
)
