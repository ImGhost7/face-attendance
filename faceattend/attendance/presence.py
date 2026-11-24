"""Turn raw entrance IN/OUT events into a per-person daily presence summary."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Event:
    person_id: int
    direction: str  # "in" | "out"
    ts: datetime
    camera: str = ""


@dataclass
class DaySummary:
    first_in: datetime | None = None
    last_out: datetime | None = None
    inside_seconds: float = 0.0
    outside_seconds: float = 0.0  # gaps between leaving and coming back (lunch, errands...)
    exits: int = 0  # times they left and came back
    inside_now: bool = False
    flags: list[str] = field(default_factory=list)  # e.g. "missing_out", "out_without_in"


def dedupe(events: list[Event], cooldown_s: int) -> list[Event]:
    """Drop repeat sightings of the same person+direction inside the cooldown window."""
    kept: list[Event] = []
    last: dict[tuple[int, str], datetime] = {}
    for e in sorted(events, key=lambda e: e.ts):
        key = (e.person_id, e.direction)
        if key in last and (e.ts - last[key]).total_seconds() < cooldown_s:
            continue
        last[key] = e.ts
        kept.append(e)
    return kept


def summarize_day(events: list[Event], now: datetime, day_end: datetime) -> DaySummary:
    """events: ONE person, ONE day. `now` = current time; `day_end` = when an unclosed day is auto-closed."""
    s = DaySummary()
    in_since: datetime | None = None
    out_since: datetime | None = None
    for e in sorted(events, key=lambda e: e.ts):
        if e.direction == "in":
            if in_since is not None:
                continue  # already inside: duplicate IN
            if s.first_in is None:
                s.first_in = e.ts
            if out_since is not None:
                s.outside_seconds += (e.ts - out_since).total_seconds()
                s.exits += 1
                out_since = None
            in_since = e.ts
        else:  # out
            if in_since is None:
                s.flags.append("out_without_in")  # camera missed them coming in
                continue
            s.inside_seconds += (e.ts - in_since).total_seconds()
            s.last_out = e.ts
            out_since, in_since = e.ts, None
    if in_since is not None:
        if now > day_end:  # never saw them leave
            s.inside_seconds += max((day_end - in_since).total_seconds(), 0)
            s.last_out = day_end
            s.flags.append("missing_out")
        else:
            s.inside_seconds += (now - in_since).total_seconds()
            s.inside_now = True
    return s


def hms(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))
