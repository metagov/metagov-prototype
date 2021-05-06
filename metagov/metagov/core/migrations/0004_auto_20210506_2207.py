# Generated by Django 3.1.8 on 2021-05-06 22:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20210421_2158'),
    ]

    operations = [
        migrations.AlterField(
            model_name='governanceprocess',
            name='callback_url',
            field=models.CharField(blank=True, help_text='Callback URL to notify when the process is updated', max_length=50, null=True),
        ),
    ]
