from pymavlink import mavutil

# Connect to SITL
print("Connecting to SITL...")
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
master.wait_heartbeat()
print(f"Heartbeat from system (system {master.target_system} "
      f"component {master.target_component})")

# Read a few messages
for _ in range(5):
    msg = master.recv_match(blocking=True)
    print(msg)