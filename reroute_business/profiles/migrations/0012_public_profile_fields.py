from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0011_userprofile_ready_to_discuss_background'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='headline',
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='location',
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='is_public',
            field=models.BooleanField(default=True, help_text='Allow employers/reentry orgs to view this profile.'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='core_skills',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='soft_skills',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
        migrations.CreateModel(
            name='ProfileExperience',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120)),
                ('company', models.CharField(blank=True, max_length=120)),
                ('start_year', models.CharField(blank=True, max_length=4)),
                ('end_year', models.CharField(blank=True, max_length=4)),
                ('highlights', models.JSONField(blank=True, default=list, null=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experiences', to='profiles.userprofile')),
            ],
            options={
                'ordering': ['order', '-start_year', '-end_year', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ProfileCertification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('issuer', models.CharField(blank=True, max_length=200)),
                ('year', models.CharField(blank=True, max_length=4)),
                ('order', models.PositiveIntegerField(default=0)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certifications', to='profiles.userprofile')),
            ],
            options={
                'ordering': ['order', '-year', 'id'],
            },
        ),
    ]
