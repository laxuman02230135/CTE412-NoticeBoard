import json
import sys
from datetime import datetime
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("Usage: python mixed-window.py <monitor-log>")

old_times = []
new_times = []

with Path(sys.argv[1]).open(encoding="utf-8-sig") as log:
    for line in log:
        parts = line.strip().split(" ", 2)
        if len(parts) != 3 or parts[1] != "OK":
            continue

        timestamp, _, body = parts
        version = json.loads(body)["version"]
        moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        if version == "1.0.0":
            old_times.append(moment)
        elif version == "1.1.0":
            new_times.append(moment)

if not old_times or not new_times:
    raise SystemExit("Both versions must appear in the measurement log.")

first_new = min(new_times)
last_old = max(old_times)

print("Student ID: 02230135")
print(f"First 1.1.0 response: {first_new.isoformat()}")
print(f"Last 1.0.0 response: {last_old.isoformat()}")

if last_old > first_new:
    print(f"Observed mixed-version window: "
          f"{(last_old - first_new).total_seconds():.3f} seconds")
else:
    print("Observed mixed-version window: 0.000 seconds")
    print("No interleaving of versions was observed.")