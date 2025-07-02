# Generated migration for VIP user management system

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0004_channelsummary_summary_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='VIPUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=50, unique=True)),
                ('username', models.CharField(max_length=100)),
                ('display_name', models.CharField(max_length=100)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('added_by', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['-added_at'],
            },
        ),
        migrations.CreateModel(
            name='VIPSummaryHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summary_type', models.CharField(choices=[('dm', 'Direct Message'), ('channel', 'Channel Activity')], max_length=20)),
                ('channel_id', models.CharField(blank=True, max_length=50)),
                ('channel_name', models.CharField(blank=True, max_length=200)),
                ('last_summarized_at', models.DateTimeField()),
                ('summary_content', models.TextField()),
                ('requested_by', models.CharField(max_length=50)),
                ('messages_count', models.IntegerField(default=0)),
                ('timeframe_hours', models.IntegerField(default=24)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('vip_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.vipuser')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ] 