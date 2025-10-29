from typing import List, Tuple, Callable
import requests
import logging
import streamlit as st
import pandas as pd
import os
from src.optimizing.child import Child, School


class OSMR_Module:
    """This module contains the functions to interact with the local OSMR instance"""
    def __init__(self, maps: bool = False, osmr_url: str = "http://127.0.0.1:5001/route/v1/driving/{},{};{},{}?steps=true"):
        if maps:
            self.osmr_url = os.getenv("OSMR_MAPS_URL", osmr_url)
        else:
            self.osmr_url = os.getenv("OSMR_URL", osmr_url)


    def _ensure_lonlat(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """Ensure the coordinate is in (lon, lat) order."""
        lat, lon = point
        return (lon, lat)


    def is_osmr_url_reachable(self, base_url: str = None) -> bool:
        """Check if the OSMR URL is reachable."""
        try:
            if not base_url:
                base_url = self.osmr_url.format(10, 20, 10, 20)
            response = requests.get(base_url, timeout=5)
            if response.status_code == 200:
                return True
            else:
                logging.warning(base_url)
                logging.warning(f"OSMR URL reachable but returned status code: {response.status_code}")
                return False
        except requests.RequestException as e:
            logging.error(f"Error reaching OSMR URL: {e}")
            return False

    def calculate_distance(self, child1: Tuple[float, float], child2: Tuple[float, float]) -> float:
        """Calculate distance between two points using OSRM."""
        if not self.is_osmr_url_reachable():
            raise ConnectionError("OSMR URL is not reachable. Please check the OSMR instance.")

        # Ensure correct order for OSRM
        c1 = self._ensure_lonlat(child1)
        c2 = self._ensure_lonlat(child2)

        url = self.osmr_url.format(*c1, *c2)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "Ok":
                return data["routes"][0]["distance"]  # meters
            else:
                logging.error(f"Invalid OSRM response: {data}")
                return float('inf')
        except Exception as e:
            logging.error(f"Error calculating distance: {e}")
            return float('inf')

    def create_routes_from_params(self, params: dict, coordinates_str: str):
        """Call the osmr module using defined params"""
        url = f"{self.osmr_url}{coordinates_str}"
        logging.info(f"OSMR Request URL: {url} with params: {params}")
        if not self.is_osmr_url_reachable(base_url=url):
            st.sidebar.error("OSMR URL is not reachable. Please check the OSMR instance.")
            return None
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()



    def create_distance_matrix_from_osmr(self, children_list: List[Child], school_element: School, update_progress: Callable) -> pd.DataFrame:
        """Create a distance matrix from the OSMR instance."""
        if not self.is_osmr_url_reachable():
            st.sidebar.error("OSMR URL is not reachable. Please check the OSMR instance.")
            return None

        # Initialize the distance matrix
        matrix_size = len(children_list) + 1  # +1 for the school
        distance_matrix = pd.DataFrame(index=range(matrix_size), columns=range(matrix_size))

        # Fill the distance matrix
        count = 0
        for i, child1 in enumerate(children_list):
            st.session_state["children_to_index"][child1.id] = i
            for j, child2 in enumerate(children_list):
                count += 1
                if i == j:
                    distance_matrix.iloc[i, j] = 0  # Distance to self is 0
                else:
                    distance_matrix.iloc[i, j] = self.calculate_distance((child1.lat, child1.lon), (child2.lat, child2.lon))
                # Update Progress
                if update_progress:
                    update_progress(count, matrix_size ** 2)


            # Distance between child and school
            distance_matrix.iloc[i, len(children_list)] = self.calculate_distance((child1.lat, child1.lon), (school_element.lat,
                                                                             school_element.lon))

        # Distance between school and all children
        for j, child in enumerate(children_list):
            count += 1
            distance_matrix.iloc[len(children_list), j] = self.calculate_distance((school_element.lat, school_element.lon),
                                                                             (child.lat, child.lon))
            # Update Progress
            if update_progress:
                update_progress(count, matrix_size ** 2)

        # Distance from school to itself is 0
        distance_matrix.iloc[len(children_list), len(children_list)] = 0

        return distance_matrix