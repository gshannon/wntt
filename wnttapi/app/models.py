from django.db import models


class Station(models.TextChoices):
    WELLS = "WE", "welinwq"
    NOCAL = "NC", "nocrcwq"


class User(models.Model):
    uuid = models.CharField(max_length=13, unique=True)
    created_at = models.DateTimeField(auto_now=False, auto_now_add=False)


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


class Surge(models.Model):
    noaa_id = models.CharField(max_length=7, null=False)
    tide_time = models.DateTimeField(auto_now=False, auto_now_add=False)
    tide = models.FloatField(null=False)
    surge = models.FloatField(null=False)
    bias = models.FloatField(null=True)
    total = models.FloatField(null=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["noaa_id", "tide_time"], name="uniq_station_time"
            )
        ]


def get_station(station_id: str) -> Station:
    if station_id is None:
        return None
    if station_id == "welinwq":
        return Station.WELLS
    if station_id == "nocrcwq":
        return Station.NOCAL
    raise Exception(f"Unknown station: {station_id}")
