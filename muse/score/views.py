from django.shortcuts import render, redirect, get_object_or_404
from .models import StyleComparison
from .tasks import style_comparison_task
import base64
from io import BytesIO
from PIL import Image

def score(request):
    """The main upload page"""
    return render(request, "home_page.html")

def compare_image(request):
    """View that starts the comparison process"""
    if request.method == 'POST':
        file1 = request.FILES.get('image1')
        file2 = request.FILES.get('image2')

        if not file1 or not file2:
            return render(request, "home_page.html", {"error": "Please select both images!"})

        obj = StyleComparison.objects.create(
            image1=file1,
            image2=file2,
            status='PENDING'
        )

        style_comparison_task.delay(obj.id)

        return redirect('check_status', task_id=obj.id)

    return render(request, "home_page.html")

def check_status(request, task_id):

    task = get_object_or_404(StyleComparison, id=task_id)

    if task.status == 'COMPLETED':
        return render(request, "result.html", {
            "similarity": round(task.score, 2),
            "task": task
        })

    elif task.status == 'FAILED':
        return render(request, "home_page.html", {"error": "The model failed to process your images."})

    return render(request, "load.html", {"task": task})