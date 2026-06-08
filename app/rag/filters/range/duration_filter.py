"""DurationFilter: bound on play time.

Heads-up on the name: the payload field is `duration_min`, where `min` means **MINUTES**, not
"minimum" — it is the single play-time value in minutes (FEAT_PLAY_TIME, e.g. 120 = a 2-hour
game). The actual lower/upper bounds of this filter are the RangeFilter's `min`/`max`, so e.g.
`{"max": 60}` means "play time <= 60 minutes".
"""

from app.rag.filters.range.range_filter import RangeFilter


class DurationFilter(RangeFilter):
    field = "duration_min"  # duration in MINutes (not a minimum)
