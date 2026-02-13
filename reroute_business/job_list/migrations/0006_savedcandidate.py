from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('job_list', '0005_jobinvitation'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedCandidate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by_employers', to=settings.AUTH_USER_MODEL)),
                ('saved_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_candidates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'unique_together': {('saved_by', 'candidate')},
            },
        ),
        migrations.AddIndex(
            model_name='savedcandidate',
            index=models.Index(fields=['saved_by', 'candidate'], name='savedcand_user_idx'),
        ),
    ]
