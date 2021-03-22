# Generated by Django 3.1.5 on 2021-03-22 14:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AsyncProcess',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('callback_url', models.CharField(blank=True, max_length=50, null=True)),
                ('status', models.CharField(choices=[('created', 'CREATED'), ('pending', 'PENDING'), ('completed', 'COMPLETED')], default='created', max_length=15)),
                ('data', models.OneToOneField(help_text='Datastore to persist any data', on_delete=django.db.models.deletion.CASCADE, to='core.datastore')),
                ('plugin', models.ForeignKey(help_text='Plugin instance that this process belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='plugin', to='core.plugin')),
            ],
        ),
    ]