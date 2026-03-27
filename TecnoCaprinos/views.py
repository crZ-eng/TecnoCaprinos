import os
from django.shortcuts import render, redirect
from django.contrib import messages
# from django.http import  HttpRequestForbidden
from firebase_admin import firestore, auth
from config.firebaseConnection import initialize_firebase
from functools import wraps
import requests

# Inicializar la DB con FireStore

db = initialize_firebase()

def bienvenido(request):
    return render(request, 'bienvenido.html')

def registro_usuario(request):
    mensaje = None
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            # Vamos a crear en Firebase auth
            user = auth.create_user(
                email = email,
                password = password
            )

            db.collection('usuarios').document(user.uid).set({
                'nombre' : nombre,
                'email' : email,
                'uid' : user.uid,
                'fecha_registro' : firestore.SERVER_TIMESTAMP,
            })

            mensaje = f"Te has registrado correctamente 😊: {nombre}"
        except Exception as e:
            mensaje = f"Error: {e}"
    return render(request, 'registro.html', {'mensaje' : mensaje})

def login_required_firebase(view_func):
    # Este decorador personalizado va a proteger nuestras vistas
    # si el usuario no ha iniciado sesión.
    # Si el UID no existe, lo va a enviar a iniciar sesión.

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'uid' not in request.session:
            messages.warning(request, "Warning, no has iniciado sesión")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# logica para solicitarle a Google la validación

def login(request):
    if ('uid' in request.session):
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        apiKey = os.getenv('FIREBASE_WEB_API_KEY')

        # Endpoind oficial de Google
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={apiKey}"

        payload = {
            "email" : email,
            "password" : password,
            "returnSecureToken" : True
        }

        try:

            # petición http al servicio de autenticación de google
            response = requests.post(url, json=payload)
            data = response.json()

            if response.status_code == 200:
                # All good
                request.session['uid'] = data['localId']
                request.session['email'] = data['email']
                request.session['idToken'] = data['idToken']
                messages.success(request, f'👌 Acceso correcto al sistema')
                return redirect('dashboard')
            else:
                # Error: Analizarlo
                errorMessage = data.get('error', {}).get('message', 'UNKNOWN ERROR')

                errores_comunes = {
                    'INVALID_LOGIN_CREDENTIALS': 'La contraseña es incorrecta o el correo no es válido.',
                    'EMAIL_NOT_FOUND': 'Este correo no está registrado en el sistema.',
                    'USER_DISABLED': 'Esta cuenta ha sido inhabilitada por el administrador.',
                    'TOO_MANY_ATTEMPTS_TRY_LATER': 'Demasiados intentos fallidos. Espere unos minutos.'
                }

                mensaje_usuario = errores_comunes.get(errorMessage, "Error de autenticación, revisa tus credenciales")
                messages.error(request, mensaje_usuario)
        except requests.exceptions.RequestException as e:
            messages.error(request, "Error de conexión con el servidor")
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")
    return render(request, 'login.html')

def cerrar_sesion(request):
    request.session.flush()
    messages.info(request, 'Has cerrado sesión correctamente')
    return redirect('login')

@login_required_firebase #Verifica que el user esté logueado
def dashboard(request):
    # Este es el panl principal, este solo lo permite si el decorador lo permite
    # Recuparar los datos de Firestore

    uid= request.session.get('uid')
    datosUser = {}

    try:
        # Consulta a Firestore usando SDK 
        doc_ref = db.collection('usuarios').document(uid)
        doc = doc_ref.get()

        if doc.exists:
            datosUser = doc.to_dict()
        else:
            # Si entra en el out pero no tiene un perfil en Firestore vamos a manejar el caso
            datosUser = {
                'nombre' : request.session.get('nombre'),
                'email' : request.session.get('email'),
                'rol' : request.session.get('rol'),
                'uid' : request.session.get('uid'),
                'fecha_registro' : firestore.SERVER_TIMESTAMP
            }
    except Exception as e:
        messages.error(request, f'Error al cargar los datos de la base de datos: {e}')
    return render(request, 'dashboard.html', {'datos': datosUser})
