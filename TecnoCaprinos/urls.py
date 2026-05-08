from django.urls import path
from . import views

urlpatterns = [
    path('', views.bienvenido, name='bienvenido'),
    path('registro/', views.registro_usuario, name='registro'),
    path('login/', views.login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.cerrar_sesion, name='logout'),

    # info animales primera pestaña
    path('info-animales/', views.info_animales, name= 'info_animales'),
    
    
    path('info-animales/cinta', views.cinta, name= 'cinta'),
    path('info-animales/vacunas', views.vacunas, name= 'vacunas'),
    path('info-animales/produccion', views.produccion, name= 'produccion'),
    path('info-animales/enfermas', views.enfermas, name= 'enfermas'),
    
    
    #btn añadir cabra
    path('info-animales/anadir', views.anadir, name= 'anadir'),
    
    



path('info-animales/', views.info_animales, name='info_animales'),


    path('info-animales/cinta', views.cinta, name='cinta'),
    path('info-animales/vacunas', views.vacunas, name='vacunas'),
    path('info-animales/produccion', views.produccion, name='produccion'),
    path('info-animales/enfermas', views.enfermas, name='enfermas'),


    # btn añadir cabra
    path('info-animales/anadir', views.anadir, name='anadir'),


    path('registrar-enfermo/', views.registrar_enfermo, name='registrar_enfermo'),
    path('registrar-vacuna/', views.registrar_vacuna, name='registrar_vacuna'),
    path('agregar-produccion/', views.agregar_produccion,name='agregar_produccion'),
    path('registrar-seguimiento-gestacion/', views.registrar_seguimiento_gestacion,name='registrar_seguimiento_gestacion'),
    
    path('guardar_animal/', views.guardar_animal,name='guardar_animal'),
    path('listar_cabras/', views.listar_cabras,name='listar'),

]
