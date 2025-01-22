from django.urls import path
from app.views import CreateGraphView, LatestInfoView

urlpatterns = [
    path('graph/', CreateGraphView.as_view()),
    path('latest/', LatestInfoView.as_view()),
]
