#!/usr/bin/env python3
"""
Chains - long-running live poller for GitHub Actions.

WHY THIS EXISTS (2026-08-29, Worlds round 4):
The three `*/5` cron workflows (live_A/B/C) are best-effort on GitHub's side and
in practice fired only 1-2 times an HOUR during Worlds - on Friday (round 3)
there was a 5-hour gap. The app's Live Course map places every player on a hole
from Firebase /live, so a stale feed means "who's on what hole" is hours wrong.

This script is meant to run as ONE job that stays alive for most of the 6-hour
Actions job limit and calls poller_once.run_once() every POLL_SECONDS, so
freshness no longer depends on cron actually firing every 5 minutes. The
workflow (live_poller.yml) re-dispatches itself when the job ends and an hourly
cron acts as a heartbeat; a concurrency group keeps at most one alive.

Outside an event's date window it does a single cycle and exits, so it costs
nothing between tournaments.
"""
import os, sys, time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poller_once

MAX_SECONDS = int(os.environ.get("MAX_SECONDS", "19800"))   # 5h30m
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "25"))
WINDOW_DAYS = 1


def in_event_window():
    """True when today (UTC) is inside the current event's scheduled dates,
    with a day of slack either side (timezones / weather delays)."""
    try:
        rec = poller_once.current_event()
        sd, ed = poller_once._sd(rec), poller_once._ed(rec)
        if not sd:
            return False
        today = datetime.now(timezone.utc).date()
        start = datetime.strptime(sd, "%Y-%m-%d").date() - timedelta(days=WINDOW_DAYS)
        end = datetime.strptime(ed or sd, "%Y-%m-%d").date() + timedelta(days=WINDOW_DAYS)
        return start <= today <= end
    except Exception as e:
        print(f"[window] could not decide ({e}); assuming live")
        return True


def main():
    t0 = time.time()
    last = None
    cycles = errors = 0
    live = in_event_window()
    print(f"[poller_loop] start {datetime.now(timezone.utc).isoformat()} "
          f"window={'LIVE' if live else 'idle'} max={MAX_SECONDS}s every={POLL_SECONDS}s", flush=True)
    while True:
        try:
            msg = poller_once.run_once()
            cycles += 1
            if msg != last:                       # log only on change, keep the run log small
                print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {msg}", flush=True)
                last = msg
        except Exception as e:
            errors += 1
            print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} ERR {e!r}", flush=True)
        if not live:
            print("[poller_loop] no event in window - single cycle done", flush=True)
            break
        if time.time() - t0 + POLL_SECONDS > MAX_SECONDS:
            break
        time.sleep(POLL_SECONDS)
    print(f"[poller_loop] end cycles={cycles} errors={errors} "
          f"elapsed={int(time.time() - t0)}s", flush=True)


if __name__ == "__main__":
    main()
