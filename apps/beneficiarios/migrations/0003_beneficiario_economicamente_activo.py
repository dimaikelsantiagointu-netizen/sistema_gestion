from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beneficiarios', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='beneficiario',
            name='es_economicamente_activo',
            field=models.BooleanField(default=False, verbose_name='Población Económicamente Activa'),
        ),
    ]
