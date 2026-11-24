"""Work schedules (assigned per employee) and the late / short / overtime rules.

The schedule belongs to the *employee record*, set by the owner/admin. Details of the
fixed vs flexible policies are still to be confirmed with the owner - everything here is a parameter.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from .presence import DaySummary


@dataclass(frozen=True)
class Schedule:
    kind: str  # "fixed" | "flexible"
    start: time | None = None  # fixed: shift start
    end: time | None = None  # fixed: shift end
    grace_min: int = 10
    required_hours: float = 8.0  # flexible: hours to complete (fixed derives it from start/end)
    core_start: time | None = None  # flexible: optional "must be in by"


@dataclass
class DayEvaluation:
    status: str = "absent"  # absent | present | late
    late_min: int = 0
    short_min: int = 0
    overtime_min: int = 0
    flags: list[str] = field(default_factory=list)


def _mins(td: timedelta) -> int:
    return int(td.total_seconds() // 60)


def evaluate(schedule: Schedule, summary: DaySummary, day: date, on_field_duty: bool = False) -> DayEvaluation:
    ev = DayEvaluation(flags=list(summary.flags))
    if summary.first_in is None:
        ev.status = "present" if on_field_duty else "absent"
        if on_field_duty:
            ev.flags.append("field_duty")
        return ev
    ev.status = "present"
    inside = timedelta(seconds=summary.inside_seconds)
    if schedule.kind == "fixed":
        start = datetime.combine(day, schedule.start)
        end = datetime.combine(day, schedule.end)
        required = end - start
        if summary.first_in > start + timedelta(minutes=schedule.grace_min):
            ev.status, ev.late_min = "late", _mins(summary.first_in - start)
        if summary.last_out and summary.last_out > end:
            ev.overtime_min = _mins(summary.last_out - end)
    else:
        required = timedelta(hours=schedule.required_hours)
        if schedule.core_start is not None:
            core = datetime.combine(day, schedule.core_start)
            if summary.first_in > core + timedelta(minutes=schedule.grace_min):
                ev.status, ev.late_min = "late", _mins(summary.first_in - core)
        ev.overtime_min = max(_mins(inside - required), 0)
    if not on_field_duty and not summary.inside_now:
        ev.short_min = max(_mins(required - inside), 0)
    if on_field_duty:
        ev.flags.append("field_duty")
    return ev
