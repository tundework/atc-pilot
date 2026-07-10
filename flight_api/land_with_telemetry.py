import csv
import functools
import logging
import sys
import time

from flight_api import FlightAPI

logging.basicConfig(level=logging.INFO)
print = functools.partial(print, flush=True)

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "telemetry.csv"

with FlightAPI(connection_string="tcp:127.0.0.1:5760") as fc:
    fc.ensure_sim_params()
    fc.set_mode("MANUAL")

    print("=== upload landing mission ===")
    assert fc.upload_landing_mission(land_heading_deg=0)

    print("=== takeoff ===")
    fc.takeoff(50)
    fc.wait_for_altitude(50)

    print("=== RTL (fly back and land) ===")
    fc.rtl()

    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "mode", "alt_m", "lat", "lon", "volt", "rem_pct", "wp_dist", "seq"])
        t0 = time.time()
        for i in range(80):  # up to 20 min
            time.sleep(15)
            pos = fc.get_position()
            batt = fc.master.recv_match(type="BATTERY_STATUS", blocking=True, timeout=3)
            nco = fc.master.recv_match(type="NAV_CONTROLLER_OUTPUT", blocking=True, timeout=3)
            cur = fc.master.recv_match(type="MISSION_CURRENT", blocking=True, timeout=3)
            volt = batt.voltages[0] / 1000.0 if batt and batt.voltages[0] != 65535 else None
            rem = batt.battery_remaining if batt else None
            row = [
                round(time.time() - t0, 1),
                fc.master.flightmode,
                round(pos["alt_m"], 1),
                pos["lat"], pos["lon"],
                volt, rem,
                nco.wp_dist if nco else None,
                cur.seq if cur else None,
            ]
            w.writerow(row)
            f.flush()
            print(f"t={row[0]:6.1f}s mode={row[1]:8s} alt={row[2]:5.1f}m "
                  f"volt={volt} rem%={rem} wp_dist={row[7]} seq={row[8]}")
            if pos["alt_m"] < 2.0 and i > 2:
                print("TOUCHDOWN")
                break
