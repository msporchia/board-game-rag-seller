"""CooperativeFilter: constrain the `cooperative` flag (genuine tri-state, SEL-142).

`{"val": True}` keeps cooperative games, `{"val": False}` keeps competitive ones — an exact
boolean match either way. Because the flag is set only on a confident verdict (True or False) and
left None when UNKNOWN, the hard filter excludes the UNKNOWN games in both directions: a customer
asking for one mode is never handed the opposite or an unverified guess (better to under-offer).
"""

from app.rag.filters.bool.bool_filter import BoolFilter


class CooperativeFilter(BoolFilter):
    field = "cooperative"
