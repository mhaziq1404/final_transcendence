# Generated by Django 3.2.7 on 2024-07-22 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0011_room_is_expired'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='opponent_type',
            field=models.CharField(choices=[('vs Player', 'vs Player'), ('Tournament', 'Tournament'), ('ai', 'AI')], default='ai', max_length=10),
        ),
    ]