"""Project storage growth from a single scan.

You do not need a history of snapshots. Every file already carries the day it
was written, so the mtime distribution *is* the history -- bytes created per
day, recoverable from one walk of the tree.
"""
import time
from collections import defaultdict


def daily_growth(files, window=180, now=None):
    now = now or time.time()
    per_day = defaultdict(int)
    for f in files:
        age = (now - f.mtime) / 86400
        if 0 <= age <= window:
            per_day[int(age)] += f.size
    return per_day


def rate(files, window=180, now=None):
    """Mean bytes added per day over the window."""
    per_day = daily_growth(files, window, now)
    return sum(per_day.values()) / window if per_day else 0.0


def days_until_full(files, free_bytes, window=180, now=None):
    r = rate(files, window, now)
    return None if r <= 0 else free_bytes / r
