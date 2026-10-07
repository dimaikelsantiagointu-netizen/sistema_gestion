from django.urls import path
from . import views

app_name = 'personal'

urlpatterns = [
    path('', views.PersonalListView.as_view(), name='lista'),
    path('nuevo/', views.PersonalCreateView.as_view(), name='crear'),
    path('editar/<int:pk>/', views.PersonalUpdateView.as_view(), name='editar'),
    path('expediente/<int:pk>/', views.PersonalDetailView.as_view(), name='detalle'),
    
    # Gestión de Documentos
    path('expediente/<int:pk>/subir/', views.subir_archivo_personal, name='subir_documento'),
]