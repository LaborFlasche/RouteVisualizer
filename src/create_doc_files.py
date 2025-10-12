import pandas as pd
import docx
from docx.shared import Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from io import BytesIO





def turn_df_into_word(tour_id_to_df: dict, google_distances=None) -> str:
    """
    Create word document from dataframe.
    5 Tours per Page.

    Args:
        tour_id_to_df: Dictionary with tour_id as key and dict with keys:
                       - "tour_df": pd.DataFrame with columns children_on_tour, Street, Number, PLZ, Region
                       - "symbol": tour symbol
                       - "km_besetzt": distance in km
        filename: output filename
        google_distances: dict mapping tour_id to google maps distance
    """
    if google_distances is None:
        google_distances = {}

    # Neues Dokument
    doc = docx.Document()

    # Querformat einstellen
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Cm(1)
    section.bottom_margin = Cm(1)
    section.left_margin = Cm(1)
    section.right_margin = Cm(1)

    # Überschrift
    original_distances_all = sum([tour["km_besetzt"] for tour in tour_id_to_df.values()])
    doc.add_heading("Tourenübersicht der Maria Stern Schule", 0)
    doc.add_heading(f"Gesamtdistanz Malteser: {original_distances_all} km", level=1)
    if len(google_distances) != 0:
        doc.add_heading(f"Gesamtdistanz Google Maps: {sum(google_distances.values())} km", level=2)

    max_tours_per_page = 5
    tour_ids = list(tour_id_to_df.keys())
    num_tours = len(tour_ids)

    # In Seitenblöcke teilen
    for start in range(0, num_tours, max_tours_per_page):
        end = min(start + max_tours_per_page, num_tours)
        tours_block = tour_ids[start:end]

        num_rows = 9 + 1 + (4 if len(google_distances) != 0 else 2)  # 9 Kinder/Zeilen, 1 Anm., 2 Zusatzzeilen
        num_cols = len(tours_block) + 1  # +1 für erste Spalte (Labels)

        table = doc.add_table(rows=num_rows + 1, cols=num_cols)  # +1 für Kopfzeile
        table.style = "Table Grid"
        table.autofit = False

        # Define Header with enumeration
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = ""
        for i, tour_id in enumerate(tours_block, start=start + 1):  # <-- start offset added here
            hdr_cells[i - start].text = str(i)  # <-- adjust column index
            p = hdr_cells[i - start].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                p.runs[0].bold = True

        # First row with Tour informations
        fr_cells = table.rows[1].cells
        fr_cells[0].text = "Tour-Infos:"
        for i, tour_id in enumerate(tours_block, start=1):
            tour_data = tour_id_to_df[tour_id]
            fr_text = f"{tour_id[-5:]} - {tour_data['symbol']}"  # Letzte Ziffern der ID + Symbol
            fr_cells[i].text = fr_text
            p = fr_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                p.runs[0].bold = True

        # Erste Spalte: Labels
        for i in range(1, 10):
            table.rows[i + 1].cells[0].text = str(i)
        table.rows[10].cells[0].text = "Anm."

        # KM-Besetzt Zeile
        row_km = table.rows[11].cells
        merged_km = row_km[0].merge(row_km[-1])
        p = merged_km.paragraphs[0]
        p.add_run("KM-Besetzt Malteser").bold = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # KM-Besetzt Maps
        if len(google_distances) != 0:
            row_km = table.rows[13].cells
            merged_km = row_km[0].merge(row_km[-1])
            p = merged_km.paragraphs[0]
            p.add_run("KM-Besetzt Google Maps").bold = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Grüne Zeilen
        row_green_malteser = table.rows[12].cells
        row_green_maps = table.rows[14].cells if len(google_distances) != 0 else None

        for row in [row for row in [row_green_malteser, row_green_maps] if row is not None]:
            for cell in row:
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                shading_elm = OxmlElement("w:shd")
                shading_elm.set(qn("w:val"), "clear")
                shading_elm.set(qn("w:color"), "auto")
                shading_elm.set(qn("w:fill"), "92D050")
                cell._tc.get_or_add_tcPr().append(shading_elm)

        # Inhalte je Tour
        for col_idx, tour_id in enumerate(tours_block, start=1):
            tour_data = tour_id_to_df[tour_id]
            tour_df = tour_data["tour_df"]

            # Kinder/Adresse füllen
            children = tour_df["children_on_tour"].tolist()
            streets = tour_df["Street"].tolist()
            numbers = tour_df["Number"].tolist()
            regions = tour_df["Region"].tolist()

            for i in range(min(9, len(children))):
                cell = table.rows[i + 2].cells[col_idx]
                if all(element[i] == "Platz ist frei!" for element in [children, streets, numbers]):
                    text = f" \n \n "
                else:
                    text = f"{children[i]}\n{streets[i]} {numbers[i]}\n{regions[i]}"
                cell.text = text

            # KM-besetzt in grüne Zelle
            green_cell = table.rows[12].cells[col_idx]
            green_cell.text = str(tour_data["km_besetzt"])
            green_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            # KM per tour for google maps
            if row_green_maps is not None and tour_id in google_distances:
                green_cell = table.rows[14].cells[col_idx]
                green_cell.text = str(google_distances[tour_id])
                green_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Seitenumbruch falls weitere Touren folgen
        if end < num_tours:
            doc.add_page_break()

    # Save file in acceptable format
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return buffer


