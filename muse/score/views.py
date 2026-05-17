import base64
from io import BytesIO
from django.shortcuts import render
from PIL import Image
from pillow_heif import register_heif_opener
import torch 
import torch.nn.functional as F 
import torchvision.transforms as transforms 
from muse.style import style_encoder

register_heif_opener()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
style_enc = style_encoder().to(device)

model_path = r"C:\Users\nishi\code\MUSE\muse\muse\saved model\muse_model_epoch_49.pth"
 
checkpoint = torch.load(model_path, map_location=device)
state_dict = checkpoint['style_enc_state_dict']

new_state_dict = {}
for k, v in state_dict.items():
    if k.startswith('module.'):
        new_state_dict[k[7:]] = v
    else:
        new_state_dict[k] = v

style_enc.load_state_dict(new_state_dict)
style_enc.eval()

transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485,0.456,0.406],
                         std=[0.229,0.224,0.225])
])

def image_to_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def compare_image(request):
    if request.method == 'POST':

        if 'image1' not in request.FILES or 'image2' not in request.FILES:
            return render(request, "home_page.html", {"error": "Please upload both images!"})

        try:
            img1_file = request.FILES['image1']
            img2_file = request.FILES['image2']

            img1 = Image.open(img1_file).convert('RGB')
            img2 = Image.open(img2_file).convert('RGB')

            t1 = transform(img1).unsqueeze(0).to(device)
            t2 = transform(img2).unsqueeze(0).to(device)

            with torch.no_grad():
                _, _, vec1 = style_enc(t1)
                _, _, vec2 = style_enc(t2)

                vec1 = F.normalize(vec1, dim=-1)
                vec2 = F.normalize(vec2, dim=-1)

                similarity = torch.matmul(vec1, vec2.T).item()

            return render(request, "result.html", {
                "similarity": round(similarity * 100, 2),
                "img1_data": image_to_base64(img1),
                "img2_data": image_to_base64(img2)
            })

        except Exception as e:
            return render(request, "home_page.html", {"error": f"Error: {str(e)}"})
            
    return render(request, "home_page.html")

def score(request):
    return render(request, "home_page.html")