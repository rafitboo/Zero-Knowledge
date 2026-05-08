from rest_framework import serializers
from .models import Post, DirectMessage

class PostSerializer(serializers.ModelSerializer):
    # This pulls the username from the author ID so it's readable
    author_username = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Post
        fields = ['id', 'author_username', 'encrypted_content', 'created_at']

class DirectMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = DirectMessage
        fields = ['id', 'sender_username', 'receiver_username', 'encrypted_content', 'mac_tag', 'timestamp']