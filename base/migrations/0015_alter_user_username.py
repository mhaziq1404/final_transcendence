# Generated by Django 3.2.25 on 2024-07-25 09:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0014_auto_20240723_0503'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=200, null=True),
        ),
    ]