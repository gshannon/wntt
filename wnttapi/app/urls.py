from app.views import (
    AddressView,
    CreateGraphView,
    LatestInfoView,
    StationDataView,
    StationSelectionView,
)
from django.urls import path

urlpatterns = [
    path("stations/", StationSelectionView.as_view()),
    path("station/", StationDataView.as_view()),
    path("graph/", CreateGraphView.as_view()),
    path("latest/", LatestInfoView.as_view()),
    path("address/", AddressView.as_view()),
]
