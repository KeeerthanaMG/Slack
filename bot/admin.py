from django.contrib import admin
from .models import (
    SlackWorkspace, SlackChannel, ChannelSummary, 
    ConversationContext, BotCommand, ChatbotInteraction,
    UserReadStatus, VIPUser, VIPSummaryHistory
)


@admin.register(SlackWorkspace)
class SlackWorkspaceAdmin(admin.ModelAdmin):
    list_display = ('workspace_name', 'workspace_id', 'created_at')
    search_fields = ('workspace_name', 'workspace_id')
    readonly_fields = ('created_at',)


@admin.register(SlackChannel)
class SlackChannelAdmin(admin.ModelAdmin):
    list_display = ('channel_name', 'channel_id', 'workspace', 'is_private', 'created_at')
    list_filter = ('is_private', 'workspace')
    search_fields = ('channel_name', 'channel_id')
    readonly_fields = ('created_at',)


@admin.register(ChannelSummary)
class ChannelSummaryAdmin(admin.ModelAdmin):
    list_display = ('channel', 'summary_type', 'messages_count', 'timeframe_hours', 'requested_by_user', 'created_at')
    list_filter = ('summary_type', 'timeframe_hours', 'created_at')
    search_fields = ('channel__channel_name', 'requested_by_user')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel')


@admin.register(ConversationContext)
class ConversationContextAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'channel_id', 'context_type', 'last_interaction_type', 'created_at', 'updated_at')
    list_filter = ('context_type', 'last_interaction_type', 'created_at')
    search_fields = ('user_id', 'channel_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BotCommand)
class BotCommandAdmin(admin.ModelAdmin):
    list_display = ('command', 'user_id', 'channel_id', 'status', 'execution_time', 'created_at')
    list_filter = ('command', 'status', 'created_at')
    search_fields = ('command', 'user_id', 'channel_id')
    readonly_fields = ('created_at',)


@admin.register(ChatbotInteraction)
class ChatbotInteractionAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'message_type', 'intent_classified', 'confidence_score', 'processing_time', 'created_at')
    list_filter = ('message_type', 'intent_classified', 'created_at')
    search_fields = ('user_id', 'user_message', 'intent_classified')
    readonly_fields = ('created_at',)


@admin.register(UserReadStatus)
class UserReadStatusAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'channel_id', 'last_read_ts', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user_id', 'channel_id')
    readonly_fields = ('updated_at',)


@admin.register(VIPUser)
class VIPUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'display_name', 'user_id', 'added_by', 'is_active', 'added_at')
    list_filter = ('is_active', 'added_at')
    search_fields = ('username', 'display_name', 'user_id')
    readonly_fields = ('added_at',)
    
    fieldsets = (
        ('VIP User Information', {
            'fields': ('user_id', 'username', 'display_name')
        }),
        ('Status & Management', {
            'fields': ('is_active', 'added_by', 'added_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-added_at')


@admin.register(VIPSummaryHistory)
class VIPSummaryHistoryAdmin(admin.ModelAdmin):
    list_display = ('vip_user', 'summary_type', 'channel_name', 'messages_count', 'requested_by', 'created_at')
    list_filter = ('summary_type', 'created_at', 'timeframe_hours')
    search_fields = ('vip_user__username', 'vip_user__display_name', 'channel_name', 'requested_by')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Summary Information', {
            'fields': ('vip_user', 'summary_type', 'channel_id', 'channel_name')
        }),
        ('Summary Details', {
            'fields': ('messages_count', 'timeframe_hours', 'last_summarized_at', 'requested_by')
        }),
        ('Content', {
            'fields': ('summary_content',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vip_user').order_by('-created_at')
