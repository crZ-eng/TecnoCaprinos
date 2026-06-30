import uuid

from firebase_admin import firestore

from config.firebaseConnection import initialize_firebase

from pagos.config_planes import PLANES


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

    return orden