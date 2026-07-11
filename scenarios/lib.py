from scenario import Scenario, ScenarioStep

MY_CS = "Cessna one seven two alpha bravo"

pattern_flight = Scenario(
    name="pattern_flight",
    description="Standard traffic-pattern flight: takeoff, one circuit, land.",
    steps=[
        ScenarioStep(f"{MY_CS}, cleared for takeoff runway two seven",
                     "ACCEPT", "takeoff_clearance", wait_after_s=25),
        # 400ft (~122m): must stay inside supervisor.ENVELOPE's alt range
        # ([30, 150]m for this sim) — "one thousand" (305m) and "one
        # thousand five hundred" (457m) both exceed it and get correctly
        # REJECTed, a lesson already paid for in Week 7 Day 4.
        ScenarioStep(f"{MY_CS}, turn crosswind, climb and maintain four hundred",
                     "ACCEPT", "altitude_change", wait_after_s=20),
        ScenarioStep(f"{MY_CS}, cleared to land runway two seven",
                     "ACCEPT", "landing_clearance", wait_after_s=70),
    ],
)

vectors_and_altitude = Scenario(
    name="vectors_and_altitude",
    description="ATC vectors the aircraft through several heading and "
                "altitude changes before clearing to land.",
    steps=[
        ScenarioStep(f"{MY_CS}, cleared for takeoff runway two seven",
                     "ACCEPT", "takeoff_clearance", wait_after_s=25),
        ScenarioStep(f"{MY_CS}, turn left heading two seven zero",
                     "ACCEPT", "heading_change", wait_after_s=15),
        ScenarioStep(f"{MY_CS}, climb and maintain four hundred",
                     "ACCEPT", "altitude_change", wait_after_s=15),
        ScenarioStep(f"{MY_CS}, turn right heading zero niner zero",
                     "ACCEPT", "heading_change", wait_after_s=15),
        ScenarioStep(f"{MY_CS}, cleared to land runway two seven",
                     "ACCEPT", "landing_clearance", wait_after_s=70),
    ],
)
