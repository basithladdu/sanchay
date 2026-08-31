"""Estimate storage growth from a single scan.

Modification times can offer a first-run hint about recent write activity, but
they do not measure future net growth. A later SANCHAY snapshot is required for
an observed mounted-filesystem growth rate.
"""
import time
from collections import defaultdict

from . import storage


def daily_growth(files, window=180, now=None):
    now = now or time.time()
    per_day = defaultdict(int)
    for f in storage.physical_records(files):
        age = (now - f.mtime) / 86400
        if 0 <= age <= window:
            per_day[int(age)] += storage.allocated_bytes(f)
    return per_day


def rate(files, window=180, now=None):
    """Mean bytes added per day over the window."""
    per_day = daily_growth(files, window, now)
    return sum(per_day.values()) / window if per_day else 0.0


def days_until_full(files, free_bytes, window=180, now=None):
    r = rate(files, window, now)
    return None if r <= 0 else free_bytes / r


def runway_label(days):
    """Format a runway without pretending a first-pass estimate is precise."""
    if days is None:
        return "—"
    if days >= 3650:
        return ">10 years"
    if days >= 365:
        return f"~{days / 365:.1f} years"
    return f"~{days:.0f} days"
