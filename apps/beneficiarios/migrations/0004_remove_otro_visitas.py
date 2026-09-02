from django.db import migrations


def map_otro_to_solicitud(apps, schema_editor):
    Visita = apps.get_model('beneficiarios', 'Visita')
    # Mapear registros existentes con motivo 'OTRO' a 'SOLICITUD' para preservar datos
    Visita.objects.filter(motivo='OTRO').update(motivo='SOLICITUD')


def no_op(apps, schema_editor):
    # Reversión no restaurará el estado previo
    return


class Migration(migrations.Migration):

    dependencies = [
        ('beneficiarios', '0003_beneficiario_economicamente_activo'),
    ]

    operations = [
        migrations.RunPython(map_otro_to_solicitud, no_op),
    ]
