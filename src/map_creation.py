import traceback

import streamlit as st
import pandas as pd
import folium
import time
import polyline
import logging
from typing import Tuple, Optional
from src.utils.geolocation import GeoLocation
from src.optimizing.osmr.osm_routing import OSMR_Module


def create_single_map(tour_data: Tuple[int, pd.Series], idx: int, progress_callback=None) -> Optional[
    Tuple[folium.Map, float]]:
    """Create single map and return it with the total distance in km"""
    osmr_module = OSMR_Module(maps=True)
    tour_id, elements = tour_data
    row = elements["tour_df"]

    try:
        # DEBUG: Struktur prüfen
        logging.info(f"🔍 Tour {idx + 1} - Debug Info:")
        logging.info(f"  Type of row: {type(row)}")
        logging.info(f"  Row shape: {row.shape if hasattr(row, 'shape') else 'N/A'}")

        # Prüfe ob row ein DataFrame ist
        if not isinstance(row, pd.DataFrame):
            logging.error(f"❌ Tour {idx + 1}: row ist kein DataFrame")
            return None

        if len(row) == 0:
            logging.error(f"❌ Tour {idx + 1}: DataFrame ist leer")
            return None

        # Prüfe ob die Spalten existieren
        required_cols = ["streets", "housenumbers", "regions"]
        for col in required_cols:
            if col not in row.columns:
                logging.error(f"❌ Tour {idx + 1}: Spalte '{col}' fehlt")
                return None

        # Extrahiere ALLE Zeilen als Listen (nicht nur die erste!)
        streets = row["streets"].tolist()
        numbers = row["housenumbers"].tolist()
        regions = row["regions"].tolist()
        postcodes = row["postcodes"].tolist()

        logging.info(f"📊 Tour {idx + 1}: {len(streets)} streets, {len(numbers)} numbers, {len(regions)} regions")

        # Prüfe ob alle Listen die gleiche Länge haben
        if not (len(streets) == len(numbers) == len(regions)):
            logging.error(
                f"❌ Tour {idx + 1}: Listen haben unterschiedliche Längen - streets: {len(streets)}, numbers: {len(numbers)}, regions: {len(regions)}")
            return None

        # Erstelle Adressen und filtere "Platz ist frei!"
        addresses = [f"{s} {n}, {p}, {r}, Deutschland" for s, n, p, r in zip(streets, numbers, postcodes, regions) if
                     str(s) != "Platz ist frei!"]

        logging.info(f"📍 Tour {idx + 1}: {len(addresses)} Adressen erstellt")
        logging.info(f"   Erste Adresse: {addresses[0] if addresses else 'KEINE'}")

        if len(addresses) < 2:
            logging.warning(f"⚠️ Tour {idx + 1}: Zu wenige Adressen ({len(addresses)})")
            return None

        logging.info(f"🌍 Tour {idx + 1}: Starte Geocoding...")
        locations, full_adresses = GeoLocation().geocode_adresses_from_dict({
            "street": streets, "housenumber": numbers, "city": regions, "postcode": postcodes
        })
        logging.info(f"✅ Tour {idx + 1}: Geocoding abgeschlossen, {len(locations)} Locations erhalten")

        # Prüfe ob alle Adressen geocodiert werden konnten
        valid_locations = {addr: loc for addr, loc in locations.items() if loc is not None}
        logging.info(f"📍 Tour {idx + 1}: {len(valid_locations)} gültige Locations von {len(addresses)} Adressen")

        if len(valid_locations) < 2:
            logging.error(f"❌ Tour {idx + 1}: Zu wenige gültige Locations ({len(valid_locations)})")
            logging.error(f"   Locations: {list(locations.keys())[:3]}")  # Erste 3 anzeigen
            return None

        # Erstelle Route nur wenn nötig (mehr als 2 Punkte)
        total_distance_km = 0.0
        route_geometry = None

        if len(addresses) >= 2:
            coords = []
            seen_coords = set()

            for address in full_adresses:
                if address in valid_locations:
                    loc = valid_locations[address]
                    coord_str = f"{loc['lng']},{loc['lat']}"

                    # Überspringe Duplikate
                    if coord_str not in seen_coords:
                        coords.append(coord_str)
                        seen_coords.add(coord_str)


            logging.info(f"🗺️ Tour {idx + 1}: {len(coords)} Koordinaten für Route erstellt")

            if len(coords) >= 2:
                coordinates_str = ";".join(coords)
                params = {
                    'overview': 'full',
                    'geometries': 'polyline',
                    'steps': 'true'
                }
                try:
                    logging.info(f"🚗 Tour {idx + 1}: Sende OSRM Request...")
                    route_data = osmr_module.create_routes_from_params(coordinates_str=coordinates_str, params=params)
                    logging.info(f"📦 Tour {idx + 1}: OSRM Response Code: {route_data.get('code', 'UNKNOWN')}")

                    if route_data.get('code') == 'Ok' and route_data.get('routes'):
                        route = route_data['routes'][0]
                        total_distance_meters = route['distance']
                        total_distance_km = total_distance_meters / 1000
                        route_geometry = route['geometry']

                        logging.info(f"📏 Tour {idx + 1}: Distanz: {total_distance_km:.2f} km")
                    else:
                        logging.warning(f"⚠️ Tour {idx + 1}: OSRM konnte keine Route finden")

                except Exception as e:
                    logging.error(f"❌ Tour {idx + 1}: OSRM Route Fehler: {e}")

        # Erstelle Karte
        first_location = next(iter(valid_locations.values()))
        map_center = [first_location['lat'], first_location['lng']]
        m = folium.Map(location=map_center, zoom_start=12)

        # Füge Route hinzu wenn verfügbar
        if route_geometry:
            logging.info(f"📍 Tour {idx + 1}: Zeichne Route")
            # Dekodiere Polyline (OSRM verwendet encoded polyline format)
            route_points = polyline.decode(route_geometry)

            folium.PolyLine(route_points, color="blue", weight=5, opacity=0.7).add_to(m)

            info_html = f"""
                        <div style="position: fixed; 
                                    top: 10px; 
                                    right: 10px; 
                                    width: 150px; 
                                    background-color: white; 
                                    border: 2px solid grey; 
                                    border-radius: 5px;
                                    z-index: 9999; 
                                    padding: 10px;
                                    font-size: 11px;">
                            <b>Tour {tour_id}</b><br>
                            📏 Distanz Malteser: {elements.get("km_besetzt", 0):.0f} km<br>
                            📏 Distanz OSRM: {total_distance_km:.0f} km<br>
                            📍 Stops: {len(addresses)}
                        </div>
                        """
            m.get_root().html.add_child(folium.Element(info_html))

        # Füge Marker hinzu
        for i, address in enumerate(full_adresses):
            if address in valid_locations:
                loc = valid_locations[address]
                color = 'green' if i == 0 else ('red' if i == len(addresses) - 1 else 'blue')
                folium.Marker(
                    [loc['lat'], loc['lng']],
                    popup=f"Stop {i + 1}: {address}",
                    icon=folium.Icon(color=color)
                ).add_to(m)

        logging.info(f"✅ Tour {idx + 1}: Karte erfolgreich erstellt")
        if progress_callback:
            progress_callback(idx + 1)

        return m, total_distance_km

    except Exception as e:
        logging.error(f"❌ Tour {idx + 1}: Allgemeiner Fehler: {e}")
        logging.error(f"   Traceback: {traceback.format_exc()}")
        return None


def create_maps_for_tours(tour_id_to_df: dict, geocoding_cache, gmaps, optimized: bool) -> list:
    """Create maps for all tours with improved progress indication"""
    tour_len = len(list(tour_id_to_df.keys()))

    maps, tour_distances = {}, {}
    total_tours = tour_len

    # Erstelle einen Progress Container in Streamlit
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(completed_tours):
        progress = completed_tours / total_tours
        progress_bar.progress(progress)
        if optimized:
            status_text.text(f"Erstelle Optimierte Karten: {completed_tours}/{total_tours} Touren abgeschlossen")
        else:
            status_text.text(f"Erstelle Karten: {completed_tours}/{total_tours} Touren abgeschlossen")

    for i, (tour_id, tour_element) in enumerate(tour_id_to_df.items()):
        status_text.text(f"Verarbeite Tour {i + 1}/{total_tours}...")

        map_obj, tour_distance = create_single_map((tour_id, tour_element), i, update_progress)
        if map_obj:
            maps[tour_id] = map_obj
        if tour_distance:
            tour_distances[tour_id] = round(tour_distance)
        time.sleep(0.1)

    progress_bar.progress(1.0)
    status_text.text(f"✅ Kartenerstellung abgeschlossen: {len(maps)}/{total_tours} Karten erstellt")

    logging.info(f"🎉 Kartenerstellung abgeschlossen: {len(maps)} von {total_tours} Karten erfolgreich erstellt")
    return maps, tour_distances
