from django.db import models
from django.conf import settings
from accounts.models import User

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    encrypted_content = models.TextField()  
    ecc_public_key = models.TextField(default="[]")  
    encrypted_ecc_private_key = models.TextField(default="[]") 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post by {self.author.username}"


class DirectMessage(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    
    encrypted_content = models.TextField()
    
    # Public key + server-wrapped private key
    rsa_public_key = models.TextField(default="[]")
    encrypted_rsa_private_key = models.TextField(default="{}") 
    
    mac_tag = models.CharField(max_length=256) 
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Secure Transmission: {self.sender.username} -> {self.receiver.username}"


class Conversation(models.Model):
    user_a = models.ForeignKey(User, related_name='convo_as_a', on_delete=models.CASCADE)
    user_b = models.ForeignKey(User, related_name='convo_as_b', on_delete=models.CASCADE)
    # Encrypted with server RSA public key
    encrypted_shared_secret = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (('user_a', 'user_b'),)

    def __str__(self):
        return f"Conversation: {self.user_a.username} <-> {self.user_b.username}"