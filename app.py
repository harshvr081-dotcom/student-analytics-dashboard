import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
from fpdf import FPDF

# ==========================================
# 1. PAGE SETUP & CSS
# ==========================================
st.set_page_config(page_title="Academic Portal", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .metric-card { border-radius: 8px; padding: 20px; color: white; text-align: left; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .metric-card.center { text-align: center; }
    .metric-card h4 { margin: 0; font-size: 16px; font-weight: normal; opacity: 0.9; }
    .metric-card h2 { margin: 10px 0 0 0; font-size: 32px; }
    .blue-card { background-color: #4a86e8; }
    .green-card { background-color: #43a047; }
    .orange-card { background-color: #f57c00; }
</style>
""", unsafe_allow_html=True)

# --- SPPU ENGINEERING SUBJECT MAPPING ---
SEM_SUBJECTS = {
    "Semester 1": ["Eng Math-I", "Physics", "Basic Elect"],
    "Semester 2": ["Eng Math-II", "Chemistry", "Prog & Prob Solving"],
    "Semester 3": ["Data Structures", "OOP", "Digital Electronics"],
    "Semester 4": ["Comp Networks", "Software Engg", "Microprocessor"],
    "Semester 5": ["DBMS", "TOC", "SPOS"],
    "Semester 6": ["Data Science", "Web Technology", "AI"],
    "Semester 7": ["Machine Learning", "Cyber Security", "Cloud Comp"],
    "Semester 8": ["Deep Learning", "Human Comp Interact", "DevOps"]
}

# ==========================================
# 2. DATABASE CONNECTION (NEON CLOUD)
# ==========================================
# PASTE YOUR NEON STRING BELOW
DB_URL = "postgresql://neondb_owner:npg_TGkAYws63JZC@ep-autumn-bread-a1r9kd00.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(DB_URL, pool_pre_ping=True)

# --- SELF-HEALING: AUTO-CREATE TABLE ---
try:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS student_performance (
                "Roll_No" INTEGER,
                "Name" TEXT,
                "Class_Div" TEXT,
                "Semester" TEXT,
                "sex" TEXT,
                "age" INTEGER,
                "failures" INTEGER,
                "absences" INTEGER,
                "Sub1_Marks" FLOAT,
                "Sub2_Marks" FLOAT,
                "Sub3_Marks" FLOAT,
                "Total_Score" FLOAT,
                "Average_Score" FLOAT,
                "Is_At_Risk" TEXT,
                "Password" TEXT
            );
        """))
        conn.commit()
except Exception as e:
    st.error(f"Database Setup Error: {e}")

@st.cache_data(ttl=2)
def load_data():
    try:
        return pd.read_sql("SELECT * FROM student_performance", engine)
    except:
        return pd.DataFrame()

df = load_data()

# --- HELPER: GET LATEST DATA ---
if not df.empty:
    df_sorted = df.sort_values(by=['Roll_No', 'Semester'])
    current_df = df_sorted.drop_duplicates(subset=['Roll_No'], keep='last')
else:
    current_df = pd.DataFrame()

# ==========================================
# 3. SESSION STATE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.roll_no = None

def logout():
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.roll_no = None
    st.rerun()

# ==========================================
# 4. ADMIN PORTAL
# ==========================================
def admin_portal():
    st.sidebar.title("👨‍🏫 ADMIN PANEL")
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Student Profile", "Add Marks", "View Reports"])
    if st.sidebar.button("Logout", type="primary"):
        logout()

    if df.empty and menu != "Add Marks":
        st.warning("Database is empty. Please go to 'Add Marks' to insert your first record.")
        return

    if menu == "Dashboard":
        st.title("Academic Overview")
        total = len(current_df)
        avg = round(current_df['Average_Score'].mean(), 1) if not current_df.empty else 0
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="metric-card blue-card"><h4>Total Students</h4><h2>{total}</h2></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-card green-card"><h4>Avg Score</h4><h2>{avg}%</h2></div>', unsafe_allow_html=True)
        st.dataframe(current_df, use_container_width=True)

    elif menu == "Add Marks":
        st.title("Entry Form")
        with st.form("entry"):
            name = st.text_input("Name")
            roll = st.number_input("Roll No", min_value=100000)
            sem = st.selectbox("Semester", list(SEM_SUBJECTS.keys()))
            pwd = st.text_input("Set Password", value="student123")
            s1 = st.number_input("Subject 1", 0, 100)
            s2 = st.number_input("Subject 2", 0, 100)
            s3 = st.number_input("Subject 3", 0, 100)
            if st.form_submit_button("Save"):
                avg_val = round((s1+s2+s3)/3, 2)
                risk = "Yes" if avg_val < 40 else "No"
                new_row = pd.DataFrame([{
                    "Roll_No": roll, "Name": name, "Class_Div": "TE-A", "Semester": sem,
                    "Sub1_Marks": s1, "Sub2_Marks": s2, "Sub3_Marks": s3,
                    "Average_Score": avg_val, "Is_At_Risk": risk, "Password": pwd
                }])
                new_row.to_sql('student_performance', engine, if_exists='append', index=False)
                st.success("Data Saved!")
                st.rerun()

# ==========================================
# 5. STUDENT PORTAL
# ==========================================
def student_portal():
    user_data = df[df['Roll_No'] == st.session_state.roll_no].sort_values(by='Semester')
    latest = user_data.iloc[-1]
    
    st.title(f"Welcome, {latest['Name']}")
    if st.button("Logout"): logout()
    
    st.metric("Latest Average", f"{latest['Average_Score']}%")
    st.write("### Full Performance History")
    st.dataframe(user_data[['Semester', 'Average_Score', 'Is_At_Risk']], use_container_width=True)

# ==========================================
# 6. LOGIN ROUTING
# ==========================================
if not st.session_state.logged_in:
    st.title("🎓 University Portal")
    choice = st.radio("Login As", ["Student", "Admin"])
    
    with st.form("login"):
        if choice == "Admin":
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin" and p == "admin":
                    st.session_state.logged_in, st.session_state.role = True, "Admin"
                    st.rerun()
        else:
            r = st.number_input("Roll No", min_value=100000)
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                match = df[(df['Roll_No'] == r) & (df['Password'] == p)]
                if not match.empty:
                    st.session_state.logged_in, st.session_state.role, st.session_state.roll_no = True, "Student", r
                    st.rerun()
                else: st.error("Invalid Credentials")
elif st.session_state.role == "Admin": admin_portal()
else: student_portal()