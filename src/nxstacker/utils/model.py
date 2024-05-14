from datetime import datetime, timedelta, tzinfo


class UKtz(tzinfo):
    """Time zone in the UK."""

    def utcoffset(self, dt):
        """Determine the offset based on the date and year."""
        if self.is_dst(dt):
            # UTC +1
            return timedelta(hours=1)

        return timedelta()

    def dst(self, dt):
        """Return the DST adjustment."""
        year = dt.year

        # In the UK the clocks go forward 1 hour at 1am on the last
        # Sunday in March, and back 1 hour at 2am on the last Sunday in
        # October.
        last_sunday_march = self._last_sunday(year, 3)
        last_sunday_october = self._last_sunday(year, 10)
        dston = last_sunday_march.replace(hour=1)
        dstoff = last_sunday_october.replace(hour=2)

        if dston <= dt.replace(tzinfo=None) < dstoff:
            # BST
            return timedelta(hours=1)

        # GMT
        return timedelta()

    def tzname(self, dt):
        """Return time zone name as BST or GMT."""
        return "BST" if self.is_dst(dt) else "GMT"

    def is_dst(self, dt):
        """Check if it is DST."""
        return self.dst(dt) != timedelta()

    def _last_sunday(self, year, month):
        """Find the last Sunday of the specified year and month."""
        last_day = 31
        while True:
            try:
                last_sunday = datetime(year, month, last_day)  # noqa: DTZ001
            except ValueError:
                pass
            else:
                if last_sunday.weekday() == 6:
                    return last_sunday

            last_day -= 1
