# -*- coding: utf-8 -*-
# Generated by Django 2.0.3 on 2018-04-20 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proctoring', '0006_org_description'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={'ordering': ['event_start']},
        ),
        migrations.AlterModelOptions(
            name='exam',
            options={'ordering': ['id']},
        ),
        migrations.AddField(
            model_name='comment',
            name='event_type',
            field=models.CharField(choices=[('comment', 'Comment'), ('warning', 'Warning')], default='comment', max_length=20),
        ),
        migrations.RunSQL("UPDATE proctoring_comment SET event_type = IF(event_status = 'Подозрительно', 'warning', 'comment');"),
    ]
