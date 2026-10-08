from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("mission-vision/", views.mission_vision, name="mission_vision"),
    path("programs/", views.programs, name="programs"),
    path("gallery/", views.gallery, name="gallery"),
    path("contact/", views.contact, name="contact"),
    path("donate/", views.donate, name="donate"),
    path("api/map-data/", views.map_data, name="map_data"),
    path("api/stats/", views.stats_api, name="stats_api"),
]
