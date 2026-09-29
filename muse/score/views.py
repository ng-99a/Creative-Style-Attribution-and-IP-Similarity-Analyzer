import io
import os
import hashlib
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from .models import StyleComparison, BatchStyleComparison, BatchImage, ExploreCollection, ExploreImage
from .tasks import style_comparison_task, batch_style_comparison_task

def score(request):
    return render(request, "batch_upload.html")


def compare_image(request):
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

def batch_upload(request):
    return render(request, "batch_upload.html")

def optimize_and_hash_image(uploaded_file):
    uploaded_file.seek(0)
    hasher = hashlib.md5()
    for chunk in uploaded_file.chunks():
        hasher.update(chunk)
    file_hash = hasher.hexdigest()
    uploaded_file.seek(0)

    try:
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)

        buffer = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
            img.save(buffer, format="WEBP", quality=88, method=6, optimize=True)
        else:
            img = img.convert("RGB")
            img.save(buffer, format="WEBP", quality=88, method=6, optimize=True)

        size_bytes = buffer.tell()
        buffer.seek(0)
        size_kb = max(1, size_bytes // 1024)

        base_name = os.path.splitext(uploaded_file.name)[0]
        new_filename = f"{base_name}.webp"

        content_file = ContentFile(buffer.read(), name=new_filename)
        return content_file, file_hash, size_kb
    except Exception:
        uploaded_file.seek(0)
        size_kb = max(1, uploaded_file.size // 1024)
        return uploaded_file, file_hash, size_kb

def batch_compare(request):
    if request.method == 'POST':
        files = request.FILES.getlist('images')
        try:
            threshold = float(request.POST.get('threshold', 75.0))
        except (ValueError, TypeError):
            threshold = 75.0

        if not files or len(files) < 2:
            return render(request, "batch_upload.html", {"error": "Please select at least 2 images for batch comparison!"})

        if len(files) > 30:
            return render(request, "batch_upload.html", {"error": "You can upload 30 images only."})


        batch = BatchStyleComparison.objects.create(
            threshold=threshold,
            status='PENDING'
        )

        for img in files:
            BatchImage.objects.create(
                batch=batch,
                image=img,
                original_name=img.name
            )
            # Auto-populate explore gallery with deduplicated WebP optimized images
            try:
                optimized_file, f_hash, size_kb = optimize_and_hash_image(img)
                exists = ExploreImage.objects.filter(file_hash=f_hash).exists() or \
                         ExploreImage.objects.filter(original_name=img.name).exists()
                if not exists:
                    ExploreImage.objects.create(
                        image=optimized_file,
                        original_name=img.name,
                        file_hash=f_hash,
                        file_size_kb=size_kb
                    )
            except Exception:
                pass

        batch_style_comparison_task.delay(batch.id)

        return redirect('batch_status', batch_id=batch.id)

    return render(request, "batch_upload.html")

def batch_status(request, batch_id):
    batch = get_object_or_404(BatchStyleComparison, id=batch_id)

    if batch.status == 'COMPLETED':
        return render(request, "batch_result.html", {
            "batch": batch,
            "results": batch.results_data
        })

    elif batch.status == 'FAILED':
        return render(request, "batch_upload.html", {"error": "The model failed to process your batch of images."})

    return render(request, "batch_load.html", {"batch": batch})

def explore_art(request):
    # Retrieve all unique artwork images stored in database till date
    all_raw = ExploreImage.objects.order_by('-uploaded_at')
    
    unique_images = []
    seen = set()
    for item in all_raw:
        key = item.file_hash or item.original_name
        if key not in seen:
            seen.add(key)
            unique_images.append(item)
            
    return render(request, "explore.html", {
        "images": unique_images
    })

def explore_gallery(request, collection_id):
    return redirect('explore_art')