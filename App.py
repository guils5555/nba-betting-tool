import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
import re

# ==========================================
# 🏀 CONFIGURATION
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTZb3EzZ2pQUO1NttC8Wo3WRWY02_THxEmzcMESCN5Y4QCCAgI26WxWbfeyVvnTSWkYjv-Vd0yxtSmF/pub?gid=1128595491&single=true&output=csv"

st.set_page_config(page_title="Evan's NBA Tool", page_icon="🏀", layout="wide")

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def am_to_dec(odds):
    try:
        o = float(odds)
        if o == 0: return 1.0
        return (o / 100) + 1 if o > 0 else (100 / abs(o)) + 1
    except:
        return 1.0

def calc_edge(projection, line, odds):
    try:
        std_dev = projection * 0.20
        z_score = (line - projection) / std_dev
        true_prob = 1 - norm.cdf(z_score)
        dec_odds = am_to_dec(odds)
        implied_prob = 1 / dec_odds if dec_odds > 0 else 0
        return true_prob, true_prob - implied_prob
    except:
        return 0.0, 0.0

@st.cache_data(ttl=300)
def load_sheet_data():
    try:
        # Read the CSV, assuming the whole sheet is exported
        df = pd.read_csv(SHEET_URL, header=None, on_bad_lines='skip')
        return df
    except Exception as e:
        return None

# ==========================================
# 📱 THE APP UI
# ==========================================

st.title("🏀 NBA Hammer Tool")

# 1. LOAD DATA
df = load_sheet_data()

if df is None:
    st.error("❌ Could not load data.")
    st.stop()

# 2. SIDEBAR
with st.sidebar:
    st.header("⚙️ Settings")
    show_debug = st.checkbox("Show Raw Data (Debug)", value=False)
    
    opp_rank = st.selectbox(
        "Opponent Defense Rank", 
        ["Neutral (Rank #15)", "Soft (Rank #20-30)", "Tough (Rank #1-10)"],
        index=0
    )
    defense_mult = 1.08 if "Soft" in opp_rank else (0.92 if "Tough" in opp_rank else 1.0)
    
    if 'ticket' not in st.session_state: st.session_state.ticket = []
    
    st.divider()
    st.subheader("🎟️ Active Ticket")
    if st.session_state.ticket:
        for leg in st.session_state.ticket: st.text(f"✅ {leg}")
        if st.button("Clear Ticket"):
            st.session_state.ticket = []
            st.rerun()
    else:
        st.caption("No bets added.")

# 3. ANALYSIS ENGINE (SMART FINDER)
if show_debug:
    st.warning("Debugging: Here is the raw CSV data the app sees.")
    st.dataframe(df.head(20))

betting_opportunities = []
found_stats = False

# Convert to list of lists for easier scanning
rows = df.values.tolist()

for row in rows:
    # Sanitize row: replace NaN with empty string
    clean_row = [str(x) if pd.notna(x) else "" for x in row]
    
    # We look for the "Stat Name" in the first 5 columns (Columns A-E)
    # This accounts for the fact that your data might start in Column C
    stat_col_idx = -1
    
    for i in range(5):
        if i < len(clean_row):
            val = clean_row[i].strip()
            # If we find a recognized stat name
            if any(x in val for x in ['Points', 'Rebounds', 'Assists', '3 Pointer', 'Pts+']) and len(val) < 20:
                stat_col_idx = i
                break
    
    if stat_col_idx != -1:
        # We found a stat row!
        label = clean_row[stat_col_idx]
        
        # The "History" is usually the NEXT column
        history_idx = stat_col_idx + 1
        if history_idx < len(clean_row):
            history = clean_row[history_idx]
            
            # Check if history is valid (has commas)
            if "," in history:
                found_stats = True
                
                # --- CALCULATE PROJECTION ---
                try:
                    past_games = [float(x.strip()) for x in history.split(',') if x.strip() and x.replace('.','',1).isdigit()]
                    if not past_games: continue
                    avg = sum(past_games) / len(past_games)
                    projection = avg * defense_mult
                    
                    # --- FIND BETS ---
                    # Scan all remaining columns for betting lines (e.g., "27.5 / -110")
                    for i in range(history_idx + 1, len(clean_row)):
                        cell_val = clean_row[i]
                        if "/" in cell_val:
                            parts = cell_val.split('/')
                            try:
                                line = float(re.findall(r'-?\d+\.?\d*', parts[0])[0])
                                odds = float(re.findall(r'-?\d+\.?\d*', parts[1])[0])
                                prob, edge = calc_edge(projection, line, odds)
                                
                                if edge > 0.02:
                                    rec = "🚨 HAMMER" if edge > 0.15 else ("✅ BET" if edge > 0.05 else "⚖️ PASS")
                                    betting_opportunities.append({
                                        "Stat": label,
                                        "Line": line,
                                        "Odds": int(odds),
                                        "Proj": round(projection, 1),
                                        "Win%": f"{int(prob*100)}%",
                                        "Edge": f"{int(edge*100)}%",
                                        "Verdict": rec,
                                        "Raw_Edge": edge
                                    })
                            except: continue
                except: continue

# 4. DISPLAY
if not found_stats:
    st.error("⚠️ Didn't find any stat rows. Check the 'Show Raw Data' box to see if the columns are misaligned.")
elif not betting_opportunities:
    st.info("✅ Analysis ran, but no edges > 2% were found.")
else:
    res_df = pd.DataFrame(betting_opportunities).sort_values(by="Raw_Edge", ascending=False).drop(columns=["Raw_Edge"])
    st.dataframe(res_df, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("➕ Add to Ticket")
    opts = res_df.apply(lambda x: f"{x['Stat']} {x['Line']}+ ({x['Odds']})", axis=1).tolist()
    sel = st.selectbox("Select Bet:", opts)
    if st.button("Add Leg"):
        st.session_state.ticket.append(sel)
        st.rerun()
