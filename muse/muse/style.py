import torch
import torch.nn.functional as F

def extract_Style_mean(layer):
    return torch.mean(layer , dim =(2,3))

def extract_Style_std(layer):
    return torch.std(layer, dim = (2,3))

import torchvision.models as models

class style_encoder(torch.nn.Module):
    def __init__(self):
        super().__init__()
        vgg = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)
        features = list(vgg.features.children())

        self.slice1 = torch.nn.Sequential(*features[:4])
        self.slice2 = torch.nn.Sequential(*features[4:9])
        self.slice3 = torch.nn.Sequential(*features[9:16])

        for params in self.parameters():
            params.requires_grad = False

        self.mlp = torch.nn.Sequential(
            torch.nn.Linear(896,500),
            torch.nn.ReLU(),
            torch.nn.Linear(500,128),
        )

    def forward(self,x):
        s1 = self.slice1(x)
        s2 = self.slice2(s1)
        s3 = self.slice3(s2)

        mu = torch.cat([extract_Style_mean(s1),
                       extract_Style_mean(s2),
                       extract_Style_mean(s3)],dim = 1)
        std = torch.cat([extract_Style_std(s1),
                       extract_Style_std(s2),
                       extract_Style_std(s3)],dim = 1)
        style = self.mlp(torch.cat([mu,std],dim =1 ))
        style = F.normalize(style)
        return mu,std,style