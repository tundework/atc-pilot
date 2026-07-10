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

    DEFAULT_CONNECTIONS = (
        "tcp:127.0.0.1:5760",
        "tcp:127.0.0.1:5763",
        "udp:127.0.0.1:14550",
    )

    def __init__(self, connection_string=None):
        self.connection_string = connection_string
        self.master = None

    def connect(self, timeout=30):
        """Connect to the autopilot and wait for heartbeat.

        When no explicit connection string is supplied, try the common
        local SITL endpoints in order: direct TCP on 5760/5763 (no MAVProxy)
        and the legacy UDP 14550 relay.
        """
        candidates = [self.connection_string] if self.connection_string else list(self.DEFAULT_CONNECTIONS)
        attempt_timeout = timeout if self.connection_string else max(2, min(5, timeout // max(1, len(candidates))))
        last_error = None

        for candidate in candidates:
            logger.info(f"Connecting to {candidate}")
            try:
                self.master = mavutil.mavlink_connection(candidate)
                heartbeat = self.master.wait_heartbeat(timeout=attempt_timeout)
                if heartbeat is None or self.master.target_system <= 0:
                    raise RuntimeError("No valid heartbeat received")
                self.connection_string = candidate
                logger.info(
                    f"Heartbeat from system {self.master.target_system} "
                    f"component {self.master.target_component}"
                )
                return True
            except Exception as exc:  # pragma: no cover - depends on runtime transport
                last_error = exc
                logger.warning(f"Connection attempt failed for {candidate}: {exc}")
                if self.master is not None:
                    self.master.close()
                    self.master = None

        raise RuntimeError(
            f"Could not connect to any MAVLink endpoint from {candidates}: "
            f"{last_error}"
        )

    def disconnect(self):
        """Close the connection cleanly."""
        if self.master:
            self.master.close()
            self.master = None
            logger.info("Disconnected")
    def set_mode(self, mode_name, timeout=5, retries=3):
        """Switch flight mode and VERIFY via HEARTBEAT.custom_mode.
        set_mode_send is fire-and-forget; ArduPilot can silently ignore a
        mode change (e.g. mid-landing-sequence), so a caller trusting the
        send alone can believe it's in RTL while it's still in GUIDED."""
        if mode_name not in PLANE_MODES:
            raise ValueError(f"Unknown mode: {mode_name}")
        mode_id = PLANE_MODES[mode_name]
        for _ in range(retries):
            self.master.mav.set_mode_send(
                self.master.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_id,
            )
            deadline = time.time() + timeout
            while time.time() < deadline:
                hb = self.master.recv_match(type="HEARTBEAT", blocking=True,
                                            timeout=1)
                if hb and hb.custom_mode == mode_id:
                    logger.info(f"Mode set to {mode_name} (verified)")
                    return
        raise RuntimeError(f"Mode change to {mode_name} not confirmed by "
                            f"HEARTBEAT after {retries} attempts")

    def set_param(self, name: str, value: float, retries=3) -> bool:
        """Set a parameter and VERIFY the echoed PARAM_VALUE matches."""
        for _ in range(retries):
            self.master.mav.param_set_send(
                self.master.target_system, self.master.target_component,
                name.encode(), float(value),
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
            deadline = time.time() + 3
            while time.time() < deadline:
                msg = self.master.recv_match(type="PARAM_VALUE",
                                             blocking=True, timeout=1)
                if msg and msg.param_id.rstrip("\x00") == name:
                    if abs(msg.param_value - value) < 0.5:
                        logger.info(f"param {name} = {msg.param_value}")
                        return True
                    break   # echoed wrong value; retry the set
        logger.error(f"param {name} set FAILED")
        return False

    def ensure_sim_params(self):
        """Self-provision the SITL params this project depends on.
        NEVER call on real hardware — skipping arming checks is sim-only.

        This ArduPilot build (4.8.0-dev) renamed ARMING_CHECK -> ARMING_SKIPCHK
        (upstream's 4.7 param conversion) and inverted its meaning: it's now a
        bitmask of checks to SKIP, not checks to run, so 0 no longer means
        "skip everything". 2097150 = bits 1..20 (AP_Arming::Check, everything
        except the unused bit 0 and the CHECK_LAST sentinel bit 21) set.
        """
        if not self.connection_string.startswith(("udp:", "tcp:127.0.0.1")):
            raise RuntimeError(
                "ensure_sim_params() refused: connection does not look like "
                "SITL. This sets ARMING_SKIPCHK to bypass ALL pre-arm safety "
                "checks and must never run against real hardware.")
        ok = all([
            self.set_param("ARMING_SKIPCHK", 2097150),
            self.set_param("RTL_AUTOLAND", 2),
            self.set_param("WP_RADIUS", 30),
        ])
        if not ok:
            raise RuntimeError("SIM param provisioning failed")

    def arm(self, timeout=5):
        """Arm and VERIFY via COMMAND_ACK + armed bit. Raises on refusal."""
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, 0, 0, 0, 0, 0, 0)
        ack = self.master.recv_match(type="COMMAND_ACK", blocking=True,
                                     timeout=timeout)
        if ack is None or ack.result != 0:
            # Drain STATUSTEXT for the pre-arm reason before raising
            reasons = []
            deadline = time.time() + 2
            while time.time() < deadline:
                st = self.master.recv_match(type="STATUSTEXT",
                                            blocking=True, timeout=0.5)
                if st:
                    reasons.append(st.text)
            raise RuntimeError(
                f"Arming REFUSED (ack={ack.result if ack else 'none'}): "
                f"{'; '.join(reasons) or 'no reason reported'}")
        # motors_armed() reads a cached HEARTBEAT; pump for a fresh one so
        # we don't check a pre-arm snapshot that just hasn't updated yet.
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.master.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
            if self.master.motors_armed():
                break
        else:
            raise RuntimeError("Arm ack OK but motors_armed bit not set")
        logger.info("Armed (verified)")

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

    def get_position(self, require_fix=False, timeout=15):
        """Get current GPS position as a dict.

        Drains any backlog of queued GLOBAL_POSITION_INT messages and
        returns the freshest one. recv_match returns the oldest queued
        match otherwise — right after connect, before GPS lock, a stale
        lat=0/lon=0 message can sit at the front of the buffer and get
        returned instead of a current reading.

        require_fix=True actively polls until a plausible (non-zero,
        non-null-island) reading arrives, raising on timeout instead of
        silently returning (0, 0) — this was the root cause of
        upload_landing_mission() once building a mission around Null
        Island because "home" was read before GPS/EKF had converged."""
        deadline = time.time() + timeout if require_fix else None
        while True:
            msg = self.master.recv_match(
                type="GLOBAL_POSITION_INT", blocking=True, timeout=5
            )
            if msg is None:
                if require_fix and time.time() < deadline:
                    continue
                raise TimeoutError("No GPS position received")
            while True:
                newer = self.master.recv_match(type="GLOBAL_POSITION_INT", blocking=False)
                if newer is None:
                    break
                msg = newer
            pos = {
                "lat": msg.lat / 1e7,
                "lon": msg.lon / 1e7,
                "alt_m": msg.relative_alt / 1000.0,
                "heading_deg": msg.hdg / 100.0,
            }
            implausible = abs(pos["lat"]) < 0.001 and abs(pos["lon"]) < 0.001
            if not implausible or not require_fix:
                return pos
            if time.time() >= deadline:
                raise TimeoutError(
                    f"GPS position still (0,0)-ish after {timeout}s — "
                    f"EKF/GPS never converged")
            logger.warning("Discarding implausible (0,0) GPS reading, "
                           "waiting for real fix...")
            time.sleep(0.5)
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
        """Fly to a GPS coordinate.

        ArduPlane's SET_POSITION_TARGET_GLOBAL_INT handler
        (GCS_MAVLink_Plane.cpp) only reads the altitude field out of that
        message and silently drops lat/lon — unlike Copter, it never calls
        set_guided_WP() from it. The plane just keeps loitering at its
        existing GUIDED point. MAV_CMD_DO_REPOSITION is the message ArduPlane
        actually wires to set_guided_WP(), so that's what a real horizontal
        fly-to has to use.
        """
        self.master.mav.command_int_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            mavutil.mavlink.MAV_CMD_DO_REPOSITION,
            0, 0,
            -1,  # param1: airspeed, -1 = no change
            mavutil.mavlink.MAV_DO_REPOSITION_FLAGS_CHANGE_MODE,  # param2
            0, 0,  # param3 radius, param4 yaw: no change
            int(lat * 1e7), int(lon * 1e7), altitude_m,
        )
        ack = self.master.recv_match(type="COMMAND_ACK", blocking=True, timeout=3)
        if ack is None or ack.command != mavutil.mavlink.MAV_CMD_DO_REPOSITION or ack.result != 0:
            logger.warning(f"DO_REPOSITION ack: {ack}")
        logger.info(f"Waypoint: ({lat}, {lon}) at {altitude_m}m")
    def fly_heading(self, heading_deg, distance_m=2000):
        """Fly a compass heading by projecting a waypoint distance_m out
        along that heading from the current position. Workaround for
        ArduPlane's unreliable GUIDED-mode yaw on fixed-wing. Holds current
        altitude — a heading instruction is not an altitude instruction."""
        import math
        pos = self.get_position()
        lat0 = math.radians(pos["lat"])
        hdg = math.radians(heading_deg)

        # Equirectangular projection — plenty accurate at 2km
        R = 6371000.0
        dlat = (distance_m * math.cos(hdg)) / R
        dlon = (distance_m * math.sin(hdg)) / (R * math.cos(lat0))

        target_lat = pos["lat"] + math.degrees(dlat)
        target_lon = pos["lon"] + math.degrees(dlon)
        self.goto_waypoint(target_lat, target_lon, pos["alt_m"])
        logger.info(f"fly_heading {heading_deg}: waypoint projected "
                    f"{distance_m}m out at ({target_lat:.5f}, {target_lon:.5f})")

    def upload_landing_mission(self, land_heading_deg=0):
        """Upload a minimal mission: DO_LAND_START + approach + LAND at home.
        Gives RTL_AUTOLAND=2 a landing sequence to execute."""
        import math
        home = self.get_position(require_fix=True, timeout=20)
        if abs(home["lat"]) < 0.001 and abs(home["lon"]) < 0.001:
            raise RuntimeError(
                f"Refusing to build a landing mission around implausible "
                f"home position {home} — GPS/EKF likely not settled")
        R = 6371000.0
        lat0 = math.radians(home["lat"])

        def offset(dist_m, brg_deg):
            b = math.radians(brg_deg)
            dlat = (dist_m * math.cos(b)) / R
            dlon = (dist_m * math.sin(b)) / (R * math.cos(lat0))
            return home["lat"] + math.degrees(dlat), home["lon"] + math.degrees(dlon)

        # Approach point: 400m out on the reciprocal of landing heading, 40m up
        app_lat, app_lon = offset(400, (land_heading_deg + 180) % 360)

        mission = [
            # (seq, command, p1..p4, lat, lon, alt)
            (0, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0,
             home["lat"], home["lon"], 0),                       # home placeholder
            (1, mavutil.mavlink.MAV_CMD_DO_LAND_START, 0, 0, 0, 0, 0, 0, 0),
            (2, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0,
             app_lat, app_lon, 40),                              # approach gate
            (3, mavutil.mavlink.MAV_CMD_NAV_LAND, 0, 0, 0, 0,
             home["lat"], home["lon"], 0),                       # touchdown
        ]

        self.master.waypoint_clear_all_send()
        time.sleep(1)
        self.master.waypoint_count_send(len(mission))
        for _ in range(len(mission)):
            msg = self.master.recv_match(type=["MISSION_REQUEST",
                                               "MISSION_REQUEST_INT"],
                                         blocking=True, timeout=5)
            if msg is None:
                raise TimeoutError("Mission upload: no request from autopilot")
            seq = msg.seq
            s, cmd, p1, p2, p3, p4, lat, lon, alt = mission[seq]
            if msg.get_type() == "MISSION_REQUEST_INT":
                self.master.mav.mission_item_int_send(
                    self.master.target_system, self.master.target_component,
                    seq, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    cmd, 0, 1, p1, p2, p3, p4,
                    int(lat * 1e7), int(lon * 1e7), alt)
            else:
                # Legacy MISSION_REQUEST expects MISSION_ITEM with lat/lon as
                # plain floats in degrees, not int32*1e7 — replying with the
                # scaled-int encoding here silently corrupts the coordinate
                # (observed: autopilot navigated toward ~(0,0) instead of the
                # intended point).
                self.master.mav.mission_item_send(
                    self.master.target_system, self.master.target_component,
                    seq, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    cmd, 0, 1, p1, p2, p3, p4,
                    lat, lon, alt)
        ack = self.master.recv_match(type="MISSION_ACK", blocking=True, timeout=5)
        logger.info(f"Landing mission uploaded, ack={ack.type if ack else 'NONE'}")
        return ack is not None and ack.type == 0

    def get_attitude(self):
        """Get current pitch, roll, yaw in degrees."""
        import math
        msg = self.master.recv_match(
            type="ATTITUDE", blocking=True, timeout=5
        )
        if msg is None:
            return {"roll_deg": 0.0, "pitch_deg": 0.0, "yaw_deg": 0.0}
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
        if msg is None:
            return {"airspeed": 0.0, "groundspeed": 0.0, "throttle_pct": 0.0, "climb_rate": 0.0}
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
        if msg is None:
            return "UNKNOWN(0)"
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