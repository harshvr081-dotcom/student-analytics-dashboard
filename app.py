import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import random
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
# 2. DATABASE CONNECTION
# ==========================================
# ==========================================
# 2. DATABASE CONNECTION (NEON CLOUD)
# ==========================================
# Use your specific Neon connection string here
# ==========================================
# 2. DATABASE CONNECTION (NEON CLOUD)
# ==========================================
# I've cleaned your string to make it compatible with Streamlit's environment
DB_URL = "postgresql://neondb_owner:npg_TGkAYws63JZC@ep-autumn-bread-a1r9kd00.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# Create the engine with 'pool_pre_ping' to handle connection drops
engine = create_engine(
    DB_URL, 
    pool_pre_ping=True,
    connect_args={'connect_timeout': 10}
)

@st.cache_data(ttl=2)
def load_data():
    return pd.read_sql("SELECT * FROM student_performance", engine)

df = load_data()

# --- MAGIC FIX: ADD PASSWORDS TO DATABASE ---
if 'Password' not in df.columns:
    df['Password'] = 'student123'  # Default password for all existing students
    df.to_sql('student_performance', engine, if_exists='replace', index=False)
    if os.path.exists('data/cleaned_students.csv'):
        df.to_csv('data/cleaned_students.csv', index=False)
    st.rerun()

# --- HELPER: GET LATEST SEMESTER ONLY FOR ADMIN DASHBOARD ---
df_sorted = df.sort_values(by=['Roll_No', 'Semester'])
current_df = df_sorted.drop_duplicates(subset=['Roll_No'], keep='last')

# ==========================================
# 3. SESSION STATE (Role Tracking)
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
# 4. ADMIN PORTAL FUNCTION
# ==========================================
def admin_portal():
    st.sidebar.title("👨‍🏫 ADMIN PANEL")
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Student Profile", "Add Marks", "View Reports", "Analytics"])
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", type="primary"):
        logout()

    if menu == "Dashboard":
        st.title("Computer Engineering Dashboard")
        st.markdown("*(Displaying Latest Semester Data)*")
        total_students = len(current_df)
        avg_marks = round(current_df['Average_Score'].mean(), 1)
        passed_students = len(current_df[current_df['Is_At_Risk'] == 'No'])
        pass_percentage = round((passed_students / total_students) * 100, 1) if total_students > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1: st.markdown(f'<div class="metric-card blue-card"><h4>👤 Total Students</h4><h2>{total_students:,}</h2></div>', unsafe_allow_html=True)
        with col2: st.markdown(f'<div class="metric-card green-card"><h4>🎓 Current Avg Marks</h4><h2>{avg_marks}%</h2></div>', unsafe_allow_html=True)
        with col3: st.markdown(f'<div class="metric-card orange-card"><h4>✔️ Pass Percentage</h4><h2>{pass_percentage}%</h2></div>', unsafe_allow_html=True)

        st.markdown("### Latest Student Performance")
        display_df = current_df[['Roll_No', 'Name', 'Class_Div', 'Semester', 'Average_Score', 'Is_At_Risk']].copy()
        display_df.rename(columns={'Roll_No': 'Roll No', 'Class_Div': 'Class', 'Average_Score': 'Overall %', 'Is_At_Risk': 'Status'}, inplace=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    elif menu == "Student Profile":
        st.title("Individual Student Profile & Trends")
        col_filter, col_search = st.columns([1, 2])
        with col_filter: selected_div = st.selectbox("📂 Filter by Class", ["All Classes"] + sorted(list(current_df['Class_Div'].unique())))
        filtered_students = current_df if selected_div == "All Classes" else current_df[current_df['Class_Div'] == selected_div]
        with col_search:
            student_list = filtered_students['Name'] + " (Roll No: " + filtered_students['Roll_No'].astype(str) + ")"
            selected_student_str = st.selectbox("🔍 Search for a Student", ["Select a Student..."] + list(student_list))
        st.markdown("---")

        if selected_student_str != "Select a Student...":
            roll_no = int(selected_student_str.split("Roll No: ")[1].replace(")", ""))
            student_history = df[df['Roll_No'] == roll_no].sort_values(by='Semester')
            latest_data = student_history.iloc[-1]
            current_sem = latest_data['Semester']
            subs = SEM_SUBJECTS.get(current_sem, ["Subject 1", "Subject 2", "Subject 3"])
            
            def create_pdf(latest_data, history_data, subs):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt=f"ACADEMIC REPORT: {latest_data['Name']}", ln=True, align='C')
                pdf.ln(5)
                pdf.set_font("Arial", '', 12)
                pdf.cell(100, 10, txt=f"Roll Number: {latest_data['Roll_No']}", ln=True)
                pdf.cell(100, 10, txt=f"Class: {latest_data['Class_Div']}", ln=True)
                pdf.cell(100, 10, txt=f"Current Semester: {latest_data['Semester']}", ln=True)
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, txt="Current Subject Performance (Out of 100)", ln=True)
                pdf.set_font("Arial", '', 12)
                pdf.cell(100, 10, txt=f"{subs[0]}: {latest_data['Sub1_Marks']}")
                pdf.cell(100, 10, txt=f"{subs[1]}: {latest_data['Sub2_Marks']}", ln=True)
                pdf.cell(100, 10, txt=f"{subs[2]}: {latest_data['Sub3_Marks']}", ln=True)
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(200, 10, txt="Historical Semester Averages:", ln=True)
                pdf.set_font("Arial", '', 11)
                for _, row in history_data.iterrows():
                    pdf.cell(200, 8, txt=f"{row['Semester']}: {row['Average_Score']}%", ln=True)
                return pdf.output(dest='S').encode('latin-1')

            col_title, col_btn = st.columns([3, 1])
            with col_title: st.markdown(f"### Profile: {latest_data['Name']}")
            with col_btn:
                pdf_bytes = create_pdf(latest_data, student_history, subs)
                st.download_button("📄 Download Full Report", data=pdf_bytes, file_name=f"{latest_data['Name']}_Report.pdf", mime="application/pdf", type="primary")
                
            st.write(f"**Class:** {latest_data['Class_Div']} | **Current Sem:** {latest_data['Semester']}")
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{current_sem} Average", f"{latest_data['Average_Score']}%")
            if len(student_history) > 1:
                prev_score = student_history.iloc[-2]['Average_Score']
                trend = round(latest_data['Average_Score'] - prev_score, 1)
                c2.metric("Growth vs Last Sem", f"{trend}%", delta=trend)
            else: c2.metric("Growth vs Last Sem", "N/A")
            c3.metric("Current Status", "⚠️ At Risk" if latest_data['Is_At_Risk'] == 'Yes' else "✅ Clear")
            
            st.markdown(f"#### {current_sem} Subject-Wise Marks")
            marks_data = pd.DataFrame({"Subject": subs, "Marks": [float(latest_data['Sub1_Marks']), float(latest_data['Sub2_Marks']), float(latest_data['Sub3_Marks'])]})
            st.bar_chart(marks_data, x="Subject", y="Marks", color="#4a86e8")
            
            st.markdown("#### Academic Progression")
            st.line_chart(student_history.set_index('Semester')['Average_Score'], color="#4a86e8")

            st.markdown("#### Detailed Semester-Wise Subjects & Marks")
            history_display = []
            for _, row in student_history.iterrows():
                sem = row['Semester']
                row_subs = SEM_SUBJECTS.get(sem, ["Subject 1", "Subject 2", "Subject 3"])
                history_display.append({
                    "Semester": sem,
                    "Subject 1": f"{row_subs[0]} ({row['Sub1_Marks']})",
                    "Subject 2": f"{row_subs[1]} ({row['Sub2_Marks']})",
                    "Subject 3": f"{row_subs[2]} ({row['Sub3_Marks']})",
                    "Average (%)": row['Average_Score'],
                    "Status": "⚠️ At Risk" if row['Is_At_Risk'] == 'Yes' else "✅ Clear"
                })
            st.dataframe(pd.DataFrame(history_display).set_index('Semester'), use_container_width=True)

    elif menu == "Add Marks":
        st.title("Add Student Engineering Marks")
        selected_semester = st.selectbox("Select Semester for Entry", list(SEM_SUBJECTS.keys()), index=4)
        current_subs = SEM_SUBJECTS[selected_semester]
        
        with st.form("student_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Full Name")
                roll_no = st.number_input("Roll Number", min_value=100000, value=101500)
                class_div = st.selectbox("Class Division", ["TE-A", "TE-B", "TE-C"])
            with c2:
                sex = st.selectbox("Gender", ["F", "M"])
                age = st.number_input("Age", min_value=18, max_value=25, value=20)
                # Ensure new students get a default password (they can theoretically change it later in a real app)
                password = st.text_input("Temporary Password", value="student123")
                
            st.subheader(f"{selected_semester} Marks Entry")
            col1, col2, col3 = st.columns(3)
            with col1: sub1_marks = st.number_input(current_subs[0], min_value=0, max_value=100, value=40)
            with col2: sub2_marks = st.number_input(current_subs[1], min_value=0, max_value=100, value=40)
            with col3: sub3_marks = st.number_input(current_subs[2], min_value=0, max_value=100, value=40)
            absences = st.number_input("Total Absences", min_value=0, max_value=100, value=0)
            submitted = st.form_submit_button("Save Semester Data", type="primary")

            if submitted and name:
                total_score = sub1_marks + sub2_marks + sub3_marks
                average_score = round(total_score / 3, 2)
                is_at_risk = 'Yes' if (sub1_marks < 40 or sub2_marks < 40 or sub3_marks < 40 or absences > 15) else 'No'
                new_student = pd.DataFrame([{
                    'Roll_No': roll_no, 'Name': name, 'Class_Div': class_div, 'Semester': selected_semester, 'sex': sex, 'age': age, 
                    'failures': 0, 'absences': absences, 'Sub1_Marks': sub1_marks, 'Sub2_Marks': sub2_marks, 'Sub3_Marks': sub3_marks, 
                    'Total_Score': total_score, 'Average_Score': average_score, 'Is_At_Risk': is_at_risk, 'Password': password
                }])
                new_student.to_sql('student_performance', engine, if_exists='append', index=False)
                st.success(f"Success! Marks for {name} ({selected_semester}) saved.")

    elif menu == "View Reports":
        st.title("Download Performance Reports")
        col_class, col_sort = st.columns(2)
        with col_class: report_class = st.selectbox("Select Class Filter", ["All Classes", "TE-A", "TE-B", "TE-C"])
        with col_sort: sort_order = st.selectbox("Sort by Overall Marks", ["Highest to Lowest", "Lowest to Highest", "Roll Number"])
        
        report_df = current_df.copy() if report_class == "All Classes" else current_df[current_df['Class_Div'] == report_class]
        if sort_order == "Highest to Lowest": report_df = report_df.sort_values(by='Average_Score', ascending=False)
        elif sort_order == "Lowest to Highest": report_df = report_df.sort_values(by='Average_Score', ascending=True)
        else: report_df = report_df.sort_values(by='Roll_No', ascending=True)
            
        csv_data = report_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Filtered & Sorted Report (CSV)", data=csv_data, file_name=f"Ranked_Report_{report_class}.csv", mime="text/csv", type="primary")
        st.dataframe(report_df[['Roll_No', 'Name', 'Class_Div', 'Semester', 'Average_Score', 'Is_At_Risk']], use_container_width=True, hide_index=True)

    elif menu == "Analytics":
        st.title("Analytics & Insights")
        c1, c2 = st.columns(2)
        with c1: st.markdown("### Average Score by Class Division"); st.bar_chart(current_df.groupby('Class_Div')['Average_Score'].mean(), color="#43a047")
        with c2: st.markdown("### Average Score by Gender"); st.bar_chart(current_df.groupby('sex')['Average_Score'].mean(), color="#f57c00")


# ==========================================
# 5. STUDENT PORTAL FUNCTION
# ==========================================
def student_portal():
    student_history = pd.read_sql(f"SELECT * FROM student_performance WHERE \"Roll_No\" = {st.session_state.roll_no} ORDER BY \"Semester\"", engine)
    latest_data = student_history.iloc[-1]
    current_sem = latest_data['Semester']
    subs = SEM_SUBJECTS.get(current_sem, ["Subject 1", "Subject 2", "Subject 3"])

    col_head, col_out = st.columns([5, 1])
    with col_head:
        st.title(f"🎓 Welcome, {latest_data['Name']}!")
        st.write(f"**Class:** {latest_data['Class_Div']} | **Roll No:** {latest_data['Roll_No']}")
    with col_out:
        st.write("")
        if st.button("Logout", type="primary", use_container_width=True): logout()

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="metric-card blue-card center"><h4>{current_sem} Average</h4><h2>{latest_data["Average_Score"]}%</h2></div>', unsafe_allow_html=True)
    if len(student_history) > 1:
        trend = round(latest_data['Average_Score'] - student_history.iloc[-2]['Average_Score'], 1)
        trend_text = f"📈 +{trend}% Improvement" if trend > 0 else f"📉 {trend}% Decline"
    else: trend_text = "Initial Data"
    with c2: st.markdown(f'<div class="metric-card green-card center"><h4>Progress vs Last Sem</h4><h2>{trend_text}</h2></div>', unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown(f"#### {current_sem} Subject Scores")
        st.bar_chart(pd.DataFrame({"Subject": subs, "Marks": [float(latest_data['Sub1_Marks']), float(latest_data['Sub2_Marks']), float(latest_data['Sub3_Marks'])]}), x="Subject", y="Marks", color="#4a86e8")
    with col_chart2:
        st.markdown("#### Overall Progression")
        st.line_chart(student_history.set_index('Semester')['Average_Score'], color="#43a047")

    st.markdown("---")
    st.markdown("#### Detailed Semester-Wise Subjects & Marks")
    history_display = []
    for _, row in student_history.iterrows():
        sem = row['Semester']
        row_subs = SEM_SUBJECTS.get(sem, ["Subject 1", "Subject 2", "Subject 3"])
        history_display.append({
            "Semester": sem,
            "Subject 1": f"{row_subs[0]} ({row['Sub1_Marks']})",
            "Subject 2": f"{row_subs[1]} ({row['Sub2_Marks']})",
            "Subject 3": f"{row_subs[2]} ({row['Sub3_Marks']})",
            "Average (%)": row['Average_Score'],
            "Status": "⚠️ At Risk" if row['Is_At_Risk'] == 'Yes' else "✅ Clear"
        })
    st.dataframe(pd.DataFrame(history_display).set_index('Semester'), use_container_width=True)

    st.markdown("---")
    st.markdown("### Official Documents")
    
    def create_pdf(latest_data, history_data, subs):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=f"STUDENT ACADEMIC RECORD", ln=True, align='C')
        pdf.ln(5)
        pdf.set_font("Arial", '', 12)
        pdf.cell(100, 10, txt=f"Name: {latest_data['Name']}", ln=True)
        pdf.cell(100, 10, txt=f"Roll Number: {latest_data['Roll_No']}", ln=True)
        pdf.cell(100, 10, txt=f"Class: {latest_data['Class_Div']}", ln=True)
        pdf.cell(100, 10, txt=f"Current Semester: {latest_data['Semester']}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="Historical Semester Averages:", ln=True)
        pdf.set_font("Arial", '', 11)
        for _, row in history_data.iterrows():
            pdf.cell(200, 8, txt=f"{row['Semester']}: {row['Average_Score']}%", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    pdf_bytes = create_pdf(latest_data, student_history, subs)
    st.download_button("📄 Download Complete Academic Record (PDF)", data=pdf_bytes, file_name=f"{latest_data['Name']}_Record.pdf", mime="application/pdf", type="primary")

# ==========================================
# 6. MAIN ROUTING & LOGIN SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🎓 University Academic Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Select your portal to continue</p>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        login_type = st.radio("Login As:", ["Student", "Admin"], horizontal=True)
        st.write("")
        
        if login_type == "Admin":
            with st.form("admin_login"):
                st.markdown("### Admin Access")
                user = st.text_input("Username")
                pwd = st.text_input("Password", type="password")
                if st.form_submit_button("Login to Dashboard", use_container_width=True):
                    if user == "admin" and pwd == "admin": 
                        st.session_state.logged_in = True
                        st.session_state.role = "Admin"
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Try username: admin, password: admin")
                        
        elif login_type == "Student":
            with st.form("student_login"):
                st.markdown("### Student Access")
                roll_input = st.number_input("Enter Roll Number", min_value=100000, value=101201, step=1)
                pwd_input = st.text_input("Password", type="password", placeholder="Enter your password")
                if st.form_submit_button("Access My Record", use_container_width=True):
                    # SECURE DB CHECK: Validates both Roll Number and Password
                    check_query = f"SELECT COUNT(*) FROM student_performance WHERE \"Roll_No\" = {roll_input} AND \"Password\" = '{pwd_input}'"
                    if pd.read_sql(check_query, engine).iloc[0, 0] > 0:
                        st.session_state.logged_in = True
                        st.session_state.role = "Student"
                        st.session_state.roll_no = roll_input
                        st.rerun()
                    else:
                        st.error("Invalid Roll Number or Password. Please try again.")

elif st.session_state.role == "Admin":
    admin_portal()

elif st.session_state.role == "Student":
    student_portal()