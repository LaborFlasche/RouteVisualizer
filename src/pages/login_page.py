import streamlit as st
from src.database.connect_db import get_db_connection
from src.database.sql_querys import SQLQueries


# Ensure session state key exists
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

class LoginPage:
    def __init__(self, logo_url: str = "./images/logo/LoginPage.jpg"):
        self.setup_page_layout()
        self.logo_url = logo_url
        # Hole gecachte Connection
        self.db = get_db_connection()
        self.conn = self.db.get_current_connection()
        st.session_state.db_instance = self.conn

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
                cursor = self.conn.cursor()
                cursor.execute(
                    SQLQueries.GET_USER_BY_NAME_and_PASSWORD.get_query(),
                    (username, password)
                )
                result = cursor.fetchone()
                cursor.close()

                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_id = int(result[0])
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