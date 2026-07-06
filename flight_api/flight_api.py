from pymavlink import mavutil
import time
import logging

logger = logging.getLogger(__name__)

# ArduPlane mode numbers
PLANE_MODES = {
    "MANUAL": 0,
    "CIRCLE": 1,
    "STABILIZE": 2,
    "FBWA": 5,
    "FBWB": 6,
    "AUTO": 10,
    "RTL": 11,
    "LOITER": 12,
    "TAKEOFF": 13,
    "GUIDED": 15,
}


class FlightAPI:
    """Clean Python interface to ArduPlane via MAVLink."""

    def __init__(self, connection_string="udp:127.0.0.1:14550"):
        self.connection_string = connection_string
        self.master = None

    def connect(self, timeout=30):
        """Connect to the autopilot and wait for heartbeat."""
        logger.info(f"Connecting to {self.connection_string}")
        self.master = mavutil.mavlink_connection(self.connection_string)
        self.master.wait_heartbeat(timeout=timeout)
        logger.info(
            f"Heartbeat from system {self.master.target_system} "
            f"component {self.master.target_component}"
        )
        return True

    def disconnect(self):
        """Close the connection cleanly."""
        if self.master:
            self.master.close()
            self.master = None
            logger.info("Disconnected")
    def set_mode(self, mode_name):
        """Switch flight mode. Example: set_mode("AUTO")."""
        if mode_name not in PLANE_MODES:
            raise ValueError(f"Unknown mode: {mode_name}")
        mode_id = PLANE_MODES[mode_name]
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
        )
        logger.info(f"Mode set to {mode_name}")
        time.sleep(1)

    def arm(self):
        """Arm the motors."""
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, 0, 0, 0, 0, 0, 0,
        )
        logger.info("Armed")
        time.sleep(1)

    def disarm(self):
        """Disarm the motors."""
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, 0, 0, 0, 0, 0, 0,
        )
        logger.info("Disarmed")

    def takeoff(self, altitude_m=50, pitch_deg=15):
        """Switch to TAKEOFF mode, arm, and climb to target altitude."""
        self.set_mode("TAKEOFF")
        self.arm()
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, pitch_deg, 0, 0, 0, 0, 0, altitude_m,
        )
        logger.info(f"Takeoff to {altitude_m}m commanded")

    def get_position(self):
        """Get current GPS position as a dict."""
        msg = self.master.recv_match(
            type="GLOBAL_POSITION_INT", blocking=True, timeout=5
        )
        if msg is None:
            raise TimeoutError("No GPS position received")
        return {
            "lat": msg.lat / 1e7,
            "lon": msg.lon / 1e7,
            "alt_m": msg.relative_alt / 1000.0,
            "heading_deg": msg.hdg / 100.0,
        }    
    def goto_altitude(self, altitude_m):
        """Climb or descend to a target altitude (relative to home)."""
        self.set_mode("GUIDED")
        pos = self.get_position()
        self.master.mav.set_position_target_global_int_send(
            0,
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            0b110111111000,  # only position fields active
            int(pos["lat"] * 1e7),
            int(pos["lon"] * 1e7),
            altitude_m,
            0, 0, 0, 0, 0, 0, 0, 0,
        )
        logger.info(f"Target altitude: {altitude_m}m")

    def set_heading(self, heading_deg):
        """Turn to a compass heading in GUIDED mode."""
        self.set_mode("GUIDED")
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_CONDITION_YAW,
            0, heading_deg, 10, 1, 0, 0, 0, 0,
        )
        logger.info(f"Heading commanded: {heading_deg} deg")

    def goto_waypoint(self, lat, lon, altitude_m):
        """Fly to a GPS coordinate."""
        self.set_mode("GUIDED")
        self.master.mav.set_position_target_global_int_send(
            0,
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            0b110111111000,
            int(lat * 1e7),
            int(lon * 1e7),
            altitude_m,
            0, 0, 0, 0, 0, 0, 0, 0,
        )
        logger.info(f"Waypoint: ({lat}, {lon}) at {altitude_m}m")
    def get_attitude(self):
        """Get current pitch, roll, yaw in degrees."""
        import math
        msg = self.master.recv_match(
            type="ATTITUDE", blocking=True, timeout=5
        )
        return {
            "roll_deg": math.degrees(msg.roll),
            "pitch_deg": math.degrees(msg.pitch),
            "yaw_deg": math.degrees(msg.yaw),
        }

    def get_velocity(self):
        """Get airspeed and groundspeed in m/s."""
        msg = self.master.recv_match(
            type="VFR_HUD", blocking=True, timeout=5
        )
        return {
            "airspeed": msg.airspeed,
            "groundspeed": msg.groundspeed,
            "throttle_pct": msg.throttle,
            "climb_rate": msg.climb,
        }

    def get_mode(self):
        """Get current flight mode as a string."""
        msg = self.master.recv_match(
            type="HEARTBEAT", blocking=True, timeout=5
        )
        mode_id = msg.custom_mode
        for name, mid in PLANE_MODES.items():
            if mid == mode_id:
                return name
        return f"UNKNOWN({mode_id})"

    def get_state(self):
        """Snapshot of everything at once."""
        return {
            "position": self.get_position(),
            "attitude": self.get_attitude(),
            "velocity": self.get_velocity(),
            "mode": self.get_mode(),
        }
    def rtl(self):
        """Return to launch. With RTL_AUTOLAND=2, this also lands."""
        self.set_mode("RTL")

    def land(self):
        """Trigger autoland via AUTO mode (requires LAND in mission)."""
        self.set_mode("AUTO")

    def loiter(self):
        """Circle in place — holding pattern or emergency pause."""
        self.set_mode("LOITER")

    def wait_for_altitude(self, target_m, tolerance_m=5, timeout=120):
        """Block until the plane reaches an altitude (within tolerance)."""
        start = time.time()
        while time.time() - start < timeout:
            pos = self.get_position()
            if abs(pos["alt_m"] - target_m) < tolerance_m:
                logger.info(f"Reached {target_m}m")
                return True
            time.sleep(1)
        logger.warning(f"Timeout waiting for {target_m}m altitude")
        return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()