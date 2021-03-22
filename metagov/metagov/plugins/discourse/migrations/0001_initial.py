# Generated by Django 3.1.5 on 2021-03-22 14:19

from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0002_asyncprocess'),
    ]

    operations = [
        migrations.CreateModel(
            name='Discourse',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.plugin',),
        ),
        migrations.CreateModel(
            name='DiscoursePoll',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.asyncprocess',),
        ),
    ]