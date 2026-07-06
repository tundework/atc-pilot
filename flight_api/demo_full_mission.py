import logging
import time
from flight_api import FlightAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

with FlightAPI() as fc:
    print("=== TAKEOFF ===")
    fc.takeoff(50)
    fc.wait_for_altitude(50)

    print("=== CLIMB TO CRUISE ===")
    fc.goto_altitude(120)
    fc.wait_for_altitude(120)

    print("=== ATC: TURN HEADING 090 ===")
    fc.set_heading(90)
    time.sleep(20)

    print("=== HOLDING PATTERN ===")
    fc.loiter()
    time.sleep(20)

    print("=== ATC: CLEARED TO LAND ===")
    fc.rtl()
    time.sleep(90)

    print("=== FINAL STATE ===")
    print(fc.get_state())