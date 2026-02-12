import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
import re

# ==========================================
# 🎨 CUSTOM STYLING (From your HTML file)
# ==========================================
st.set_page_config(page_title="Automated Bet Finder", page_icon="🤖", layout="wide")

# This injects your HTML's CSS directly into the Streamlit app
st.markdown("""
<style>
    /* MAIN BACKGROUND GRADIENT */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* CARDS */
    div[data-testid="stMetric"], div[data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        color: #333;
    }
    
    /* HEADERS */
    h1, h2, h3 {
        color: white !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    /* BUTTONS */
    div.stButton > button {
        background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: bold;
        transition: transform 0.2s;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.2);
    }
    
    /* DATAFRAME TEXT COLOR FIX */
    div[data-testid="stDataFrame"] * {
        color: #333 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🏀 CONFIGURATION & LOGIC (The Brains)
# ==========================================
# PASTE YOUR GOOGLE SHEET CSV LINK HERE
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTZb3EzZ2pQUO1NttC8Wo3WRWY02_THxEmzcMESCN5Y4QCCAgI26WxWbfeyVvnTSWkYjv-Vd0yxtSmF/pub?gid=1128595491&single=true&output=csv"

# --- HELPER FUNCTIONS ---
def am_to_dec(odds):
    try:
        o = float(odds)
        if o == 0: return 1.0
        return (o / 100) + 1 if o > 0 else (100 / abs(o)) + 1
    except: return 1.0

def calc_edge(projection, line, odds):
    try:
        std_dev = projection * 0.20
        z_score = (line - projection) / std_dev
        true_prob = 1 - norm.cdf(z_score)
        dec_odds = am_to_dec(odds)
        implied_prob = 1 / dec_odds if dec_odds > 0 else 0
        return true_prob, true_prob - implied_prob
    except: return 0.0, 0.0

@st.cache_data(ttl=300)
def load_sheet_data():
    try:
        return pd.read_csv(SHEET_URL, header=None, on_bad_lines='skip')
    except: return None

# ==========================================
# 📱 THE APP UI
# ==========================================

st.title("🤖 Automated Bet Finder v3.0-ML")
st.markdown("### *AI-Powered Sports Analytics Engine*")

# 1. LOAD DATA
df = load_sheet_data()
if df is None:
    st.error("❌ Could not connect to database.")
    st.stop()

# 2. SIDEBAR
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4140/4140047.png", width=100)
    st.header("Control Panel")
    
    opp_rank = st.selectbox(
        "Matchup Difficulty", 
        ["Neutral (Rank #15)", "Soft (Rank #20-30)", "Tough (Rank #1-10)"],
        index=0
    )
    defense_mult = 1.08 if "Soft" in opp_rank else (0.92 if "Tough" in opp_rank else 1.0)
    
    if 'ticket' not in st.session_state: st.session_state.ticket = []
    
    st.divider()
    st.subheader("🎟️ Active Ticket")
    if st.session_state.ticket:
        for leg in st.session_state.ticket: 
            st.code(f"✅ {leg}")
        if st.button("Clear Ticket"):
            st.session_state.ticket = []
            st.rerun()
    else:
        st.caption("No bets staged.")

# 3. LOGIC ENGINE
betting_opportunities = []
rows = df.values.tolist()

for row in rows:
    clean_row = [str(x) if pd.notna(x) else "" for x in row]
    stat_col_idx = -1
    for i in range(5):
        if i < len(clean_row):
            val = clean_row[i].strip()
            if any(x in val for x in ['Points', 'Rebounds', 'Assists', '3 Pointer', 'Pts+']) and len(val) < 20:
                stat_col_idx = i
                break
    
    if stat_col_idx != -1:
        label = clean_row[stat_col_idx]
        history_idx = stat_col_idx + 1
        if history_idx < len(clean_row):
            history = clean_row[history_idx]
            if "," in history:
                try:
                    past_games = [float(x.strip()) for x in history.split(',') if x.strip() and x.replace('.','',1).isdigit()]
                    if not past_games: continue
                    avg = sum(past_games) / len(past_games)
                    projection = avg * defense_mult
                    
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
                                        "Player Stat": label,
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

# 4. DISPLAY RESULTS
if not betting_opportunities:
    st.info("No high-value edges found right now.")
else:
    # Top Metrics Row
    col1, col2, col3 = st.columns(3)
    best_bet = max(betting_opportunities, key=lambda x: x['Raw_Edge'])
    col1.metric("Top Edge Found", best_bet['Edge'], best_bet['Player Stat'])
    col2.metric("Total Opportunities", len(betting_opportunities))
    col3.metric("System Status", "Online 🟢")

    st.markdown("### 📋 Analysis Board")
    res_df = pd.DataFrame(betting_opportunities).sort_values(by="Raw_Edge", ascending=False).drop(columns=["Raw_Edge"])
    
    st.dataframe(
        res_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Verdict": st.column_config.TextColumn("Verdict"),
        }
    )
    
    st.markdown("---")
    st.subheader("Add to Ticket")
    opts = res_df.apply(lambda x: f"{x['Player Stat']} {x['Line']}+ ({x['Odds']})", axis=1).tolist()
    sel = st.selectbox("Select Leg:", opts)
    if st.button("Add Leg"):
        st.session_state.ticket.append(sel)
        st.rerun()
