from typing import List, Callable
import streamlit as st
import pandas as pd
import numpy as np
from src.utils.geolocation import GeoLocation
from src.optimizing.osmr.osm_routing import OSMR_Module
from src.optimizing.child import Child, create_object, Object, School


class OptimizingDataset:
    """Module to generate the Dataset needed for Optimizing the Routs"""
    @staticmethod
    def _get_distance_matrix_from_osmr(children: List[Child], school: Object,
                                       update_pogress: Callable, status_text, osmr_url: str) -> pd.DataFrame:
        # First get the geolocations of all children
        status_text.text("Ermittle Geokoordinaten der Adressen...")
        children, school = GeoLocation().geocode_addresses(children, school)
        # Then get the distance matrix from OpenStreetMap
        osmr_module = OSMR_Module(maps=False, osmr_url=osmr_url)
        status_text.text("Erstelle Distanzmatrix von OpenStreetMap...")
        distance_matrix = osmr_module.create_distance_matrix_from_osmr(children, school, update_pogress)
        if distance_matrix is None:
            st.sidebar.error("Fehler beim Erstellen der Distanzmatrix von OpenStreetMap.")
            return None
        return distance_matrix

    @staticmethod
    def _check_distance_matrix(children: List[Child]) -> bool:
        """Check if all Person-to-Person information entries are within the distance matrix."""
        if "children_to_index" not in st.session_state:
            return False

        children_to_index: dict = st.session_state["children_to_index"]
        if len(children) != len(children_to_index):
            return False
        child_ids = {child.id for child in children}

        return all(child_id in child_ids for child_id in children_to_index.keys())

    @staticmethod
    def load_distance_matrix(children: List[Child], school: School,
                             update_pogress: Callable, status_text, osmr_url: str) -> dict:
        """Load distance matrix from the current session_state or load it from OpenStreetMap"""
        assert len(children) > 0, "No children provided to load distance matrix."
        if "distance_matrix" in st.session_state:
            if OptimizingDataset._check_distance_matrix(children=children):
                return st.session_state.distance_matrix
        # Load the distance matrix from OpenStreetMap
        new_distance_matrix = OptimizingDataset._get_distance_matrix_from_osmr(children, school, update_pogress, status_text, osmr_url)
        if new_distance_matrix is None:
            st.sidebar.error("Fehler beim Laden der Distanzmatrix von OpenStreetMap.")
            return None
        st.session_state.distance_matrix = new_distance_matrix
        return new_distance_matrix

    @staticmethod
    def get_school_indeces(distance_matrix: np.ndarray, school: School) -> list[int]:
        """Get the indeces of all Schools in the distance matrix"""
        school_indeces = []
        for i in range(distance_matrix.shape[0]):
            for j in range(distance_matrix.shape[1]):
                # Schools are marked with -1 in the distance matrix
                if distance_matrix[i][j] == -1:
                    school_indeces.append(i)
        return {school.id: distance_matrix.shape[0]-1}

    @staticmethod
    def turn_children_list_into_tour_dict(tour_to_children_dict: dict, school: School) -> dict:
        """Turn a dict of tour_id to a list of Child objects into a tour dict with DataFrames."""
        tour_dict = {}

        for tour_id, children in tour_to_children_dict.items():
            tour_rows = []

            # Add children rows
            for child in children:
                row = {
                    "fornames": child.forname,
                    "surnames": child.surname,
                    "streets": child.street,
                    "housenumbers": child.housenumber,
                    "postcodes": child.postcode,
                    "regions": child.region,
                }
                tour_rows.append(row)

            # Add placeholder rows if less than 8 entries
            while len(tour_rows) < 8:
                placeholder_row = {
                    "fornames": "Platz ist frei!",
                    "surnames": "Platz ist frei!",
                    "streets": "Platz ist frei!",
                    "housenumbers": "Platz ist frei!",
                    "postcodes": "Platz ist frei!",
                    "regions": "Platz ist frei!",
                }
                tour_rows.append(placeholder_row)

            # Add the school row
            school_row = {
                "fornames": school.forname,
                "surnames": school.surname,
                "streets": school.street,
                "housenumbers": school.housenumber,
                "postcodes": school.postcode,
                "regions": school.region,
            }
            tour_rows.append(school_row)

            # Create DataFrame and add to tour_dict
            tour_dict[str(tour_id)] = pd.DataFrame(tour_rows)

        return tour_dict

    @staticmethod
    def turn_tour_dict_into_children_list(tour_dict: dict) -> list[Child]:
        """Turn the tour dict into a list of Child objects, with the last row creating a School object."""
        children = []
        school = None
        for tour_id, tour_list in tour_dict.items():
            if "tour_df" not in tour_list:
                continue  # Skip if no tour_df present
            tour_df = tour_list["tour_df"]
            # First generate the school object
            last_row = tour_df.iloc[-1].to_dict()
            last_row["tour_id"] = tour_id
            school = create_object(last_row, School)
            for index, row in tour_df.iterrows():
                row = row.to_dict()
                if any([row[column] == "Platz ist frei!" for column in tour_df.columns]):
                    continue
                row["tour_id"] = tour_id
                if index == tour_df.index[-1]:  # Check if it's the last row
                    continue
                else:
                    row["school_id"] = school.id
                    children.append(
                        create_object(row, Child),  # Create a Child object
                    )
        return children, school

    @staticmethod
    def generate_optimizing_dataset(update_progress: Callable, status_text, osmr_url: str) -> tuple[np.ndarray, list[int], list[Child]]:
        """Generate the dataset needed for optimizing the routes"""
        if "tour_id_to_df" not in st.session_state:
            st.error("Keine Tourdaten gefunden. Bitte zuerst Touren hochladen.")
            return None
        tour_data = st.session_state["tour_id_to_df"]
        status_text.text("Bringe die Kinder in das korrekte Format...")
        children, school = OptimizingDataset.turn_tour_dict_into_children_list(tour_data)
        status_text.text("Lade Distanzmatrix von OpenStreetMap...")
        distance_matrix = OptimizingDataset.load_distance_matrix(children, school, update_progress,
                                                                 status_text, osmr_url)
        school_indeces = OptimizingDataset.get_school_indeces(distance_matrix, school)
        return distance_matrix, school_indeces, children, school
