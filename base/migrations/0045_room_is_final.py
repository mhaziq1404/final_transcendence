# Generated by Django 4.2.16 on 2024-11-15 01:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0044_remove_room_final_player1_remove_room_final_player2'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='is_final',
            field=models.BooleanField(default=False),
        ),
    ]
