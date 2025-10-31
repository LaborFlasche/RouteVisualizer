import pymysql
import streamlit as st
import os
import time
@st.cache_resource
def get_db_connection():
    """Generate and cache a DB connection."""
    if "db_instance" not in st.session_state:
        db = MySQL_DB(
            host=os.getenv("HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        st.session_state["db_instance"] = try_connect_with_retry(db)
        return st.session_state["db_instance"]
    else:
        db = st.session_state["db_instance"]
        if db.get_current_connection() is None:
            st.session_state["db_instance"] = try_connect_with_retry(db)
        return st.session_state["db_instance"]

def get_current_db_instance():
    if "db_instance" not in st.session_state:
        st.warning("Not Database instance currently connected!")
        return
    return st.session_state["db_instance"]

class MySQL_DB:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        if self.connection:
            print("Already connected to a database connection - disconnecting first.")
            self.disconnect()
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=int(os.getenv("DB_PORT", 3306))
            )
            print("Connection to MySQL database established.")
        except pymysql.Error as err:
            print(f"Error: {err}")
            self.connection = None

    def get_current_connection(self):
        return self.connection

    def disconnect(self):
        if self.connection:
            self.connection.close()
            print("MySQL database connection closed.")

def try_connect_with_retry(db_instance, initial_delay=5):
    """Try to connect to the database with exponential backoff."""
    delay = initial_delay
    max_retries = 5
    retries = 0

    placeholder = st.empty()

    while retries < max_retries:
        db_instance.connect()
        if db_instance.get_current_connection() is not None:
            return db_instance
        else:
            placeholder.warning(f"Connection failed. Retrying in {delay} seconds...")
            time.sleep(delay)
            retries += 1
            delay *= 2  # Exponentiell steigender Timer: 5, 10, 20, 40, ...
    st.error("Failed to connect to the database after multiple attempts.")
    return None


