import streamlit as st
import pandas as pd

from geocaching import GeocodingCache
import googlemaps
import folium
from streamlit import components
import time
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
from document_parsing import document_parser
import os
from map_creation import create_single_map, create_maps_for_tours
import asyncio
import base64
from utils import save_map_as_png

# Load env variables e.g. API-Key
load_dotenv()

# --------------------------------------------------
# Init: Global Cache
# --------------------------------------------------
geocoding_cache = GeocodingCache()

# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------
st.set_page_config(page_title="Tour Routen Generator", layout="wide")
st.title("🚚 Touren aus Word-Dokumenten extrahieren & Karten erstellen")

# Sidebar API-Key Eingabe
st.sidebar.header("🔑 API Einstellungen")
default_api_key = os.getenv("API_KEY", "")
api_key_input = st.sidebar.text_input("Google Maps API Key", value=default_api_key, type="password")

if not api_key_input:
    st.warning("Bitte gib einen gültigen Google Maps API Key ein.")
    st.stop()

# Google Maps Client initialisieren
gmaps = googlemaps.Client(key=api_key_input)




# Cache Status anzeigen
if hasattr(geocoding_cache, 'cache'):
    st.sidebar.write(f"📍 Geocoding Cache: {len(geocoding_cache.cache)} Einträge")

uploaded_file = st.file_uploader("Ziehe dein Word-Dokument hierher", type=["docx"])



if uploaded_file:
    with st.spinner("📑 Lese Tabellen aus Word..."):
        df = document_parser(uploaded_file)
    st.success("Tabellen erfolgreich extrahiert!")

    # -----------------
    # Navigation für Tabellen
    # -----------------
    if "tour_index" not in st.session_state:
        st.session_state.tour_index = 0

    col1, col2, col3 = st.columns([1, 0.02, 1])
    with col1:
        if st.button("⬅️", key="prev_tour") and st.session_state.tour_index > 0:
            st.session_state.tour_index -= 1
    with col3:
        if st.button("➡️", key="next_tour") and st.session_state.tour_index < len(df) - 1:
            st.session_state.tour_index += 1

    current_idx = st.session_state.tour_index
    st.write(f"Tour {current_idx + 1}/{len(df)}")

    editable_df = st.data_editor(pd.DataFrame({
        "Kinder": df.loc[current_idx, "children_on_tour"],
        "Straße": df.loc[current_idx, "Street"],
        "Hausnummer": df.loc[current_idx, "Number"],
        "Region": df.loc[current_idx, "Region"]
    }))

    # Karten erstellen
    if st.button("Erstelle Karten"):
        print(f"🚀 Benutzer startet Kartenerstellung für {len(df)} Touren")
        start_time = time.time()

        with st.spinner("🗺️ Karten werden erstellt..."):
            created_maps = create_maps_for_tours(df, geocoding_cache, gmaps)
            st.session_state.maps = created_maps

        end_time = time.time()
        duration = end_time - start_time
        print(f"⏱️ Kartenerstellung abgeschlossen in {duration:.2f} Sekunden")

        st.success(f"🎉 {len(created_maps)} Karten erfolgreich erstellt! (Dauer: {duration:.1f}s)")

    # Karten-Navigation
    if "maps" in st.session_state and st.session_state.maps:
        if "tour_index" not in st.session_state:
            st.session_state.tour_index = 0

        current_idx = st.session_state.tour_index
        st.write(f"Karte {current_idx + 1}/{len(st.session_state.maps)}")
        map_html = st.session_state.maps[current_idx]._repr_html_()
        components.v1.html(map_html, height=600, width=800)

        # Download-Button für PNG
        if st.button("📥 Karte als PNG herunterladen"):
            file_path = asyncio.run(
                save_map_as_png(st.session_state.maps[current_idx])
            )
            with open(file_path, "rb") as f:
                png_data = f.read()
                b64 = base64.b64encode(png_data).decode()
                href = f'<a href="data:file/png;base64,{b64}" download="karte.png">👉 Download PNG</a>'
                st.markdown(href, unsafe_allow_html=True)
