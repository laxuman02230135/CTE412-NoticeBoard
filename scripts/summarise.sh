#!/bin/sh
# Purpose: Summarise one saved availability-monitor log.
# Usage: sh scripts/summarise.sh path/to/monitor-log.txt

set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: sh scripts/summarise.sh <monitor-log>" >&2
    exit 1
fi

python3 - "$1" <<'PY'
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

path = Path(sys.argv[1])
total = 0
failed = 0
first = None
last = None
versions = Counter()

try:
    with path.open(encoding="utf-8-sig") as log:
        for number, raw_line in enumerate(log, start=1):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split(" ", 2)
            if len(parts) != 3 or parts[1] not in ("OK", "FAIL"):
                raise ValueError(f"Invalid log format at line {number}")

            timestamp, status, body = parts
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            total += 1
            if first is None:
                first = timestamp
            last = timestamp

            if status == "FAIL":
                failed += 1
            else:
                payload = json.loads(body)
                if payload.get("student") != "02230135":
                    raise ValueError(f"Unexpected student ID at line {number}")
                versions[payload["version"]] += 1

    if total == 0:
        raise ValueError("The log contains no requests")

except (OSError, ValueError, KeyError) as error:
    print(f"Error: {error}", file=sys.stderr)
    sys.exit(1)

print("Student ID: 02230135")
print(f"Total requests: {total}")
print(f"Failed requests: {failed}")
print(f"First timestamp: {first}")
print(f"Last timestamp: {last}")
print("Responses per version:")
for version, count in sorted(versions.items()):
    print(f"  {version}: {count}")
PY