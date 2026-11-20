from django.db import migrations


ESTATUS_INICIALES = [
    ('En revisión', 1),
    ('Registrado', 2),
    ('Anulado', 3),
]


def crear_catalogos(apps, schema_editor):
    EstatusDocumento = apps.get_model('gestion_documental', 'EstatusDocumento')
    SecuenciaExpediente = apps.get_model(
        'gestion_documental',
        'SecuenciaExpediente',
    )
    database = schema_editor.connection.alias

    for nombre, orden in ESTATUS_INICIALES:
        EstatusDocumento.objects.using(database).get_or_create(
            nombre=nombre,
            defaults={'orden': orden, 'activo': True},
        )
    SecuenciaExpediente.objects.using(database).get_or_create(
        pk=1,
        defaults={'ultimo_numero': 0},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_documental', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_catalogos, migrations.RunPython.noop),
    ]
