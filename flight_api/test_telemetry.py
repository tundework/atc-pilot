import time
import json
import logging
from flight_api import FlightAPI

logging.basicConfig(level=logging.WARNING)  # quieter this time

with FlightAPI() as fc:
    fc.takeoff(50)

    for i in range(12):
        state = fc.get_state()
        print(json.dumps(state, indent=2))
        print(f"--- snapshot {i+1} ---")
        time.sleep(2)

    fc.set_mode("RTL")
    time.sleep(60)