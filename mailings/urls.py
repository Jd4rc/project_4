from django.urls import path

from mailings.apps import MailingsConfig
from mailings.views import HomeView

app_name = MailingsConfig.name

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
]
