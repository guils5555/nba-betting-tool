import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
import re

# ==========================================
# 🏀 CONFIGURATION
# ==========================================
# YOUR SPECIFIC GOOGLE SHEET LINK
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTZb3EzZ2pQUO1NttC8Wo3WRWY02_THxEmzcMESCN5Y4QCCAgI26WxWbfeyVvnTSWkYjv-Vd0yxtSmF/pub?gid=1128595491&single=true&output=csv"

st.set_page_config(page_title="Evan's NBA Tool", page_icon="🏀", layout="wide")

# ==========================================
# 🛠️ HELPER FUNCTIONS (The Math Engine)
# ==========================================
def am_to_dec(odds):
    """Converts American Odds (-110) to Decimal (1.91)"""
    try:
        o = float(odds)
        if o == 0: return 1.0
        return (o / 100) + 1 if o > 0 else (100 / abs(o)) + 1
    except:
        return 1.0

def calc_edge(projection, line, odds):
    """Calculates the True Win Probability and Edge"""
    try:
        # Volatility factor (0.20 is standard for NBA props)
        std_dev = projection * 0.20
        # Z-Score and Probability
        z_score = (line - projection) / std_dev
        true_prob = 1 - norm.cdf(z_score)
        
        # Implied Probability from Odds
        dec_odds = am_to_dec(odds)
        implied_prob = 1 / dec_odds if dec_odds > 0 else 0
        
        edge = true_prob - implied_prob
        return true_prob, edge
    except:
        return 0.0, 0.0

@st.cache_data(ttl=300) # Clears cache every 5 minutes to get fresh data
def load_sheet_data():
    """Reads the Raw Data from the Google Sheet"""
    try:
        # Read CSV. We assume header is on the first row found.
        # on_bad_lines='skip' helps avoiding errors if the sheet has messy rows
        df = pd.read_csv(SHEET_URL, on_bad_lines='skip')
        return df
    except Exception as e:
        return None

# ==========================================
# 📱 THE APP UI
# ==========================================

st.title("🏀 NBA Hammer Tool")
st.markdown("### *The Automated Edge Finder*")

# 1. LOAD DATA
df = load_sheet_data()

if df is None:
    st.error("❌ Could not load data. Please check if your Google Sheet is published as CSV.")
    st.stop()

# 2. SIDEBAR CONTROLS
with st.sidebar:
    st.header("⚙️ Analysis Settings")
    
    # Defense Adjustment
    st.info("Since we can't read the Defense Tab automatically in this mode, select the matchup strength manually:")
    opp_rank = st.selectbox(
        "Opponent Defense Rank", 
        ["Neutral (Rank #15)", "Soft (Rank #20-30)", "Tough (Rank #1-10)"],
        index=0
    )
    
    # Determine multiplier based on selection
    defense_mult = 1.0
    if "Soft" in opp_rank: defense_mult = 1.08  # Boost projection by 8%
    if "Tough" in opp_rank: defense_mult = 0.92 # Lower projection by 8%

    st.divider()
    
    # Ticket Management
    if 'ticket' not in st.session_state:
        st.session_state.ticket = []
        
    st.subheader("🎟️ Your Active Ticket")
    if len(st.session_state.ticket) > 0:
        for i, leg in enumerate(st.session_state.ticket):
            st.text(f"✅ {leg}")
        
        if st.button("Clear Ticket"):
            st.session_state.ticket = []
            st.rerun()
    else:
        st.caption("No bets added yet.")

# 3. MAIN ANALYSIS ENGINE
st.subheader("📊 Live Projections")

# We look for rows that look like player stats (containing 'Points', 'Assists', etc.)
# and assume the CSV structure matches your V157 input (Stat Name in Col A, History in Col B)
# If headers are different, we try to find the relevant columns by index.

found_stats = False

# Iterate through the DataFrame rows to find betting lines
# We convert the dataframe to a list of dicts for easier looping
rows = df.to_dict('records')

betting_opportunities = []

for row in rows:
    # Get values by index to be safe (Col A=0, Col B=1, etc.)
    vals = list(row.values())
    if len(vals) < 3: continue
    
    label = str(vals[0])  # Stat Name (e.g., "Points")
    history = str(vals[1]) # History String (e.g., "25, 30, 22")
    
    # Filter for valid stat rows
    if any(x in label for x in ['Points', 'Rebounds', 'Assists', '3 Pointer', 'Pts+']) and "," in history:
        found_stats = True
        
        # A. CALCULATE PROJECTION
        try:
            # Clean string and convert to floats
            past_games = [float(x.strip()) for x in history.split(',') if x.strip() and x.replace('.','',1).isdigit()]
            if not past_games: continue
            
            avg = sum(past_games) / len(past_games)
            projection = avg * defense_mult
            
            # B. FIND HAMMERS IN THIS ROW
            # Iterate through the rest of the columns (Alt lines)
            best_edge = -1.0
            best_bet_str = ""
            
            for i in range(2, len(vals)):
                cell_val = str(vals[i])
                # Look for format like "27.5 / -110"
                if "/" in cell_val:
                    parts = cell_val.split('/')
                    try:
                        line = float(re.findall(r'-?\d+\.?\d*', parts[0])[0])
                        odds = float(re.findall(r'-?\d+\.?\d*', parts[1])[0])
                        
                        prob, edge = calc_edge(projection, line, odds)
                        
                        # Save if it's a good bet
                        if edge > 0.02: # Show anything with >2% edge
                            
                            rec = "⚖️ PASS"
                            color = "grey"
                            if edge > 0.05: 
                                rec = "✅ BET"
                                color = "green"
                            if edge > 0.15: 
                                rec = "🚨 HAMMER"
                                color = "red"
                                
                            betting_opportunities.append({
                                "Stat": label,
                                "Line": line,
                                "Odds": int(odds),
                                "Proj": round(projection, 1),
                                "Win%": f"{int(prob*100)}%",
                                "Edge": f"{int(edge*100)}%",
                                "Verdict": rec,
                                "Raw_Edge": edge # For sorting
                            })
                    except:
                        continue
        except:
            continue

# 4. DISPLAY RESULTS
if not found_stats:
    st.warning("⚠️ Connected to Sheet, but didn't find recognizable stat rows. Make sure your CSV has 'Stat Name' in the first column and 'History' (comma separated) in the second.")
    st.write("Here is a preview of the raw data we see:")
    st.dataframe(df.head())

elif not betting_opportunities:
    st.info("✅ Analysis ran, but no edges > 2% were found with the current settings.")

else:
    # Convert results to DataFrame for nice display
    res_df = pd.DataFrame(betting_opportunities)
    
    # Sort by Edge (Highest First)
    res_df = res_df.sort_values(by="Raw_Edge", ascending=False).drop(columns=["Raw_Edge"])
    
    # Display as a table
    st.dataframe(
        res_df, 
        column_config={
            "Verdict": st.column_config.TextColumn("Verdict"),
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # 5. TICKET BUILDER DROPDOWN
    st.subheader("➕ Add to Ticket")
    
    # Create readable list of options
    ticket_options = res_df.apply(lambda x: f"{x['Stat']} {x['Line']}+ ({x['Odds']}) | Edge: {x['Edge']}", axis=1).tolist()
    
    selected_bet = st.selectbox("Select a winning leg:", ticket_options)
    
    if st.button("Add Leg to Ticket", type="primary"):
        st.session_state.ticket.append(selected_bet)
        st.success("Added! Check sidebar.")
        st.rerun()
