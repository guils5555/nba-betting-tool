import streamlit as st
import pandas as pd
from scipy.stats import norm

# --- CONFIGURATION ---
# PASTE YOUR PUBLISHED CSV LINK HERE
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-..../pub?gid=0&single=true&output=csv"

st.set_page_config(page_title="Evan's Betting Tool", page_icon="🏀")

# --- 1. LOAD DATA (No Auth Required) ---
@st.cache_data(ttl=600) # Refreshes every 10 mins
def load_data():
    # Read directly from the public CSV link
    df = pd.read_csv(SHEET_URL)
    return df

try:
    df_raw = load_data()
    st.toast("Data Loaded Successfully from Sheet!")
except Exception as e:
    st.error(f"Could not load data. Check your published link. Error: {e}")
    st.stop()

st.title("🏀 NBA Hammer Tool")

# --- 2. SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Search")
    # Get unique player names from your sheet (assuming col A or similar)
    # Adjust 'Player' to match the EXACT column header in your sheet
    all_players = df_raw['Player'].unique().tolist() if 'Player' in df_raw.columns else []
    
    player_name = st.selectbox("Select Player", all_players)
    
    # Session State to hold the Ticket
    if 'ticket' not in st.session_state:
        st.session_state.ticket = []

# --- 3. FILTER & ANALYZE ---
# Simple filtering logic based on the selected player
player_data = df_raw[df_raw['Player'] == player_name]

if not player_data.empty:
    st.subheader(f"Analysis for {player_name}")
    
    # Show the main stats (adjust column names to match your sheet)
    # Example: If your sheet has 'Projection' and 'Opponent Rank' columns
    col1, col2 = st.columns(2)
    proj = player_data.iloc[0]['Projection'] if 'Projection' in player_data.columns else "N/A"
    opp = player_data.iloc[0]['Opponent'] if 'Opponent' in player_data.columns else "N/A"
    
    col1.metric("Projection", proj)
    col2.metric("Opponent", opp)
    
    st.divider()
    
    # --- 4. THE LADDER DISPLAY ---
    st.subheader("🪜 Available Ladders")
    
    # Display the rows for this player from your sheet
    # We select just the relevant columns to make it readable
    display_cols = ['Stat', 'Line', 'Odds', 'Edge', 'Recommendation'] # Adjust these!
    valid_cols = [c for c in display_cols if c in player_data.columns]
    
    st.dataframe(player_data[valid_cols], use_container_width=True, hide_index=True)
    
    # --- 5. TICKET BUILDER ---
    st.divider()
    st.subheader("🎟️ Build Ticket")
    
    # Dropdown to pick a specific bet from the table above
    bet_options = player_data.apply(lambda x: f"{x['Stat']} {x['Line']} ({x['Odds']})", axis=1).tolist()
    selected_bet = st.selectbox("Choose a leg:", bet_options)
    
    if st.button("Add to Ticket"):
        st.session_state.ticket.append({
            "Player": player_name,
            "Bet": selected_bet
        })
        st.success(f"Added {selected_bet}")

# --- 6. YOUR ACTIVE TICKET ---
if st.session_state.ticket:
    st.sidebar.divider()
    st.sidebar.header("Your Active Slip")
    
    for i, leg in enumerate(st.session_state.ticket):
        st.sidebar.text(f"{i+1}. {leg['Player']}\n   {leg['Bet']}")
    
    if st.sidebar.button("Clear Ticket"):
        st.session_state.ticket = []
        st.experimental_rerun()

else:
    st.info("Select a player to see their ladders.")
