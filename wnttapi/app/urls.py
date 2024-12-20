from django.urls import path
from app.views import CreateGraphView

urlpatterns = [
    path('', CreateGraphView.as_view(), name="anywhere")
]
