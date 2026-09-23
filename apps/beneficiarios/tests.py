from django.test import SimpleTestCase

from apps.beneficiarios.models import Visita


class VisitaMotivoChoicesTest(SimpleTestCase):
    def test_motivo_choices_include_business_order_and_separate_ctu_and_comercial_categories(self):
        displayed_names = [name for _, name in Visita.MOTIVO_CHOICES]

        expected = [
            'Atenciones AVV Técnicas y Jurídicas',
            'Informes de Prefactibilidad',
            'Inspección del Terreno',
            'Topografía',
            'Estudios de Suelo',
            'CTU: Registro de CTU',
            'CTU: Actualización de CTU',
            'CTU: Corrección y asistencia jurídica al CTU',
            'Regularización Comercial: Consignación de recaudos',
            'Regularización Comercial: Inspección del local comercial',
            'Regularización Comercial: Regularización comercial',
            'Regularización Extinto INAVI',
            'Solicitud',
            'Status de solicitudes',
            'Reunión',
            'Asesorías',
            'Otros',
            'Expediente (Consignación)',
            'Inspección para Linderos',
            'Autorización de Pago',
            'Liberaciones de Título Supletorio',
            'Aclaratoria',
            'Autorización para Título Supletorio',
            'Transferencia de Terrenos',
            'Solicitud de Linderos',
        ]

        self.assertEqual(expected, displayed_names)
        self.assertEqual(80, Visita._meta.get_field('motivo').max_length)
        self.assertIn('CTU: Registro de CTU', displayed_names)
        self.assertIn('CTU: Actualización de CTU', displayed_names)
        self.assertIn('CTU: Corrección y asistencia jurídica al CTU', displayed_names)
        self.assertIn('Regularización Comercial: Consignación de recaudos', displayed_names)
        self.assertIn('Regularización Comercial: Inspección del local comercial', displayed_names)
        self.assertIn('Regularización Comercial: Regularización comercial', displayed_names)

    def test_motivo_choices_include_additional_visit_categories(self):
        displayed_names = [name for _, name in Visita.MOTIVO_CHOICES]

        self.assertEqual(
            [
                'Status de solicitudes',
                'Reunión',
                'Asesorías',
                'Otros',
            ],
            displayed_names[13:17],
        )
