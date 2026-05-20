from django.db import models
from django.contrib.auth.models import User

class StyleComparison(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    image1 = models.ImageField(upload_to='comparisons/')
    image2 = models.ImageField(upload_to='comparisons/')
    vector1 = models.JSONField(null=True, blank=True)
    vector2 = models.JSONField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comparison {self.id} - {self.status}"

class ImageUpload(models.Model):

    image = models.ImageField(upload_to='uploded/%y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta():
        app_label = 'score'