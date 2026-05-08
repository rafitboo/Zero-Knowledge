from django.contrib import admin
from .models import Post, DirectMessage, Conversation


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
	list_display = ('id', 'author', 'created_at')
	search_fields = ('author__username', 'encrypted_content', 'ecc_public_key', 'encrypted_ecc_private_key')

	fieldsets = (
		('Post Metadata', {
			'fields': ('author',),
		}),
		('Encrypted Post Payload', {
			'fields': ('encrypted_content',),
		}),
		('Post Key Material', {
			'fields': ('ecc_public_key', 'encrypted_ecc_private_key'),
		}),
	)


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
	list_display = ('id', 'sender', 'receiver', 'timestamp')
	search_fields = (
		'sender__username',
		'receiver__username',
		'encrypted_content',
		'rsa_public_key',
		'encrypted_rsa_private_key',
		'mac_tag',
	)
	fieldsets = (
		('Participants', {
			'fields': ('sender', 'receiver'),
		}),
		('Encrypted Message Payload', {
			'fields': ('encrypted_content',),
		}),
		('Per-Message Key Material', {
			'fields': ('rsa_public_key', 'encrypted_rsa_private_key'),
		}),
		('Integrity', {
			'fields': ('mac_tag',),
		}),
	)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
	list_display = ('id', 'user_a', 'user_b')
	search_fields = ('user_a__username', 'user_b__username', 'encrypted_shared_secret')

	fieldsets = (
		('Conversation Members', {
			'fields': ('user_a', 'user_b'),
		}),
		('Encrypted Shared Secret', {
			'fields': ('encrypted_shared_secret',),
		}),
	)