# Generated by Django 3.1.8 on 2021-04-26 21:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20210421_2158'),
        ('opencollective', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpenCollectiveVote',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.governanceprocess',),
        ),
    ]
