# Scenario clips

Video assets for each scenario in the library (see
[scenarios/README.md](../../scenarios/README.md)), for the Week 11-12
video/blog.

For each scenario, keep:
- A screen recording of one clean run (Mission Planner map + Terminal 3's
  live trace, side by side if possible) — capture manually while running
  `python run_one.py <name>` against SITL; this isn't something that can
  be generated from a log file.
- The corresponding `results.json` from that run (copied from
  `scenarios/out/<name>/results.json`, which is gitignored/regenerated
  per run and not committed itself).

The go_around scenario is the one really worth a few takes to get the
timing dramatic on camera — see the README's note on tuning
`wait_after_s` so the go-around call visibly happens while the plane is
still in the air, headed for the runway.
