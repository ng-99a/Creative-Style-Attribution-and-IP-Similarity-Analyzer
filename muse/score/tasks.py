from celery import shared_task
from .models import StyleComparison
from PIL import Image
import torch
import torch.nn.functional as F
from django.conf import settings
from pathlib import Path
import torchvision.transforms as transforms
from muse.style import style_encoder
import logging

logger = logging.getLogger(__name__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485,0.456,0.406],
                         std=[0.229,0.224,0.225])
])

print("Loading MUSE model into memory")
logger.info("Loading MUSE model into memory...")
model_path = Path(settings.BASE_DIR) / "muse" / "saved model" / "muse_model_epoch_49.pth"

if not model_path.exists():
    print(f"--- CRITICAL: Model file not found at {model_path} ---")
    logger.error(f"CRITICAL: Model file not found at {model_path}")
    model = None 
else:
    model = style_encoder().to(device)
    checkpoint = torch.load(model_path, map_location=device)
    saved_weights = checkpoint['style_enc_state_dict']
    clean_weights = {k[7:] if k.startswith('module.') else k: v for k, v in saved_weights.items()}
    model.load_state_dict(clean_weights)
    model.eval()
    print("MUSE model loaded successfully")
    logger.info("MUSE model loaded successfully")

@shared_task
def style_comparison_task(task_id):
    try:
        if model is None:
            raise FileNotFoundError("Model was not loaded correctly")
            
        task = StyleComparison.objects.get(id=task_id)
        task.status = 'RUNNING'
        task.save()

        logger.info(f"Starting comparison for task {task_id}")
        
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

            task.score = similarity * 100
            task.status = 'COMPLETED'
            task.save()

    except Exception as e:
        task.status = 'FAILED'
        task.save()
