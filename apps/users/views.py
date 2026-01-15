# apps/users/views.py
from django.views.generic import TemplateView, CreateView, ListView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import Usuario

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'gestores.html'  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['username'] = self.request.user.username
        context['rol'] = self.request.user.rol
        return context

# --- VISTA PARA CREAR ---
class CrearUsuarioView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    template_name = 'users/crear_usuario.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('home')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.rol == 'superadmin'

    def form_valid(self, form):
        usuario = form.save(commit=False)
        if usuario.rol == 'superadmin':
            usuario.is_superuser = True
            usuario.is_staff = True
        else:
            usuario.is_superuser = False
            usuario.is_staff = False
        usuario.save()
        form.save_m2m()
        messages.success(self.request, f"El usuario '{usuario.username}' ha sido registrado exitosamente.")
        return super().form_valid(form)

# --- VISTA PARA LISTAR (CORREGIDA LA INDENTACIÓN) ---
class UsuarioListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Usuario
    template_name = 'users/usuario_list.html'
    context_object_name = 'usuarios'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.rol == 'superadmin'

# --- VISTA PARA EDITAR ---
class UsuarioUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Usuario
    form_class = CustomUserChangeForm
    template_name = 'users/crear_usuario.html'
    success_url = reverse_lazy('users:usuario_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.rol == 'superadmin'

    def form_valid(self, form):
        usuario = form.save(commit=False)
        if usuario.rol == 'superadmin':
            usuario.is_superuser = True
            usuario.is_staff = True
        else:
            usuario.is_superuser = False
            usuario.is_staff = False
        usuario.save()
        form.save_m2m()
        messages.success(self.request, "Usuario actualizado correctamente.")
        return super().form_valid(form)

# --- VISTA PARA ELIMINAR ---
class UsuarioDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Usuario
    template_name = 'users/usuario_confirm_delete.html'
    success_url = reverse_lazy('users:usuario_list')

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.rol == 'superadmin'