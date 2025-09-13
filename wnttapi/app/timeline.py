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

    def __init__(self, start_dt: datetime, end_dt: datetime):
        self._raw_times = []
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.time_zone = start_dt.tzinfo
        self.now = tz.now(self.time_zone)
        if self.start_dt.tzinfo != self.end_dt.tzinfo:
            logger.error(f"time zone mismatch: {start_dt.tzinfo}, {end_dt.tzinfo}")
            raise ValueError()
        if self.end_dt <= self.start_dt:
            logger.error("end must be greater than start")
            raise ValueError()

        # timedelta is broken when crossing DST boundaries in tz's which honor DST, so
        # we'll do all datetime arithmetic in UTC in modern Python.
        utc_end = self.end_dt.astimezone(tz.utc)
        utc_cur = self.start_dt.astimezone(tz.utc)
        while utc_cur <= utc_end:
            self._raw_times.append(utc_cur.astimezone(self.start_dt.tzinfo))
            utc_cur += timedelta(minutes=15)

    def is_all_future(self):
        """Returns whether the timeline start time is in the future."""
        return self.start_dt > self.now

    def length_raw(self):
        """Return the number of times in the initial timeline."""
        return len(self._raw_times)

    def contains_raw(self, dt: datetime) -> bool:
        """Returns whether the given datetime is in the initial timeline."""
        return dt in self._raw_times

    def within(self, dt: datetime) -> bool:
        return self.start_dt <= dt <= self.end_dt

    def get_all_past_raw(self) -> list:
        """Return all datetimes in the initial timeline that are before now."""
        return list(filter(lambda dt: dt < self.now, self._raw_times))


class GraphTimeline(Timeline):
    """A subclass of Timeline suitable for building Plotly scatter plots with full days shown.
    This timeline will always include an extra element for 00:00 on the day following the end_date.
    """

    def __init__(self, start_date: date, end_date: date, time_zone: ZoneInfo):
        """Constructor.

        Args:
            start_date (date): First day.
            end_date (date): Last day.
            time_zone (ZoneInfo): time zone data will be displayed in.
        """
        self.start_date = start_date
        self.end_date = end_date

        super().__init__(
            datetime.combine(start_date, time(0)).replace(tzinfo=time_zone),
            datetime.combine(end_date + timedelta(days=1), time(0)).replace(
                tzinfo=time_zone
            ),
        )

    def add_time(self, dt: datetime):
        """Add a datetime to the timeline, if its in bounds, and sort the times so it's still in order.
        This is useful when adding a time for a phase of moon display.  Does nothing if the time is already
        in the timeline.

        Args:
            dt (datetime): time to add

        Raises:
            ValueError: if the time is out of bounds.
        """
        if not self.within(dt):
            raise ValueError(f"{dt} is outside of timeline boundaries")
        if not self.contains_raw(dt):
            self._raw_times.append(dt)
            self._raw_times.sort()

    def build_plot(self, callback):
        """Build a list containing a combination of data values and None's, which correspond to
            this timeline, suitable for using to build a Plotly scatter plot.

        Args:
            callback (function): Callback function that, based on the datetime in question,
            returns the data that matches, or None as appropriate.

        Returns:
            list: The resulting list of data values or None
        """
        return list(map(callback, self._raw_times))

    def get_final_times(self, change_dict: dict):
        """Get a corrected timeline consisting of start + times with data + end, without repeating start or end

        Args:
            corrections (dict): Corrections to make to the raw timeline, so they can display the actual time of the
            future predicted tide rather than the nearest 15-min boundary value. The key is the datetime in question, and
            the value is the correct datetime.

        Returns:
            list: An array of datetimes which will define a Plotly scatter plot x axis.
        """
        return [change_dict[dt] if dt in change_dict else dt for dt in self._raw_times]


class HiloTimeline(GraphTimeline):
    """A specialization of GraphTimeline where the initial 15-min interval timeline gets replaced with the
    start time, all times which map to an observed or predicted high or low tide, and the end time.
    In case the start and/or end times also correspond to a high or low tide, they will not be repeated.
    You must register the high/low tide times before calling build_plot or get_final_times.
    """

    def __init__(self, start_date: date, end_date: date, time_zone: ZoneInfo):
        """Constructor.

        Args:
            start_date (date): First day.
            end_date (date): Last day.
            time_zone (ZoneInfo): time zone data will be displayed in.
        """
        self._hilo_timeline = None
        self._start_has_data = False
        self._end_has_data = False
        super().__init__(start_date, end_date, time_zone)

    def register_hilo_times(self, hilo_dts: list):
        """Call this to alter the alter the timeline so it includes only these times, plus start and end times,
        with no repeats. This must be called before build_plot or get_final_times.

        Args:
            - hilo_dts (list): datetimes which correspond with a high or low tide, either
              observed or predicted. All times must be between the start and end times, inclusive.
              Any duplicates are silently removed.

        Raises:
            ValueError: if any times are outside the timeline start/end times.
        """
        # We'll need to know if the start and end times have data, to determine whether we include them
        # in the final plot.
        self._start_has_data = hilo_dts is not None and self.start_dt in hilo_dts
        self._end_has_data = hilo_dts is not None and self.end_dt in hilo_dts
        self._hilo_timeline = list(
            set(
                [self.start_dt]
                + (hilo_dts if hilo_dts is not None else [])
                + [self.end_dt]
            )
        )
        self._hilo_timeline.sort()

        if (
            min(self._hilo_timeline) < self.start_dt
            or max(self._hilo_timeline) > self.end_dt
        ):
            raise ValueError("All dts must be within the timeline start and end")

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
