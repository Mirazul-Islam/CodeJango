# Generated by Django 5.1.4 on 2024-12-18 02:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0002_playerscore'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='category',
            field=models.CharField(choices=[('HTML', 'HTML'), ('CSS', 'CSS'), ('JavaScript', 'JavaScript'), ('Other', 'Other')], default='Other', max_length=50),
        ),
    ]
