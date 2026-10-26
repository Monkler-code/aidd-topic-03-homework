from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0011_strategyrun_strategy_snapshot"),
    ]

    operations = [
        migrations.AlterField(
            model_name="strategyrun",
            name="strategy",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="runs",
                to="dashboard.tradingstrategy",
            ),
        ),
    ]
