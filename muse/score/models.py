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

class BatchStyleComparison(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    threshold = models.FloatField(default=75.0)
    status = models.CharField(max_length=20, default='PENDING')
    results_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BatchComparison {self.id} - {self.status}"

class BatchImage(models.Model):
    batch = models.ForeignKey(BatchStyleComparison, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='batch_comparisons/')
    original_name = models.CharField(max_length=255)
    vector = models.JSONField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BatchImage {self.id} ({self.original_name})"

class ExploreCollection(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

class ExploreImage(models.Model):
    collection = models.ForeignKey(ExploreCollection, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    image = models.ImageField(upload_to='explore_artworks/')
    original_name = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, null=True, blank=True)
    file_size_kb = models.IntegerField(null=True, blank=True, default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ExploreImage {self.id} ({self.original_name})"


