from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fieldsets = (
        ('Profile Picture', {'fields': ('avatar',)}),
        ('Personal Info', {'fields': ('bio',)}),
        ('Storage Management', {
            'fields': ('storage_used', 'storage_limit', 'storage_limit_enforced', 'last_storage_update'),
            'description': 'Control user storage allocation and limits'
        }),
    )
    readonly_fields = ('storage_used', 'last_storage_update')

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_storage_used', 'get_storage_percentage', 'get_storage_limit', 'get_limit_enforced', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'profile__storage_limit_enforced', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    actions = ['reset_storage_usage', 'recalculate_storage_usage', 'set_1gb_limit', 'set_5gb_limit', 'set_10gb_limit', 'enforce_storage_limits', 'disable_storage_limits']
    
    def get_storage_used(self, obj):
        return obj.profile.get_readable_storage_used()
    get_storage_used.short_description = 'Storage Used'
    
    def get_storage_limit(self, obj):
        return obj.profile.get_readable_storage_limit()
    get_storage_limit.short_description = 'Storage Limit'
    
    def get_limit_enforced(self, obj):
        return obj.profile.storage_limit_enforced
    get_limit_enforced.boolean = True
    get_limit_enforced.short_description = 'Limit Enforced'
    
    def get_storage_percentage(self, obj):
        percentage = obj.profile.get_storage_usage_percentage()
        color = 'green'
        if percentage > 70:
            color = 'orange'
        if percentage > 90:
            color = 'red'
        return format_html('<div style="width:100px; height:10px; background-color:#f2f2f2; border-radius:5px;">'
                          '<div style="width:{}%; height:10px; background-color:{}; border-radius:5px;"></div></div>'
                          '<span style="margin-left:5px;">{}</span>', percentage, color, f"{percentage:.1f}%")
    get_storage_percentage.short_description = 'Usage'
    
    def reset_storage_usage(self, request, queryset):
        for user in queryset:
            profile = user.profile
            profile.storage_used = 0
            profile.save()
        self.message_user(request, f"Storage usage reset for {queryset.count()} users.")
    reset_storage_usage.short_description = "Reset storage usage to zero"
    
    def recalculate_storage_usage(self, request, queryset):
        updated = 0
        for user in queryset:
            user.profile.update_storage_usage()
            updated += 1
        self.message_user(request, f"Storage usage recalculated for {updated} users.")
    recalculate_storage_usage.short_description = "Recalculate actual storage usage"
    
    def set_1gb_limit(self, request, queryset):
        # 1GB in bytes = 1073741824
        count = queryset.update(profile__storage_limit=1073741824)
        self.message_user(request, f"Set 1GB storage limit for {count} users.")
    set_1gb_limit.short_description = "Set storage limit: 1GB"
    
    def set_5gb_limit(self, request, queryset):
        # 5GB in bytes = 5368709120
        for user in queryset:
            user.profile.storage_limit = 5368709120
            user.profile.save()
        self.message_user(request, f"Set 5GB storage limit for {queryset.count()} users.")
    set_5gb_limit.short_description = "Set storage limit: 5GB"
    
    def set_10gb_limit(self, request, queryset):
        # 10GB in bytes = 10737418240
        for user in queryset:
            user.profile.storage_limit = 10737418240
            user.profile.save()
        self.message_user(request, f"Set 10GB storage limit for {queryset.count()} users.")
    set_10gb_limit.short_description = "Set storage limit: 10GB"
    
    def enforce_storage_limits(self, request, queryset):
        for user in queryset:
            user.profile.storage_limit_enforced = True
            user.profile.save()
        self.message_user(request, f"Enabled storage limit enforcement for {queryset.count()} users.")
    enforce_storage_limits.short_description = "Enable storage limit enforcement"
    
    def disable_storage_limits(self, request, queryset):
        for user in queryset:
            user.profile.storage_limit_enforced = False
            user.profile.save()
        self.message_user(request, f"Disabled storage limit enforcement for {queryset.count()} users.")
    disable_storage_limits.short_description = "Disable storage limit enforcement"
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
