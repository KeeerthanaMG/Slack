# Generated migration for VIP user model updates

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0005_vip_user_management'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='vipuser',
            options={'ordering': ['-added_at']},
        ),
        migrations.AlterUniqueTogether(
            name='vipuser',
            unique_together={('user_id', 'added_by')},
        ),
    ] 