from django.urls import path
from .views import (
    StoreListView, BookedTimeListView, ReservationCreateView,
    GuestReservationLookupView, GuestReservationCancelView,
)

urlpatterns = [
    path("stores/", StoreListView.as_view(), name="store-list"),
    path("booked/", BookedTimeListView.as_view(), name="booked-times"),
    path("", ReservationCreateView.as_view(), name="reservation-create"),
    path("guest/lookup/", GuestReservationLookupView.as_view(), name="guest-lookup"),
    path("guest/cancel/", GuestReservationCancelView.as_view(), name="guest-cancel"),
]