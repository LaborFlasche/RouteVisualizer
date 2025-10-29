import logging
import pandas as pd
import re
import streamlit as st
from src.models.icon_mapping import icons
from src.utils.utils import read_pdf_content



def _get_regions_from_pdf_string(pdf_string: str) -> list:
    """
    Extrahiert alle Regionen/Stadtteile aus dem Text inklusive Stadt, z.B. 'Würzburg - Versbach'.
    Duplikate werden beibehalten.
    """
    # Regex Erklärung:
    # \d{5}       -> PLZ (5 Ziffern)
    # \s+         -> mindestens ein Leerzeichen
    # ([^\d,]+)   -> alles bis zur nächsten Zahl oder Komma, das ist die Region inkl. Stadt
    # -?          -> optionaler Bindestrich für Unterregionen
    pattern = r"\d{5}\s+([^\d,]+?)\d{2}:\d{2}x"

    regionen = re.findall(pattern, pdf_string)

    # Leerzeichen am Anfang/Ende entfernen
    regionen = [re.sub(r'\s*-\s*$', '', r.strip()) for r in regionen]

    return regionen





def get_table_from_pdf_content(pdf_content: str, tour_dict: dict) -> pd.DataFrame:
    """Extracts table data from the given PDF content string for a single site."""
    tour_id_to_df = dict()
    for page in pdf_content:
        # Metadaten
        split_by_school = page.split("Maria-Stern-Schule")
        id_cleaned = "".join(split_by_school[0].split("\n")[-1].split())
        if not id_cleaned.isdigit():
            match = re.search(r'\d{5}\s\d{3}', page)
            if match:
                id_cleaned = match.group(0)[-6:].replace(" ", "")
            else:
                st.warning(f"⚠️ Warnung: Keine gültige ID in Seite gefunden: {id_cleaned}. Seite wird übersprungen.")
                continue



        symbol_tmp = "".join(split_by_school[1].split("\n")[0].split()).split("MO")[0]
        symbol = f"{symbol_tmp} {icons[symbol_tmp]}"
        km_besetzt = "".join(page.split("Km besetzt")[1].split("\n")[0].split(",")[0])
        if symbol.lower() in icons:
            symbol = icons[symbol.lower()]

        # Tour-Daten
        tour_text = page.split("Schuljahr:")[1].split("Ende Tour")[0]
        blocks = re.split(r'(?=[A-ZÄÖÜ][a-zäöüß]+,\s*[A-ZÄÖÜ][a-zäöüß]+)', tour_text)

        forname_l, surname_l, housenumber_l, street_l, postcode_l, region_l = [], [], [], [], [], _get_regions_from_pdf_string(page)

        for block in blocks:
            if not block.strip():
                continue

            # Name
            m_name = re.match(r'([^0-9\n]+)', block.strip())
            name = m_name.group(1).strip() if m_name else None

            # Adresse suchen
            m_addr = re.search(
                r'([A-Za-zÄÖÜäöüß\-\s\.]+)\s+(\d+[a-zA-Z]?),\s*(\d{5})\s+([^\n,]+?)(?:\s*-\s*([^\n,]+))?',
                block
            )

            if m_addr:
                street = m_addr.group(1).strip()
                number = m_addr.group(2).strip()
                plz = m_addr.group(3).strip()

            else:
                street = number = plz = None

            if not (name and street and number and plz):
                continue
            surname, forname = name.split(",")
            forname = forname.strip()
            surname = surname.strip()
            forname_l.append(forname), surname_l.append(surname)
            street_l.append(street)
            housenumber_l.append(number)
            postcode_l.append(plz)

        # Auffüllen bis 8
        for list_element in [forname_l, surname_l, street_l, housenumber_l, postcode_l, region_l]:
            while len(list_element) < 8:
                list_element.append("Platz ist frei!")

        # Schule hinzufügen
        if not (
            forname_l and
            forname_l[-1] == "Maria-Stern-Schule" and
            surname_l[-1] == "Maria-Stern-Schule" and
            street_l[-1] == "Felix-Dahn-Str." and
            housenumber_l[-1] == "11" and
            postcode_l[-1] == "97072"
        ):
            forname_l.append("Maria-Stern-Schule")
            surname_l.append("Maria-Stern-Schule")
            street_l.append("Felix-Dahn-Str.")
            housenumber_l.append("11")
            region_l.append("Würzburg")
            postcode_l.append("97072")

        # Speichern

        tour_dict["fornames"] = forname_l
        tour_dict["surnames"] = surname_l
        tour_dict["streets"] = street_l
        tour_dict["housenumbers"] = housenumber_l
        tour_dict["postcodes"] = postcode_l
        tour_dict["regions"] = region_l

        tour_id_to_df[id_cleaned] = {"tour_df": pd.DataFrame(tour_dict), "symbol": symbol, "km_besetzt": int(km_besetzt)}

    return tour_id_to_df


def pdf_parser(path_to_pdf) -> pd.DataFrame:
    """Method extracting the Tour Tables from the PDF using Deep Learning.
    param: path_to_pdf: Path to the PDF file
    return: pd.DataFrame with the extracted tours
    """
    pdf_content = read_pdf_content(path_to_pdf)

    tour_dict = {
        "fornames": [],
        "surnames": [],
        "streets": [],
        "housenumbers": [],
        "postcodes": [],
        "regions": []
    }
    tour_id_to_df = get_table_from_pdf_content(pdf_content, tour_dict)
    st.session_state["tour_id_to_df"] = tour_id_to_df
    st.session_state["current_idx"] = list(tour_id_to_df.keys())[0]
    logging.info(f"🎉 Parsing abgeschlossen: {len(list(tour_id_to_df.keys()))} Touren extrahiert")
    return tour_id_to_df


