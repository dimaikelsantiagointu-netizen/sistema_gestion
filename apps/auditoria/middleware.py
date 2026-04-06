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
        # 1. Capturar usuario
        _thread_locals.user = request.user if request.user.is_authenticated else None
        
        # 2. Capturar IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            _thread_locals.ip = x_forwarded_for.split(',')[0]
        else:
            _thread_locals.ip = request.META.get('REMOTE_ADDR')

        response = self.get_response(request)
        return response