from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0002_resourcemodule'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Lesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('description', models.TextField(blank=True)),
                ('video_static_path', models.CharField(help_text='Static path under /static, e.g., /static/resources/videos/ResumeBasics101-improved.mp4', max_length=500)),
                ('youtube_video_id', models.CharField(blank=True, help_text='Optional YouTube video ID (e.g., bBkWA7sBOEg) to stream via YouTube player.', max_length=32, null=True)),
                ('duration_seconds', models.FloatField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='LessonQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=1)),
                ('timestamp_seconds', models.FloatField(help_text='Time in seconds when the question should appear')),
                ('prompt', models.TextField()),
                ('qtype', models.CharField(choices=[('MULTIPLE_CHOICE', 'Multiple Choice'), ('OPEN_ENDED', 'Open Ended')], default='MULTIPLE_CHOICE', max_length=32)),
                ('is_required', models.BooleanField(default=True)),
                ('is_scored', models.BooleanField(default=True)),
                ('active', models.BooleanField(default=True)),
                ('lesson', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='questions', to='resources.lesson')),
            ],
            options={'ordering': ('order',)},
        ),
        migrations.CreateModel(
            name='LessonChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(help_text='e.g., a, b, c, d', max_length=5)),
                ('text', models.TextField()),
                ('is_correct', models.BooleanField(default=False)),
                ('position', models.PositiveIntegerField(default=1)),
                ('question', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='choices', to='resources.lessonquestion')),
            ],
            options={'ordering': ('position',)},
        ),
        migrations.CreateModel(
            name='LessonAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, db_index=True, max_length=64)),
                ('open_text', models.TextField(blank=True)),
                ('is_correct', models.BooleanField(default=False)),
                ('attempt_number', models.PositiveIntegerField(default=1)),
                ('video_time', models.FloatField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('question', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='attempts', to='resources.lessonquestion')),
                ('selected_choice', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to='resources.lessonchoice')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='lesson_attempts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='LessonProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, db_index=True, max_length=64)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('correct_count', models.PositiveIntegerField(default=0)),
                ('scored_count', models.PositiveIntegerField(default=0)),
                ('accuracy_percent', models.PositiveIntegerField(default=0)),
                ('last_video_time', models.FloatField(default=0)),
                ('last_answered_question_order', models.PositiveIntegerField(default=0)),
                ('raw_state', models.JSONField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('lesson', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='progress', to='resources.lesson')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='lesson_progress', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-updated_at',)},
        ),
    ]
