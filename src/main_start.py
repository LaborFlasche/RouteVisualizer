import streamlit as st
from dotenv import load_dotenv
import logging
import os, sys

current_file_path = os.path.abspath(__file__)
project_root_path = os.path.dirname(os.path.dirname(current_file_path))
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

def main():
    # Configure page early
    st.set_page_config(
        page_title="Tourenplan-Generator",
        page_icon="./images/logo/Logo_FFsolutions.jpg",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    # Initialize login state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Define pages
    login_page = st.Page("pages/login_page.py", title="Login")
    main_page = st.Page("pages/streamlit_main.py", title="Main")

    # Conditional navigation based on login state
    if st.session_state.logged_in:
        current = st.navigation([main_page], position="hidden")
    else:
        current = st.navigation([login_page], position="hidden")

    current.run()


if __name__ == "__main__":
    main()