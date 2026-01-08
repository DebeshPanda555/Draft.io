"""
Draft.io - Main Application
"""
import time
import io
import json
import base64
import traceback
import requests
import pandas as pd
import datetime
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from PIL import Image
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from streamlit_lottie import st_lottie

from jobs.job_search import render_job_search
from feedback.feedback import FeedbackManager
from dashboard.dashboard import DashboardManager

from ui_components import (
    apply_modern_styles,
    hero_section,
    feature_card,
    about_section,
    page_header,
    render_analytics_section,
    render_activity_section,
    render_suggestions_section
)

from config.job_roles import JOB_ROLES
from config.courses import (
    COURSES_BY_CATEGORY,
    RESUME_VIDEOS,
    INTERVIEW_VIDEOS,
    get_courses_for_role,
    get_category_for_role
)

from config.database import (
    get_database_connection,
    save_resume_data,
    save_analysis_data,
    init_database,
    verify_admin,
    log_admin_action,
    save_ai_analysis_data,
    get_ai_analysis_stats,
    reset_ai_analysis_stats,
    get_detailed_ai_analysis_stats
)

from utils.resume_analyzer import ResumeAnalyzer
from utils.ai_resume_analyzer import AIResumeAnalyzer
from utils.resume_builder import ResumeBuilder


# Page config
st.set_page_config(
    page_title="Draft.io",
    page_icon="📝",
    layout="wide"
)


class ResumeApp:

    def __init__(self):

        if 'form_data' not in st.session_state:
            st.session_state.form_data = {
                'personal_info': {
                    'full_name': '',
                    'email': '',
                    'phone': '',
                    'location': '',
                    'linkedin': '',
                    'portfolio': ''
                },
                'summary': '',
                'experiences': [],
                'education': [],
                'projects': [],
                'skills_categories': {
                    'technical': [],
                    'soft': [],
                    'languages': [],
                    'tools': []
                }
            }

        if 'page' not in st.session_state:
            st.session_state.page = 'home'

        if 'is_admin' not in st.session_state:
            st.session_state.is_admin = False

        self.pages = {
            "🏠 HOME": self.render_home,
            "🔍 RESUME ANALYZER": self.render_analyzer,
            "📝 RESUME BUILDER": self.render_builder,
            "📊 DASHBOARD": self.render_dashboard,
            "🎯 JOB SEARCH": self.render_job_search,
            "💬 FEEDBACK": self.render_feedback_page,
            "ℹ️ ABOUT": self.render_about
        }

        self.dashboard_manager = DashboardManager()
        self.analyzer = ResumeAnalyzer()
        self.ai_analyzer = AIResumeAnalyzer()
        self.builder = ResumeBuilder()
        self.job_roles = JOB_ROLES

        if 'user_id' not in st.session_state:
            st.session_state.user_id = 'default_user'

        init_database()

        with open('style/style.css') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def render_dashboard(self):
        self.dashboard_manager.render_dashboard()

    def render_job_search(self):
        render_job_search()

    def render_feedback_page(self):
        apply_modern_styles()
        page_header(
            "Feedback & Suggestions",
            "Help us improve by sharing your thoughts"
        )
        manager = FeedbackManager()
        form_tab, stats_tab = st.tabs(["Submit Feedback", "Feedback Stats"])
        with form_tab:
            manager.render_feedback_form()
        with stats_tab:
            manager.render_feedback_stats()

    def render_builder(self):
        st.title("Resume Builder 📝")

        template_options = ["Modern", "Professional", "Minimal", "Creative"]
        selected_template = st.selectbox("Select Resume Template", template_options)

        st.subheader("Personal Information")

        col1, col2 = st.columns(2)

        with col1:
            full_name = st.text_input("Full Name", value=st.session_state.form_data['personal_info']['full_name'])
            email = st.text_input("Email", value=st.session_state.form_data['personal_info']['email'], key="email_input")
            phone = st.text_input("Phone", value=st.session_state.form_data['personal_info']['phone'])

        with col2:
            location = st.text_input("Location", value=st.session_state.form_data['personal_info']['location'])
            linkedin = st.text_input("LinkedIn", value=st.session_state.form_data['personal_info']['linkedin'])
            portfolio = st.text_input("Portfolio", value=st.session_state.form_data['personal_info']['portfolio'])

        st.session_state.form_data['personal_info'] = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'location': location,
            'linkedin': linkedin,
            'portfolio': portfolio
        }

        st.subheader("Professional Summary")
        summary = st.text_area("Summary", value=st.session_state.form_data.get('summary', ''))
        st.session_state.form_data['summary'] = summary

        if st.button("Generate Resume 📄", type="primary"):

            if not full_name.strip():
                st.error("⚠️ Please enter your full name.")
                return

            if not email.strip():
                st.error("⚠️ Please enter your email.")
                return

            resume_data = {
                "personal_info": st.session_state.form_data['personal_info'],
                "summary": summary,
                "experience": st.session_state.form_data.get('experiences', []),
                "education": st.session_state.form_data.get('education', []),
                "projects": st.session_state.form_data.get('projects', []),
                "skills": st.session_state.form_data.get('skills_categories', {}),
                "template": selected_template
            }

            try:
                resume_buffer = self.builder.generate_resume(resume_data)

                if resume_buffer:
                    try:
                        save_resume_data(resume_data)
                        st.success("✅ Resume generated successfully!")
                        st.snow()

                        st.download_button(
                            label="Download Resume 📥",
                            data=resume_buffer,
                            file_name=f"{full_name.replace(' ', '_')}_resume.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            on_click=lambda: st.balloons()
                        )

                    except Exception as db_error:
                        print(f"Database error: {db_error}")
                        st.warning("Resume generated but could not be saved.")
                        st.download_button(
                            label="Download Resume 📥",
                            data=resume_buffer,
                            file_name=f"{full_name.replace(' ', '_')}_resume.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                else:
                    st.error("❌ Failed to generate resume.")
                    print("Resume buffer was None")

            except Exception as gen_error:
                print(traceback.format_exc())
                st.error(f"❌ Error generating resume: {gen_error}")

    def render_analyzer(self):
        apply_modern_styles()
        page_header(
            "Resume Analyzer",
            "Get instant AI-powered feedback"
        )

        categories = list(self.job_roles.keys())
        selected_category = st.selectbox("Job Category", categories)
        roles = list(self.job_roles[selected_category].keys())
        selected_role = st.selectbox("Role", roles)
        role_info = self.job_roles[selected_category][selected_role]

        uploaded_file = st.file_uploader("Upload Resume", type=["pdf", "docx"])

        if not uploaded_file:
            st.info("Upload a resume to begin analysis.")
            return

        if st.button("Analyze Resume", type="primary"):

            try:
                if uploaded_file.type == "application/pdf":
                    text = self.analyzer.extract_text_from_pdf(uploaded_file)
                else:
                    text = self.analyzer.extract_text_from_docx(uploaded_file)

                analysis = self.analyzer.analyze_resume({'raw_text': text}, role_info)

                if 'error' in analysis:
                    st.error(analysis['error'])
                    return

                st.snow()
                st.success("Analysis complete")

                if analysis.get('document_type') != 'resume':
                    st.error(
                        f"⚠️ This appears to be a {analysis['document_type']} document, not a resume!"
                    )
                    return

                st.metric("ATS Score", f"{analysis['ats_score']}%")
                st.metric("Format Score", f"{analysis['format_score']}%")
                st.metric("Section Score", f"{analysis['section_score']}%")

            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.code(traceback.format_exc())

    def render_home(self):
        apply_modern_styles()
        hero_section(
            "Smart Resume AI",
            "AI-powered resume analysis and builder"
        )

        feature_card(
            "fas fa-robot",
            "AI Analysis",
            "Get resume feedback instantly"
        )

        feature_card(
            "fas fa-magic",
            "Resume Builder",
            "Create professional resumes easily"
        )

    def render_about(self):
        apply_modern_styles()
        st.markdown("## About Draft.io")

    def main(self):

        with st.sidebar:
            st.title("Draft.io")
            st.markdown("---")

            for page in self.pages:
                if st.button(page, use_container_width=True):
                    cleaned = page.lower().replace(" ", "_").replace("🏠", "").replace("🔍", "").replace("📝", "").replace("📊", "").replace("🎯", "").replace("💬", "").replace("ℹ️", "").strip()
                    st.session_state.page = cleaned
                    st.rerun()

            st.markdown("---")

            if st.session_state.get('is_admin', False):
                if st.button("Logout"):
                    st.session_state.is_admin = False
                    st.rerun()
            else:
                with st.expander("Admin Login"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.button("Login"):
                        try:
                            if verify_admin(email, password):
                                st.session_state.is_admin = True
                                log_admin_action(email, "login")
                                st.rerun()
                            else:
                                st.error("Invalid credentials")
                        except Exception as e:
                            st.error(str(e))

        page_map = {
            name.lower().replace(" ", "_").replace("🏠", "").replace("🔍", "").replace("📝", "").replace("📊", "").replace("🎯", "").replace("💬", "").replace("ℹ️", "").strip(): name
            for name in self.pages
        }

        current_page = st.session_state.get('page', 'home')

        if current_page in page_map:
            self.pages[page_map[current_page]]()
        else:
            self.render_home()


if __name__ == "__main__":
    app = ResumeApp()
    app.main()
