import logging, time, sys
sys.path.insert(0, "/home/babat/atc-pilot/flight_api")
from flight_api import FlightAPI

logging.basicConfig(level=logging.INFO)

with FlightAPI(connection_string="tcp:127.0.0.1:5760") as fc:
    fc.ensure_sim_params()
    fc.set_mode("MANUAL")
    assert fc.upload_landing_mission(land_heading_deg=0)
    fc.takeoff(50)
    fc.wait_for_altitude(50)
    print("=== RTL immediately (no heading detours, to isolate landing behavior) ===")
    fc.rtl()
    for i in range(40):
        time.sleep(15)
        pos = fc.get_position()
        nco = fc.master.recv_match(type="NAV_CONTROLLER_OUTPUT", blocking=True, timeout=2)
        cur = fc.master.recv_match(type="MISSION_CURRENT", blocking=True, timeout=2)
        print(f"t={15*(i+1):4d}s alt={pos['alt_m']:.1f}m mode={fc.master.flightmode} "
              f"wp_dist={nco.wp_dist if nco else None} seq={cur.seq if cur else None}")
        if pos['alt_m'] < 2.0:
            print("TOUCHDOWN")
            break
