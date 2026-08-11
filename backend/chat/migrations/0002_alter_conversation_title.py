from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chat", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="title",
            field=models.CharField(max_length=255),
        ),
    ]
