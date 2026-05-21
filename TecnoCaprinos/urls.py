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
    path('info-animales/produccion', views.produccion, name='produccion'),
    path('info-animales/enfermas', views.enfermas, name='enfermas'),

    # Registros
    path('registrar-enfermo/', views.registrar_enfermo, name='registrar_enfermo'),
    path('registrar-vacuna/', views.registrar_vacuna, name='registrar_vacuna'),
    path('agregar-produccion/', views.agregar_produccion, name='agregar_produccion'),
    path('registrar-seguimiento-gestacion/',views.registrar_seguimiento_gestacion,name='registrar_seguimiento_gestacion'),

    #btn añadir cabra
    path('info-animales/anadir', views.anadir_cabra, name= 'anadir'),
    
    #CRUD
    path('info-animales/listar/eliminar/<str:cabra_id>/', views.eliminar_cabra, name='eliminar_cabra'),
    path('info-animales/listar/editar/<str:cabra_id>/', views.editar_cabra, name='editar_cabra'),
    
    # producción
    path('guardar-produccion/<str:cabra_id>/',views.guardar_produccion,name='guardar_produccion'
),
]