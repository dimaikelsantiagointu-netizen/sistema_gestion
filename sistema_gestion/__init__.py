from .base import *

# Para desarrollo, usar development settings
try:
    from .development import *
except ImportError:
    pass

# Para producción, usar production settings  
try:
    from .production import *
except ImportError:
    pass
