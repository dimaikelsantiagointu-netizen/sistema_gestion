from django.urls import path
from . import views

app_name = 'personal'

urlpatterns = [
    # 1. LISTADO Y FILTROS (Punto 5)
    # Accesible como 'personal:lista'
    path('', views.PersonalListView.as_view(), name='lista'),
    
    # 2. REGISTRO DE NUEVO TALENTO (Punto 3)
    path('nuevo/', views.PersonalCreateView.as_view(), name='crear'),
    
    # 3. EXPEDIENTE DIGITAL DETALLADO (Punto 4)
    # Importante: El nombre 'detalle' es el que usamos en el redirect de 'subir_archivo'
    path('expediente/<int:pk>/', views.PersonalDetailView.as_view(), name='detalle'),
    
    # 4. CARGA DE DOCUMENTOS (Punto 4.1)
    # El nombre 'subir_documento' es el que invoca el formulario del template detail
    path('expediente/<int:pk>/subir/', views.subir_archivo_personal, name='subir_documento'),

    # 5. ELIMINACIÓN DE DOCUMENTOS (Recomendado)
    # Útil para mantener el orden del archivo sin entrar al admin
    # path('documento/eliminar/<int:doc_id>/', views.eliminar_documento_personal, name='eliminar_documento'),
]