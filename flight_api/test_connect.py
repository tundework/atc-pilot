import logging
from flight_api import FlightAPI

logging.basicConfig(level=logging.INFO)

with FlightAPI() as fc:
    print(f"Connected. System ID: {fc.master.target_system}")