# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proctoring', '0002_exam_last_poll'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='last_poll',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
