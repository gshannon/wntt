from django.db import models

from app import util


class Station(models.TextChoices):
    WELLS = "WE", "welinwq"
    NOCAL = "NC", "nocrcwq"


def get_station(station_id: str) -> Station:
    if station_id is None:
        return None
    if station_id == "welinwq":
        return Station.WELLS
    if station_id == "nocrcwq":
        return Station.NOCAL
    raise util.InternalError(f"Unknown station: {station_id}")


class User(models.Model):
    uuid = models.CharField(max_length=13, unique=True)
    created_at = models.DateTimeField(auto_now=False, auto_now_add=False)

    class Meta:
        db_table = "user"


class Request(models.Model):
    class Type(models.TextChoices):
        STATION = "S", "Station"
        GRAPH = "G", "Graph"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    when = models.DateTimeField(auto_now=True)
    type = models.CharField(
        max_length=1,
        choices=Type.choices,
    )
    station = models.CharField(max_length=2, choices=Station.choices, null=True)
    version = models.CharField(max_length=7)
    start = models.DateField(null=True)
    days = models.SmallIntegerField(null=True)
    hilo = models.BooleanField(default=False, null=True)
    customNav = models.FloatField(null=True)
    screenWidth = models.SmallIntegerField(null=True)

    class Meta:
        db_table = "request"


class Water(models.Model):
    station = models.CharField(max_length=2, choices=Station.choices, null=False)
    time = models.CharField(
        max_length=25, null=False
    )  # store as ISO string in UTC, e.g. "2024-01-01T05:30:00+00:00"
    temp_f = models.FloatField(null=True)
    clevel_nf = models.FloatField(null=True)  #  Corrected NAVD88 feet

    class Meta:
        db_table = "water"
        constraints = (
            models.UniqueConstraint(fields=["station", "time"], name="water_uk1"),
        )


class Wind(models.Model):
    station = models.CharField(max_length=2, choices=Station.choices, null=False)
    time = models.CharField(
        max_length=25, null=False
    )  # store as ISO string in UTC, e.g. "2024-01-01T05:30:00+00:00"
    speed = models.FloatField(null=False)
    gust = models.FloatField(null=False)
    dir_deg = models.SmallIntegerField(null=False)

    class Meta:
        db_table = "wind"
        constraints = (
            models.UniqueConstraint(fields=["station", "time"], name="wind_uk1"),
        )


class AstroTide15(models.Model):
    noaa_id = models.CharField(max_length=7, null=False)
    time = models.CharField(
        max_length=25, null=False
    )  # store as ISO string in UTC, e.g. "2024-01-01T05:30:00+00:00"
    nav_level = models.FloatField(null=False)  # This is NAVD88 tide level, not MLLW

    class Meta:
        db_table = "astrotide15"
        constraints = (
            models.UniqueConstraint(fields=["noaa_id", "time"], name="astrotide15_uk1"),
        )


class AstroTideHilo(models.Model):
    class Type(models.TextChoices):
        HIGH = "H", "High"
        LOW = "L", "Low"

    noaa_id = models.CharField(max_length=7, null=False)
    time = models.CharField(
        max_length=25, null=False
    )  # store as ISO string in UTC, e.g. "2024-01-01T05:30:00+00:00"
    real_time = models.CharField(
        max_length=25, null=False
    )  # store as ISO string in UTC, e.g. "2024-01-01T05:30:00+00:00"
    nav_level = models.FloatField(null=False)  # This is NAVD88 tide level, not MLLW
    hilo = models.CharField(max_length=2, null=False, choices=Type.choices)

    class Meta:
        db_table = "astrotidehilo"
        constraints = (
            models.UniqueConstraint(
                fields=["noaa_id", "time"], name="astrotideHilo_uk1"
            ),
        )
