from django.urls import path
from .views import StoreListView, BookedTimeListView, ReservationCreateView

urlpatterns = [
    path("stores/", StoreListView.as_view(), name="store-list"),
    path("booked/", BookedTimeListView.as_view(), name="booked-times"),
    path("", ReservationCreateView.as_view(), name="reservation-create"),
]