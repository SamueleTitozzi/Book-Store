from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0008_alter_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='refunded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Очікує оплати'),
                    ('paid', 'Оплачено'),
                    ('processing', 'В обробці'),
                    ('shipped', 'Відправлено'),
                    ('delivered', 'Доставлено'),
                    ('cancelled', 'Скасовано'),
                    ('return_pending', 'Очікує повернення'),
                    ('refunded', 'Повернено кошти'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
