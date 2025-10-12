import streamlit as st
import pandas as pd

import googlemaps
import folium
import math
import time

from typing import Tuple, Optional


def create_single_map(tour_data: Tuple[int, pd.Series], idx: int, progress_callback=None, geocoding_cache=None,
                      gmaps=None) -> Optional[Tuple[folium.Map, float]]:
    """Create single map and return it with the total distance in km"""
    tour_id, elements = tour_data
    row = elements["tour_df"]

    try:
        streets = row["Street"].to_list()
        numbers = row["Number"].to_list()
        regions = row["Region"].to_list()
        addresses = [f"{s} {n}, {r}" for s, n, r in zip(streets, numbers, regions) if s != "Platz ist frei!"]

        if len(addresses) < 2:
            print(f"⚠️ Tour {idx + 1}: Zu wenige Adressen ({len(addresses)})")
            return None

        print(f"🗺️ Erstelle Karte für Tour {idx + 1} mit {len(addresses)} Stops")

        # Geocodiere alle Adressen für diese Tour
        locations = geocoding_cache.geocode_addresses_batch(addresses, gmaps)

        # Prüfe ob alle Adressen geocodiert werden konnten
        valid_locations = {addr: loc for addr, loc in locations.items() if loc is not None}
        if len(valid_locations) < 2:
            print(f"❌ Tour {idx + 1}: Zu wenige gültige Locations ({len(valid_locations)})")
            return None

        # Erstelle Route nur wenn nötig (mehr als 2 Punkte)
        total_distance_km = 0.0

        if len(addresses) > 2:
            start = addresses[0]
            end = addresses[-1]
            waypoints = addresses[1:-1]

            print(f"🛣️ Tour {idx + 1}: Berechne Route mit {len(waypoints)} Waypoints")
            try:
                route = gmaps.directions(
                    origin=start,
                    destination=end,
                    waypoints=waypoints,
                    mode="driving"
                )

                # Extrahiere Distanz
                if route and route[0]['legs']:
                    total_distance_meters = 0
                    for leg in route[0]['legs']:
                        total_distance_meters += leg['distance']['value']

                    total_distance_km = total_distance_meters / 1000

                    print(f"📏 Tour {idx + 1}: Distanz: {total_distance_km:.2f} km")

            except Exception as e:
                print(f"❌ Tour {idx + 1}: Route Fehler: {e}")
                route = None
        else:
            route = None

        # Erstelle Karte
        first_location = next(iter(valid_locations.values()))
        map_center = [first_location['lat'], first_location['lng']]
        m = folium.Map(location=map_center, zoom_start=12)

        # Füge Route hinzu wenn verfügbar
        if route and route[0]['legs']:
            print(f"📍 Tour {idx + 1}: Zeichne Route")
            polyline_points = []
            for leg in route[0]['legs']:
                for step in leg['steps']:
                    polyline = step['polyline']['points']
                    points = googlemaps.convert.decode_polyline(polyline)
                    for point in points:
                        polyline_points.append((point['lat'], point['lng']))

            folium.PolyLine(polyline_points, color="blue", weight=5, opacity=0.7).add_to(m)

            info_html = f"""
            <div style="position: fixed; 
                        top: 10px; 
                        right: 10px; 
                        width: 250px; 
                        background-color: white; 
                        border: 2px solid grey; 
                        border-radius: 5px;
                        z-index: 9999; 
                        padding: 10px;
                        font-size: 14px;">
                <b>Tour {tour_id}</b><br>
                📏 Distanz Malteser: {elements["km_besetzt"]:.0f} km<br>
                📏 Distanz Google: {total_distance_km:.0f} km<br>
                📍 Stops: {len(addresses)}
            </div>
            """
            m.get_root().html.add_child(folium.Element(info_html))

        # Füge Marker hinzu
        for i, address in enumerate(addresses):
            if address in valid_locations:
                loc = valid_locations[address]
                color = 'green' if i == 0 else ('red' if i == len(addresses) - 1 else 'blue')
                folium.Marker(
                    [loc['lat'], loc['lng']],
                    popup=f"Stop {i + 1}: {address}",
                    icon=folium.Icon(color=color)
                ).add_to(m)

        print(f"✅ Tour {idx + 1}: Karte erfolgreich erstellt")
        if progress_callback:
            progress_callback(idx + 1)

        return m, total_distance_km

    except Exception as e:
        print(f"❌ Tour {idx + 1}: Allgemeiner Fehler: {e}")
        return None


def create_maps_for_tours(tour_id_to_df: dict, geocoding_cache, gmaps) -> list:
    """Erstellt Karten für alle Touren mit optimierter Performance"""
    tour_len = len(list(tour_id_to_df.keys()))
    print(f"🚀 Starte Kartenerstellung für {tour_len} Touren")

    maps, tour_distances = {}, {}
    total_tours = tour_len

    # Erstelle einen Progress Container in Streamlit
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(completed_tours):
        progress = completed_tours / total_tours
        progress_bar.progress(progress)
        status_text.text(f"Erstelle Karten: {completed_tours}/{total_tours} Touren abgeschlossen")

    # Sequenzielle Verarbeitung mit besserer Progress-Anzeige
    for i, (tour_id, tour_element) in enumerate(tour_id_to_df.items()):
        status_text.text(f"Verarbeite Tour {i + 1}/{total_tours}...")

        map_obj, tour_distance = create_single_map((tour_id, tour_element), i, update_progress, geocoding_cache, gmaps)
        if map_obj:
            maps[tour_id] = map_obj
        if tour_distance:
            tour_distances[tour_id] = round(tour_distance)
        time.sleep(0.1)

    progress_bar.progress(1.0)
    status_text.text(f"✅ Kartenerstellung abgeschlossen: {len(maps)}/{total_tours} Karten erstellt")

    print(f"🎉 Kartenerstellung abgeschlossen: {len(maps)} von {total_tours} Karten erfolgreich erstellt")
    return maps, tour_distances
