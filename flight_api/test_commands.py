import logging
import time
from flight_api import FlightAPI

logging.basicConfig(level=logging.INFO)

with FlightAPI() as fc:
    fc.takeoff(50)
    time.sleep(25)

    print("=== ATC: climb and maintain 100 ===")
    fc.goto_altitude(100)
    time.sleep(25)

    print("=== ATC: turn heading 270 ===")
    fc.set_heading(270)
    time.sleep(20)

    print("=== ATC: proceed to waypoint ===")
    pos = fc.get_position()
    # a point ~500m north of wherever we are now
    fc.goto_waypoint(pos["lat"] + 0.0045, pos["lon"], 100)
    time.sleep(30)

    print("=== RTL ===")
    fc.set_mode("RTL")
    time.sleep(90)