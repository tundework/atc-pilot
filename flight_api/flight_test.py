from pymavlink import mavutil
import time

# Connect
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
master.wait_heartbeat()
print("Connected.")

# Set mode to TAKEOFF (ArduPlane mode 13)
master.mav.set_mode_send(
    master.target_system,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    13,  # TAKEOFF mode
)
time.sleep(2)

# Arm the plane
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0, 1, 0, 0, 0, 0, 0, 0
)
print("Armed. Takeoff requested.")

# Wait and watch altitude climb
for _ in range(30):
    msg = master.recv_match(type='VFR_HUD', blocking=True, timeout=1)
    if msg:
        print(f"Alt: {msg.alt:.1f}m Airspeed: {msg.airspeed:.1f}m/s")
    time.sleep(1)

# Switch to RTL (mode 11) to come home
master.mav.set_mode_send(
    master.target_system,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    11,
)
print("RTL commanded. Watch it land.")