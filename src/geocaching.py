from threading import Lock
from typing import Dict, List, Optional
import logging


class GeocodingCache:
    def __init__(self):
        self.cache = {}
        self.lock = Lock()

    def get_location(self, gmaps, address: str) -> Optional[Dict]:
        with self.lock:
            if address in self.cache:
                logging.info(f"✅ Cache Hit on: {address}")
                return self.cache[address]

        try:
            logging.info(f"🔍 Geocoding: {address}")
            result = gmaps.geocode(address)
            if result:
                location = result[0]['geometry']['location']
                with self.lock:
                    self.cache[address] = location
                logging.info(f"✅ Geocoded: {address} -> {location['lat']:.4f}, {location['lng']:.4f}")
                return location
        except Exception as e:
            logging.error(f"❌ Error when Geocoding adress: {address} with: {e}")
        return None


    def geocode_addresses_batch(self, addresses: List[str], gmaps) -> Dict[str, Dict]:
        """Geocodiert alle Adressen und cached die Ergebnisse"""
        locations = {}
        uncached_addresses = []

        # Prüfe welche Adressen bereits gecacht sind
        for address in addresses:
            cached_location = self.get_location(gmaps, address)
            if cached_location:
                locations[address] = cached_location
            else:
                uncached_addresses.append(address)

        logging.info(f"📍 {len(addresses) - len(uncached_addresses)}/{len(addresses)} Adressen aus Cache")
        logging.info(f"🔍 {len(uncached_addresses)} neue API Calls erforderlich")

        # Geocodiere nur uncached Adressen
        for i, address in enumerate(uncached_addresses):
            location = self.get_location(gmaps, address)
            if location:
                locations[address] = location

            # Progress Update
            if (i + 1) % 5 == 0 or i == len(uncached_addresses) - 1:
                logging.info(f"⏳ Geocoding Progress: {i + 1}/{len(uncached_addresses)}")

        return locations