# Generated by Django 2.0 on 2018-02-27 12:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interface', '0011_auto_20180222_1554'),
    ]

    operations = [
        migrations.AddField(
            model_name='content',
            name='permissions',
            field=models.ManyToManyField(to='interface.UserProfile'),
        ),
        migrations.AddField(
            model_name='timelinecontents',
            name='permissions',
            field=models.ManyToManyField(to='interface.UserProfile'),
        ),
        migrations.AddField(
            model_name='viewtimelines',
            name='permissions',
            field=models.ManyToManyField(to='interface.UserProfile'),
        ),
    ]
