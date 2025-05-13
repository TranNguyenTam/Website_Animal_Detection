from django.db import models
from django.contrib.auth.models import User
from pathlib import Path

# Create your models here.

class Upload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Liên kết với người dùng
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    video = models.FileField(upload_to='videos/', null=True, blank=True)
    result = models.FileField(upload_to='results/', null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload by {self.user} at {self.uploaded_at}"

    @property
    def file_type(self):
        if not self.result or not self.result.name:
            return 'unsupported'
        
        ext = Path(self.result.name).suffix.lower() 
        if ext in ['.jpg', '.jpeg', '.png']:
            return 'image'
        elif ext in ['.mp4', '.mov', '.avi']:
            return 'video'
        else:
            return 'unsupported'
        
    @property
    def output_filename(self):
        if not self.result:
            return ''
        return Path(self.result.name).name
    
    @property
    def download_filename(self):
        if not self.result:
            return ''
        original_filename = self.original_filename
        base_name, ext = Path(original_filename).stem, Path(original_filename).suffix
        
        return f"{base_name}_ket_qua{ext}"
