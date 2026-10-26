from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0010_share_last_price_decimal"),
    ]

    operations = [
        migrations.AddField(
            model_name="strategyrun",
            name="strategy_snapshot",
            field=models.JSONField(default=dict),
        ),
    ]
