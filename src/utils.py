import pandas as pd
from pyppeteer import launch
from PyPDF2 import PdfReader
import streamlit as st

async def save_map_as_png(map_obj, file_path="map.png"):
    """Rendert eine Folium-Karte als PNG mit pyppeteer."""
    map_html = map_obj._repr_html_()

    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.setViewport({"width": 800, "height": 600})
    await page.setContent(map_html)
    await page.screenshot({"path": file_path})
    await browser.close()
    return file_path

def read_pdf_content(pdf_path: str) -> str:
    """Helper method to read text content from a PDF file."""
    reader = PdfReader(pdf_path)
    text_content = []
    for page in reader.pages:
        text_content.append(page.extract_text())
    return text_content


def merge_editable_df_into_original(original_df: pd.DataFrame, editable_df: pd.DataFrame,
                                    key_mapping: dict) -> pd.DataFrame:
    """
    Merge values from editable_df into a specific row of original_df.
    Allows lists to be stored in cells.

    Args:
        original_df (pd.DataFrame): The dataframe to update.
        row_id (int): Index (row) in original_df to update.
        editable_df (pd.DataFrame): Source dataframe containing updated values.
        key_mapping (dict): Mapping {editable_col: original_col}.

    Returns:
        pd.DataFrame: Updated dataframe with changes applied.
    """
    original_df = original_df.copy()
    for key_editable, key_original in key_mapping.items():
        original_df[key_original] = editable_df[key_editable].values
    return original_df

