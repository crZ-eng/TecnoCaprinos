import uuid
import os

from firebase_admin import firestore

from config.firebaseConnection import initialize_firebase

from pagos.config_planes import PLANES

import requests
from django.conf import settings

db = initialize_firebase()


def crear_orden(uid, plan):

    datos_plan = PLANES[plan]

    referencia = str(uuid.uuid4())

    orden = {

        "usuario_id": uid,

        "plan": plan,

        "precio": datos_plan["precio"],

        "estado": "pendiente",

        "referencia": referencia,

        "metodo_pago": None,

        "fecha": firestore.SERVER_TIMESTAMP
    
    }
    

    db.collection("pagos").document(referencia).set(orden)

    # Datos que usará el Checkout de Wompi
    orden["public_key"] = os.getenv("WOMPI_PUBLIC_KEY")
    orden["currency"] = "COP"
    orden["amount_in_cents"] = datos_plan["precio"] * 100
    orden["redirect_url"] = "http://127.0.0.1:8000/planes/exitoso/"

    return orden