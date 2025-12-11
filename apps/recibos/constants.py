# constants.py

CATEGORY_CHOICES = (
    ('categoria1', 'Título Tierra Urbana'),
    ('categoria2', 'Título + Vivienda'),
    ('categoria3', 'Municipal'),
    ('categoria4', 'Tierra Privada'),
    ('categoria5', 'Tierra INAVI'),
    ('categoria6', 'Excedentes Título'),
    ('categoria7', 'Excedentes INAVI'),
    ('categoria8', 'Estudio Técnico'),
    ('categoria9', 'Locales Comerciales'),
    ('categoria10', 'Arrendamiento Terrenos'),
)
CATEGORY_CHOICES_MAP = dict(CATEGORY_CHOICES)

# -------------------------------------------------------------
# 🚀 ADICIÓN NECESARIA: Definición de Estados del Recibo
# -------------------------------------------------------------

ESTADO_PAGADO = 'PAGADO'
ESTADO_ANULADO = 'ANULADO'
ESTADO_PENDIENTE = 'PENDIENTE'

ESTADO_CHOICES = (
    (ESTADO_PAGADO, 'Pagado'),
    (ESTADO_ANULADO, 'Anulado'),
    (ESTADO_PENDIENTE, 'Pendiente'),
)

ESTADO_CHOICES_MAP = dict(ESTADO_CHOICES)