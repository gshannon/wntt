from django.db import models


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
    raise Exception(f"Unknown station: {station_id}")


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


class Surge(models.Model):
    noaa_id = models.CharField(max_length=7, null=False)
    cycle = models.SmallIntegerField(null=True)
    tide_time = models.DateTimeField(auto_now=False, auto_now_add=False)
    tide = models.FloatField(null=False)
    surge = models.FloatField(null=False)
    surge_1day = models.FloatField(null=True)
    surge_2day = models.FloatField(null=True)
    bias = models.FloatField(null=True)
    calc_bias = models.FloatField(null=True)
    calc_bias2 = models.FloatField(null=True)
    calc_bias3 = models.FloatField(null=True)
    obs = models.FloatField(null=True)

    class Meta:
        db_table = "surge"
        constraints = [
            models.UniqueConstraint(
                fields=["noaa_id", "tide_time"], name="uniq_station_time"
            )
        ]


# One record for each downloaded surge file for which we need to calculate bias ourselves, currently just Wells.
# Calculaged and written by the cron job, consumed by the surge API to apply the bias to the file values.
class SurgeBias(models.Model):
    noaa_id = models.CharField(max_length=7, null=False)
    filedate = models.DateField(auto_now=False, auto_now_add=False)
    cycle = models.SmallIntegerField(null=False)
    bias = models.FloatField(null=False)
    bias2 = models.FloatField(null=True)
    bias3 = models.FloatField(null=True)

    class Meta:
        db_table = "surgebias"
        constraints = [
            models.UniqueConstraint(
                fields=["noaa_id", "filedate", "cycle"], name="surgebias_uk1"
            )
        ]


class Water(models.Model):
    station = models.CharField(max_length=2, choices=Station.choices, null=False)
    time = models.CharField(
        max_length=25, null=False
    )  # store as ISO string in UTC, e.g. "2024-01-01T05:30:00+00:00"
    temp = models.FloatField(null=True)
    level = models.FloatField(null=False)  # This is MLLW tide level, not NAVD88

    class Meta:
        db_table = "water"
        constraints = [
            models.UniqueConstraint(fields=["station", "time"], name="water_uk1")
        ]


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
        constraints = [
            models.UniqueConstraint(fields=["station", "time"], name="wind_uk1")
        ]
