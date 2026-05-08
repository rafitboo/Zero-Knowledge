from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'role', 'is_active', 'is_email_verified', 'password_salt')
    search_fields = ('username', 'email', 'role', 'password_salt', 'encrypted_email', 'encrypted_contact_info')
    readonly_fields = ('password_hash_display',)

    def password_hash_display(self, obj):
        return obj.password

    password_hash_display.short_description = 'password (hashed)'

    fieldsets = (
        (None, {
            'fields': ('username', 'password_hash_display', 'is_active', 'role'),
        }),

        ('Cryptographic Info', {
            'fields': (
                'password_salt',
                'encrypted_contact_info',
                'encrypted_email',
                'encrypted_rsa_private_key',
                'rsa_public_key',
            ),
        }),
    )
admin.site.register(User, CustomUserAdmin)