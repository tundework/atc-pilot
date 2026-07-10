import functools
import logging, time
from flight_api import FlightAPI

logging.basicConfig(level=logging.INFO)
print = functools.partial(print, flush=True)   # survive nohup/pipe buffering

with FlightAPI(connection_string="tcp:127.0.0.1:5760") as fc:
    fc.ensure_sim_params()      # -w wipes params; never rely on ambient SITL state
    fc.set_mode("MANUAL")       # clear any leftover RTL — arming is refused mid-landing-sequence

    print("=== upload landing mission ===", flush=True)
    assert fc.upload_landing_mission(land_heading_deg=0)

    print("=== takeoff ===")
    fc.takeoff(50)
    fc.wait_for_altitude(50)

    print("=== fly_heading 090 ===")
    fc.fly_heading(90)
    time.sleep(30)
    print(f"heading now: {fc.get_position()['heading_deg']:.0f}")

    print("=== fly_heading 270 (reciprocal — a real turn) ===")
    fc.fly_heading(270)
    time.sleep(90)
    print(f"heading now: {fc.get_position()['heading_deg']:.0f}")

    print("=== RTL — should now actually LAND ===")
    fc.rtl()
    for i in range(24):
        time.sleep(15)
        pos = fc.get_position()
        print(f"t={15*(i+1):3d}s alt={pos['alt_m']:.1f}m mode={fc.master.flightmode}")
        if pos['alt_m'] < 2.0:
            print("touchdown detected")
            break
