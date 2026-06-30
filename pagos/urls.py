from django.urls import path
from . import views

urlpatterns = [

    path("", views.planes, name="planes"),

    path(
        "checkout/<str:plan>/",
        views.checkout,
        name="checkout"
    ),

    path(
        "exitoso/",
        views.pago_exitoso,
        name="pago_exitoso"
    ),

    path(
        "error/",
        views.pago_error,
        name="pago_error"
    ),

]