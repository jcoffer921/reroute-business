from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_inline_quiz_data(apps, schema_editor):
    Module = apps.get_model('resources', 'Module')
    QuizQuestion = apps.get_model('resources', 'QuizQuestion')
    QuizAnswer = apps.get_model('resources', 'QuizAnswer')

    for module in Module.objects.exclude(quiz_data=None):
        data = module.quiz_data or {}
        questions = data.get('questions') if isinstance(data, dict) else None
        if not questions:
            continue

        order_counter = 1
        for question_data in questions:
            prompt = question_data.get('prompt') if isinstance(question_data, dict) else ''
            if not prompt:
                continue
            order_value = question_data.get('order') if isinstance(question_data, dict) else None
            question = QuizQuestion.objects.create(
                module=module,
                prompt=prompt,
                order=order_value or order_counter,
            )
            order_counter += 1

            choices = question_data.get('choices') if isinstance(question_data, dict) else []
            if not isinstance(choices, list):
                continue
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                text = choice.get('text') or ''
                if not text:
                    continue
                QuizAnswer.objects.create(
                    question=question,
                    text=text,
                    is_correct=bool(choice.get('is_correct') or choice.get('correct')),
                )

        module.quiz_data = None
        module.save(update_fields=['quiz_data'])


def reverse_inline_quiz_data(apps, schema_editor):
    # No-op: we cannot reliably recreate the exact original JSON payload.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0005_resourcemodule_quiz_data'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ResourceModule',
            new_name='Module',
        ),
        migrations.AddField(
            model_name='module',
            name='key_takeaways',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name='QuizQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prompt', models.TextField()),
                ('order', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='resources.module')),
            ],
            options={
                'ordering': ('order', 'id'),
            },
        ),
        migrations.CreateModel(
            name='QuizAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255)),
                ('is_correct', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='resources.quizquestion')),
            ],
            options={
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='ModuleQuizScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveIntegerField(default=0)),
                ('total_questions', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scores', to='resources.module')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='module_quiz_scores', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='modulequizscore',
            constraint=models.UniqueConstraint(fields=('module', 'user'), name='unique_user_module_score'),
        ),
        migrations.RunPython(migrate_inline_quiz_data, reverse_inline_quiz_data),
    ]
