# apps/users/views.py
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .forms import CustomUserCreationForm  # Importamos el formulario que creamos

class DashboardView(LoginRequiredMixin, TemplateView):
    # Nota: Asegúrate de que este sea 'home.html' si moviste los botones allí
    template_name = 'gestores.html'  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['username'] = self.request.user.username
        context['rol'] = self.request.user.rol
        return context

class CrearUsuarioView(LoginRequiredMixin, UserPassesTestMixin, CreateView):

    template_name = 'users/crear_usuario.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('home')

    def test_func(self):
        # Seguridad: Solo superusuarios o el rol 'superadmin' pueden entrar
        return self.request.user.is_superuser or self.request.user.rol == 'superadmin'

    def form_valid(self, form):
        # Si el formulario es válido, guardamos y enviamos un mensaje de éxito
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        messages.success(self.request, f"El usuario '{username}' ha sido creado correctamente.")
        return response