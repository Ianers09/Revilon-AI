from django.contrib import admin

from .models import EmailVerificationCode, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "has_profile_picture",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )

    @admin.display(boolean=True, description="Picture")
    def has_profile_picture(self, profile):
        return bool(profile.profile_picture)


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "expires_at",
        "attempt_count",
        "last_sent_at",
    )
    search_fields = (
        "user__username",
        "user__email",
    )
    readonly_fields = (
        "code_hash",
        "created_at",
        "last_sent_at",
    )
