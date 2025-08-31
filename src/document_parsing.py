from docx import Document
import pandas as pd
import re
def document_parser(path_to_word):
    print("📄 Start Word document parsing...")
    doc = Document(path_to_word)
    tour_df = {"tour_id": [], "children_on_tour": [], "Street": [], "Number": [], "Region": []}

    l = 0
    total_tables = len(doc.tables)
    print(f"📊 Gefundene Tabellen: {total_tables}")

    for i, table in enumerate(doc.tables):
        print(f"🔄 Verarbeite Tabelle {i + 1}/{total_tables}")
        for j, column in enumerate(table.columns):
            list_of_children = []
            list_of_street_names = []
            list_of_street_numbers = []
            list_region = []
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
                    list_of_children.append(children_name)
                    list_region.append(entry_elements[-1])
                    list_of_street_numbers.append(entry_elements[-2])
                    list_of_street_names.append(" ".join(entry_elements[2:-2]))
                except Exception:
                    continue
            tour_df["tour_id"].append(l)
            tour_df["children_on_tour"].append(list_of_children)
            tour_df["Street"].append(list_of_street_names)
            tour_df["Number"].append(list_of_street_numbers)
            tour_df["Region"].append(list_region)

            if list_of_children:
                print(f"✅ Tour {l}: {len(list_of_children)} Kinder gefunden")

    result_df = pd.DataFrame(tour_df)
    print(f"🎉 Parsing abgeschlossen: {len(result_df)} Touren extrahiert")
    return result_df