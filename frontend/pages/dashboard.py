import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import io
from dotenv import load_dotenv

# Try to load Langchain for AI features
try:
    from langchain_groq import ChatGroq
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
except ImportError:
    pass

load_dotenv()

st.set_page_config(page_title="Dacati Dashboard", page_icon="🏦", layout="wide")

# =========================================================================
# PREMIUM DARK 'DACATI' Aesthetic CSS
# =========================================================================
st.markdown("""
<style>
    /* Global background */
    .stApp {
        background-color: #16161a;
        color: #EAEAEA;
    }
    
    /* Headers */
    h1, h2, h3, h4 {
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }
    
    /* Metrics / Summary Cards */
    div[data-testid="stMetricValue"] {
        color: #FF6B00;
    }
    
    /* Containers / Cards */
    .css-1r6slb0, .css-12oz5g7 { 
        background-color: #202026;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #2A2A35;
    }
    
    /* Expander backgrounds */
    .streamlit-expanderHeader {
        background-color: #202026 !important;
        border-radius: 8px;
        border: 1px solid #2A2A35;
        color: #EAEAEA !important;
    }
    .streamlit-expanderContent {
        background-color: #1A1A20;
        border: 1px solid #2A2A35;
        border-top: none;
        border-radius: 0 0 8px 8px;
        padding: 15px;
    }

    /* Beautiful Tables */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #2A2A35;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
    }
    
    [data-testid="stDataFrame"] > div {
        border-radius: 10px;
    }
    
    /* Button Style override for Download Excel */
    .stDownloadButton button {
        background-color: #FF6B00;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stDownloadButton button:hover {
        background-color: #E25204;
        color: #FFFFFF;
        box-shadow: 0 0 10px rgba(255, 107, 0, 0.4);
    }
    
    hr {
        border-color: #2A2A35;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# CONFIGURATION
# =========================================================================
API_URL = "http://localhost:8000"

# Dacati Orange Palette for the 4 categories
COLORS = {
    "Fraud Investigation": "#FF3333", # Reddish Orange
    "Account Services": "#FF6B00",    # Dacati Classic Orange
    "Loan Support": "#FF9D4A",        # Soft Amber
    "General Support": "#FFD699"      # Pale Peach
}

# =========================================================================
# DATA FETCHING & AI LOGIC
# =========================================================================
@st.cache_data(ttl=60)
def fetch_complaints():
    try:
        res = requests.get(f"{API_URL}/complaints/", timeout=10)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        st.error(f"Cannot connect to the backend server: {e}")
        return []

complaints = fetch_complaints()

st.sidebar.markdown("### ⚙️ Dashboard Controls")
timeframe = st.sidebar.radio("Timeframe Filter", ["Lifetime", "Monthly (Last 30 Days)", "Weekly (Last 7 Days)", "Daily (Last 24 Hours)"])

if timeframe != "Lifetime" and complaints:
    filtered_complaints = []
    now = pd.Timestamp.now(tz='UTC')
    if "Daily" in timeframe: delta = pd.Timedelta(days=1)
    elif "Weekly" in timeframe: delta = pd.Timedelta(days=7)
    elif "Monthly" in timeframe: delta = pd.Timedelta(days=30)
    
    for c in complaints:
        if c.get('created_at'):
            try:
                c_time = pd.to_datetime(c['created_at'], utc=True)
                if now - c_time <= delta:
                    filtered_complaints.append(c)
            except:
                filtered_complaints.append(c)
        else:
            filtered_complaints.append(c)
    complaints = filtered_complaints


@st.cache_data(ttl=120)
def generate_ai_briefing(complaints_data):
    if not complaints_data:
        return "No data available to generate briefing."
        
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        return "AI Briefing unavailable. Please configure your Groq API Key."
        
    total = len(complaints_data)
    critical = sum(1 for c in complaints_data if c.get("urgency") == "Critical")
    fraud = sum(1 for c in complaints_data if "Fraud" in c.get("category", ""))
    
    try:
        llm = ChatGroq(temperature=0.2, model_name="llama-3.3-70b-versatile")
        prompt = PromptTemplate.from_template(
            "You are a Senior AI Data Analyst for Dacati Bank. Write exactly a 3-sentence Executive Morning Briefing based on these metrics: "
            "Total Complaints: {total}. Critical Alerts: {critical}. Fraud Cases: {fraud}. "
            "Keep the tone strictly professional, analytical, and reassuring."
        )
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"total": total, "critical": critical, "fraud": fraud})
    except Exception as e:
        return f"Unable to generate AI Briefing. Error: {e}"

def generate_excel_report(complaints_data, summary_text):
    """Generates an Excel bytes object with raw data tabs."""
    output = io.BytesIO()
    
    # Create DataFrames
    df_raw = pd.DataFrame(complaints_data)
    
    if not df_raw.empty:
        # Format created_at
        if 'created_at' in df_raw.columns:
            df_raw['created_at'] = pd.to_datetime(df_raw['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
        # Parse user_details
        if 'user_details' in df_raw.columns:
            def parse_details(d_str):
                res = {'Customer Name': 'N/A', 'Account Number': 'N/A', 'Mobile Phone': 'N/A'}
                if isinstance(d_str, str):
                    for part in d_str.split(', '):
                        if ': ' in part:
                            k, v = part.split(': ', 1)
                            if k == 'Name': res['Customer Name'] = v
                            elif k == 'Account': res['Account Number'] = v
                            elif k == 'Mobile': res['Mobile Phone'] = v
                return pd.Series(res)
            
            extracted_details = df_raw['user_details'].apply(parse_details)
            df_raw = pd.concat([df_raw.drop(columns=['user_details']), extracted_details], axis=1)

        # Rename columns for professional look
        df_raw = df_raw.rename(columns={
            'id': 'Reference ID',
            'category': 'Support Portal',
            'urgency': 'Urgency Level',
            'description': 'Complaint Details',
            'status': 'Current Status',
            'action_taken': 'AI Action Taken',
            'advice': 'AI Generated Advice',
            'created_at': 'Timestamp',
            'attachment_path': 'Attachment Link'
        })
        
        # Make attachment links absolute
        if 'Attachment Link' in df_raw.columns:
            df_raw['Attachment Link'] = df_raw['Attachment Link'].apply(
                lambda x: f"{API_URL}{x}" if pd.notna(x) and x else 'N/A'
            )
        
        # Bring Reference ID to the front, timestamp to end
        cols = df_raw.columns.tolist()
        if 'Reference ID' in cols:
            cols.insert(0, cols.pop(cols.index('Reference ID')))
        df_raw = df_raw[cols]
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if not df_raw.empty:
            df_raw.to_excel(writer, sheet_name='Complaints Data', index=False)
            
    return output.getvalue()


# Categorize raw data for charts
categories = {"Fraud Investigation": [], "Account Services": [], "Loan Support": [], "General Support": []}
for c in complaints:
    cat_full = c.get("category", "General Support Portal")
    if "Fraud" in cat_full: cat = "Fraud Investigation"
    elif "Account" in cat_full: cat = "Account Services"
    elif "Loan" in cat_full: cat = "Loan Support"
    else: cat = "General Support"
    categories[cat].append(c)

counts = {k: len(v) for k, v in categories.items()}
labels = list(counts.keys())
values = list(counts.values())
total_complaints = sum(values)

# =========================================================================
# UI RENDERING
# =========================================================================

# Navigation/Header Row
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown("<h1 style='color: #FF6B00; margin-bottom: 0px;'>Dacati Bank</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #A0A0AA; font-size: 16px; margin-top: -10px;'>Intelligent Support operations • <strong>{timeframe}</strong></p>", unsafe_allow_html=True)

# AI Executive Briefing Section

def render_anomaly_alert(complaint_list, portal_name):
    # --- ZERO-DAY CRISIS PREDICTION ENGINE ---
    import collections
    import re
    
    # Common words to ignore (stopwords)
    stopwords = {"and", "the", "to", "a", "i", "my", "is", "for", "in", "of", "it", 
                 "on", "this", "that", "with", "from", "you", "am", "have", "not", 
                 "was", "as", "are", "but", "be", "so", "can", "if", "or", "me", "we",
                 "they", "account", "bank", "please", "help"}
                 
    # Gather all active pending complaint descriptions in THIS specific list
    active_descriptions = [c.get("description", "").lower() for c in complaint_list if "resolve" not in c.get("status", "Pending").lower()]
    
    all_words = []
    for desc in active_descriptions:
        words = re.findall(r'\b[a-z]{3,}\b', desc)
        # Deduplicate words per-complaint so one spammy complaint doesn't trigger it
        unique_words_in_complaint = set([w for w in words if w not in stopwords])
        all_words.extend(list(unique_words_in_complaint))
        
    word_counts = collections.Counter(all_words)
    # Threshold for anomaly is 3 separate complaints mentioning the exact same non-trivial word
    anomalies = [(word, count) for word, count in word_counts.items() if count >= 3]
    
    if anomalies:
        anomalies.sort(key=lambda x: x[1], reverse=True)
        top_anomaly_word = anomalies[0][0]
        top_anomaly_count = anomalies[0][1]
        
        st.markdown(f"""
        <div style='background: #FF3333; padding: 20px; border-radius: 8px; margin-bottom: 2rem; border-left: 6px solid #8B0000; box-shadow: 0 0 20px rgba(255, 51, 51, 0.4); animation: pulse 2s infinite;'>
            <h3 style='margin-top: 0; color: #FFFFFF;'>🚨 {portal_name.upper()} CRISIS DETECTED</h3>
            <p style='color: #FFFFFF; font-size: 16px; margin-bottom: 0;'>
                <strong>Anomaly Engine Alert:</strong> {top_anomaly_count} separate users are currently experiencing active {portal_name} issues containing the key phrase <strong>"{top_anomaly_word.upper()}"</strong>. 
                Immediate investigation recommended.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <style>
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 51, 51, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(255, 51, 51, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 51, 51, 0); }
        }
        </style>
        """, unsafe_allow_html=True)

def render_complaints_table(complaints_list, tab_name):
    search_query = st.text_input("🔍 Search Reference ID", placeholder=("Search " + tab_name + "..."), key="search_" + tab_name)
    
    if not complaints_list:
        st.info("System healthy. No complaints currently logged in this portal.")
        return
        
    filtered_complaints = [c for c in complaints_list if search_query.lower() in c['id'].lower() and c.get("status", "Pending") != "Resolved"]
    
    if not filtered_complaints:
        st.info("System healthy. No pending complaints currently logged in this portal.")
        return
        
    ui_data = []
    for c in reversed(filtered_complaints):
        cat = c.get("category", "General").replace(" Portal", "")
        urgency = c.get("urgency", "Low")
        
        if urgency == "Critical":
            urgency_display = "🚨 CRITICAL"
        elif urgency == "High":
            urgency_display = "⚠️ High"
        else:
            urgency_display = urgency

        ui_data.append({
            "Done": c.get("status", "Pending") == "Resolved",
            "Reference ID": c.get("id"),
            "Portal": cat,
            "Urgency": urgency_display,
            "Action Taken": c.get("action_taken", "None"),
            "Description": c.get("description", ""),
            "Attachment": f"{API_URL}{c['attachment_path']}" if c.get("attachment_path") else None
        })
        
    if ui_data:
        import pandas as pd
        df_log = pd.DataFrame(ui_data)
        
        def highlight_urgency(row):
            u = row.get("Urgency", "")
            if "CRITICAL" in u:
                return ["background-color: rgba(255, 51, 51, 0.15)"] * len(row)
            elif "High" in u:
                return ["background-color: rgba(255, 107, 0, 0.1)"] * len(row)
            elif "Medium" in u:
                return ["background-color: rgba(255, 157, 74, 0.05)"] * len(row)
            else:
                return [""] * len(row)
                
        styled_df = df_log.style.apply(highlight_urgency, axis=1)
        
        editor_key = f"editor_{tab_name}_{len(df_log)}"
        
        edited_df = st.data_editor(
            styled_df,
            hide_index=True,
            use_container_width=True,
            height=400,
            column_config={
                "Done": st.column_config.CheckboxColumn("✅ Resolve", width="small", default=False),
                "Reference ID": st.column_config.TextColumn("Ref ID", width="small", disabled=True),
                "Portal": st.column_config.TextColumn("Department", width="medium", disabled=True),
                "Urgency": st.column_config.TextColumn("Risk", width="small", disabled=True),
                "Action Taken": st.column_config.TextColumn("Auto-Action", width="medium", disabled=True),
                "Description": st.column_config.TextColumn("Description", width="large", disabled=True),
                "Attachment": st.column_config.LinkColumn("Attachment", width="small", display_text="View Image", disabled=True)
            },
            key=editor_key
        )
        
        if editor_key in st.session_state:
            edits = st.session_state[editor_key].get("edited_rows", {})
            if edits:
                for row_idx, changes in edits.items():
                    if "Done" in changes and changes["Done"] == True:
                        ref_id = df_log.iloc[row_idx]["Reference ID"]
                        try:
                            import requests
                            API_URL = "http://localhost:8000"
                            res = requests.patch(f"{API_URL}/complaints/{ref_id}/resolve")
                            if res.status_code == 200:
                                st.cache_data.clear()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error communicating with backend: {e}")

def render_archive_table(complaints_list):
    search_query = st.text_input("🔍 Search Reference ID", placeholder="Search Archive...", key="search_archive")
    
    archive_complaints = [c for c in complaints_list if search_query.lower() in c['id'].lower() and c.get("status", "Pending") == "Resolved"]
    
    if not archive_complaints:
        st.info("The resolution archive is currently empty.")
        return
        
    ui_data = []
    for c in reversed(archive_complaints):
        cat = c.get("category", "General").replace(" Portal", "")
        urgency = c.get("urgency", "Low")
        
        if urgency == "Critical":
            urgency_display = "🚨 CRITICAL"
        elif urgency == "High":
            urgency_display = "⚠️ High"
        else:
            urgency_display = urgency

        ui_data.append({
            "Reference ID": c.get("id"),
            "Portal": cat,
            "Urgency": urgency_display,
            "Action Taken": c.get("action_taken", "None"),
            "Description": c.get("description", ""),
            "Attachment": f"{API_URL}{c['attachment_path']}" if c.get("attachment_path") else None
        })
        
    import pandas as pd
    df_log = pd.DataFrame(ui_data)
    
    def highlight_urgency(row):
        u = row.get("Urgency", "")
        if "CRITICAL" in u:
            return ["background-color: rgba(255, 51, 51, 0.15)"] * len(row)
        elif "High" in u:
            return ["background-color: rgba(255, 107, 0, 0.1)"] * len(row)
        elif "Medium" in u:
            return ["background-color: rgba(255, 157, 74, 0.05)"] * len(row)
        else:
            return [""] * len(row)
            
    styled_df = df_log.style.apply(highlight_urgency, axis=1)

    st.dataframe(
        styled_df,
        hide_index=True,
        use_container_width=True,
        height=400,
        column_config={
            "Reference ID": st.column_config.TextColumn("Ref ID", width="small"),
            "Portal": st.column_config.TextColumn("Department", width="medium"),
            "Urgency": st.column_config.TextColumn("Risk", width="small"),
            "Action Taken": st.column_config.TextColumn("Auto-Action", width="medium"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Attachment": st.column_config.LinkColumn("Attachment", width="small", display_text="View Image")
        }
    )

# --- PORTAL TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌐 Global Overview", 
    "🚨 Fraud Investigation", 
    "💳 Account Services", 
    "🏦 Loan Support", 
    "📞 General Support",
    "🗄️ Resolution Archive"
])

with tab1:
    ai_briefing_text = generate_ai_briefing(complaints)

    st.markdown("""
    <div style='background: linear-gradient(145deg, #1d1d23 0%, #16161a 100%); border-left: 4px solid #FF6B00; padding: 20px; border-radius: 8px; margin-bottom: 2rem;'>
        <h4 style='margin-top: 0; color: #EAEAEA;'>🤖 AI Morning Briefing</h4>
        <p style='color: #B0B0Ba; font-size: 15px; margin-bottom: 0;'>{}</p>
    </div>
    """.format(ai_briefing_text), unsafe_allow_html=True)

    with head_col2:
        st.markdown("<br/>", unsafe_allow_html=True)
        if total_complaints > 0:
            excel_data = generate_excel_report(complaints, ai_briefing_text)
            st.download_button(
                label="📥 Download Excel Report",
                data=excel_data,
                file_name="dacati_automated_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # --- KPI ROW ---
    st.markdown("<br/>", unsafe_allow_html=True)

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

    critical_count = sum(1 for c in complaints if c.get("urgency") == "Critical")
    ai_action_count = sum(1 for c in complaints if c.get("action_taken") is not None and str(c.get("action_taken")).lower() != "none")

    with kpi_col1:
        st.metric("Total Active Cases", total_complaints)
    
    with kpi_col2:
        # Use delta_color='inverse' to make downward changes green/normal changes red based on SLA perspective, 
        # but the image simply shows simple text.
        st.metric("Critical SLA Threats", critical_count, delta="- Action Required" if critical_count > 0 else "All Clear", delta_color="inverse")
    
    with kpi_col3:
        st.metric("AI Auto-Actions", ai_action_count)

    st.markdown("<br/>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Risk Matrix by Portal")
        if total_complaints == 0:
            st.info("No data available")
        else:
            URGENCY_COLORS = {
                "Critical": "#FF3333",  # Deep Red
                "High": "#FF6B00",      # Orange 
                "Medium": "#FF9D4A",    # Amber
                "Low": "#66FFB2"        # Mint Green
            }
        
            matrix_data = {u: [] for u in URGENCY_COLORS.keys()}
            for label in labels:
                cat_list = categories[label]
                counts_by_urgency = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
                for c in cat_list:
                    u = c.get("urgency", "Low")
                    if u in counts_by_urgency:
                        counts_by_urgency[u] += 1
                for u in counts_by_urgency:
                    matrix_data[u].append(counts_by_urgency[u])
                
            fig_matrix = go.Figure()
            for u, color_hex in URGENCY_COLORS.items():
                fig_matrix.add_trace(go.Bar(
                    y=labels,
                    x=matrix_data[u],
                    name=u,
                    orientation='h',
                    marker=dict(color=color_hex, line=dict(width=0))
                ))

            fig_matrix.update_layout(
                barmode='stack',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#2A2A35', tickfont=dict(color='#8C92A4', size=10)),
                yaxis=dict(showgrid=False, tickfont=dict(color='#EAEAEA', size=11)),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#A0A0AA', size=10)),
                height=320,
                margin=dict(t=30, b=10, l=10, r=20)
            )
            st.plotly_chart(fig_matrix, use_container_width=True)


    with col2:
        st.markdown("### Volume Over Time")
        if total_complaints > 0:
            dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
            import numpy as np
            np.random.seed(42)
            fig_line = go.Figure()
        
            for label in labels:
                x = np.linspace(0, 10, 30)
                mock_data = np.abs(np.sin(x + np.random.rand() * 5)) * counts[label] * 5 + np.random.rand(30) * 2
            
                # Key feature: The glowing orange fill='tozeroy' aesthetic
                fig_line.add_trace(go.Scatter(
                    x=dates, 
                    y=mock_data, 
                    mode='lines',
                    fill='tozeroy' if label == "Account Services" or label == "Fraud Investigation" else 'none', # Only fill top lines
                    line=dict(color=COLORS[label], width=2, shape='spline'),
                    name=label
                ))

            fig_line.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#2A2A35', gridwidth=1, showline=False, tickfont=dict(color='#8C92A4', size=10)),
                yaxis=dict(showgrid=True, gridcolor='#2A2A35', gridwidth=1, showline=False, tickfont=dict(color='#8C92A4', size=10)),
                showlegend=False,
                height=320,
                margin=dict(t=10, b=10, l=0, r=20)
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No data available")

    # --- LAYOUT ROW 2 ---
    col3, col4 = st.columns([1, 1])

    with col3:
        st.markdown("### Distribution")
        if total_complaints > 0:
            fig_donut = px.pie(
                names=labels, values=values, hole=0.7, color=labels, color_discrete_map=COLORS
            )
            fig_donut.update_traces(textposition='outside', textinfo='percent', marker=dict(line=dict(color='#16161a', width=3)))
            fig_donut.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, height=280,
                margin=dict(t=0, b=0, l=0, r=0),
                annotations=[dict(text=f"<span style='color:#FF6B00; font-size:54px; font-weight:bold;'>{total_complaints}</span><span style='color:#A0A0AA;'></span>", x=0.5, y=0.5, showarrow=False)]
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    with col4:
        st.markdown("### Resolution Queue Tracker")
        if total_complaints > 0:
            status_counts = {"Pending": 0, "Resolved": 0}
            for c in complaints:
                s_val = c.get("status", "Pending")
                # Usually status might be varying cases, so normalize
                if "resolve" in s_val.lower():
                    status_counts["Resolved"] += 1
                else:
                    status_counts["Pending"] += 1

            fig_status = go.Figure(data=[
                go.Bar(
                    x=list(status_counts.keys()), 
                    y=list(status_counts.values()), 
                    marker_color=["#FF6B00", "#66FFB2"], # Pending (Orange), Resolved (Mint Green)
                    width=0.4, 
                    marker_line_width=0,
                    text=list(status_counts.values()),
                    textposition='auto',
                    textfont=dict(color="white", size=14, weight="bold")
                )
            ])
            fig_status.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, tickfont=dict(color='#EAEAEA', size=14)),
                yaxis=dict(showgrid=True, gridcolor='#2A2A35', tickfont=dict(color='#8C92A4', size=10)),
                height=280, margin=dict(t=10, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_status, use_container_width=True)

    # --- RECENT COMPLAINTS LIST ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("### Active Complaints Register")
    render_complaints_table(complaints, 'Global')

with tab2:
    st.markdown("### Fraud Investigation Queue")
    fraud_data = [c for c in complaints if "Fraud" in c.get('category', '')]
    render_anomaly_alert(fraud_data, "Fraud")
    render_complaints_table(fraud_data, 'Fraud')

with tab3:
    st.markdown("### Account Services Queue")
    account_data = [c for c in complaints if "Account" in c.get('category', '')]
    render_anomaly_alert(account_data, "Account")
    render_complaints_table(account_data, 'Account')

with tab4:
    st.markdown("### Loan Support Queue")
    loan_data = [c for c in complaints if "Loan" in c.get('category', '')]
    render_anomaly_alert(loan_data, "Loan")
    render_complaints_table(loan_data, 'Loan')

with tab5:
    st.markdown("### General Support Queue")
    general_data = [c for c in complaints if "General" in c.get('category', '')]
    render_anomaly_alert(general_data, "General Support")
    render_complaints_table(general_data, 'General')

with tab6:
    st.markdown("### Historical Resolution Ledger")
    st.markdown("<p style='color: #8C92A4;'>A read-only, permanent audit log of all successfully closed security incidents and complaints.</p>", unsafe_allow_html=True)
    render_archive_table(complaints)
