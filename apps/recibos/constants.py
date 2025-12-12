# constants.py

CATEGORY_CHOICES = (
    ('categoria1', '1.Título Tierra Urbana'),
    ('categoria2', '2.Título + Vivienda'),
    ('categoria3', '3.Municipal'),
    ('categoria4', '4.Tierra Privada'),
    ('categoria5', '5.Tierra INAVI'),
    ('categoria6', '6.Excedentes Título'),
    ('categoria7', '7.Excedentes INAVI'),
    ('categoria8', '8.Estudio Técnico'),
    ('categoria9', '9.Locales Comerciales'),
    ('categoria10', '10.Arrendamiento Terrenos'),
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