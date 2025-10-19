from django.contrib import admin
from .models import Notification, Interview


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for in-app notifications.

    - Searchable by recipient username, title, message
    - List shows recipient, title, created_at, is_read
    - Supports optional broadcast via target_group (choose a group and leave recipient empty)
    """

    list_display = (
        'id', 'recipient', 'title', 'created_at', 'is_read',
    )
    list_filter = ('is_read', 'created_at', 'target_group')
    search_fields = (
        'title', 'message', 'user__username',
    )
    autocomplete_fields = ('user', 'actor', 'job', 'application')
    readonly_fields = ('created_at',)
    ordering = ('-created_at', '-id')

    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'message', 'is_read')
        }),
        ('Broadcast (optional)', {
            'fields': ('target_group',),
            'description': 'To broadcast, select a target group and leave user empty.'
        }),
        ('Legacy/Context (optional)', {
            'classes': ('collapse',),
            'fields': ('actor', 'verb', 'url', 'job', 'application')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at',)
        }),
    )

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"Marked {updated} notification(s) as read.")
    mark_as_read.short_description = "Mark selected as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"Marked {updated} notification(s) as unread.")
    mark_as_unread.short_description = "Mark selected as unread"


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'job', 'employer', 'candidate', 'scheduled_at', 'status',
    )
    list_filter = ('status', 'scheduled_at', 'employer')
    search_fields = ('job__title', 'employer__username', 'candidate__username')
    autocomplete_fields = ('job', 'employer', 'candidate')
    ordering = ('-scheduled_at', '-id')
