import streamlit as st
import gspread
import pandas as pd
from scipy.stats import norm
import re

# --- PAGE SETUP ---
st.set_page_config(page_title="Evan's NBA Tool", page_icon="🏀")

st.title("🏀 NBA Player Prop Hammer")
st.write("The automated edge-finder for player props.")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("Analysis Settings")
    player_name = st.text_input("Player Name", "Donovan Mitchell")
    opponent = st.selectbox("Opponent", ["Washington", "Detroit", "Charlotte", "Lakers", "Celtics"]) # Add all teams
    run_btn = st.button("Run Analysis", type="primary")

# --- CORE LOGIC (Runs only when button clicked) ---
if run_btn:
    with st.spinner(f"Crunching numbers for {player_name}..."):
        
        # 1. AUTHENTICATION (Secrets Management)
        # Streamlit handles secrets securely
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        
        # 2. CONNECT TO SHEET
        sh = gc.open("NBA Sports Betting") # Your actual sheet name
        ws_stats = sh.worksheet("Individual Player Stats - NBA")
        ws_def = sh.worksheet("Defense Stats - NBA")
        
        # 3. GET DATA (Simulated for this example, you'd pull from your sheet)
        # In the real app, we'd pull the row for 'player_name' here
        # For now, let's assume we pulled the data for Mitchell
        
        st.success(f"Found data for {player_name} vs {opponent}")
        
        # 4. DISPLAY THE "DASHBOARD"
        col1, col2, col3 = st.columns(3)
        col1.metric("Proj Points", "31.4", "73% Prob")
        col2.metric("Proj Assists", "7.5", "91% Prob")
        col3.metric("Defense Rank", "#29", "Washington")
        
        st.divider()
        
        # 5. THE LADDER SELECTOR
        st.subheader("🪜 The Ladder Builder")
        
        # Fake data to show you the UI
        ladder_data = [
            {"Line": "20+", "Odds": -500, "Edge": "9%", "Prob": "96%"},
            {"Line": "25+", "Odds": -188, "Edge": "19%", "Prob": "84%"},
            {"Line": "27.5", "Odds": -104, "Edge": "22%", "Prob": "73%"},
            {"Line": "30+", "Odds": +142, "Edge": "17%", "Prob": "58%"}
        ]
        
        df = pd.DataFrame(ladder_data)
        st.dataframe(df, use_container_width=True)
        
        # 6. INTERACTIVE PARLAY BUILDER
        st.subheader("🎟️ Build Your Ticket")
        selected_line = st.selectbox("Select a leg to stage:", df["Line"].tolist())
        
        if st.button("Add to Ticket"):
            # Write this back to your Google Sheet (Column T)
            st.toast(f"Added {player_name} {selected_line} Points to Staging!")