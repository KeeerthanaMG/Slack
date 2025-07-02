# Generated migration to remove old unique constraint on user_id

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0006_update_vip_user_constraints'),
    ]

    operations = [
        # Remove the old unique constraint on user_id field
        migrations.AlterField(
            model_name='vipuser',
            name='user_id',
            field=models.CharField(max_length=50),  # Remove unique=True
        ),
    ] 