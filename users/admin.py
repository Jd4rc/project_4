from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Стандартный UserAdmin завязан на username — у нас его нет, вход по email."""

    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'email_confirmed', 'is_active', 'is_staff')
    list_filter = ('email_confirmed', 'is_active', 'is_staff', 'is_superuser', 'groups')
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name')}),
        ('Права', {'fields': ('email_confirmed', 'is_active', 'is_staff', 'is_superuser',
                              'groups', 'user_permissions')}),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2')}),
    )
