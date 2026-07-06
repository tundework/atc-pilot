import logging
import time
from flight_api import FlightAPI

logging.basicConfig(level=logging.INFO)

with FlightAPI() as fc:
    fc.takeoff(altitude_m=50)
    time.sleep(30)   # watch it climb
    fc.set_mode("RTL")
    time.sleep(60)   # let it come home and land