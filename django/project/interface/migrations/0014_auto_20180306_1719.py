# Generated by Django 2.0 on 2018-03-06 17:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interface', '0013_auto_20180227_1456'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='view',
            name='ip',
        ),
        migrations.AddField(
            model_name='view',
            name='configured',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='view',
            name='mac',
            field=models.CharField(default='00:00:00:00:00:00', max_length=20),
            preserve_default=False,
        ),
    ]
