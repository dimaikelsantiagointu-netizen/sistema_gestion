from django.urls import path
from . import views

app_name = 'personal'

urlpatterns = [
    # 1. LISTADO Y FILTROS (Punto 5)
    path('', views.PersonalListView.as_view(), name='lista'),
    
    # 2. REGISTRO DE NUEVO TALENTO (Punto 3)
    path('nuevo/', views.PersonalCreateView.as_view(), name='crear'),
    
    # 3. EXPEDIENTE DIGITAL DETALLADO (Punto 4)
    path('expediente/<int:pk>/', views.PersonalDetailView.as_view(), name='detalle'),
    
    # 4. CARGA DE DOCUMENTOS (Punto 4.1)
    path('expediente/<int:pk>/subir/', views.subir_archivo_personal, name='subir_documento'),

]