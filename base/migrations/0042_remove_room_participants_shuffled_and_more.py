# Generated by Django 5.1.1 on 2024-09-27 04:30

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0041_room_participants_shuffled'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='room',
            name='participants_shuffled',
        ),
        migrations.AddField(
            model_name='room',
            name='participants_shuffled',
            field=models.ManyToManyField(blank=True, related_name='participants_shuffled', to=settings.AUTH_USER_MODEL),
        ),
    ]
