# Generated by Django 5.0.6 on 2024-06-09 05:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silent_mammoth_whistle', '0003_remove_whistle_viewport_height_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='whistle',
            old_name='viewport_size',
            new_name='viewport_dimensions',
        ),
    ]
