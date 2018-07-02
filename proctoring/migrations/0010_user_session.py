# Generated by Django 2.0.3 on 2018-06-29 12:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('proctoring', '0009_update_exam_table_exam_name_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(db_index=True, max_length=255)),
                ('user_agent', models.TextField()),
                ('browser', models.CharField(max_length=255)),
                ('os', models.CharField(max_length=255)),
                ('ip_address', models.CharField(max_length=255)),
                ('timestamp', models.IntegerField()),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddField(
            model_name='usersession',
            name='exam',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='proctoring.Exam'),
        ),
    ]
