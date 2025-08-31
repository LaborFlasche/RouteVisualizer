from docx import Document

import pandas as pd
import re
import pandas as pd
import googlemaps
import folium

def main(path_to_word):
    doc = Document(path_to_word)
    tour_df = {"tour_id": [], "children_on_tour": [], "Street": [], "Number": [], "Region": []}

    l = 0
    for i, table in enumerate(doc.tables):
        print(f"\n--- Tabelle {i+1} ---")
        # One column is one tour
        for j, column in enumerate(table.columns):
            list_of_children = []
            list_of_street_names = []
            list_of_street_numbers = []
            list_region = []
            # Skip first Columns because it only contains indices
            if j == 0:
                continue
            l += 1
            stripped_cells = [cell.text.strip() for cell in column.cells][1:-3]
            if "\n" in stripped_cells:
                stripped_cells.remove("\n")
            column_data = [tour_entry for tour_entry in stripped_cells if tour_entry != '']
            if column_data == [] or column_data == ['Test']:
                continue

            for entry in column_data:
                try:
                    entry_elements = re.split(r'\s+', entry)
                    children_name = f"{entry_elements[0]} {entry_elements[1]}"
                    list_of_children.append(f"{entry_elements[0]} {entry_elements[1]}")
                    list_region.append(entry_elements[-1])
                    list_of_street_numbers.append(entry_elements[-2])
                    list_of_street_names.append(" ".join(entry_elements[2:-2]))
                except Exception as e:
                    print("sdfds")
            tour_df["tour_id"].append(l)
            tour_df["children_on_tour"].append(list_of_children)
            tour_df["Street"].append(list_of_street_names)
            tour_df["Number"].append(list_of_street_numbers)
            tour_df["Region"].append(list_region)



    return pd.DataFrame(tour_df)


# --------------------------------------------------
# Google Maps API Setup
# --------------------------------------------------
API_KEY = "ABC"
gmaps = googlemaps.Client(key=API_KEY)

# --------------------------------------------------
# Funktion: Für jede Tour im DataFrame eine Route berechnen und Karte speichern
# --------------------------------------------------
def create_maps_for_tours(df: pd.DataFrame):
    for idx, row in df.iterrows():
        streets = row["Street"]
        numbers = row["Number"]
        regions = row["Region"]

        # Eine Tour besteht aus mehreren Adressen (Listen)
        addresses = [f"{s} {n}, {r}" for s, n, r in zip(streets, numbers, regions)]
        if len(addresses) < 2:
            continue

        start = addresses[0]
        end = addresses[-1]
        waypoints = addresses[1:-1]

        # Route anfragen
        route = gmaps.directions(
            origin=start,
            destination=end,
            waypoints=waypoints,
            mode="driving"
        )

        if not route:
            print(f"Keine Route gefunden für Tour {row['tour_id']}")
            continue

        # Mittelpunkt der Karte setzen
        location_start = gmaps.geocode(start)[0]['geometry']['location']
        map_center = [location_start['lat'], location_start['lng']]
        m = folium.Map(location=map_center, zoom_start=12)

        # Polyline Punkte extrahieren
        polyline_points = []
        for leg in route[0]['legs']:
            for step in leg['steps']:
                polyline = step['polyline']['points']
                points = googlemaps.convert.decode_polyline(polyline)
                for point in points:
                    polyline_points.append((point['lat'], point['lng']))

        # Route einzeichnen
        folium.PolyLine(polyline_points, color="blue", weight=5, opacity=0.7).add_to(m)

        # Marker setzen
        for address in addresses:
            loc = gmaps.geocode(address)[0]['geometry']['location']
            folium.Marker([loc['lat'], loc['lng']], popup=address).add_to(m)

        # Karte speichern
        filename = f"route_map_tour_{row['tour_id']}.html"
        m.save(filename)
        print(f"Karte gespeichert als {filename}")

# --------------------------------------------------



if __name__ == "__main__":
    path_to_pdf = r"C:\Users\fuchs\Documents\workspace\infosim\Werkstudent\privateProject\data\Tourenpläne2025.pdf"
    path_to_word = "/Users/felix/Desktop/Private Projects/MariaSternMapsCreator/data/tours/Tourenpläne2025-2.docx"
    df = main(path_to_word)
    create_maps_for_tours(df)
