from django.contrib import admin

from core.models import AppSetting


@admin.register(AppSetting)
class AppSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "str_value", "int_value", "float_value", "bool_value")
    search_fields = ("key",)
