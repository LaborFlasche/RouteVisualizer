import logging
import googlemaps
import requests

class GeoCoder:
    def __init__(self, base_url: str, gmaps: googlemaps.Client = None):
        self.base_url = base_url.rstrip("/")
        self.gmaps = gmaps

    def geocode(self, coding_type: str, **params):
        """Return a list of geocoding results from local Nominatim (structured query)"""
        if coding_type == "LOCAL":
            return self.geocode_local(**params)
        elif coding_type == "GM":
            address = f"{params.get('street', '')}, {params.get('city', '')}, {params.get('postcode', '')}"
            return self.geocode_google_maps(address)
        return None

    def geocode_local(self, **params):
        if "city" in params:
            params["city"] = params["city"] if "-" not in params["city"] else params["city"].split("-")[0].strip()
        try:
            if "format" not in params:
                params["format"] = "json"

            response = requests.get(f"{self.base_url}/search", params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result and len(result) > 0:
                lat = float(result[0]["lat"])
                lon = float(result[0]["lon"])
                return lat, lon
            return None, None
        except Exception as e:
            logging.info(f"Error calling local geocoder: {e}")
            return None, None

    def geocode_google_maps(self, address):
        """Geocode an address using the Google Maps API."""
        try:
            result = self.gmaps.geocode(address)
            if result:
                location = result[0]["geometry"]["location"]
                return location["lat"], location["lng"]
        except Exception as e:
            logging.info(f"Error geocoding with Google Maps: {e}")
        return None, None
