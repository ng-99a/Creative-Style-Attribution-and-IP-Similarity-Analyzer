from celery import shared_task
from .models import StyleComparison
from PIL import Image
import torch
import torch.nn.functional as F
from django.conf import settings
from pathlib import Path
import torchvision.transforms as transform
from muse.style import modeloder

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = modeloder().to(device)
model_path = Path(settings.BASE_DIR) / "muse" / "saved model" / "muse_model_epoch_49.pth"

checkpoint = torch.load(model_path, map_location=device)
saved_weights = checkpoint['model_state_dict']
clean_weights = {k[7:] if k.startswith('module.') else k: v for k, v in saved_weights.items()}
model.load_state_dict(clean_weights)
model.eval()

@shared_task
def style_comparision_task(task_id):
    task = StyleComparison.objects.get(id=task_id)
    task.status = 'RUNNING'
    task.save()

    try:
        img1 = Image.open(task.image1.path).convert('RGB')
        img2 = Image.open(task.image2.path).convert('RGB')

        t1 = transform(img1).unsqueeze(0).to(device)
        t2 = transform(img2).unsqueeze(0).to(device)

        with torch.no_grad():
            _, _, vec1 = model(t1)
            _, _, vec2 = model(t2)

            vec1 = F.normalize(vec1, dim=-1)
            vec2 = F.normalize(vec2, dim=-1)

            similarity = torch.matmul(vec1, vec2.T).item()

            task.score = similarity
            task.status = 'SUCCESS'
            task.save()

    except Exception as e:
        task.status = 'FAILED'
        task.save()
