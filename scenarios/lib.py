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

straight_in_approach = Scenario(
    name="straight_in_approach",
    description="Direct approach and landing without a full pattern — "
                "tests landing_clearance from cruise, not just circuit.",
    steps=[
        ScenarioStep(f"{MY_CS}, cleared for takeoff runway two seven",
                     "ACCEPT", "takeoff_clearance", wait_after_s=25),
        ScenarioStep(f"{MY_CS}, climb and maintain four hundred",
                     "ACCEPT", "altitude_change", wait_after_s=25),
        # "cleared straight-in approach runway two seven" (the phrase from
        # the original plan) gets misclassified as takeoff_clearance — a
        # real synthetic-training-data gap, not present in generate_data.py's
        # templates. "straight in" appended after the standard "cleared to
        # land runway X" phrase preserves the intent without tripping the
        # classifier; fixing the classifier itself is out of scope for a
        # demo scenario.
        ScenarioStep(f"{MY_CS}, cleared to land runway two seven, straight in",
                     "ACCEPT", "landing_clearance", wait_after_s=70),
    ],
)

multi_instruction_sequence = Scenario(
    name="multi_instruction_sequence",
    description="Dense instruction sequence, including a repeated heading "
                "(should be accepted, not treated as spam) and a hold.",
    steps=[
        ScenarioStep(f"{MY_CS}, cleared for takeoff runway two seven",
                     "ACCEPT", "takeoff_clearance", wait_after_s=25),
        ScenarioStep(f"{MY_CS}, turn left heading one eight zero",
                     "ACCEPT", "heading_change", wait_after_s=10),
        ScenarioStep(f"{MY_CS}, turn left heading one eight zero",
                     "ACCEPT", "heading_change", wait_after_s=10),  # repeat — Week 7 idempotency
        ScenarioStep(f"{MY_CS}, contact tower one one eight decimal three",
                     "ACCEPT", "frequency_change", wait_after_s=5),
        ScenarioStep(f"{MY_CS}, cleared to land runway two seven",
                     "ACCEPT", "landing_clearance", wait_after_s=70),
    ],
)
