# Generated by Django 3.1.5 on 2021-03-22 17:54

from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SourceCred',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.plugin',),
        ),
    ]
