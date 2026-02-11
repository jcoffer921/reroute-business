from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0008_module_poster_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="module",
            name="is_archived",
            field=models.BooleanField(default=False),
        ),
    ]
