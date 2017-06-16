# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proctoring', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='last_poll',
            field=models.DateTimeField(null=True),
        ),
    ]
