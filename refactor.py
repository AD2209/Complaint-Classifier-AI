import re

with open("frontend/pages/dashboard.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find where UI Rendering starts (Line 221 - AI Executive Briefing Section)
start_idx = 0
for i, line in enumerate(lines):
    if "ai_briefing_text = generate_ai_briefing(complaints)" in line:
        start_idx = i
        break

# The helper function
helper_func = """
def render_complaints_table(complaints_list, tab_name):
    search_query = st.text_input("🔍 Search Reference ID", placeholder=("Search " + tab_name + "..."), key="search_" + tab_name)
    
    if not complaints_list:
        st.info("System healthy. No complaints currently logged in this portal.")
        return
        
    filtered_complaints = [c for c in complaints_list if search_query.lower() in c['id'].lower()]
    
    if not filtered_complaints:
        st.warning("No matches found.")
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
            "Reference ID": c.get("id"),
            "Portal": cat,
            "Urgency": urgency_display,
            "Action Taken": c.get("action_taken", "None"),
            "Description": c.get("description", "")
        })
        
    if ui_data:
        import pandas as pd
        df_log = pd.DataFrame(ui_data)
        st.dataframe(
            df_log,
            hide_index=True,
            use_container_width=True,
            height=400,
            column_config={
                "Reference ID": st.column_config.TextColumn("Ref ID", width="small"),
                "Portal": st.column_config.TextColumn("Department", width="medium"),
                "Urgency": st.column_config.TextColumn("Risk", width="small"),
                "Action Taken": st.column_config.TextColumn("Auto-Action", width="medium"),
                "Description": st.column_config.TextColumn("Description", width="large")
            }
        )

# --- PORTAL TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌐 Global Overview", 
    "🚨 Fraud Investigation", 
    "💳 Account Services", 
    "🏦 Loan Support", 
    "📞 General Support"
])

with tab1:
"""

# Extract the rest of the file
rest_of_file = lines[start_idx:]

# We need to indent the rest of the file by 4 spaces
indented_rest = []
for line in rest_of_file:
    # Remove the old complaints list rendering section entirely after 'st.markdown("### Active Complaints Register")'
    indented_rest.append("    " + line if line.strip() else line)

# Let's find where the old complaints list starts
cut_idx = -1
for i, line in enumerate(indented_rest):
    if "st.markdown(\"### Active Complaints Register\")" in line:
        cut_idx = i
        break

if cut_idx != -1:
    # Keep the header, add call to helper function, and discard the rest.
    indented_rest = indented_rest[:cut_idx+1]
    indented_rest.append("    render_complaints_table(complaints, 'Global')\n")
    
# Now add the other tabs
other_tabs = """
with tab2:
    st.markdown("### Fraud Investigation Queue")
    fraud_data = [c for c in complaints if "Fraud" in c.get('category', '')]
    render_complaints_table(fraud_data, 'Fraud')

with tab3:
    st.markdown("### Account Services Queue")
    account_data = [c for c in complaints if "Account" in c.get('category', '')]
    render_complaints_table(account_data, 'Account')

with tab4:
    st.markdown("### Loan Support Queue")
    loan_data = [c for c in complaints if "Loan" in c.get('category', '')]
    render_complaints_table(loan_data, 'Loan')

with tab5:
    st.markdown("### General Support Queue")
    general_data = [c for c in complaints if "General" in c.get('category', '')]
    render_complaints_table(general_data, 'General')
"""

new_content = lines[:start_idx] + [helper_func] + indented_rest + [other_tabs]

with open("frontend/pages/dashboard.py", "w", encoding="utf-8") as f:
    f.writelines(new_content)

print("Refactored successfully")
