# Generated by Django 4.2 on 2025-05-13 03:32

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0003_alter_upload_uploaded_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='upload',
            name='uploaded_at',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2025, 5, 13, 3, 32, 51, 931991, tzinfo=datetime.timezone.utc)),
            preserve_default=False,
        ),
    ]
