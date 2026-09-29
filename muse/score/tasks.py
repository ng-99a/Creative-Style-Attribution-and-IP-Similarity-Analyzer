from celery import shared_task
from .models import StyleComparison, BatchStyleComparison, BatchImage
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

@shared_task
def batch_style_comparison_task(batch_id):
    try:
        if model is None:
            raise FileNotFoundError("Model was not loaded correctly")
            
        batch = BatchStyleComparison.objects.get(id=batch_id)
        batch.status = 'RUNNING'
        batch.save()

        images = list(batch.images.all())
        if len(images) < 2:
            batch.status = 'FAILED'
            batch.save()
            return

        logger.info(f"Starting batch comparison {batch_id} for {len(images)} images")

        tensor_list = []
        for img_obj in images:
            img = Image.open(img_obj.image.path).convert('RGB')
            t = transform(img).unsqueeze(0).to(device)
            tensor_list.append(t)

        all_tensors = torch.cat(tensor_list, dim=0)

        with torch.no_grad():
            _, _, vec_batch = model(all_tensors)
            vec_batch = F.normalize(vec_batch, dim=-1)

            sim_matrix_tensor = torch.matmul(vec_batch, vec_batch.T) * 100.0
            sim_matrix = sim_matrix_tensor.cpu().numpy().tolist()

        vec_list = vec_batch.cpu().numpy().tolist()
        for idx, img_obj in enumerate(images):
            img_obj.vector = vec_list[idx]
            img_obj.save()

        threshold = batch.threshold
        n = len(images)

        similar_pairs = []
        adj = {i: [] for i in range(n)}

        for i in range(n):
            for j in range(i + 1, n):
                score = round(sim_matrix[i][j], 2)
                if score >= threshold:
                    similar_pairs.append({
                        "image1": {
                            "id": images[i].id,
                            "name": images[i].original_name,
                            "url": images[i].image.url,
                            "index": i + 1
                        },
                        "image2": {
                            "id": images[j].id,
                            "name": images[j].original_name,
                            "url": images[j].image.url,
                            "index": j + 1
                        },
                        "similarity": score
                    })
                    adj[i].append(j)
                    adj[j].append(i)

        visited = set()
        groups = []
        group_char_code = 65

        for i in range(n):
            if i not in visited and len(adj[i]) > 0:
                component = []
                queue = [i]
                visited.add(i)
                while queue:
                    curr = queue.pop(0)
                    component.append(curr)
                    for nbr in adj[curr]:
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)

                if len(component) >= 2:
                    group_letter = chr(group_char_code) if group_char_code <= 90 else f"Group {len(groups)+1}"
                    if group_char_code <= 90:
                        group_char_code += 1

                    group_images = [
                        {
                            "id": images[idx].id,
                            "name": images[idx].original_name,
                            "url": images[idx].image.url,
                            "index": idx + 1
                        }
                        for idx in component
                    ]

                    intra_pairs = []
                    for c1 in range(len(component)):
                        for c2 in range(c1 + 1, len(component)):
                            idx1 = component[c1]
                            idx2 = component[c2]
                            intra_pairs.append({
                                "img1_name": images[idx1].original_name,
                                "img2_name": images[idx2].original_name,
                                "img1_index": idx1 + 1,
                                "img2_index": idx2 + 1,
                                "similarity": round(sim_matrix[idx1][idx2], 2)
                            })

                    groups.append({
                        "name": f"Group {group_letter}",
                        "images": group_images,
                        "pairs": intra_pairs
                    })

        image_summary = [
            {
                "id": img.id,
                "name": img.original_name,
                "url": img.image.url,
                "index": idx + 1
            }
            for idx, img in enumerate(images)
        ]

        similarity_matrix = [[round(val, 2) for val in row] for row in sim_matrix]
        matrix_rows = []
        for i, row in enumerate(similarity_matrix):
            row_cells = []
            for j, score in enumerate(row):
                row_cells.append({
                    "row_image": image_summary[i],
                    "col_image": image_summary[j],
                    "score": score,
                    "is_diagonal": i == j,
                    "is_match": score >= threshold and i != j,
                })
            matrix_rows.append({
                "image": image_summary[i],
                "cells": row_cells,
            })

        batch.results_data = {
            "threshold": threshold,
            "total_images": n,
            "image_list": image_summary,
            "similarity_matrix": similarity_matrix,
            "matrix_rows": matrix_rows,
            "similar_pairs": sorted(similar_pairs, key=lambda x: x["similarity"], reverse=True),
            "groups": groups,
            "has_matches": len(similar_pairs) > 0
        }

        batch.status = 'COMPLETED'
        batch.save()
        logger.info(f"Successfully finished batch comparison {batch_id}")

    except Exception as e:
        logger.error(f"Error in batch_style_comparison_task {batch_id}: {str(e)}", exc_info=True)
        if 'batch' in locals():
            batch.status = 'FAILED'
            batch.save()

