# Generated by Django 2.0 on 2018-02-15 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interface', '0003_content_file_format'),
    ]

    operations = [
        migrations.AlterField(
            model_name='content',
            name='file_format',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AlterField(
            model_name='content',
            name='path',
            field=models.CharField(max_length=140, null=True),
        ),
    ]
