import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from . import tzutil as tz

logger = logging.getLogger(__name__)


class Timeline:
    """
    Build a datetime list with 15-minute intervals in the requested timezone for a given range.

    If a daylight savings time boundary is included, you will get:
    - for spring forward, the 02:00 hour will be skipped
    - for fall back:
        ...
        01:00 daylight time
        01:15 daylight time
        01:30 daylight time
        01:45 daylight time
        01:00 standard time
        01:15 standard time
        01:30 standard time
        01:45 standard time
        02:00 standard time (etc)

    """

    # The "now" param is for testing only!
    def __init__(self, start_dt: datetime, end_dt: datetime, now: datetime = None):
        self._requested_times = []
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.time_zone = start_dt.tzinfo
        self.now = tz.now(self.time_zone) if now is None else now
        if self.start_dt.tzinfo is None or self.end_dt.tzinfo is None:
            raise ValueError("datetimes cannot be naive")
        if self.start_dt.tzinfo != self.end_dt.tzinfo:
            raise ValueError(f"time zone mismatch: {start_dt.tzinfo}, {end_dt.tzinfo}")
        if self.end_dt <= self.start_dt:
            raise ValueError("end must be greater than start")

        # timedelta is broken when crossing DST boundaries in tz's which honor DST, so
        # we'll do all datetime arithmetic in UTC in modern Python.
        utc_end = self.end_dt.astimezone(tz.utc)
        utc_cur = self.start_dt.astimezone(tz.utc)
        while utc_cur <= utc_end:
            self._requested_times.append(utc_cur.astimezone(self.time_zone))
            utc_cur += timedelta(minutes=15)

    def is_future(self, dt):
        return dt > self.now

    def is_all_future(self):
        """Returns whether the start time is in the future."""
        return self.start_dt > self.now

    def length_requested(self):
        """Return the number of times in the requested timeline."""
        return len(self._requested_times)

    def contains(self, dt: datetime) -> bool:
        """Returns whether the given datetime is within the boundries of the requested timeline."""
        return dt and self.start_dt <= dt <= self.end_dt

    def get_requested(self) -> list:
        return self._requested_times

    def get_all_past(self) -> list:
        """Return all datetimes in the initial timeline that are before now."""
        return list(filter(lambda dt: dt < self.now, self._requested_times))

    def get_min_with_padding(self) -> datetime:
        """Return the minimum datetime requested, including padding (none for this class)"""
        return self._requested_times[0]

    def get_max_with_padding(self) -> datetime:
        """Return the maximum datetime requested, including padding (none for this class)"""
        return self._requested_times[-1]


class GraphTimeline(Timeline):
    """A subclass of Timeline suitable for building Plotly scatter plots with full days shown.
    This timeline will always include an extra element for 00:00 on the day following the end_date.
    """

    _padding_points = 8  # How many 15-min intervals to go beyond the start/end times.

    def __init__(
        self,
        start_date: date,
        end_date: date,
        time_zone: ZoneInfo,
        now: datetime = None,
    ):
        """Constructor.

        Args:
            start_date (date): First day.
            end_date (date): Last day.
            time_zone (ZoneInfo): time zone data will be displayed in.
            now (datetime): For testing only. Default is current time.
        """
        self.start_date = start_date
        self.end_date = end_date

        super().__init__(
            datetime.combine(start_date, time(0)).replace(tzinfo=time_zone),
            datetime.combine(end_date + timedelta(days=1), time(0)).replace(
                tzinfo=time_zone
            ),
            now,
        )

        # For determining highs and lows for CDMO data, which is by definition only in the
        # past (before "self.now"), we need to look a bit beyond the requested timeline in case
        # there is a high or low near or on the first or last displayed time. Here we define
        # the timeline extensions used for that purpose.
        self._start_padding = []
        self._end_padding = []
        # Pad the start if any part of the timeline is in the past.
        if self.start_dt < self.now:
            utc_cur = self.start_dt.astimezone(tz.utc)
            for _ in range(self._padding_points):
                utc_cur -= timedelta(minutes=15)
                self._start_padding.insert(0, utc_cur.astimezone(self.time_zone))

        # Pad the end, limiting to the past.
        if self.end_dt < self.now:
            utc_cur = self.end_dt.astimezone(tz.utc)
            for _ in range(self._padding_points):
                utc_cur += timedelta(minutes=15)
                dt = utc_cur.astimezone(self.time_zone)
                if dt <= self.now:
                    self._end_padding.append(dt)

    def get_all_past(self) -> list:
        # Return all requested times, plus any padding, that are in the past.
        if len(self._start_padding) == 0:
            return []
        all = self._start_padding + self._requested_times + self._end_padding
        return list(filter(lambda dt: dt < self.now, all))

    def get_min_with_padding(self) -> datetime:
        # Return the earliest time, including padding.
        return min(self._start_padding + self._requested_times)

    def get_max_with_padding(self) -> datetime:
        # Return the latest time, including padding.
        return max(self._end_padding + self._requested_times)

    def add_time(self, dt: datetime):
        """Add a datetime to the timeline, if its in bounds, and sort the times so it's still in order.
        This is useful when adding a time for a phase of moon display.  Does nothing if the time is already
        in the timeline.

        Args:
            dt (datetime): time to add

        Raises:
            ValueError: if the time is out of bounds.
        """
        if not self.contains(dt):
            raise ValueError(f"{dt} is outside of timeline boundaries")
        if dt not in self._requested_times:
            self._requested_times.append(dt)
            self._requested_times.sort()

    def build_plot(self, callback):
        """Build a list containing a combination of data values and None's, which correspond to
            this timeline, suitable for using to build a Plotly scatter plot.

        Args:
            callback (function): Callback function that, based on the datetime in question,
            returns the data that matches, or None as appropriate.

        Returns:
            list: The resulting list of data values or None
        """
        return list(map(callback, self._requested_times))

    def get_final_times(self, corrections: dict):
        """Get a corrected timeline consisting of start + times with data + end, without repeating start or end

        Args:
            corrections (dict): Corrections to make to the raw timeline, so they can display the actual time of the
            future predicted tide rather than the nearest 15-min boundary value. The key is the datetime in question, and
            the value is the correct datetime.

        Returns:
            list: An array of datetimes which will define a Plotly scatter plot x axis.
        """
        return [
            corrections[dt] if dt in corrections else dt for dt in self._requested_times
        ]


class HiloTimeline(GraphTimeline):
    """A specialization of GraphTimeline where the initial 15-min interval timeline gets replaced with the
    start time, all times which map to an observed or predicted high or low tide, and the end time.
    In case the start and/or end times also correspond to a high or low tide, they will not be repeated.
    You must register the high/low tide times before calling build_plot or get_final_times.
    """

    def __init__(
        self,
        start_date: date,
        end_date: date,
        time_zone: ZoneInfo,
        now: datetime = None,
    ):
        """Constructor.

        Args:
            start_date (date): First day.
            end_date (date): Last day.
            time_zone (ZoneInfo): time zone data will be displayed in.
            now (datetime): For testing only. Default is current time.
        """
        self._hilo_timeline = None
        self._start_has_data = False
        self._end_has_data = False
        super().__init__(start_date, end_date, time_zone, now)

    def register_hilo_times(self, hilo_dts: list):
        """Call this to alter the timeline so it includes only these times, plus start and end times,
        with no repeats. This must be called before build_plot or get_final_times. Times not between
        the start and end times are ignored. Any duplicates are silently removed.

        Args:
            - hilo_dts (list): datetimes which correspond with a high or low tide, either
              observed or predicted.

        Raises:
            ValueError: if any times are outside the timeline start/end times.
        """
        # We'll need to know if the start and end times have data, to determine whether we include them
        # in the final plot.

        if hilo_dts is None:
            raise ValueError("hilo_dts cannot be null")

        self._start_has_data = self.start_dt in hilo_dts
        self._end_has_data = self.end_dt in hilo_dts
        # putting into a set, so duplicates are removed
        self._hilo_timeline = list(
            set(
                [self.start_dt]
                + list(filter(lambda dt: self.contains(dt), hilo_dts))
                + [self.end_dt]
            )
        )
        self._hilo_timeline.sort()

    def build_plot(self, callback) -> list:
        """Using the caller's callback function, build an array of data values or None's -- which
            matches the known datetimes that correspond to a High or Low tide data value, suitable
            for using to build a plot line.

        Args:
            - callback (function): Callback function that, based on the datetime in question, returns
              the matching data, or None as appropriate.

        Raises:
            ValueError: If register_hilo_times has not been called.

        Returns:
            list: The resulting list of data values or None
        """
        if self._hilo_timeline is None:
            raise ValueError("register_hilo_times must be called first")

        # Get caller's data plot, one for each high/low dt, either None or their data, using their callback.
        # Note we only callback for the start and end times if they have data.
        plot = []
        plot.append(callback(self.start_dt) if self._start_has_data else None)
        plot += list(map(callback, self._hilo_timeline[1:-1]))
        plot.append(callback(self.end_dt) if self._end_has_data else None)
        return plot

    def get_final_times(self, corrections) -> list:
        """Get a corrected timeline consisting of start + times with data + end, without repeating start or end

        Args:
            corrections (dict): Corrections to make to the timeline of high/low, so they can display the actual time of the
            future predicted tide rather than the nearest 15-min boundary value. The key is the datetime in question, and
            the value is the correct datetime. It may be empty.

        Raises:
            ValueError: If register_hilo_times has not been called.

        Returns:
            list: An array of datetimes which will define a Plotly scatter plot x axis.
        """
        if self._hilo_timeline is None:
            raise ValueError("register_hilo_times must be called first")

        return [
            corrections[dt] if dt in corrections else dt for dt in self._hilo_timeline
        ]
