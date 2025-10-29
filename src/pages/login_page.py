import streamlit as st
from src.database.connect_db import get_current_db_instance
from src.database.sql_querys import PostgresQueries


# Ensure session state key exists
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

class LoginPage:
    def __init__(self, logo_url: str = "./images/logo/LoginPage.jpg"):
        self.setup_page_layout()
        self.logo_url = logo_url
        # Hole gecachte Connection
        self.db = get_current_db_instance()

    def setup_page_layout(self):
        st.markdown("""
            <style>
            .stApp {
                background: #E0F7FA;
                color: black;
            }
            .center {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 80vh;
            }
            </style>
            """, unsafe_allow_html=True)

    def _header(self):
        st.subheader("Erstelle und analysiere Tourenpläne mit Leichtigkeit")

    def _form(self):
        username = st.text_input("Benutzername")
        password = st.text_input("Passwort", type="password")
        st.markdown("<small>Die Anmeldedaten werden von uns bereitgestellt</small>", unsafe_allow_html=True)

        if st.button("Login"):
            if not username or not password:
                st.warning("Bitte Benutzername und Passwort eingeben.")
                return

            try:
                response = self.db.run_query(
                    PostgresQueries.GET_USER_BY_NAME_AND_PASSWORD,
                    username=username,
                    password=password
                )
                result = response.data[0] if response.data else None
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_id = int(result["id"])
                    st.rerun()
                else:
                    st.error("Ungültiger Benutzername oder Passwort.")

            except Exception as e:
                st.error(f"Datenbankfehler: {str(e)}")

    def run(self):
        self._header()
        self._form()


login = LoginPage()
login.run()


