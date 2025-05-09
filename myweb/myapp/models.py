from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Upload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Liên kết với người dùng
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    video = models.FileField(upload_to='videos/', null=True, blank=True)
    result = models.FileField(upload_to='results/', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)