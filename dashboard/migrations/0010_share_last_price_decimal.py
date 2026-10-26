from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0009_tradingstrategy_strategy_lookback_days_positive"),
    ]

    operations = [
        migrations.AlterField(
            model_name="share",
            name="last_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=20,
                null=True,
                verbose_name="Текущая цена",
            ),
        ),
    ]
