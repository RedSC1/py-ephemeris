"""Position services exposed from :class:`taiyin.EphemerisContext`."""


class PositionApi:
    """Native positions and Cartesian states for one calculation context."""

    def __init__(self, context):
        self._context = context

    def at_tdb(self, target_id, tdb, tt, *, flags=0):
        self._context._ensure_open()
        return self._context._native_context.position_at_tdb(target_id, tdb, tt, flags)

    def at_tt(self, target_id, tt, *, flags=0):
        self._context._ensure_open()
        return self._context._native_context.position_at_tt(target_id, tt, flags)

    def at_ut1(self, target_id, ut1, *, flags=0):
        self._context._ensure_open()
        return self._context._native_context.position_at_ut1(target_id, ut1, flags)

    def state_at_tdb(self, target_id, tdb, tt, *, flags=0):
        self._context._ensure_open()
        return self._context._native_context.state_at_tdb(target_id, tdb, tt, flags)
