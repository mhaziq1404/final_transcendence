# Generated by Django 4.2.16 on 2024-11-15 00:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0043_room_final_player1_room_final_player2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='room',
            name='final_player1',
        ),
        migrations.RemoveField(
            model_name='room',
            name='final_player2',
        ),
    ]
