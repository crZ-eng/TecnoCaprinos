from config.firebaseConnection import initialize_firebase
from pagos.config_planes import PLANES

db = initialize_firebase()


def obtener_usuario(uid):
    """
    Obtiene el documento del usuario desde Firestore.
    """

    doc = db.collection("usuarios").document(uid).get()

    if doc.exists:
        return doc.to_dict()

    return None


def obtener_plan(uid):
    """
    Retorna el plan del usuario.
    """

    usuario = obtener_usuario(uid)

    if not usuario:
        return "gratis"

    return usuario.get("plan", "gratis")


def obtener_configuracion_plan(uid):
    """
    Devuelve la configuración completa del plan.
    """

    plan = obtener_plan(uid)

    return PLANES[plan]


def tiene_permiso(uid, permiso):
    """
    Verifica si el plan tiene un permiso específico.

    Ejemplo:
    tiene_permiso(uid, "pdf")
    """

    configuracion = obtener_configuracion_plan(uid)

    return configuracion.get(permiso, False)


def limite_cabras(uid):
    """
    Devuelve el límite de cabras del usuario.
    """

    configuracion = obtener_configuracion_plan(uid)

    return configuracion["cabras"]

def contar_cabras(uid):
    """
    Cuenta las cabras registradas por el usuario.
    """

    documentos = db.collection("cabras") \
        .where("uid", "==", uid) \
        .stream()

    return len(list(documentos))
def contar_cabras(uid):
    """
    Cuenta cuántas cabras tiene registradas un usuario.
    """

    documentos = (
        db.collection("cabras")
        .where("usuario_id", "==", uid)
        .stream()
    )

    return len(list(documentos))


def puede_registrar_cabra(uid):
    """
    Retorna True si el usuario aún puede registrar cabras.
    """

    limite = limite_cabras(uid)

    # Premium = ilimitado
    if limite == -1:
        return True

    cantidad = contar_cabras(uid)

    return cantidad < limite