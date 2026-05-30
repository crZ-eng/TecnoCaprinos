import os
import cloudinary
import cloudinary.uploader
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from firebase_admin import firestore, auth
from config.firebaseConnection import initialize_firebase
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from functools import wraps
import requests
from firebase_admin import firestore
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import landscape, letter

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

    return render(request, 'dashboard.html', {'datos': datosUser})


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

    return render(request, 'info_animales.html',
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

        uid = request.session.get('uid')

        # =========================
        # OBTENER FOTO
        # =========================

        foto = request.FILES.get('foto')

        foto_url = ""

        try:
            cabra_existente = db.collection('cabras') \
                .where('usuario_id', '==', uid) \
                .where('codigo', '==', cod) \
                .limit(1) \
                .stream()

            if any(cabra_existente):

                messages.warning(
                    request,
                    "Ya existe una cabra con ese código 🐐"
                )

                return redirect('anadir_cabra')

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

@login_required_firebase  # Verifica que el usuario esta loggeado
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

@login_required_firebase  # Verifica que el usuario esta loggeado
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
        docs = db.collection('en_cinta')\
            .where('usuario_id', '==', uid)\
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

        docs = db.collection('vacunas')\
            .where('usuario_id', '==', uid)\
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

        docs = db.collection('enfermas')\
            .where('usuario_id', '==', uid)\
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

        docs = db.collection('produccion')\
            .where('usuario_id', '==', uid)\
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

def info_completa_cabra(request, cabra_id):
    try:
        doc = db.collection('cabras').document(cabra_id).get()

        cabra = doc.to_dict()

        cabra['id'] = doc.id

    except Exception as e:
        print(e)
        cabra = None

    return render(
        request,
        'info_completa_cabras.html',
        {
            'cabra': cabra
        }
    )

# =========================
# vista para detalles de cada cabra por separado al oprimir sobre.
# =========================


@login_required_firebase
def detalle_animal(request, cabra_id):

    try:

        doc = db.collection('cabras').document(cabra_id).get()

        if not doc.exists:

            messages.error(request, "La cabra no existe")

            return redirect('info_animales')

        animal = doc.to_dict()

        animal['id'] = doc.id

        return render(

            request,

            'detallesCabras/detalle_animal.html',

            {
                'animal': animal
            }

        )

    except Exception as e:

        messages.error(
            request,
            f'Error al cargar animal: {e}'
        )

        return redirect('info_animales')
    
    # parte duvan pdf
    
    
@login_required_firebase
def pdf_vacunas(request):

    uid = request.session.get('uid')

    cabras = []

    try:

        docs = db.collection('vacunas')\
            .where('usuario_id', '==', uid)\
            .stream()

        for doc in docs:

            cabra = doc.to_dict()

            cabra['id'] = doc.id

            cabras.append(cabra)

    except Exception as e:

        print(e)

    # =========================
    # RESPUESTA PDF
    # =========================

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        'attachment; filename="reporte_vacunas.pdf"'
    )

    # =========================
    # IMPORT HORIZONTAL
    # =========================

    from reportlab.lib.pagesizes import landscape, letter

    # =========================
    # DOCUMENTO HORIZONTAL
    # =========================

    doc = SimpleDocTemplate(

        response,

        pagesize=landscape(letter),

        rightMargin=20,
        leftMargin=20,
        topMargin=25,
        bottomMargin=20

    )

    elementos = []

    estilos = getSampleStyleSheet()

    # =========================
    # TITULO PRINCIPAL
    # =========================

    titulo = Paragraph(
        """
        <para align="center">

        <font size="24" color="#7F5637">
        <b>TECNOCAPRINOS</b>
        </font>

        <br/><br/>

        <font size="14" color="#C9A06D">
        REPORTE GENERAL DE VACUNAS
        </font>

        </para>
        """,
        estilos['Title']
    )

    elementos.append(titulo)

    elementos.append(Spacer(1, 20))

    # =========================
    # FECHA
    # =========================

    from datetime import datetime

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    info = Paragraph(
        f"""
        <font size="10" color="#3E2A1F">
        <b>Fecha de generación:</b> {fecha}
        </font>
        """,
        estilos['Normal']
    )

    elementos.append(info)

    elementos.append(Spacer(1, 18))

    # =========================
    # DATOS TABLA
    # =========================

    datos = [

        [
            'Código',
            'Nombre',
            'Raza',
            'Peso',
            'Sexo',
            'Medicamento',
            'Vía Administración'
        ]

    ]

    # =========================
    # FILAS CABRAS
    # =========================

    for cabra in cabras:

        datos.append([

            Paragraph(
                str(cabra.get('codigo', 'No registrado')),
                estilos['BodyText']
            ),

            Paragraph(
                str(cabra.get('nombre', 'No registrado')),
                estilos['BodyText']
            ),

            Paragraph(
                str(cabra.get('raza', 'No registrado')),
                estilos['BodyText']
            ),

            Paragraph(
                str(cabra.get('peso', 'No registrado')),
                estilos['BodyText']
            ),

            Paragraph(
                str(cabra.get('sexo', 'No registrado')),
                estilos['BodyText']
            ),

            Paragraph(
                str(cabra.get('dosis', 'No asignado')),
                estilos['BodyText']
            ),

            Paragraph(
                str(cabra.get('Via_admin', 'No asignado')),
                estilos['BodyText']
            )

        ])

    # =========================
    # TABLA PRINCIPAL
    # =========================
    tabla = Table(

        datos,
        
        splitByRow=True,

        colWidths=[
            80,   # Código
            120,  # Nombre
            110,  # Raza
            70,   # Peso
            70,   # Sexo
            150,  # Medicamento
            150   # Vía administración
        ],

        repeatRows=1

    )

    # =========================
    # ESTILOS TABLA
    # =========================

    tabla.setStyle(TableStyle([

        # =========================
        # HEADER
        # =========================

        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7F5637')),

        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

        ('FONTSIZE', (0, 0), (-1, 0), 11),

        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

        # AJUSTAR TEXTO
        ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),

        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        ('TOPPADDING', (0, 0), (-1, 0), 12),

        # =========================
        # CUERPO TABLA
        # =========================

        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFDF9')),

        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#3E2A1F')),

        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),

        ('FONTSIZE', (0, 1), (-1, -1), 9),

        # =========================
        # FILAS ALTERNADAS
        # =========================

        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [

            colors.HexColor('#FFFDF9'),
            colors.HexColor('#F5E6D3')

        ]),

        # =========================
        # BORDES
        # =========================

        ('GRID', (0, 0), (-1, -1), 1.2, colors.HexColor('#7F5637')),

        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#7F5637')),

        # =========================
        # ALINEACIÓN
        # =========================

        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),

        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # =========================
        # ESPACIADO
        # =========================

        ('TOPPADDING', (0, 1), (-1, -1), 8),

        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),

    ]))

    elementos.append(tabla)

    elementos.append(Spacer(1, 25))

    # =========================
    # FOOTER
    # =========================

    footer = Paragraph(
        """
        <para align="center">

        <font size="9" color="#7F5637">

        Documento generado automáticamente por TECNOCAPRINOS

        </font>

        </para>
        """,
        estilos['Normal']
    )

    elementos.append(footer)

    # =========================
    # CREAR PDF
    # =========================

    doc.build(elementos)

    return response


# =========================
# ENFERMAS
# =========================

@login_required_firebase
def enfermas(request):
    
    uid = request.session.get('uid')
    
    cabras = []

    try:

        docs = db.collection('enfermas')\
        .where('usuario_id', '==', uid)\
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
        
        docs = db.collection('produccion')\
            .where('usuario_id', '==', uid)\
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
# PDF PRODUCCIÓN
# =========================

@login_required_firebase
def pdf_produccion(request):

    uid = request.session.get('uid')

    cabras = []

    try:

        docs = db.collection('vacunas')\
            .where('usuario_id', '==', uid)\
            .stream()

        for doc in docs:

            cabra = doc.to_dict()

            cabra['id'] = doc.id

            cabras.append(cabra)

    except Exception as e:

        print(e)

    # =========================
    # RESPUESTA PDF
    # =========================

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        'attachment; filename="reporte_produccion.pdf"'
    )

    # =========================
    # DOCUMENTO HORIZONTAL
    # =========================

    doc = SimpleDocTemplate(

        response,

        pagesize=landscape(letter),

        rightMargin=15,
        leftMargin=15,
        topMargin=20,
        bottomMargin=20

    )

    elementos = []

    estilos = getSampleStyleSheet()

    # =========================
    # TITULO
    # =========================

    titulo = Paragraph(
        """
        <para align="center">

        <font size="24" color="#7F5637">
        <b>TECNOCAPRINOS</b>
        </font>

        <br/><br/>

        <font size="14" color="#C9A06D">
        REPORTE GENERAL DE PRODUCCIÓN
        </font>

        </para>
        """,
        estilos['Title']
    )

    elementos.append(titulo)

    elementos.append(Spacer(1, 18))

    # =========================
    # FECHA
    # =========================

    from datetime import datetime

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    info = Paragraph(
        f"""
        <font size="10" color="#3E2A1F">
        <b>Fecha de generación:</b> {fecha}
        </font>
        """,
        estilos['Normal']
    )

    elementos.append(info)

    elementos.append(Spacer(1, 15))

    # =========================
    # DATOS TABLA
    # =========================

    datos = [[

        'Código',
        'Nombre',
        'Peso',
        'Sexo',
        'Ordeño Mañana',
        'Ordeño Tarde',
        'Total Diario',
        'Observaciones',
        'Responsable'

    ]]

    # =========================
    # ESTILO CELDAS
    # =========================

    estilo_celda = estilos['BodyText']

    estilo_celda.fontName = 'Helvetica'

    estilo_celda.fontSize = 7

    estilo_celda.leading = 9

    # =========================
    # FILAS
    # =========================

    for cabra in cabras:

        observaciones = Paragraph(
            str(cabra.get('observaciones', '-')),
            estilo_celda
        )

        responsable = Paragraph(
            str(cabra.get('responsable', '-')),
            estilo_celda
        )

        datos.append([

            Paragraph(
                str(cabra.get('codigo', '-')),
                estilo_celda
            ),

            Paragraph(
                str(cabra.get('nombre', '-')),
                estilo_celda
            ),

            Paragraph(
                str(cabra.get('peso', '-')),
                estilo_celda
            ),

            Paragraph(
                str(cabra.get('sexo', '-')),
                estilo_celda
            ),

            Paragraph(
                str(cabra.get('ordeno_manana', '0')),
                estilo_celda
            ),

            Paragraph(
                str(cabra.get('ordeno_tarde', '0')),
                estilo_celda
            ),

            Paragraph(
                str(cabra.get('total_diario', '0')),
                estilo_celda
            ),

            observaciones,

            responsable

        ])

    # =========================
    # TABLA OPTIMIZADA
    # =========================

    tabla = Table(

        datos,

        repeatRows=1,

        splitByRow=True,

        colWidths=[

            55,   # Código
            120,  # Nombre
            45,   # Peso
            55,   # Sexo
            70,   # Ordeño mañana
            70,   # Ordeño tarde
            65,   # Total diario
            145,  # Observaciones
            95    # Responsable

        ]

    )

    # =========================
    # ESTILOS TABLA
    # =========================

    tabla.setStyle(TableStyle([

        # =========================
        # HEADER
        # =========================

        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7F5637')),

        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

        ('FONTSIZE', (0, 0), (-1, 0), 9),

        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

        ('TOPPADDING', (0, 0), (-1, 0), 8),

        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

        # =========================
        # CUERPO
        # =========================

        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFDF9')),

        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#3E2A1F')),

        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),

        ('FONTSIZE', (0, 1), (-1, -1), 7),

        # =========================
        # FILAS ALTERNAS
        # =========================

        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [

            colors.HexColor('#FFFDF9'),

            colors.HexColor('#F5E6D3')

        ]),

        # =========================
        # BORDES
        # =========================

        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#7F5637')),

        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#7F5637')),

        # =========================
        # ALINEACIÓN
        # =========================

        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),

        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),

        # =========================
        # ESPACIADOS
        # =========================

        ('TOPPADDING', (0, 1), (-1, -1), 5),

        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),

        ('LEFTPADDING', (0, 0), (-1, -1), 4),

        ('RIGHTPADDING', (0, 0), (-1, -1), 4),

        # =========================
        # AJUSTE TEXTO
        # =========================

        ('WORDWRAP', (0, 0), (-1, -1), 'LTR'),

    ]))

    elementos.append(tabla)

    elementos.append(Spacer(1, 20))

    # =========================
    # FOOTER
    # =========================

    footer = Paragraph(
        """
        <para align="center">

        <font size="9" color="#7F5637">

        Documento generado automáticamente por TECNOCAPRINOS

        </font>

        </para>
        """,
        estilos['Normal']
    )

    elementos.append(footer)

    # =========================
    # CONSTRUIR PDF
    # =========================

    doc.build(elementos)

    return response

@login_required_firebase
def registrar_enfermo(request, cabra_id):
    uid = request.session.get('uid')
    try:
        doc = db.collection('cabras').document(cabra_id).get()
        if not doc.exists:
            messages.error(request, "La cabra no existe")
            return redirect('info_animales')
        cabra = doc.to_dict()

    except Exception as e:
        messages.error(request, f"Error al obtener la cabra: {e}")
        return redirect('info_animales')

    if request.method == 'POST':
        existe = (
            db.collection('enfermas')
            .where('codigo', '==', cabra['codigo'])
            .where('usuario_id', '==', uid)
            .stream()
        )

        if list(existe):
            messages.error(
                request,
                "Esta cabra ya está registrada en enfermas"
            )
            return redirect('info_animales')
        try:
            db.collection('enfermas').add({
                'codigo': cabra['codigo'],
                'nombre': cabra['nombre'],
                'raza': cabra['raza'],
                'peso': cabra['peso'],
                'fecha_nacimiento': cabra['fecha_nacimiento'],
                'sexo': cabra['sexo'],
                'color': cabra['color'],
                'usuario_id': uid,
                'codigo_madre': cabra.get('codigo_madre'),
                'codigo_padre': cabra.get('codigo_padre')
            })

            messages.success(request, "Cabra registrada como enferma 🐐")
            return redirect('info_animales')

        except Exception as e:

            messages.error(
                request,
                f"Error al registrar la cabra enferma: {e}"
            )

    return redirect('info_animales')

@login_required_firebase
def registrar_vacuna(request, cabra_id):
    uid = request.session.get('uid')
    try:
        doc = db.collection('cabras').document(cabra_id).get()
        if not doc.exists:
            messages.error(request, "La cabra no existe")
            return redirect('info_animales')
        cabra = doc.to_dict()

    except Exception as e:
        messages.error(request, f"Error al obtener la cabra: {e}")
        return redirect('info_animales')

    if request.method == 'POST':
        existe = (
            db.collection('vacunas')
            .where('codigo', '==', cabra['codigo'])
            .where('usuario_id', '==', uid)
            .stream()
        )

        if list(existe):
            messages.error(
                request,
                "Esta cabra ya está registrada en vacunas"
            )
            return redirect('info_animales')
        try:
            db.collection('vacunas').add({
                'codigo': cabra['codigo'],
                'nombre': cabra['nombre'],
                'raza': cabra['raza'],
                'peso': cabra['peso'],
                'fecha_nacimiento': cabra['fecha_nacimiento'],
                'sexo': cabra['sexo'],
                'color': cabra['color'],
                'usuario_id': uid,
                'codigo_madre': cabra.get('codigo_madre'),
                'codigo_padre': cabra.get('codigo_padre')
            })

            messages.success(request, "Cabra registrada como enferma 🐐")
            return redirect('info_animales')

        except Exception as e:

            messages.error(
                request,
                f"Error al registrar la cabra enferma: {e}"
            )

    return redirect('info_animales')

@login_required_firebase
def agregar_produccion(request, cabra_id):
    uid = request.session.get('uid')
    try:
        doc = db.collection('cabras').document(cabra_id).get()
        if not doc.exists:
            messages.error(request, "La cabra no existe")
            return redirect('info_animales')
        cabra = doc.to_dict()

    except Exception as e:
        messages.error(request, f"Error al obtener la cabra: {e}")
        return redirect('info_animales')

    if request.method == 'POST':
        if cabra['sexo'] == 'Hembra':
            existe = (
                db.collection('produccion')
                .where('codigo', '==', cabra['codigo'])
                .where('usuario_id', '==', uid)
                .stream()
            )

            if list(existe):
                messages.error(
                    request,
                    "Esta cabra ya está registrada en producción"
                )
                return redirect('info_animales')
            
            try:
                db.collection('produccion').add({
                    'codigo': cabra['codigo'],
                    'nombre': cabra['nombre'],
                    'raza': cabra['raza'],
                    'peso': cabra['peso'],
                    'fecha_nacimiento': cabra['fecha_nacimiento'],
                    'sexo': cabra['sexo'],
                    'color': cabra['color'],
                    'usuario_id': uid,
                    'codigo_madre': cabra.get('codigo_madre'),
                    'codigo_padre': cabra.get('codigo_padre')
                })

                messages.success(request, "Cabra registrada en producción 🐐")
                return redirect('info_animales')
            except Exception as e:
                messages.error(request, f"Error al registrar la cabra en producción: {e}")
        else:
            messages.error(request, 'Solo las hembras pueden entrar en producción')
    return redirect('info_animales')

@login_required_firebase
def registrar_seguimiento_gestacion(request, cabra_id):
    uid = request.session.get('uid')
    try:
        doc = db.collection('cabras').document(cabra_id).get()
        if not doc.exists:
            messages.error(request, "La cabra no existe")
            return redirect('info_animales')
        cabra = doc.to_dict()

    except Exception as e:
        messages.error(request, f"Error al obtener la cabra: {e}")
        return redirect('info_animales')

    if request.method == 'POST':
        if cabra['sexo'] == 'Hembra':
            existe = (
                db.collection('en_cinta')
                .where('codigo', '==', cabra['codigo'])
                .where('usuario_id', '==', uid)
                .stream()
            )

            if list(existe):
                messages.error(
                    request,
                    "Esta cabra ya está registrada en En CInta"
                )
                return redirect('info_animales')
            
            try:
                db.collection('en_cinta').add({
                    'codigo': cabra['codigo'],
                    'nombre': cabra['nombre'],
                    'raza': cabra['raza'],
                    'peso': cabra['peso'],
                    'fecha_nacimiento': cabra['fecha_nacimiento'],
                    'color': cabra['color'],
                    'usuario_id': uid,
                    'codigo_madre': cabra.get('codigo_madre'),
                    'codigo_padre': cabra.get('codigo_padre')
                })

                messages.success(request, "Cabra registrada en En Cinta 🐐")
                return redirect('info_animales')
            except Exception as e:
                messages.error(request, f"Error al registrar la cabra en En Cinta: {e}")
        else:
            messages.error(request, 'Solo las hembras pueden entrar en En Cinta')
    return redirect('info_animales')

@login_required_firebase
def editar_enCinta(request, cabra_id):
    """
    UPDATE: Recupera los datos de la ca especifico y actualiza los campos en firebase
    """
    uid = request.session.get('uid')
    cabra_ref = db.collection('en_cinta').document(cabra_id)

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
            cod = request.POST.get('codigo')
            nombre = request.POST.get('nombre')
            raza = request.POST.get('raza')
            peso = request.POST.get('peso')
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            sexo = request.POST.get('sexo')
            color = request.POST.get('color')
            cod_madre = request.POST.get('cod_madre')
            cod_padre = request.POST.get('cod_padre')

            mes_gestacion = request.POST.get('mes_gestacion')
            estado_gestacion = request.POST.get('estado_gestacion')
            peso_actual = request.POST.get('peso_actual')
            veterinario_responsable = request.POST.get('veterinario_responsable')

            cabra_ref.update({
                'codigo': cod,
                'nombre': nombre,
                'raza': raza,
                'peso': peso,
                'fecha_nacimiento': fecha_nacimiento,
                'sexo': sexo,
                'color': color,
                'codigo_madre': cod_madre,
                'codigo_padre': cod_padre,
                
                'mes_gestacion': mes_gestacion,
                'estado_gestacion': estado_gestacion,
                'peso_actual': peso_actual,
                'veterinario_responsable': veterinario_responsable,
                'fecha_anadido': firestore.SERVER_TIMESTAMP
            })

            messages.success(request, "✅ Cabra actualizada correctamente.")
            return redirect('info_animales')
    except Exception as e:
        messages.error(request, f"Error al editar la cabra: {e}")
        return redirect('info_animales')
    return render(request, 'info/editar/editar_enCinta.html', {'cabra': cabra_data, 'id': cabra_id})

@login_required_firebase  # Verifica que el usuario esta loggeado
def eliminar_enCinta(request, cabra_id):
    """
    DELETE: Eliminar un documento especifico por id
    """
    try:
        db.collection('en_cinta').document(cabra_id).delete()
        messages.success(request, "🗑️ Cabra eliminada de En Cinta.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {e}")

    return redirect('info_animales')

@login_required_firebase
def editar_vacunas(request, cabra_id):
    """
    UPDATE: Recupera los datos de la ca especifico y actualiza los campos en firebase
    """
    uid = request.session.get('uid')
    cabra_ref = db.collection('vacunas').document(cabra_id)

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
            cod = request.POST.get('codigo')
            nombre = request.POST.get('nombre')
            raza = request.POST.get('raza')
            peso = request.POST.get('peso')
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            sexo = request.POST.get('sexo')
            color = request.POST.get('color')
            cod_madre = request.POST.get('cod_madre')
            cod_padre = request.POST.get('cod_padre')

            medicamento = request.POST.get('medicamento')
            cantidad = request.POST.get('cantidad')
            via_admin = request.POST.get('via_admin')
            veterinario_responsable = request.POST.get('veterinario_responsable')

            cabra_ref.update({
                'codigo': cod,
                'nombre': nombre,
                'raza': raza,
                'peso': peso,
                'fecha_nacimiento': fecha_nacimiento,
                'sexo': sexo,
                'color': color,
                'codigo_madre': cod_madre,
                'codigo_padre': cod_padre,
                
                'medicamento': medicamento,
                'cantidad': cantidad,
                'via_admin': via_admin,
                'veterinario_responsable': veterinario_responsable,
                'fecha_anadido': firestore.SERVER_TIMESTAMP
            })

            messages.success(request, "✅ Cabra actualizada correctamente.")
            return redirect('info_animales')
    except Exception as e:
        messages.error(request, f"Error al editar la cabra: {e}")
        return redirect('info_animales')
    return render(request, 'info/editar/editar_vacuna.html', {'cabra': cabra_data, 'id': cabra_id})

@login_required_firebase  # Verifica que el usuario esta loggeado
def eliminar_vacunas(request, cabra_id):
    """
    DELETE: Eliminar un documento especifico por id
    """
    try:
        db.collection('vacunas').document(cabra_id).delete()
        messages.success(request, "🗑️ Cabra eliminada de Vacunas.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {e}")

    return redirect('info_animales')

@login_required_firebase
def editar_enfermas(request, cabra_id):
    """
    UPDATE: Recupera los datos de la ca especifico y actualiza los campos en firebase
    """
    uid = request.session.get('uid')
    cabra_ref = db.collection('en_cinta').document(cabra_id)

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
            cod = request.POST.get('codigo')
            nombre = request.POST.get('nombre')
            raza = request.POST.get('raza')
            peso = request.POST.get('peso')
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            sexo = request.POST.get('sexo')
            color = request.POST.get('color')
            cod_madre = request.POST.get('cod_madre')
            cod_padre = request.POST.get('cod_padre')

            mes_gestacion = request.POST.get('mes_gestacion')
            estado_gestacion = request.POST.get('estado_gestacion')
            peso_actual = request.POST.get('peso_actual')
            veterinario_responsable = request.POST.get('veterinario_responsable')

            cabra_ref.update({
                'codigo': cod,
                'nombre': nombre,
                'raza': raza,
                'peso': peso,
                'fecha_nacimiento': fecha_nacimiento,
                'sexo': sexo,
                'color': color,
                'codigo_madre': cod_madre,
                'codigo_padre': cod_padre,
                
                'mes_gestacion': mes_gestacion,
                'estado_gestacion': estado_gestacion,
                'peso_actual': peso_actual,
                'veterinario_responsable': veterinario_responsable,
                'fecha_anadido': firestore.SERVER_TIMESTAMP
            })

            messages.success(request, "✅ Cabra actualizada correctamente.")
            return redirect('info_animales')
    except Exception as e:
        messages.error(request, f"Error al editar la cabra: {e}")
        return redirect('info_animales')
    return render(request, 'info/editar/editar_enCinta.html', {'cabra': cabra_data, 'id': cabra_id})

@login_required_firebase  # Verifica que el usuario esta loggeado
def eliminar_enfermas(request, cabra_id):
    """
    DELETE: Eliminar un documento especifico por id
    """
    try:
        db.collection('en_cinta').document(cabra_id).delete()
        messages.success(request, "🗑️ Cabra eliminada de En Cinta.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {e}")

    return redirect('info_animales')

@login_required_firebase
def editar_produccion(request, cabra_id):
    """
    UPDATE: Recupera los datos de la ca especifico y actualiza los campos en firebase
    """
    uid = request.session.get('uid')
    cabra_ref = db.collection('en_cinta').document(cabra_id)

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
            cod = request.POST.get('codigo')
            nombre = request.POST.get('nombre')
            raza = request.POST.get('raza')
            peso = request.POST.get('peso')
            fecha_nacimiento = request.POST.get('fecha_nacimiento')
            sexo = request.POST.get('sexo')
            color = request.POST.get('color')
            cod_madre = request.POST.get('cod_madre')
            cod_padre = request.POST.get('cod_padre')

            mes_gestacion = request.POST.get('mes_gestacion')
            estado_gestacion = request.POST.get('estado_gestacion')
            peso_actual = request.POST.get('peso_actual')
            veterinario_responsable = request.POST.get('veterinario_responsable')

            cabra_ref.update({
                'codigo': cod,
                'nombre': nombre,
                'raza': raza,
                'peso': peso,
                'fecha_nacimiento': fecha_nacimiento,
                'sexo': sexo,
                'color': color,
                'codigo_madre': cod_madre,
                'codigo_padre': cod_padre,
                
                'mes_gestacion': mes_gestacion,
                'estado_gestacion': estado_gestacion,
                'peso_actual': peso_actual,
                'veterinario_responsable': veterinario_responsable,
                'fecha_anadido': firestore.SERVER_TIMESTAMP
            })

            messages.success(request, "✅ Cabra actualizada correctamente.")
            return redirect('info_animales')
    except Exception as e:
        messages.error(request, f"Error al editar la cabra: {e}")
        return redirect('info_animales')
    return render(request, 'info/editar/editar_enCinta.html', {'cabra': cabra_data, 'id': cabra_id})

@login_required_firebase  # Verifica que el usuario esta loggeado
def eliminar_produccion(request, cabra_id):
    """
    DELETE: Eliminar un documento especifico por id
    """
    try:
        db.collection('en_cinta').document(cabra_id).delete()
        messages.success(request, "🗑️ Cabra eliminada de En Cinta.")
    except Exception as e:
        messages.error(request, f"Error al eliminar: {e}")

    return redirect('info_animales')