from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ReentryOrganization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('category', models.CharField(choices=[('employment', 'Employment'), ('education', 'Education'), ('housing', 'Housing'), ('legal', 'Legal'), ('health', 'Health'), ('mentorship', 'Mentorship'), ('financial', 'Financial'), ('family', 'Family & Children'), ('transportation', 'Transportation'), ('other', 'Other')], db_index=True, max_length=32)),
                ('is_verified', models.BooleanField(db_index=True, default=False)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='org_logos/')),
                ('website', models.URLField(blank=True)),
                ('description', models.TextField(blank=True)),
                ('city', models.CharField(blank=True, max_length=128)),
                ('state', models.CharField(blank=True, max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='reentryorganization',
            index=models.Index(fields=['is_verified', 'category'], name='reentry_org_is_verified_category_idx'),
        ),
    ]

