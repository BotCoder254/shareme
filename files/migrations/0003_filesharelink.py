# Generated by Django 5.0.1 on 2025-05-14 12:08

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0002_folder_fileitem_folder_sharedfolder'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FileShareLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('password', models.CharField(blank=True, max_length=128, null=True)),
                ('access_count', models.IntegerField(default=0)),
                ('max_access_count', models.IntegerField(blank=True, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_share_links', to=settings.AUTH_USER_MODEL)),
                ('file', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='share_links', to='files.fileitem')),
                ('folder', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='share_links', to='files.folder')),
            ],
        ),
    ]
