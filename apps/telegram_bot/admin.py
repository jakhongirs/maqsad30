# Register your models here.

from django.contrib import admin

from .models import CustomMessage


@admin.register(CustomMessage)
class CustomMessageAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "sent", "sent_at")
    list_filter = ("sent", "created_at", "sent_at")
    search_fields = ("title", "message")
    readonly_fields = ("sent", "sent_at")

    def save_model(self, request, obj, form, change):
        # Save the model without triggering signals
        obj._skip_signal = True
        super().save_model(request, obj, form, change)
        # Remove the flag after save
        delattr(obj, "_skip_signal")
