import streamlit as st
import pandas as pd
import googlemaps
import os
import hashlib
from typing import Tuple, List
from dataclasses import dataclass
from src.geocaching import GeocodingCache
from src.document_parsing import pdf_parser
from src.map_creation import create_maps_for_tours
from src.create_doc_files import turn_df_into_word, turn_changes_into_word
from src.utils.utils import merge_editable_df_into_original, show_optimized_informations
from src.optimizing.optimizer import OptimizerModule



@dataclass
class SessionStateKeys:
    """Centralized session state key definitions."""
    UPLOADED_FILE_HASH = "uploaded_file_hash"
    TOUR_DISTANCE = "tour_distance"
    TOUR_INDEX = "current_idx"
    TOUR_ID_TO_DF = "tour_id_to_df"
    OPTIMIZED_TOUR_TO_DF = "optimized_tour_id_to_df"
    MAPS = "maps"
    OPTIMIZED_MAPS = "optimized_maps"
    FILE_PROCESSED = "file_processed"
    GENERATING_MAPS = "generating_maps"  # NEW: Track if maps are being generated
    CHANGES = "changes"  # track changes done by optimization
    CHILDREN_TO_INDEX = "children_to_index"  # NEW: Map child IDs to their indices in the distance matrix
    DISTANCE_MATRIX = "distance_matrix"  # NEW: Store the distance matrix
    OPTIMIZATION_INFOS = "optimization_infos"  # NEW: Store optimization infos
    OPTIMIZED_DISTANCES = "optimized_distances"  # NEW: Store distances for optimized tours
    GEOCODING_CACHE = "geocoding_cache"  # NEW: Cache for children's addresses



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
            SessionStateKeys.GENERATING_MAPS: False,  # NEW
            SessionStateKeys.CHANGES: {}, # NEW
            SessionStateKeys.OPTIMIZED_TOUR_TO_DF: {},
            SessionStateKeys.CHILDREN_TO_INDEX: {},
            SessionStateKeys.DISTANCE_MATRIX: pd.DataFrame(),
            SessionStateKeys.OPTIMIZATION_INFOS: {},
            SessionStateKeys.OPTIMIZED_DISTANCES: {},
            SessionStateKeys.OPTIMIZED_MAPS: [],
            SessionStateKeys.GEOCODING_CACHE: {},

        }
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

        with open("/Users/felix/PycharmProjects/RouteVisualizer/addresses.txt", "r") as f:
            import json
            st.session_state[SessionStateKeys.GEOCODING_CACHE] = json.load(f)

    @staticmethod
    def reset_tour_data():
        """Reset tour-related session state when new file is uploaded."""
        st.session_state[SessionStateKeys.TOUR_DISTANCE] = {}
        # Remove the widget key instead of setting internal key
        if "current_idx" in st.session_state:
            del st.session_state["current_idx"]
        st.session_state[SessionStateKeys.TOUR_INDEX] = None
        st.session_state[SessionStateKeys.MAPS] = []
        st.session_state[SessionStateKeys.TOUR_ID_TO_DF] = {}
        st.session_state[SessionStateKeys.FILE_PROCESSED] = False
        st.session_state[SessionStateKeys.GENERATING_MAPS] = False
        st.session_state[SessionStateKeys.CHANGES] = {}
        st.session_state[SessionStateKeys.OPTIMIZED_TOUR_TO_DF] = {}
        st.session_state[SessionStateKeys.CHILDREN_TO_INDEX] = {}
        st.session_state[SessionStateKeys.DISTANCE_MATRIX] = pd.DataFrame()
        st.session_state[SessionStateKeys.OPTIMIZATION_INFOS] = {}
        st.session_state[SessionStateKeys.OPTIMIZED_DISTANCES] = {}
        st.session_state[SessionStateKeys.OPTIMIZED_MAPS] = []
        st.session_state[SessionStateKeys.GEOCODING_CACHE] = {}


    @staticmethod
    def handle_file_change(current_hash: str) -> bool:
        """Handle file change by resetting relevant session state. Returns True if file changed."""
        if st.session_state[SessionStateKeys.UPLOADED_FILE_HASH] != current_hash:
            SessionManager.reset_tour_data()
            st.session_state[SessionStateKeys.UPLOADED_FILE_HASH] = current_hash
            return True
        return False

    @staticmethod
    def load_user_data_and_history():
        """Method to load the complete user informations + History based on the given login account"""
        return


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
        st.sidebar.caption(f"Angemeldet als **{st.session_state.get('username', 'Admin')}**")
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()
        st.sidebar.header("Historie vergangener Tourenpläne")
        api_key_input = os.getenv("GMAPS_API_KEY", "")

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

        symbol_col, km_original_col, km_maps_col, km_maps_optimized_col = st.columns([1, 1, 1, 1])

        st.selectbox(
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
                st.metric("Km Open-Street-Map: ", f"{tour_distances[current_idx]} km")
                st.metric("Km total Open-Street-Map: ", f"{sum(list(tour_distances.values()))} km")
        if st.session_state[SessionStateKeys.OPTIMIZED_DISTANCES] != {}:
            with km_maps_optimized_col:
                st.metric("Km Open-Street-Map optimiert: ", f"{st.session_state[SessionStateKeys.OPTIMIZED_DISTANCES][current_idx]} km")
                st.metric("Km Open-Street-Map optimiert: ", f"{sum(list(st.session_state[SessionStateKeys.OPTIMIZED_DISTANCES].values()))} km")



class TourTableTab:
    """Handles the tour table tab functionality."""

    COLUMN_MAPPING = {
        "Vorname": "fornames",
        "Nachname": "surnames",
        "Straße": "streets",
        "Hausnummer": "housenumbers",
        "PLZ": "postcodes",
        "Region": "regions"
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

        # Determine which DataFrame to display
        is_optimized = bool(st.session_state[SessionStateKeys.CHANGES] and
                            st.session_state[SessionStateKeys.OPTIMIZED_TOUR_TO_DF])

        # Create a container to ensure consistent width
        table_container = st.container()

        with table_container:
            if is_optimized:
                # Display both original and optimized tours side-by-side
                st.write("### 📊 Vergleich: Original vs. Optimiert")

                # Create two columns for side-by-side comparison
                col1, col2 = st.columns(2)

                # Get original DataFrame
                original_df = tour_dict[st.session_state["current_idx"]]["tour_df"]

                # Get optimized DataFrame and color map
                optimized_df = st.session_state[SessionStateKeys.OPTIMIZED_TOUR_TO_DF][selected_tours]["tour_df"]
                color_map = st.session_state[SessionStateKeys.OPTIMIZED_TOUR_TO_DF][selected_tours].get(
                    "color_map", {})

                # Column 1: Original Tour
                with col1:
                    st.write("**📋 Original Tour:**")
                    original_display_df = pd.DataFrame({
                        "Vorname": original_df["fornames"].reset_index(drop=True),
                        "Nachname": original_df["surnames"].reset_index(drop=True),
                        "Straße": original_df["streets"].reset_index(drop=True),
                        "Hausnummer": original_df["housenumbers"].reset_index(drop=True),
                        "PLZ": original_df["postcodes"].reset_index(drop=True),
                        "Region": original_df["regions"].reset_index(drop=True)
                    })
                    original_display_df.index = range(1, len(original_display_df) + 1)

                    editable_original_df = st.data_editor(
                        original_display_df,
                        num_rows="fixed",
                        use_container_width=True,
                        height=350,
                        key=f"original_editable_table_{selected_tours}"
                    )

                    original_df = merge_editable_df_into_original(original_df, editable_original_df, cls.COLUMN_MAPPING)
                    st.session_state["tour_id_to_df"][selected_tours]["tour_df"] = original_df

                # Column 2: Optimized Tour with colors
                with col2:
                    st.write("**✨ Optimierte Tour:**")
                    optimized_display_df = pd.DataFrame({
                        "Vorname": optimized_df["fornames"].reset_index(drop=True),
                        "Nachname": optimized_df["surnames"].reset_index(drop=True),
                        "Straße": optimized_df["streets"].reset_index(drop=True),
                        "Hausnummer": optimized_df["housenumbers"].reset_index(drop=True),
                        "PLZ": optimized_df["postcodes"].reset_index(drop=True),
                        "Region": optimized_df["regions"].reset_index(drop=True)
                    })
                    optimized_display_df.index = range(1, len(optimized_display_df) + 1)

                    # Apply colors using Styler
                    def apply_row_colors(row):
                        row_idx = row.name - 1
                        color = color_map.get(row_idx, "#FFFFFF")
                        return [f"background-color: {color}"] * len(row)

                    styled_df = optimized_display_df.style.apply(apply_row_colors, axis=1)

                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        height=350,
                        key=f"optimized_table_{selected_tours}"
                    )

                # Show the metrics for the optimized tours

                show_optimized_informations(st.session_state[SessionStateKeys.OPTIMIZATION_INFOS])

                # Show change details below the comparison
                if selected_tours in st.session_state[SessionStateKeys.CHANGES]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        with st.expander(f"📝 Details zu Änderungen für Tour {selected_tours}"):
                            change_list = st.session_state[SessionStateKeys.CHANGES][selected_tours]
                            if isinstance(change_list, str):
                                change_list = [change_list]

                            change_text = "\n".join(
                                [f"{change}" for idx, change in enumerate(change_list)]
                            )
                            st.markdown(f"```\n{change_text}\n```")
                    with col2:
                        st.download_button(
                            "📄 Generiere Änderungsdokument...",
                            data=turn_changes_into_word(tour_id_to_df=st.session_state[SessionStateKeys.TOUR_ID_TO_DF],
                                                        changes=st.session_state[SessionStateKeys.CHANGES],
                                                        optimized_distances=st.session_state[SessionStateKeys.OPTIMIZED_DISTANCES]),
                            file_name=f"änderungen_tour.docx",
                            key=f"download_changes",
                            width="stretch"
                        )
            else:
                # Display editable tour (unchanged)
                df = tour_dict[st.session_state["current_idx"]]["tour_df"]
                st.write("✏️ Bearbeite die aktuelle Tour:")

                display_df = pd.DataFrame({
                    "Vorname": df["fornames"].reset_index(drop=True),
                    "Nachname": df["surnames"].reset_index(drop=True),
                    "Straße": df["streets"].reset_index(drop=True),
                    "Hausnummer": df["housenumbers"].reset_index(drop=True),
                    "PLZ": df["postcodes"].reset_index(drop=True),
                    "Region": df["regions"].reset_index(drop=True)
                })
                display_df.index = range(1, len(display_df) + 1)

                editable_df = st.data_editor(
                    display_df,
                    num_rows="fixed",
                    width='stretch',
                    height=350,
                    key=f"editable_table_{selected_tours}"
                )

                df = merge_editable_df_into_original(df, editable_df, cls.COLUMN_MAPPING)
                st.session_state["tour_id_to_df"][selected_tours]["tour_df"] = df

        # Action buttons (always visible)
        col1, col2 = st.columns(2)

        with col1:
            if st.session_state[SessionStateKeys.OPTIMIZED_TOUR_TO_DF]:
                # Auswahlbox für Original oder Optimiert
                tour_choice = st.selectbox(
                    "Wähle die Tour-Version für den Download:",
                    ["Original", "Optimiert"],
                    key="tour_download_choice"
                )
                if tour_choice == "Original":
                    tour_data = st.session_state[SessionStateKeys.TOUR_ID_TO_DF]
                else:
                    tour_data = st.session_state[SessionStateKeys.OPTIMIZED_TOUR_TO_DF]
            else:
                tour_data = st.session_state[SessionStateKeys.TOUR_ID_TO_DF]

            # Download-Button
            st.download_button(
                "📄 Generiere Word-Dokument...",
                data=turn_df_into_word(tour_data, google_distances=tour_distances, optimized_distances=st.session_state[SessionStateKeys.OPTIMIZED_DISTANCES]),
                file_name="touren.docx",
                key="download_button",
                width="stretch"
            )

        with col2:
            if st.button("🔄 Optimiere die Touren...", width="stretch"):
                with st.spinner("Optimiere die Tour...", show_time=True):
                    optimizer = OptimizerModule({})
                    optimized_tours, changes, optimization_infos, optimized_distances, osm_distances = optimizer.optimize()
                    st.session_state[SessionStateKeys.OPTIMIZED_TOUR_TO_DF] = optimized_tours
                    st.session_state[SessionStateKeys.CHANGES] = changes
                    st.session_state[SessionStateKeys.OPTIMIZATION_INFOS] = optimization_infos
                    st.session_state[SessionStateKeys.OPTIMIZED_DISTANCES] = optimized_distances
                    st.session_state[SessionStateKeys.TOUR_DISTANCE] = osm_distances
                    st.success("Touren erfolgreich optimiert!")
                    st.rerun()


        return df if not is_optimized else optimized_df


class MapTab:
    """Handles the map tab functionality."""

    @staticmethod
    def render(geocoding_cache: GeocodingCache, gmaps: googlemaps.Client):
        """Render the map tab with map generation and display."""
        tour_id_to_df = st.session_state.get(SessionStateKeys.TOUR_ID_TO_DF, {})
        optimized_tour_id_to_df = st.session_state.get(SessionStateKeys.OPTIMIZED_TOUR_TO_DF, {})
        current_idx = st.session_state.get(SessionStateKeys.TOUR_INDEX, list(tour_id_to_df.keys())[0])
        maps = st.session_state.get(SessionStateKeys.MAPS, [])
        optimized_maps = st.session_state.get(SessionStateKeys.OPTIMIZED_MAPS, [])
        # Check if we're currently generating maps
        if st.session_state.get(SessionStateKeys.GENERATING_MAPS, False):
            with st.spinner("🗺️ Karten werden erstellt..."):
                created_maps, tour_distances = create_maps_for_tours(tour_id_to_df, geocoding_cache, gmaps, optimized=False)
                st.session_state[SessionStateKeys.MAPS] = created_maps
                st.session_state[SessionStateKeys.TOUR_DISTANCE] = tour_distances

                if optimized_tour_id_to_df:
                    created_optimized_maps, _ = create_maps_for_tours(optimized_tour_id_to_df, geocoding_cache, gmaps, optimized=True)
                    st.session_state[SessionStateKeys.OPTIMIZED_MAPS] = created_optimized_maps

                st.session_state[SessionStateKeys.GENERATING_MAPS] = False
            st.success(f"🎉 {len(created_maps)} Karten erfolgreich erstellt!")
            st.rerun()

        if not maps:
            MapTab._render_map_generation_button()
        else:
            MapTab._render_map_display(maps, optimized_maps, current_idx)

    @staticmethod
    def _render_map_generation_button():
        """Render button to generate maps."""
        st.info("Klicke auf den Button, um die Karten für alle Touren zu generieren.")
        if st.button("Erstelle Karten"):
            # Set flag to trigger map generation on next render
            st.session_state[SessionStateKeys.GENERATING_MAPS] = True
            st.rerun()

    @staticmethod
    def _render_map_display(maps: List, optimized_maps: List, current_idx: int):
        """Display the current map."""
        col1, col2 = st.columns(2)

        def render_map_object(original: bool = True, map_object=None, height: int = 300, width: int = 800):
            tour_text = "Original Touren" if original else "Optimierte Touren"
            st.write(f"**{tour_text} - Karte für Tour: {current_idx}**")
            st.components.v1.html(map_object._repr_html_(), height=height, width=width)

        if not optimized_maps:
            render_map_object(original=True, map_object=maps[current_idx], width=1000)
        else:
            with col1:
                render_map_object(original=True, map_object=maps[current_idx], width=800)
            with col2:
                render_map_object(original=False, map_object=optimized_maps[current_idx], width=800)

        # Render the map generation button directly below the maps
        st.info("Klicke auf den Button, um die Karten für alle Touren zu generieren.")
        if st.button("Erstelle Karten"):
            # Set flag to trigger map generation on next render
            st.session_state[SessionStateKeys.GENERATING_MAPS] = True
            st.rerun()

class TourenplanApp:
    """Main application controller."""

    def __init__(self):
        #TODO load uder data and set session states
        self.geocoding_cache = GeocodingCache()
        SessionManager.initialize_session_state()
        SessionManager.load_user_data_and_history()

    def run(self):
        """Main application entry point."""
        UIComponents.setup_page_config()
        UIComponents.render_header()

        api_key, gmaps = UIComponents.render_sidebar()

        uploaded_file = st.file_uploader(
            "Ziehe das PDF-Dokument mit den Touren hier rein...",
            key=f"uploader_{st.session_state.get('upload_widget_key', 0)}",
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

        # Initialisiere active_tab, falls nicht vorhanden
        if "active_tab" not in st.session_state:
            st.session_state["active_tab"] = 0  # Index des aktiven Tabs (0 = erster Tab)

        current_idx = st.session_state[SessionStateKeys.TOUR_INDEX]
        tour_distances = st.session_state[SessionStateKeys.TOUR_DISTANCE]

        UIComponents.render_metrics(tour_distances)

        tabs = ["Touren Tabelle", "Karten Übersicht"]

        # Erstelle die Tabs und verwende den gespeicherten Index
        tab1, tab2 = st.tabs(tabs)

        with tab1:
            df = TourTableTab.render(tour_distances)
            # Optional: Wenn eine Interaktion in diesem Tab stattfindet
            if st.session_state.get("_tab_interaction") == "tab1":
                st.session_state["active_tab"] = 0

        with tab2:
            if current_idx and current_idx in st.session_state[SessionStateKeys.TOUR_ID_TO_DF]:
                MapTab.render(self.geocoding_cache, gmaps)
            # Optional: Wenn eine Interaktion in diesem Tab stattfindet
            if st.session_state.get("_tab_interaction") == "tab2":
                st.session_state["active_tab"] = 1


def main():
    """Application entry point."""
    # Check whether the user is logged in
    if not st.session_state.logged_in:
        st.session_state.clear()
    else:
        app = TourenplanApp()
        app.run()


if __name__ == "__main__":
    main()