from django.db import models

class Cabra(models.Model):
    nombre = models.CharField(max_length=100)
    edad = models.IntegerField()
    peso = models.FloatField()
    raza = models.CharField(max_length=100)
    tamaño = models.CharField(max_length=100)
    
    ESTADOS = [
        ('cinta', 'En cinta'),
        ('vacunas', 'Vacunas'),
        ('enferma', 'Enferma'),
        ('produccion', 'Producción'),
    ]
    
    estado = models.CharField(max_length=20, choices=ESTADOS)

    fecha_nacimiento = models.DateField()
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre