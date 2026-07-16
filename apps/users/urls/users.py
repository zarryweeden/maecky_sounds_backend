from django.urls import path
from apps.users.views import (
    MeView,
    AvatarUploadView,
    AddressListCreateView,
    AddressDetailView,
    SetDefaultAddressView,
)

urlpatterns = [
    path("me/", MeView.as_view(), name="user-me"),
    path("me/avatar/", AvatarUploadView.as_view(), name="user-avatar"),
    path("me/addresses/", AddressListCreateView.as_view(), name="user-addresses"),
    path("me/addresses/<uuid:pk>/", AddressDetailView.as_view(), name="user-address-detail"),
    path("me/addresses/<uuid:pk>/set-default/", SetDefaultAddressView.as_view(), name="user-address-set-default"),
]