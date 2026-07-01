import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app import util

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

    _padding_points = 8  # How many 15-min intervals to go beyond the start/end times.

    # The "now" param is for testing only!
    def __init__(self, start_dt: datetime, end_dt: datetime, now: datetime = None):
        if start_dt.tzinfo is None or end_dt.tzinfo is None:
            raise util.InternalError("datetimes cannot be naive")
        self.requested_times = []
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.start_date = start_dt.date()
        self.end_date = end_dt.date()
        self.time_zone = start_dt.tzinfo
        self.now = tz.now(self.time_zone) if now is None else now
        if self.start_dt.tzinfo != self.end_dt.tzinfo:
            logger.error(
                f"start tz is {start_dt.tzinfo}, but end tz is {end_dt.tzinfo}"
            )
            raise util.InternalError(
                f"time zone mismatch: {start_dt.tzinfo}, {end_dt.tzinfo}"
            )
        if self.end_dt <= self.start_dt:
            raise util.InternalError("end must be greater than start")

        # timedelta is broken when crossing DST boundaries in tz's which honor DST, so
        # we'll do all datetime arithmetic in UTC in modern Python.
        utc_end = self.end_dt.astimezone(tz.utc)
        utc_cur = self.start_dt.astimezone(tz.utc)
        while utc_cur <= utc_end:
            self.requested_times.append(utc_cur.astimezone(self.time_zone))
            utc_cur += timedelta(minutes=15)

        # For determining highs and lows for observed tide Level data, which is by definition only in the
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

    def is_future(self, dt):
        return dt > self.now

    def is_past(self, dt):
        return dt < self.now

    def is_all_past(self):
        """Returns whether the end time is in the past."""
        return self.end_dt <= self.now

    def is_all_future(self):
        """Returns whether the start time is in the future."""
        return self.start_dt > self.now

    def length_requested(self):
        """Return the number of times in the requested timeline."""
        return len(self.requested_times)

    def contains(self, dt: datetime) -> bool:
        """Returns whether the given datetime is within the boundries of the requested timeline."""
        return dt and self.start_dt <= dt <= self.end_dt

    def get_requested(self) -> list:
        return self.requested_times

    def get_all_past(self, padded: bool) -> list:
        # Return all requested times, plus any padding if requested, that are in the past.
        # Padding is only needed for water level in GraphTimeline and its subclasses.
        if self.start_dt >= self.now:
            return []
        if padded:
            all = self._start_padding + self.requested_times + self._end_padding
            return list(filter(lambda dt: dt < self.now, all))
        return list(filter(lambda dt: dt < self.now, self.requested_times))

    def get_min(self, padded: bool) -> datetime:
        # Return the earliest time, maybe including padding.
        # Padding is only needed for water level in GraphTimeline and its subclasses.
        return (
            min(self._start_padding + self.requested_times)
            if padded
            else min(self.requested_times)
        )

    def get_max(self, padded: bool) -> datetime:
        # Return the latest time, maybe including padding.
        # Padding is only needed for water level in GraphTimeline and its subclasses.
        return (
            max(self.requested_times + self._end_padding)
            if padded
            else max(self.requested_times)
        )


class GraphTimeline(Timeline):
    """A subclass of Timeline suitable for building Plotly scatter plots with full days shown.
    This timeline will always include an extra element for 00:00 on the day following the end_date.
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
        # Python will gladly convert a datetime to a date, but that's bad here.
        if isinstance(start_date, datetime) or isinstance(end_date, datetime):
            raise util.InternalError("start_date & end_date must be type date")

        self.start_date = start_date
        self.end_date = end_date

        super().__init__(
            datetime.combine(start_date, time(0)).replace(tzinfo=time_zone),
            datetime.combine(end_date + timedelta(days=1), time(0)).replace(
                tzinfo=time_zone
            ),
            now,
        )

    def add_syzygy_time(self, dt: datetime):
        """Add a datetime to the timeline, if it's in bounds, and sort the times so it's still in order.
        This is useful when adding a time for a phase of moon display.  Does nothing if the time is already
        in the timeline.

        Args:
            dt (datetime): time to add

        Raises:
            InternalError: if the time is out of bounds.
        """
        if not self.contains(dt):
            raise util.InternalError(f"{dt} is outside of timeline boundaries")
        if dt not in self.requested_times:
            self.requested_times.append(dt)
            self.requested_times.sort()

    def build_plots(self, callback):
        """Build one or more lists of data values corresponding to this timeline.

        If the callback returns a single value (or None), a single list is returned.
        If the callback returns a tuple of N values, a tuple of N lists is returned.

        Args:
            callback (function): Callback function that, based on the datetime in question,
                returns either a single data value (or None), or a tuple of N values.

        Returns:
            list | tuple[list, ...]: A single list of values, or a tuple of N lists.
        """
        results = [callback(dt) for dt in self.requested_times]

        if results and isinstance(results[0], tuple):
            n = len(results[0])
            return tuple([row[i] for row in results] for i in range(n))

        return results

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
            corrections[dt] if dt in corrections else dt for dt in self.requested_times
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
        super().__init__(start_date, end_date, time_zone, now)

    def register_hilo_times(self, hilo_dts: list):
        """Call this to alter the timeline so it includes only these times, plus start and end times,
        with no repeats. This must be called before build_plot or get_final_times. Times not between
        the start and end times are ignored. Any duplicates are silently removed.

        Args:
            - hilo_dts (list): datetimes which correspond with a high or low tide, either
              observed or predicted.

        Raises:
            util.InternalError: if any times are outside the timeline start/end times.
        """
        if hilo_dts is None:
            raise util.InternalError("hilo_dts cannot be None")

        # putting into a set, so duplicates are removed
        self._hilo_timeline = list(
            set(
                [self.start_dt]
                + list(filter(lambda dt: self.contains(dt), hilo_dts))
                + [self.end_dt]
            )
        )
        self._hilo_timeline.sort()

    def add_syzygy_time(self, dt: datetime):
        """Add a datetime to the timeline, if it's in bounds, and sort the times so it's still in order.
        This is useful when adding a time for a phase of moon display.  Does nothing if the time is already
        in the timeline.

        Args:
            dt (datetime): time to add
        """
        if self._hilo_timeline is None:
            raise util.InternalError("register_hilo_times must be called first")
        if dt not in self._hilo_timeline:
            self._hilo_timeline.append(dt)
            self._hilo_timeline.sort()

    def build_plots(self, callback) -> list:
        """Same as parent class function, but uses the registered high/low times, plus start and end times."""
        if self._hilo_timeline is None:
            raise util.InternalError("register_hilo_times must be called first")

        results = [callback(dt) for dt in self._hilo_timeline]

        if results and isinstance(results[0], tuple):
            n = len(results[0])
            return tuple([row[i] for row in results] for i in range(n))

        return results

    def get_final_times(self, corrections) -> list:
        """Get a corrected timeline consisting of start + times with data + end, without repeating start or end

        Args:
            corrections (dict): Corrections to make to the timeline of high/low, so they can display the actual time of the
            future predicted tide rather than the nearest 15-min boundary value. The key is the datetime in question, and
            the value is the correct datetime. It may be empty.

        Raises:
            InternalError: If register_hilo_times has not been called.

        Returns:
            list: An array of datetimes which will define a Plotly scatter plot x axis.
        """
        if self._hilo_timeline is None:
            raise util.InternalError("register_hilo_times must be called first")

        return [
            corrections[dt] if dt in corrections else dt for dt in self._hilo_timeline
        ]
