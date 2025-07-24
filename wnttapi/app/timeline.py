import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from . import tzutil as tz

logger = logging.getLogger(__name__)


class Timeline:
    """
    Build a datetime list using the given interval in requested timezone for a given date range.

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

    def length(self):
        return len(self._raw_times)

    def contains(self, dt: datetime) -> bool:
        return dt in self._raw_times

    def get_all_past(self):
        return list(filter(lambda dt: dt < self.now, self._raw_times))

    def is_all_future(self):
        return self.start_dt > self.now


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

    def build_plot(self, callback):
        """Build an array of data values or None -- that matches the known datetimes
            that correspond to a tide data value, either recorded or predicted, suitable for using to
            build a Plotly scatter plot.

        Args:
            callback (function): Callback function that, based on the datetime in question,
            returns the data that matches, or None as appropriate.
            ignored boolean parameter: present to support subclass overloading.

        Returns:
            list: The resulting list of data values or None
        """
        return list(map(callback, self._raw_times))


class HiloTimeline(GraphTimeline):
    """A type of GraphTimeline where the initial 15-min interval timeline gets replaced with the start time,
    end time, and all times which map to an observed or predicted high or low tide in between. The original
    start and end times are included in the final timeline, but not repeated.
    You must register the high/low tide times before calling build_plot or get_final_times.
    """

    _hilo_timeline = None

    def register_hilo_times(self, hilo_dts: list):
        """Call this to register the subset of raw_times which map to observed high and low tides and
        susequent predicted high and low tides.  This must be called before build_plot or get_final_times.

        Args:
            - hilo_dts (list): datetimes which correspond with an observed high or low tide, either
              observed or predicted. All times between the start and end of the raw timeline, although
              they don't need to be on a 15-min boundary. Any duplicates are removed.

        Raises:
            ValueError: if any times are outside the timeline start/end times.
        """
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
        """Build an array of data values or None's -- which matches the known datetimes
            that correspond to a High or Low tide data value, suitable for using to build a plot line.

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
        return list(map(callback, self._hilo_timeline))

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
