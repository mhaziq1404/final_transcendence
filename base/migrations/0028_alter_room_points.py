# Generated by Django 3.2.25 on 2024-08-17 06:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0027_auto_20240815_0732'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='points',
            field=models.IntegerField(default=1),
        ),
    ]