from django.contrib import admin

from mailings.models import Client, Mailing, Message


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'owner')
    search_fields = ('full_name', 'email')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'owner')
    search_fields = ('subject', 'body')


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    list_display = ('message', 'status', 'first_sent_at', 'finished_at', 'owner')
    list_filter = ('status',)
    filter_horizontal = ('clients',)
