# Running atc-pilot

## Every session, in order

1. **SITL** (Terminal 1, stays open):
   ```
   cd ~/ardupilot/ArduPlane && sim_vehicle.py -w --no-mavproxy
   ```
   Wait for a GPS 3D fix (check `/tmp/ArduPlane.log`, or connect Mission
   Planner on Windows to `tcp:127.0.0.1:5763` for a visual confirmation).
   Do **not** launch with `--console --map`/MAVProxy alongside this — the
   worker connects directly to `tcp:127.0.0.1:5760`, and MAVProxy holding
   that same port as its own exclusive client causes silent connection
   corruption (observed directly this project: heartbeats reporting
   `system 0`, every param-set failing). Use Mission Planner on :5763 for
   visuals instead — that's a separate, uncontended port.

2. **Main system** (Terminal 2):
   ```
   cd ~/atc-pilot && python main.py
   ```
   Press Enter once SITL has a fix. Wait for `System up.` — that means the
   watcher and worker are both running, SITL params are provisioned, a
   landing mission is uploaded, and the aircraft is armed-ready on the
   ground.

3. **Windows capture** — run `win_capture.ps1` from a Windows PowerShell
   window (not inside WSL — mic passthrough doesn't work there):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\win_capture.ps1
   ```
   Speak your instruction during the 8-second recording window. Repeat per
   transmission.

## Shutdown

Ctrl+C in the `main.py` terminal — this cleanly terminates both the watcher
and worker. Then Ctrl+C in the SITL terminal.

Verify nothing orphaned survived:
```
pgrep -af watch.py worker.py
```
Should print nothing. If it doesn't:
```
pkill -9 -f sim_vehicle.py; pkill -9 -f arduplane
pkill -9 -f watch.py; pkill -9 -f worker.py
```

## Sanity checks before trusting a run

- `supervisor/decisions.jsonl` — tail it, confirm phase transitions look
  sane (clearance-driven and physics-driven transitions should both appear,
  and in the right order).
- Mission Planner's map — visual confirmation should match the log.
- Terminal 2's live trace — every recognized transmission prints
  `HEARD` / `PARSED` / `SUPERVISOR` / `ACTION` (or a phase-gate `REJECT`
  with a named check).

## Known gotchas (see CLAUDE.md for full detail)

- `-w` on SITL relaunch wipes ALL params — the worker/`ensure_sim_params()`
  self-provisions on every startup; never rely on ambient SITL state
  surviving a relaunch.
- Arming is refused while the autopilot thinks it's mid-landing-sequence
  (leftover RTL mode from a killed run) — `main.py`'s worker startup
  already resets to `MANUAL` before uploading the landing mission, but if
  you're driving `FlightAPI` manually outside `main.py`, do this yourself
  first.
- A transmission with no callsign at all (not even a shortened form) is
  correctly ignored, not guessed at — silence in Terminal 2 for a spoken
  instruction usually means this, not a crash.
