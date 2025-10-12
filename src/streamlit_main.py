import streamlit as st
import pandas as pd
from geocaching import GeocodingCache
import googlemaps
import numpy as np
from dotenv import load_dotenv
from document_parsing import pdf_parser
import os
from map_creation import create_maps_for_tours
from create_doc_files import turn_df_into_word
from utils import merge_editable_df_into_original
import hashlib
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class SessionStateKeys:
    """Centralized session state key definitions."""
    UPLOADED_FILE_HASH = "uploaded_file_hash"
    TOUR_DISTANCE = "tour_distance"
    TOUR_INDEX = "current_idx"
    TOUR_ID_TO_DF = "tour_id_to_df"
    MAPS = "maps"
    FILE_PROCESSED = "file_processed"
    GENERATING_MAPS = "generating_maps"  # NEW: Track if maps are being generated


class FileHandler:
    """Handles file upload and processing operations."""

    @staticmethod
    def get_file_hash(uploaded_file) -> str:
        """Creates a hash for the file to detect changes."""
        if uploaded_file is None:
            return ""
        file_bytes = uploaded_file.getbuffer()
        return hashlib.md5(file_bytes).hexdigest()

    @staticmethod
    def process_pdf(uploaded_file) -> pd.DataFrame:
        """Processes PDF file and extracts tour data."""
        with st.spinner("📑 Lese Tabellen aus PDF..."):
            tour_id_to_df = pdf_parser(uploaded_file)

        st.success(f"✅ {len(list(tour_id_to_df.keys()))} Touren erfolgreich aus PDF extrahiert!")
        return tour_id_to_df


class SessionManager:
    """Manages Streamlit session state."""

    @staticmethod
    def initialize_session_state():
        """Initialize all required session state variables."""
        defaults = {
            SessionStateKeys.UPLOADED_FILE_HASH: "",
            SessionStateKeys.TOUR_DISTANCE: {},
            SessionStateKeys.TOUR_INDEX: None,
            SessionStateKeys.MAPS: [],
            SessionStateKeys.TOUR_ID_TO_DF: {},
            SessionStateKeys.FILE_PROCESSED: False,
            SessionStateKeys.GENERATING_MAPS: False  # NEW
        }
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @staticmethod
    def reset_tour_data():
        """Reset tour-related session state when new file is uploaded."""
        st.session_state[SessionStateKeys.TOUR_DISTANCE] = {}
        st.session_state[SessionStateKeys.TOUR_INDEX] = None
        st.session_state[SessionStateKeys.MAPS] = []
        st.session_state[SessionStateKeys.TOUR_ID_TO_DF] = {}
        st.session_state[SessionStateKeys.FILE_PROCESSED] = False
        st.session_state[SessionStateKeys.GENERATING_MAPS] = False  # NEW

    @staticmethod
    def handle_file_change(current_hash: str) -> bool:
        """Handle file change by resetting relevant session state. Returns True if file changed."""
        if st.session_state[SessionStateKeys.UPLOADED_FILE_HASH] != current_hash:
            SessionManager.reset_tour_data()
            st.session_state[SessionStateKeys.UPLOADED_FILE_HASH] = current_hash
            return True
        return False


class UIComponents:
    """Handles UI component rendering."""

    @staticmethod
    def setup_page_config():
        """Configure Streamlit page settings."""
        st.set_page_config(page_title="Tourenplan-Generator", layout="wide")
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(to bottom, #FFD500, white); }
            .center { display: flex; justify-content: center; align-items: center; height: 80vh; }
            </style>
            """, unsafe_allow_html=True)

    @staticmethod
    def render_header():
        """Render application header."""
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("./images/marienverein_logo-1-1521260711.png")
        with col2:
            st.title("Tourenplan-Generator")
            st.subheader("Automatische Erstellung von Word-Dokumenten und Karten aus PDFs für Bustouren")

    @staticmethod
    def render_sidebar() -> Tuple[str, googlemaps.Client]:
        """Render sidebar with API key input."""
        st.sidebar.header("Historie vergangener Tourenpläne")
        api_key_input = os.getenv("API_KEY", "")

        if not api_key_input:
            st.warning("Bitte gib einen gültigen Google Maps API Key ein.")
            st.stop()

        st.sidebar.text("--------------Historie----------------")
        st.sidebar.info("Die Historie vergangener Touren wird später hier dargestellt")

        return api_key_input, googlemaps.Client(key=api_key_input)

    @staticmethod
    def render_metrics(tour_distances: List[float]):
        """Render tour metrics."""
        current_idx = st.session_state["current_idx"]
        if current_idx is None or current_idx not in st.session_state["tour_id_to_df"]:
            return

        current_displayed_df = st.session_state["tour_id_to_df"][current_idx]

        symbol_col, km_original_col, km_maps_col = st.columns([1, 1, 1])

        selected_tour = st.selectbox(
            "Wähle eine Tour aus:",
            list(st.session_state[SessionStateKeys.TOUR_ID_TO_DF].keys()),
            key="current_idx"
        )

        with symbol_col:
            st.metric("Symbol: ", f"{current_displayed_df['symbol']}")

        with km_original_col:
            st.metric("Km Malteser: ", f"{current_displayed_df['km_besetzt']} km")
            st.metric("Km total Malteser: ",
                      f"{sum([tour['km_besetzt'] for tour in st.session_state['tour_id_to_df'].values()])} km")
        if tour_distances.keys() == st.session_state["tour_id_to_df"].keys():
            with km_maps_col:
                st.metric("Km Google Maps: ", f"{tour_distances[current_idx]} km")
                st.metric("Km total Google Maps: ", f"{sum(list(tour_distances.values()))} km")


class TourTableTab:
    """Handles the tour table tab functionality."""

    COLUMN_MAPPING = {
        "Kinder": "children_on_tour",
        "Straße": "Street",
        "Hausnummer": "Number",
        "PLZ": "PLZ",
        "Region": "Region"
    }

    @classmethod
    def render(cls, tour_distances: List[float]) -> pd.DataFrame:
        """Render the tour table tab with editable data."""
        if "tour_id_to_df" not in st.session_state or not st.session_state["tour_id_to_df"]:
            st.warning("Bitte lade zuerst eine PDF-Datei hoch.")
            st.stop()
            return pd.DataFrame()

        tour_dict = st.session_state["tour_id_to_df"]
        selected_tours = st.session_state["current_idx"]

        # Get current index from session state, or use first tour as default
        if st.session_state["current_idx"] is None:
            st.session_state["current_idx"] = list(tour_dict.keys())[0]


        df = tour_dict[st.session_state["current_idx"]]["tour_df"]

        st.write("✏️ Bearbeite die aktuelle Tour:")


        # Create editable DataFrame with proper indexing
        # Reset index internally but display starting from 1
        display_df = pd.DataFrame({
            "Kinder": df["children_on_tour"].reset_index(drop=True),
            "Straße": df["Street"].reset_index(drop=True),
            "Hausnummer": df["Number"].reset_index(drop=True),
            "PLZ": df["PLZ"].reset_index(drop=True),
            "Region": df["Region"].reset_index(drop=True)
        })

        # Set display index to start from 1
        display_df.index = range(1, len(display_df) + 1)

        editable_df = st.data_editor(
            display_df,
            num_rows="fixed",
            width="stretch"
        )

        df = merge_editable_df_into_original(df, editable_df, cls.COLUMN_MAPPING)
        st.session_state["tour_id_to_df"][selected_tours]["tour_df"] = df

        st.download_button(
            "📄 Generiere Word-Dokument...",
            data=turn_df_into_word(st.session_state["tour_id_to_df"], google_distances=tour_distances),
            file_name="touren.docx"
        )

        return df


class MapTab:
    """Handles the map tab functionality."""

    @staticmethod
    def render(geocoding_cache: GeocodingCache, gmaps: googlemaps.Client):
        """Render the map tab with map generation and display."""
        tour_id_to_df = st.session_state.get(SessionStateKeys.TOUR_ID_TO_DF, {})
        current_idx = st.session_state.get(SessionStateKeys.TOUR_INDEX, list(tour_id_to_df.keys())[0])
        maps = st.session_state.get(SessionStateKeys.MAPS, [])

        # Check if we're currently generating maps
        if st.session_state.get(SessionStateKeys.GENERATING_MAPS, False):
            with st.spinner("🗺️ Karten werden erstellt..."):
                created_maps, tour_distances = create_maps_for_tours(tour_id_to_df, geocoding_cache, gmaps)
                st.session_state[SessionStateKeys.MAPS] = created_maps
                st.session_state[SessionStateKeys.TOUR_DISTANCE] = tour_distances
                st.session_state[SessionStateKeys.GENERATING_MAPS] = False
            st.success(f"🎉 {len(created_maps)} Karten erfolgreich erstellt!")
            st.rerun()

        if not maps:
            MapTab._render_map_generation_button()
        else:
            MapTab._render_map_display(maps, current_idx)

    @staticmethod
    def _render_map_generation_button():
        """Render button to generate maps."""
        st.info("Klicke auf den Button, um die Karten für alle Touren zu generieren.")
        if st.button("Erstelle Karten"):
            # Set flag to trigger map generation on next render
            st.session_state[SessionStateKeys.GENERATING_MAPS] = True
            st.rerun()

    @staticmethod
    def _render_map_display(maps: List, current_idx: int):
        """Display the current map."""
        st.write(f"Karte für Tour: {current_idx}")
        map_object = maps[current_idx]
        st.components.v1.html(map_object._repr_html_(), height=600, width=1600)


class TourenplanApp:
    """Main application controller."""

    def __init__(self):
        load_dotenv()
        self.geocoding_cache = GeocodingCache()
        SessionManager.initialize_session_state()

    def run(self):
        """Main application entry point."""
        UIComponents.setup_page_config()
        UIComponents.render_header()

        api_key, gmaps = UIComponents.render_sidebar()

        uploaded_file = st.file_uploader(
            "Ziehe das PDF-Dokument mit den Touren hier rein...",
            type=["pdf"]
        )

        if not uploaded_file:
            return

        self._handle_file_upload(uploaded_file, gmaps)

    def _handle_file_upload(self, uploaded_file, gmaps: googlemaps.Client):
        """Handle file upload and processing."""
        current_file_hash = FileHandler.get_file_hash(uploaded_file)
        file_changed = SessionManager.handle_file_change(current_file_hash)

        st.write("Dateiname:", uploaded_file.name)

        if not uploaded_file.name.endswith(".pdf"):
            st.warning("Unbekannter Dateityp.")
            st.stop()

        # Only process PDF if file changed or hasn't been processed yet
        if file_changed or not st.session_state[SessionStateKeys.FILE_PROCESSED]:
            tour_id_to_df = FileHandler.process_pdf(uploaded_file)
            st.session_state[SessionStateKeys.TOUR_ID_TO_DF] = tour_id_to_df
            st.session_state[SessionStateKeys.FILE_PROCESSED] = True
            # Set initial tour index to first tour
            if tour_id_to_df:
                st.session_state[SessionStateKeys.TOUR_INDEX] = list(tour_id_to_df.keys())[0]

        self._render_tour_interface(gmaps)

    def _render_tour_interface(self, gmaps: googlemaps.Client):
        """Render the main tour interface."""
        if not st.session_state[SessionStateKeys.TOUR_ID_TO_DF]:
            st.warning("Keine Tour-Daten verfügbar.")
            return

        current_idx = st.session_state[SessionStateKeys.TOUR_INDEX]
        tour_distances = st.session_state[SessionStateKeys.TOUR_DISTANCE]

        UIComponents.render_metrics(tour_distances)

        df_tab, map_tab = st.tabs(["Touren Tabelle", "Karten Übersicht"])

        with df_tab:
            df = TourTableTab.render(tour_distances)

        with map_tab:
            if current_idx and current_idx in st.session_state[SessionStateKeys.TOUR_ID_TO_DF]:
                df = st.session_state[SessionStateKeys.TOUR_ID_TO_DF][current_idx]["tour_df"]
                MapTab.render(self.geocoding_cache, gmaps)


def main():
    """Application entry point."""
    app = TourenplanApp()
    app.run()


if __name__ == "__main__":
    main()