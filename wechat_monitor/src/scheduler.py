from __future__ import annotations

import datetime as dt
import subprocess
import time
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_monitor.sh"
TZ = ZoneInfo("America/New_York")
RUN_HOUR = 22
RUN_MINUTE = 30


def next_run(now: dt.datetime) -> dt.datetime:
    target = now.replace(hour=RUN_HOUR, minute=RUN_MINUTE, second=0, microsecond=0)
    if target <= now:
        target += dt.timedelta(days=1)
    return target


def main() -> None:
    while True:
        now = dt.datetime.now(TZ)
        target = next_run(now)
        sleep_seconds = max(1, int((target - now).total_seconds()))
        print(f"next run: {target.isoformat()}", flush=True)
        time.sleep(sleep_seconds)
        subprocess.run([str(RUNNER)], cwd=str(ROOT), check=False)


if __name__ == "__main__":
    main()
