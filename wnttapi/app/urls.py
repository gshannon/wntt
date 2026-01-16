from app.views import (
    AddressView,
    CreateGraphView,
    LatestInfoView,
    StationsView,
)
from django.urls import path

urlpatterns = [
    path("stations/", StationsView.as_view()),
    path("graph/", CreateGraphView.as_view()),
    path("latest/", LatestInfoView.as_view()),
    path("address/", AddressView.as_view()),
]
