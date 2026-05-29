from django.urls import path
from . import views

urlpatterns = [
    path('', views.bienvenido, name='bienvenido'),
    path('registro/', views.registro_usuario, name='registro'),
    path('login/', views.login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.cerrar_sesion, name='logout'),

    # Información animales
    path('info-animales/', views.info_animales, name='info_animales'),
    path('info-animales/cinta', views.cinta, name='cinta'),
    path('info-animales/vacunas', views.vacunas, name='vacunas'),
    path('info-animales/pdf-vacunas/', views.pdf_vacunas, name='pdf_vacunas'),
    path('info-animales/produccion', views.produccion, name='produccion'),
    path('info-animales/pdf-produccion/', views.pdf_produccion, name='pdf_produccion'),
    path('info-animales/enfermas', views.enfermas, name='enfermas'),

    # Registros
    path('registrar-enfermo/<str:cabra_id>/', views.registrar_enfermo, name='registrar_enfermo'),
    path('registrar-vacuna/<str:cabra_id>', views.registrar_vacuna, name='registrar_vacuna'),
    path('agregar-produccion/<str:cabra_id>', views.agregar_produccion, name='agregar_produccion'),
    path('registrar-seguimiento-gestacion/<str:cabra_id>',views.registrar_seguimiento_gestacion,name='registrar_seguimiento_gestacion'),

    #CRUD
    path('info-animales/anadir', views.anadir_cabra, name= 'anadir'),
    path('info-animales/info_cabra/<str:cabra_id>/', views.info_completa_cabra, name='info_completa_cabra'),
    path('info-animales/listar/eliminar/<str:cabra_id>/', views.eliminar_cabra, name='eliminar_cabra'),
    path('info-animales/listar/editar/<str:cabra_id>/', views.editar_cabra, name='editar_cabra'),
    
    # Detalle animales
    path('animal/<int:id>/', views.detalle_animal, name='detalle_animal'),
    path('animal/<str:cabra_id>/',views.detalle_animal, name='detalle_animal'),

    # Editar informaciones de vacunas, etc...
    path('info-animales/vacunas/editar/<str:cabra_id>', views.editar_vacunas, name='editar_vacunas'),
    path('info-animales/produccion/editar/<str:cabra_id>', views.editar_produccion, name='editar_produccion'),
    path('info-animales/enfermas/editar/<str:cabra_id>', views.editar_enfermas, name='editar_enfermas'),
    path('info-animales/enCinta/editar/<str:cabra_id>', views.editar_enCinta, name='editar_enCinta'),
]