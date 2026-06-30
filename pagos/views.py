from django.shortcuts import render, redirect

from pagos.config_planes import PLANES

from pagos.services import crear_orden

from pagos.utils import (
    obtener_plan,
    contar_cabras,
    limite_cabras
)


def planes(request):

    uid = request.session.get("uid")

    plan_actual = obtener_plan(uid)

    cabras_registradas = contar_cabras(uid)

    limite = limite_cabras(uid)

    return render(
        request,
        "pagos/planes.html",
        {
            "planes": PLANES,
            "plan_actual": plan_actual,
            "cabras": cabras_registradas,
            "limite": limite
        }
    )
    
def checkout(request, plan):

    uid = request.session.get("uid")

    if plan not in PLANES:

        return redirect("planes")

    orden = crear_orden(uid, plan)

    contexto = {

        "plan": PLANES[plan],

        "orden": orden

    }

    return render(
        request,
        "pagos/checkout.html",
        contexto
    )
def pago_exitoso(request):

    return render(
        request,
        "pagos/pago_exitoso.html"
    )


def pago_error(request):

    return render(
        request,
        "pagos/pago_error.html"
    )