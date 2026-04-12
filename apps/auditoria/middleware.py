import threading

# Variable global por hilo para guardar el usuario e IP
_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def get_current_ip():
    return getattr(_thread_locals, 'ip', None)

class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # --- LISTA DE EXCLUSIÓN ---
        # Si la URL pertenece a la app de recibos, limpiamos los datos del hilo
        # para que nada se guarde en la base de datos de auditoría.
        if 'recibos/' in request.path:
            _thread_locals.user = None
            _thread_locals.ip = None
            return self.get_response(request)

        # 1. Capturar usuario (Solo si no es una ruta excluida)
        _thread_locals.user = request.user if request.user.is_authenticated else None
        
        # 2. Capturar IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            _thread_locals.ip = x_forwarded_for.split(',')[0]
        else:
            _thread_locals.ip = request.META.get('REMOTE_ADDR')

        response = self.get_response(request)
        
        # Limpieza de seguridad al finalizar la petición para evitar fugas de memoria
        _thread_locals.user = None
        _thread_locals.ip = None
        
        return response