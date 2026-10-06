from django.db import migrations


def normalizar_orden_categorias(apps, schema_editor):
    CategoriaVisita = apps.get_model('beneficiarios', 'CategoriaVisita')
    database = schema_editor.connection.alias
    categorias = list(
        CategoriaVisita.objects.using(database).order_by('-activa', 'orden', 'nombre', 'pk')
    )

    for orden, categoria in enumerate(categorias, start=1):
        categoria.orden = orden

    CategoriaVisita.objects.using(database).bulk_update(categorias, ['orden'])


class Migration(migrations.Migration):

    dependencies = [
        ('beneficiarios', '0009_categoriavisita_remove_visita_motivo_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_orden_categorias, migrations.RunPython.noop),
    ]
