from django.urls import path

from app.views import CreateGraphView, LatestInfoView, AddressView

urlpatterns = [
    path("graph/", CreateGraphView.as_view()),
    path("latest/", LatestInfoView.as_view()),
    path("address/", AddressView.as_view()),
]
