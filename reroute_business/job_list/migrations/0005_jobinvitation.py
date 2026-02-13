from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('job_list', '0004_application_notes'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('sent', 'Sent')], default='sent', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_invitations_received', to=settings.AUTH_USER_MODEL)),
                ('employer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_invitations_sent', to=settings.AUTH_USER_MODEL)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_invitations', to='job_list.job')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='jobinvitation',
            index=models.Index(fields=['employer', 'candidate'], name='job_list_j_employe_96c1db_idx'),
        ),
        migrations.AddIndex(
            model_name='jobinvitation',
            index=models.Index(fields=['employer', 'job'], name='job_list_j_employe_e619b7_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='jobinvitation',
            unique_together={('employer', 'candidate', 'job')},
        ),
    ]
