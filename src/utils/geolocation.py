from typing import List, Dict, Tuple, Union
from tqdm import tqdm
import logging
import googlemaps
import streamlit as st
import os
from src.optimizing.child import Child, Object, School
from src.geocoding.osmr_geocoding import GeoCoder

class GeoLocation:
    def __init__(self):
        if "geocoding_cache" not in st.session_state:
            st.session_state["geocoding_cache"] = {}
        self.cache = st.session_state["geocoding_cache"]
        self.geocoding_type = os.getenv("CODING_TYPE", "GM")

    @staticmethod
    def check_for_osmr_port_key_and_gmaps() -> Tuple[str, googlemaps.Client]:
        """Check whether the local OSM/Nominatim API URL is set"""
        osm_url = os.getenv("GEOCODED_URL", None)  # default lokal
        gmaps_api_key = os.getenv("GMAPS_API_KEY", None)
        if not osm_url and not gmaps_api_key:
            logging.error("Neither GEOCODED_URL nor GMAPS_API_KEY environment variables are set.")
            st.sidebar.error("Please set either GEOCODED_URL or GMAPS_API_KEY environment variable.")

        if not gmaps_api_key:
            return osm_url, gmaps_api_key

        return osm_url, googlemaps.Client(gmaps_api_key)

    def _format_address_from_object_or_string(self, childOrSchool: Union[Object, str]) -> str:
        """Format the address string for a Child object."""
        if isinstance(childOrSchool, School) or isinstance(childOrSchool, Child):
            return f"{childOrSchool.street} {childOrSchool.housenumber}, {childOrSchool.postcode} {childOrSchool.region}, Deutschland"
        elif isinstance(childOrSchool, list):
            print(f"###DEBUG: {childOrSchool}")
            return f"{childOrSchool[0]} {childOrSchool[1]}, {childOrSchool[2]} {childOrSchool[3]}, Deutschland"
        else:
            raise ValueError("Child or School Objekt must be List or Objekt to generate address")
    def geocode_single_adresse(self, address: dict, adress_name: str, childOrSchool: Object, osm_instance: GeoCoder):
        if adress_name in self.cache:
            lat, lon = self.cache[adress_name]
            childOrSchool.lat, childOrSchool.lon = lat, lon
        else:
            try:
                lat, lon = osm_instance.geocode(coding_type=self.geocoding_type, **address)
                if lat and lon:
                    self.cache[adress_name] = (lat, lon)
                    childOrSchool.lat, childOrSchool.lon = lat, lon
                else:
                    logging.warning(f"Geocoding failed for address: {adress_name}")
                    self.cache[adress_name] = (None, None)
            except Exception as e:
                logging.error(f"Error geocoding address {adress_name}: {e}")
                self.cache[adress_name] = (None, None)


    def geocode_addresses(self, children: List[Child], school: School) -> (List[Child], School):
        """Geocode a list of Child objects and update their lat/lon."""
        osm_instance = GeoCoder(*self.check_for_osmr_port_key_and_gmaps())

        for child in tqdm(children, desc="Geocoding addresses"):
            address = self._format_address_from_object_or_string(child)
            address_dict =  {"street": f"{child.street} {child.housenumber}", "city": child.region, "postcode": child.postcode}
            self.geocode_single_adresse(address_dict, address, child, osm_instance)
        # Geocode school address
        school_address = self._format_address_from_object_or_string(school)
        address_dict = {"street": f"{school.street} {school.housenumber}", "city": child.region,
                        "postcode": school.postcode}
        self.geocode_single_adresse(address_dict, school_address, school, osm_instance)
        with open("./addresses.txt", "w") as f:
            import json
            f.write(json.dumps(self.cache))
        for chld in children:
            if chld.lat is None or chld.lon is None:
                logging.info(f"Child ID {chld} could not be geocoded.")
        if school.lat is None or school.lon is None:
            logging.info(f"School ID {school} could not be geocoded.")
        return children, school

    def geocode_adresses_from_dict(self, params: Dict[str, List[str]]) -> Dict[str, Dict[str, float]]:
        """
        Geocode addresses based on separate address components (street, housenumber, city, etc.)
        Example:
            locations = GeoLocation().geocode_adresses_from_dict({
                "street": ["Main St", "Broadway"],
                "housenumber": ["10", "200"],
                "city": ["Berlin", "New York"]
            })
        Returns:
            dict: { "address string": {"lat": float, "lng": float}, ... }
        """

        osm_instance = GeoCoder(*self.check_for_osmr_port_key_and_gmaps())
        valid_locations = {}

        # Ensure all lists are the same length
        length = len(next(iter(params.values())))
        if not all(len(v) == length for v in params.values()):
            raise ValueError("All address component lists must have the same length")

        # Combine components into full address strings
        addresses = []
        full_addresses = []
        for i in range(length):
            parts = []
            adress_dict = {}
            for key in ["street", "housenumber", "postcode", "city", "country"]:
                if key in params and params[key][i]:
                    parts.append(str(params[key][i]))
                    adress_dict[key] = str(params[key][i])
            full_address = self._format_address_from_object_or_string(parts)
            full_addresses.append(full_address)
            addresses.append(adress_dict)

        num_cache_hits = 0
        for i, address in tqdm(enumerate(addresses), desc="Geocoding addresses from dict"):
            full_address = full_addresses[i]
            if full_address in self.cache:
                num_cache_hits += 1
                lat, lon = self.cache[full_address]
                if lat is not None and lon is not None:
                    valid_locations[full_address] = {"lat": lat, "lng": lon}
            else:
                try:
                    lat, lon = osm_instance.geocode(coding_type=self.geocoding_type, **address)
                    if lat and lon:
                        self.cache[full_address] = (lat, lon)
                        valid_locations[full_address] = {"lat": lat, "lng": lon}
                    else:
                        logging.warning(f"Geocoding failed for address: {full_address}")
                        self.cache[full_address] = (None, None)
                except Exception as e:
                    logging.error(f"Error geocoding address {full_address}: {e}")
                    self.cache[full_address] = (None, None)
        logging.info(f"Valid Location: {valid_locations}")

        logging.info(f"Geocoding completed with {num_cache_hits} cache hits out of {len(addresses)} addresses.")
        return valid_locations, full_addresses
