import functools
import logging
import time

from flight_api import FlightAPI

logging.basicConfig(level=logging.INFO)
print = functools.partial(print, flush=True)

with FlightAPI() as fc:
    fc.ensure_sim_params()
    fc.set_mode("MANUAL")
    fc.upload_landing_mission(land_heading_deg=0)
    print("=== takeoff ===")
    fc.takeoff(50)
    fc.wait_for_altitude(50)
    print("=== airborne — holding here so an external process can kill -9 this one ===")
    while True:
        pos = fc.get_position()
        print(f"alive: alt={pos['alt_m']:.1f}m mode={fc.master.flightmode}")
        time.sleep(2)
