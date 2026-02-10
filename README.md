# Met Ticket Monitor

## What it is
A small, cron-friendly Python script to monitor **Met Opera student ticket availability** and alert when new performances appear.

This is built to be:
- **simple** (one script, minimal dependencies)
- **automatable** (manual run or scheduled)
- **safe** (no secrets committed; state stored locally)

## How to run (≤ 3 commands)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 src/met_ticket_monitor.py
```

(Or schedule it via cron; see below.)

## Example output
- `No new Met student ticket performances. (count=0)`
- `New Met Student Tickets: ...`

## Notes
- Fetches the current set of student-ticket performances
- Compares against a local state file
- Prints a clear message when new performances are detected

## Run (cron)
Example (hourly):
```cron
0 * * * * /usr/bin/python3 /path/to/met-ticket-monitor/src/met_ticket_monitor.py >> /path/to/met-ticket-monitor/monitor.log 2>&1
```

## Configuration
- No secrets are required for the basic monitor.
- State is stored in a local JSON file (e.g., `state.json`).

## Repo layout
- `src/` – monitor script(s)
- `demo/` – sample inputs/outputs
- `scripts/` – wrappers for cron/notifications (optional)

## TODO
- Add a small notifier adapter (Telegram/email) behind a flag
- Add a unit test for the diff logic
- Add a short README section explaining the source URL + how to validate results

---

Maintained by **Anders Van Winkle**
