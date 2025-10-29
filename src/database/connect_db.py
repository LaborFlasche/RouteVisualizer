import streamlit as st
from src.database.sql_querys import PostgresQueries
from supabase import create_client, Client

class Supabase_DB:
    def __init__(self):
        # Load secrets from Streamlit
        self.sb_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
        self.sb_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
        self.connection: Client | None = None

    # Cache the Supabase client; note _self instead of self
    @st.cache_resource
    def init_connection(_self) -> Client:
        return create_client(supabase_url=_self.sb_url, supabase_key=_self.sb_key)

    def connect(self):
        if self.connection:
            self.disconnect()
        try:
            # Use _self convention only inside cached function
            self.connection = self.init_connection()
            print("Connection to Supabase database established.")
        except Exception as err:
            print(f"Error connecting to Supabase: {err}")
            self.connection = None

    def disconnect(self):
        if self.connection:
            self.connection = None
            print("Supabase database connection closed.")

    def get_current_connection(self):
        return self.connection

    # Cached query execution; _self avoids hashing issues
    @st.cache_data(ttl=600)
    def run_query(_self, query_type: PostgresQueries, **params):
        if _self.connection is None:
            _self.connect()
            if _self.connection is None:
                raise RuntimeError("Supabase connection could not be established.")
        return query_type.build_query(_self.connection, **params)


# Helper to manage DB instance in session_state
def get_current_db_instance() -> Supabase_DB | None:
    try:
        if "db_instance" not in st.session_state:
            db_instance = Supabase_DB()
            db_instance.connect()
            st.session_state["db_instance"] = db_instance
        else:
            db_instance = st.session_state["db_instance"]
            if db_instance.connection is None:
                db_instance.connect()
        return st.session_state["db_instance"]
    except Exception as e:
        st.error(f"Fehler beim Herstellen der Datenbankverbindung: {e}")
        return None
