from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0003_resume_certifications"),
    ]

    operations = [
        migrations.AddField(
            model_name="resume",
            name="preview_image",
            field=models.ImageField(blank=True, null=True, upload_to="resumes/previews/"),
        ),
    ]

