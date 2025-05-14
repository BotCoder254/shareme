from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    
    def get_fields(self, request, obj=None):
        fields = ['avatar', 'bio', 'storage_used', 'storage_limit']
        return fields

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_storage_used')
    
    def get_storage_used(self, obj):
        return obj.profile.get_readable_storage_used()
    get_storage_used.short_description = 'Storage Used'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
