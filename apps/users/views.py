# apps/users/views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'base.html'  # Aquí es donde indicamos que cargue tu archivo principal

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasamos datos del usuario para usarlos en el menú lateral o superior
        context['username'] = self.request.user.username
        context['rol'] = self.request.user.rol
        return context
    
