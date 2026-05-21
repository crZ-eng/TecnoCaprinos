import os
import cloudinary
import cloudinary.uploader
from django.shortcuts import render, redirect
from django.contrib import messages
from firebase_admin import firestore, auth
from config.firebaseConnection import initialize_firebase
from functools import wraps
import requests
from firebase_admin import firestore

# Inicializar Firebase
db = initialize_firebase()


# =========================
# VISTA PRINCIPAL
# =========================

def bienvenido(request):
    return render(request, 'home.html')


# =========================
# REGISTRO
# =========================

def registro_usuario(request):

    mensaje = None

    if request.method == 'POST':

        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:

            user = auth.create_user(
                email=email,
                password=password
            )

            db.collection('usuarios').document(user.uid).set({
                'nombre': nombre,
                'email': email,
                'uid': user.uid,
                'fecha_registro': firestore.SERVER_TIMESTAMP,
            })

            mensaje = f"Te has registrado correctamente 😊: {nombre}"

        except Exception as e:
            mensaje = f"Error: {e}"

    return render(request, 'registro.html', {
        'mensaje': mensaje
    })


# =========================
# DECORADOR LOGIN
# =========================

def login_required_firebase(view_func):

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

        if 'uid' not in request.session:
            messages.warning(request, "Warning, no has iniciado sesión")
            return redirect('login')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


# =========================
# LOGIN
# =========================

def login(request):

    if 'uid' in request.session:
        return redirect('info_animales')

    if request.method == 'POST':

        email = request.POST.get('email')
        password = request.POST.get('password')

        apiKey = os.getenv('FIREBASE_WEB_API_KEY')

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={apiKey}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        try:

            response = requests.post(url, json=payload)
            data = response.json()

            if response.status_code == 200:

                request.session['uid'] = data['localId']
                request.session['email'] = data['email']
                request.session['idToken'] = data['idToken']

                messages.success(request, '👌 Acceso correcto al sistema')

                return redirect('info_animales')

            else:

                errorMessage = data.get(
                    'error',
                    {}
                ).get(
                    'message',
                    'UNKNOWN ERROR'
                )

                errores_comunes = {
                    'INVALID_LOGIN_CREDENTIALS': 'La contraseña es incorrecta o el correo no es válido.',
                    'EMAIL_NOT_FOUND': 'Este correo no está registrado en el sistema.',
                    'USER_DISABLED': 'Esta cuenta ha sido inhabilitada por el administrador.',
                    'TOO_MANY_ATTEMPTS_TRY_LATER': 'Demasiados intentos fallidos. Espere unos minutos.'
                }

                mensaje_usuario = errores_comunes.get(
                    errorMessage,
                    "Error de autenticación, revisa tus credenciales"
                )

                messages.error(request, mensaje_usuario)

        except requests.exceptions.RequestException:
            messages.error(request, "Error de conexión con el servidor")

        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")

    return render(request, 'login.html')


# =========================
# CERRAR SESIÓN
# =========================

def cerrar_sesion(request):

    request.session.flush()

    messages.info(
        request,
        'Has cerrado sesión correctamente'
    )

    return redirect('login')


# =========================
# DASHBOARD
# =========================

@login_required_firebase
def dashboard(request):

    uid = request.session.get('uid')

    datosUser = {}

    try:

        doc_ref = db.collection('usuarios').document(uid)

        doc = doc_ref.get()

        if doc.exists:

            datosUser = doc.to_dict()

        else:

            datosUser = {
                'nombre': request.session.get('nombre'),
                'email': request.session.get('email'),
                'rol': request.session.get('rol'),
                'uid': request.session.get('uid'),
                'fecha_registro': firestore.SERVER_TIMESTAMP
            }

    except Exception as e:

        messages.error(
            request,
            f'Error al cargar los datos: {e}'
        )

    return render(
        request,
        'dashboard.html',
        {'datos': datosUser}
    )


# =========================
# INFO ANIMALES
# =========================

@login_required_firebase
def info_animales(request):
    uid = request.session.get('uid')

    cabras = []

    razas = set()

    try:

        docs = (

            db.collection('cabras')

            .where('usuario_id', '==', uid)

            .order_by(
                'fecha_anadido',
                direction=firestore.Query.DESCENDING
            )

            .stream()

        )

        for doc in docs:

            cabra = doc.to_dict()

            cabra['id'] = doc.id

            cabras.append(cabra)

            # GUARDAR RAZAS ÚNICAS

            if cabra.get('raza'):

                razas.add(cabra['raza'])

    except Exception as e:

        messages.error(
            request,
            f"Hubo un error al obtener sus cabras: {e}"
        )

    return render(

        request,

        'info_animales.html',

        {

            'cabras': cabras,

            'razas': sorted(razas)

        }

    )

# =========================
# AÑADIR CABRA
# =========================

@login_required_firebase
def anadir_cabra(request):

    if request.method == 'POST':

        cod = request.POST.get('cod')
        nombre = request.POST.get('nombre')
        raza = request.POST.get('raza')
        peso = request.POST.get('peso')
        fecha_nacimiento = request.POST.get('fecha_nacimiento')
        sexo = request.POST.get('sexo')
        color = request.POST.get('color')
        cod_madre = request.POST.get('cod_madre')
        cod_padre = request.POST.get('cod_padre')
        categoria = request.POST.get('categoria')

        uid = request.session.get('uid')

        # =========================
        # OBTENER FOTO
        # =========================

        foto = request.FILES.get('foto')

        foto_url = ""

        try:

            # =========================
            # SUBIR FOTO A CLOUDINARY
            # =========================

            if foto:

                resultado = cloudinary.uploader.upload(
                    foto,
                    folder='cabras'
                )

                foto_url = resultado.get('secure_url')

            # =========================
            # GUARDAR EN FIREBASE
            # =========================

            db.collection('cabras').add({

                'codigo': cod,
                'nombre': nombre,
                'raza': raza,
                'peso': peso,
                'fecha_nacimiento': fecha_nacimiento,
                'sexo': sexo,
                'color': color,
                'categoria': categoria,
                'usuario_id': uid,
                'codigo_madre': cod_madre,
                'codigo_padre': cod_padre,

                # NUEVO CAMPO
                'foto_url': foto_url,

                'fecha_anadido': firestore.SERVER_TIMESTAMP
            })

            messages.success(
                request,
                "Cabra añadida con éxito 🐐"
            )
            print(foto_url)
            return redirect('info_animales')

        except Exception as e:

            messages.error(
                request,
                f"Error al añadir la cabra: {e}"
            )

    return render(
        request,
        'info/anadir.html'
    )

# =========================
# ELIMINAR CABRA
# =========================

@login_required_firebase # Verifica que el usuario esta loggeado
def eliminar_cabra(request, cabra_id):
    """
    DELETE: Eliminar un documento especifico por id
    """
    try:
        db.collection('cabras').document(cabra_id).delete()
        messages.success(request, "🗑️ Cabra eliminada.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {e}")

    return redirect('info_animales')

# ==============================
# EDITAR LOS DATOS DE UNA CABRA
# ==============================

@login_required_firebase # Verifica que el usuario esta loggeado
def editar_cabra(request, cabra_id):
    """
    UPDATE: Recupera los datos de la ca especifico y actualiza los campos en firebase
    """
    uid = request.session.get('uid')
    cabra_ref = db.collection('cabras').document(cabra_id)

    try:
        doc = cabra_ref.get()

        if not doc.exists:
            messages.error(request, "La cabra no existe")
            return redirect('info_animales')
        
        cabra_data = doc.to_dict()

        if cabra_data.get('usuario_id') != uid:
            messages.error(request, "No tienes permiso para editar esta cabra")
            return redirect('info_animales')
        
        if request.method == 'POST':
            nuevo_cod = request.POST.get('nuevo-codigo')
            nuevo_nombre = request.POST.get('nuevo-nombre')
            nueva_raza = request.POST.get('nueva-raza')
            nuevo_peso = request.POST.get('nuevo-peso')
            nueva_fecha_nacimiento = request.POST.get('nueva-fecha_nacimiento')
            nuevo_sexo = request.POST.get('nuevo-sexo')
            nuevo_color = request.POST.get('nuevo-color')
            nueva_categoria = request.POST.get('nueva-categoria')
            nuevo_cod_madre = request.POST.get('nuevo-cod_madre')
            nuevo_cod_padre = request.POST.get('nuevo-cod_padre')

            cabra_ref.update({
                'codigo': nuevo_cod,
                'nombre': nuevo_nombre,
                'raza': nueva_raza,
                'peso': nuevo_peso,
                'fecha_nacimiento': nueva_fecha_nacimiento,
                'sexo': nuevo_sexo,
                'color': nuevo_color,
                'categoria': nueva_categoria,
                'codigo_madre': nuevo_cod_madre,
                'codigo_padre': nuevo_cod_padre,
                'fecha_anadido': firestore.SERVER_TIMESTAMP
            })

            messages.success(request, "✅ Cabra actualizada correctamente.")
            return redirect('info_animales')
    except Exception as e:
        messages.error(request, f"Error al editar la cabra: {e}")
        return redirect('info_animales')
    
    return render(request, 'info/editar.html', {'cabra': cabra_data, 'id': cabra_id})

# =========================
# EN CINTA
# =========================

@login_required_firebase
def cinta(request):

    uid = request.session.get('uid')

    cabras = []

    try:

        docs = db.collection('cabras')\
            .where('usuario_id', '==', uid)\
            .where('categoria', '==', 'cinta')\
            .stream()

        for doc in docs:

            cabra = doc.to_dict()

            cabra['id'] = doc.id

            cabras.append(cabra)

    except Exception as e:
        print(e)

    return render(
        request,
        'info/cinta.html',
        {
            'cabras': cabras
        }
    )


# =========================
# VACUNAS
# =========================

@login_required_firebase
def vacunas(request):

    uid = request.session.get('uid')

    cabras = []

    try:

        docs = db.collection('cabras')\
            .where('usuario_id', '==', uid)\
            .where('categoria', '==', 'vacunas')\
            .stream()

        for doc in docs:

            cabra = doc.to_dict()

            cabra['id'] = doc.id

            cabras.append(cabra)

    except Exception as e:
        print(e)

    return render(
        request,
        'info/vacunas.html',
        {
            'cabras': cabras
        }
    )


# =========================
# ENFERMAS
# =========================

@login_required_firebase
def enfermas(request):
    
    uid = request.session.get('uid')
    
    cabras = []

    try:

        docs = db.collection('cabras')\
        .where('usuario_id', '==', uid)\
        .where('categoria', '==', 'enferma')\
        .stream()
            
        for doc in docs:

            cabra = doc.to_dict()

            cabra['id'] = doc.id

            cabras.append(cabra)

    except Exception as e:
        print(e)

    return render(
        request,
        'info/enfermas.html',
        {
            'cabras': cabras
        }
    )

# =========================
# producción
# =========================

@login_required_firebase
def produccion(request):

    uid = request.session.get('uid')

    cabras = []

    datosUser = {}

    try:
       # OBTENER DATOS DEL USUARIO

        doc_ref = db.collection('usuarios').document(uid)

        doc = doc_ref.get()

        if doc.exists:

            datosUser = doc.to_dict()

        # OBTENER CABRAS
        
        docs = db.collection('cabras')\
            .where('usuario_id', '==', uid)\
            .where('categoria', '==', 'produccion')\
            .stream()

        for doc in docs:

            cabra = doc.to_dict()

            cabra['id'] = doc.id

            cabras.append(cabra)

    except Exception as e:

        print(e)

        messages.error(
            request,
            f'Error al cargar datos: {e}'
        )

    return render(
        request,
        'info/produccion.html',
        {
            'cabras': cabras,
            'datos': datosUser
        }
    )
# =========================
# FORMULARIOS
# =========================

def registrar_enfermo(request):

    return render(
        request,
        'info/agregar/registrar_enfermo.html'
    )


def registrar_vacuna(request):

    return render(
        request,
        'info/agregar/registrar_vacuna.html'
    )


def agregar_produccion(request):

    return render(
        request,
        'info/agregar/agregar_produccion.html'
    )


def registrar_seguimiento_gestacion(request):

    return render(
        request,
        'info/agregar/registrar_seguimiento_gestacion.html'
    )