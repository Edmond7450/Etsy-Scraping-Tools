from django.urls import path
from django.views.generic import RedirectView


from .views import HomeView

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),

    path('', HomeView.as_view(), name='home'),
    path('get_status', HomeView.get_status, name='get_status'),
    path('stop_search', HomeView.stop_search, name='stop_search'),
]
