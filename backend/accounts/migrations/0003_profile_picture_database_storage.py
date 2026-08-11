from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_emailverificationcode")]

    operations = [
        migrations.AddField(
            model_name="profile", name="profile_picture_data",
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="profile", name="profile_picture_content_type",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
