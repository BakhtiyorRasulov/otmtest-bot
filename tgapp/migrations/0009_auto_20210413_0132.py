# Generated by Django 3.1.7 on 2021-04-13 01:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tgapp', '0008_auto_20210413_0122'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='language',
            field=models.CharField(choices=[('uz', "O'zbek"), ('ru', 'Русский')], default='uz', max_length=10),
        ),
    ]
