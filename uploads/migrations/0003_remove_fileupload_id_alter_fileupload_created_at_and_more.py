# Generated by Django 4.2.13 on 2024-06-23 19:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uploads', '0002_fileupload_progress'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fileupload',
            name='id',
        ),
        migrations.AlterField(
            model_name='fileupload',
            name='created_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='fileupload',
            name='guid',
            field=models.CharField(max_length=255, primary_key=True, serialize=False),
        ),
    ]