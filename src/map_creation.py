import streamlit as st
import pandas as pd

import googlemaps
import folium
import time

from typing import Tuple, Optional


def create_single_map(tour_data: Tuple[int, pd.Series], progress_callback=None, geocoding_cache=None, gmaps=None) -> Optional[folium.Map]:
    """Create single map"""
    idx, row = tour_data

    try:
        streets = row["Street"]
        numbers = row["Number"]
        regions = row["Region"]
        addresses = [f"{s} {n}, {r}" for s, n, r in zip(streets, numbers, regions)]

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

        return m

    except Exception as e:
        print(f"❌ Tour {idx + 1}: Allgemeiner Fehler: {e}")
        return None


def create_maps_for_tours(df: pd.DataFrame, geocoding_cache, gmaps) -> list:
    """Erstellt Karten für alle Touren mit optimierter Performance"""
    print(f"🚀 Starte Kartenerstellung für {len(df)} Touren")

    maps = []
    total_tours = len(df)

    # Erstelle einen Progress Container in Streamlit
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(completed_tours):
        progress = completed_tours / total_tours
        progress_bar.progress(progress)
        status_text.text(f"Erstelle Karten: {completed_tours}/{total_tours} Touren abgeschlossen")

    # Sequenzielle Verarbeitung mit besserer Progress-Anzeige
    for idx, row in df.iterrows():
        status_text.text(f"Verarbeite Tour {idx + 1}/{total_tours}...")

        map_obj = create_single_map((idx, row), update_progress, geocoding_cache, gmaps)
        if map_obj:
            maps.append(map_obj)

        # Kurze Pause um UI responsive zu halten
        time.sleep(0.1)

    progress_bar.progress(1.0)
    status_text.text(f"✅ Kartenerstellung abgeschlossen: {len(maps)}/{total_tours} Karten erstellt")

    print(f"🎉 Kartenerstellung abgeschlossen: {len(maps)} von {total_tours} Karten erfolgreich erstellt")
    return maps
