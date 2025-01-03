#Code written by Stephen Zhao

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms
import pandas as pd
from PIL import Image
import os
import torchvision.models as models
import numpy as np
import mmcv
from mmcv.runner import load_checkpoint
from mmcv.runner.checkpoint import _load_checkpoint_with_prefix

from torch.nn import functional as F
import copy
from tqdm import tqdm

from torch.optim import Adam, SGD, AdamW
from torch.nn import DataParallel
import seaborn as sns
import matplotlib.pyplot as plt
from torch.optim.lr_scheduler import StepLR, ReduceLROnPlateau

from sklearn.model_selection import KFold
from torch.utils.data import Subset
import random
import math
from sklearn.model_selection import train_test_split

import sys
sys.path.append('../../')
from mmedit.models.backbones.sr_backbones.rrdb_net import RRDB
from mmedit.models.builder import build_component
from mmedit.models.common import PixelShufflePack, make_layer
from mmedit.models.registry import BACKBONES
from mmedit.utils import get_root_logger
from mmedit.models.components.clip_hba_no_softmax import clip
from mmedit.models.components.clip_hba_no_softmax.simple_tokenizer import SimpleTokenizer as _Tokenizer
import shutil
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Prompt pairs for the model
classnames66 = [
    ['metallic; artificial', 'nonmetallic; natural'],
    ['food-related', 'non-food-related'],
    ['animal-related', 'non-animal-related; artificial; inorganic'],
    ['textile', 'non-textile'],
    ['plant-related', 'non-plant-related'],
    ['house-related; furnishing-related',
    'non-house-related; non-furnishing-related; outdoors-related'],
    ['valuable; precious', 'non-valuable; inexpensive; cheap'],
    ['transportation; movement-related', 'non-transportation; movement-related'],
    ['body; people-related', 'non-body; people-related'],
    ['wood-related; brown', 'non-wood-related; non-brown'],
    ['electronics; technology', 'non-electronics; technology'],
    ['colorful; playful', 'monotone; dull'],
    ['outdoors', 'non-outdoors'],
    ['circular; round', 'non-circular; angular'],
    ['paper-related; flat', 'non-paper-related; bumpy'],
    ['hobby-related; game-related; playing-related',
    'non-hobby-related; non-game-related; non-playing-related'],
    ['tools-related; handheld; elongated',
    'non-tools-related; non-handheld; shortened'],
    ['fluid-related; drink-related', 'solid-related; non-fluid-related'],
    ['water-related', 'dry; non-water-related'],
    ['oriented; many; plenty', 'non-oriented; few; scarce'],
    ['powdery; earth-related; waste-related',
    'non-powdery; non-earth-related; non-waste-related'],
    ['white', 'black; dark'],
    ['coarse-scale pattern; many things', 'non-coarse-scalepattern; few; scarce'],
    ['red', 'non-red'],
    ['long; thin', 'short; thick'],
    ['weapon-related; war-related; dangerous',
    'non-weapon-related; non-war-related; peaceful'],
    ['black', 'non-black; white'],
    ['household-related', 'non-household-related'],
    ['feminine', 'non-feminine; masculine'],
    ['body-part-related', 'non-body-part-related'],
    ['tubular', 'non-tubular'],
    ['music-related; hearing-related; hobby-related; loud',
    'non-music-related; non-hearing-related; non-hobby-related; silent'],
    ['grid-related; grating-related', 'non-grid-related; non-grating-related'],
    ['repetitive; spiky', 'diverse; dull'],
    ['construction-related; craftsmanship-related; housework-related',
    'non-physical-work-related'],
    ['spherical; voluminous', 'angular; small'],
    ['string-related; stringy; curved', 'non-string-related; straight'],
    ['seating; standing; lying-related',
    'non-seating; non-standing; non-lying-related'],
    ['flying-related; sky-related', 'ground-related; non-flying-related'],
    ['bug-related; non-mammalian; disgusting',
    'non-bug-related; mammalian; pleasant'],
    ['transparent; shiny; crystalline', 'opaque; matte; frosted'],
    ['sand-colored', 'non-sand-colored'],
    ['green', 'non-green'],
    ['bathroom-related; wetness-related', 'non-bathroom-related; dry'],
    ['yellow', 'non-yellow'],
    ['heat-related; fire-related; light-related', 'cold-related; dark-related'],
    ['beams-related; mesh-related', 'non-beams-related; non-mesh-related'],
    ['foot-related; walking-related', 'non-foot-related; non-walking-related'],
    ['box-related; container', 'non-box-related; non-container'],
    ['stick-shaped; container', 'non-stick-shaped; non-container'],
    ['head-related', 'non-head-related'],
    ['upright; elongated; volumous', 'non-upright; short; small'],
    ['pointed; spiky', 'non-pointed; blunt'],
    ['child-related; toy-related; cute', 'mature; adult-like'],
    ['farm-related; historical', 'non-farm-related; contemporary'],
    ['seeing-related', 'non-seeing-related; blind'],
    ['medicine-related; health-related',
    'non-medicine-related; non-health-related'],
    ['sweet; dessert-related', 'non-sweet; non-dessert-related'],
    ['orange', 'non-orange'],
    ['thin; flat; wrapping', 'thick; bumpy; non-wrapping'],
    ['cylindrical; conical; cushioning', 'triangular; angular; hardening'],
    ['coldness-related; winter-related', 'warmness-related; non-winter-related '],
    ['measurement-related; numbers-related',
    'non-measurement-related; non-numerical'],
    ['fluffy; soft', 'non-fluffy; rough'],
    ['masculine', 'non-masculine; feminine'],
    ['fine-grained; pattern', 'non-fine-grained; plain']
]


def seed_everything(seed):
    # Set the seed for PyTorch's random number generators
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    # Set the seed for Python's random number generator
    random.seed(seed)

    # Set the seed for NumPy's random number generator
    np.random.seed(seed)

    # Ensure that the CuDNN backend is deterministic
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False



def load_clip_to_cpu(backbone_name):
    url = clip._MODELS[backbone_name]
    model_path = clip._download(url, os.path.expanduser("~/.cache/clip"))

    try:
        # loading JIT archive
        model = torch.jit.load(model_path, map_location="cpu").eval()
        state_dict = None

    except RuntimeError:
        state_dict = torch.load(model_path, map_location="cpu")

    model = clip.build_model(state_dict or model.state_dict())

    return model

class CLIPHBA(nn.Module):
    def __init__(self, classnames, backbone_name='RN50', pos_embedding=False):
        super().__init__()

        self.num_clip = len(classnames)
        self.clip_model = load_clip_to_cpu(backbone_name)
        self.clip_model.float()
        self.pos_embedding = pos_embedding

        # Disable gradients for all parameters first
        for param in self.clip_model.parameters():
            param.requires_grad = False
        
        # Tokenize all prompts at once and store them as a tensor
        self.tokenized_prompts = torch.stack([clip.tokenize(classname) for classname in classnames])


    def forward(self, image):
        if self.clip_model.training:
            self.clip_model.eval()

        # Move tokenized prompts to the same device as the input image
        tokenized_prompts = self.tokenized_prompts.to(image.device)

        # Process all tokenized prompts in a single forward pass
        pred_score = self.clip_model(image, tokenized_prompts, self.pos_embedding)

        pred_score = pred_score.float()  # Adjust the dimensions accordingly

        # print(f"pred_score: {pred_score}")

        return pred_score



class LoRALayer(nn.Module):
    def __init__(self, original_layer, r=8, lora_alpha=16, lora_dropout=0.1):
        super(LoRALayer, self).__init__()
        self.original_layer = original_layer
        self.r = r
        self.lora_alpha = lora_alpha
        self.lora_dropout = nn.Dropout(p=lora_dropout)

        self.lora_A = nn.Parameter(torch.randn(self.r, original_layer.out_features))
        self.lora_B = nn.Parameter(torch.zeros(original_layer.in_features, self.r))
        self.scaling = self.lora_alpha / self.r

        self.reset_parameters()

    def reset_parameters(self):
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.kaiming_uniform_(self.lora_B, a=math.sqrt(5))

    def forward(self, x):
        lora_B = self.lora_B.to(dtype=x.dtype)
        lora_A = self.lora_A.to(dtype=x.dtype)
        return self.original_layer(x) + (self.lora_dropout(x) @ lora_B @ lora_A) * self.scaling

    @property
    def weight(self):
        return (self.original_layer.weight.to(self.lora_B.dtype) + (self.lora_B @ self.lora_A) * self.scaling).to(self.original_layer.weight.dtype)

    @property
    def bias(self):
        return self.original_layer.bias

def apply_lora_to_ViT(model, n_vision_layers=1, n_transformer_layers=1, r=8, lora_dropout=0.1):
    """
    Applies LoRA to the 'out_proj' of the 11th and the last (23rd) ResidualAttentionBlock in the
    VisionTransformer's transformer.

    :param model: The PyTorch model to modify.
    :param r: The rank of the LoRA approximation.
    :param lora_dropout: The dropout rate for LoRA layers.
    """
    if isinstance(model, torch.nn.DataParallel):
        model_module = model.module
    else:
        model_module = model

    # Specific blocks to modify
    block_indices = -n_vision_layers

    for idx in range(block_indices, 0):
        # Access the specific ResidualAttentionBlock
        target_block = model_module.clip_model.visual.transformer.resblocks[idx]
        # Access the 'out_proj' within the MultiheadAttention of the block
        target_layer = target_block.attn.out_proj
        # Replace the original layer with a LoRALayer
        lora_layer = LoRALayer(target_layer, r=r, lora_dropout=lora_dropout)
        target_block.attn.out_proj = lora_layer

    block_indices = -n_transformer_layers
    for idx in range(block_indices, 0):
        # Access the specific ResidualAttentionBlock
        target_block = model_module.clip_model.transformer.resblocks[idx]
        # Access the 'out_proj' within the MultiheadAttention of the block
        target_layer = target_block.attn.out_proj
        # Replace the original layer with a LoRALayer
        lora_layer = LoRALayer(target_layer, r=r, lora_dropout=lora_dropout)
        target_block.attn.out_proj = lora_layer



def unfreeze_lora_layers(model, freeze_all=True):
    """
    Freeze or unfreeze the model's parameters based on the presence of LoRA layers.
    If a LoRALayer is encountered, only its specific LoRA parameters are unfrozen.
    """
    for name, param in model.named_parameters():
        # Initially set requires_grad based on the freeze_all flag
        param.requires_grad = not freeze_all

    if freeze_all:
        # If freezing all parameters, selectively unfreeze LoRA parameters
        def recursive_unfreeze_lora(module):
            for child_name, child in module.named_children():
                if isinstance(child, LoRALayer):
                    # Unfreeze only LoRA-specific parameters within LoRALayer
                    child.lora_A.requires_grad = True
                    child.lora_B.requires_grad = True
                    # Keep the original layer's parameters frozen
                    child.original_layer.weight.requires_grad = False
                    if child.original_layer.bias is not None:
                        child.original_layer.bias.requires_grad = False
                else:
                    recursive_unfreeze_lora(child)

        # Apply selective unfreezing to the entire model
        if isinstance(model, torch.nn.DataParallel):
            recursive_unfreeze_lora(model.module)
        else:
            recursive_unfreeze_lora(model)

class DoRALayer(nn.Module):
    def __init__(self, original_layer, r=8, dora_alpha=16, dora_dropout=0.1):
        super(DoRALayer, self).__init__()
        self.original_layer = original_layer
        self.r = r  # Low-rank factor
        self.dora_alpha = dora_alpha  # Scaling parameter
        self.dora_dropout = nn.Dropout(p=dora_dropout)

        # Decompose original weights into magnitude and direction
        with torch.no_grad():
            W = original_layer.weight.data.clone()  # [out_features, in_features]
            W = W.T  # Transpose to [in_features, out_features]
            S = torch.norm(W, dim=0)  # Magnitudes (norms of columns), shape [out_features]
            D = W / S  # Direction matrix with unit-norm columns, shape [in_features, out_features]

        # Store S as a trainable parameter
        self.m = nn.Parameter(S)  # [out_features]
        # Store D as a buffer (since we don't want to update it directly)
        self.register_buffer('D', D)  # [in_features, out_features]

        # LoRA adaptation of D
        self.delta_D_A = nn.Parameter(torch.zeros(self.r, original_layer.out_features))
        self.delta_D_B = nn.Parameter(torch.zeros(original_layer.in_features, self.r))

        # Scaling
        self.scaling = self.dora_alpha / self.r

        # Initialize delta_D_A and delta_D_B
        self.reset_parameters()

        # Copy the bias from the original layer
        if self.original_layer.bias is not None:
            self.bias = nn.Parameter(original_layer.bias.data.clone())
        else:
            self.bias = None

    def reset_parameters(self):
        nn.init.kaiming_uniform_(self.delta_D_A, a=math.sqrt(5))
        nn.init.kaiming_uniform_(self.delta_D_B, a=math.sqrt(5))

    @property
    def weight(self):
        # Compute adapted D
        delta_D = (self.delta_D_B @ self.delta_D_A) * self.scaling  # [in_features, out_features]

        D_new = self.D + delta_D  # [in_features, out_features]

        # Normalize columns of D_new
        D_norms = torch.norm(D_new, dim=0, keepdim=True) + 1e-8  # [1, out_features], add epsilon to avoid division by zero
        D_normalized = D_new / D_norms  # [in_features, out_features]

        # Reconstruct the adapted weight
        W = D_normalized * self.m  # [in_features, out_features], m is [out_features]

        W = W.T  # Transpose back to [out_features, in_features]

        return W

    def forward(self, x):
        # Compute adapted D
        delta_D = (self.delta_D_B @ self.delta_D_A) * self.scaling  # [in_features, out_features]
        delta_D = self.dora_dropout(delta_D)

        D_new = self.D + delta_D  # [in_features, out_features]

        # Normalize columns of D_new
        D_norms = torch.norm(D_new, dim=0, keepdim=True) + 1e-8  # [1, out_features]
        D_normalized = D_new / D_norms  # [in_features, out_features]

        # Reconstruct the adapted weight
        W = D_normalized * self.m  # [in_features, out_features]
        W = W.T  # [out_features, in_features]

        # Compute output
        return F.linear(x, W, self.bias)


    

def apply_dora_to_ViT(model, n_vision_layers=1, n_transformer_layers=1, r=8, dora_dropout=0.1, seed=123):

    if isinstance(model, torch.nn.DataParallel):
        model_module = model.module
    else:
        model_module = model

    # Specific blocks to modify in the visual transformer
    block_indices = range(-n_vision_layers, 0)  # Adjusted for proper indexing

    for idx in block_indices:
        # Access the specific ResidualAttentionBlock
        target_block = model_module.clip_model.visual.transformer.resblocks[idx]
        # Access the 'out_proj' within the MultiheadAttention of the block
        target_layer = target_block.attn.out_proj
        # Replace the original layer with a DoRALayer
        dora_layer = DoRALayer(target_layer, r=r, dora_dropout=dora_dropout)
        target_block.attn.out_proj = dora_layer

    # Specific blocks to modify in the main transformer
    block_indices = range(-n_transformer_layers, 0)

    for idx in block_indices:
        # Access the specific ResidualAttentionBlock
        target_block = model_module.clip_model.transformer.resblocks[idx]
        # Access the 'out_proj' within the MultiheadAttention of the block
        target_layer = target_block.attn.out_proj
        # Replace the original layer with a DoRALayer
        dora_layer = DoRALayer(target_layer, r=r, dora_dropout=dora_dropout)
        target_block.attn.out_proj = dora_layer



def switch_dora_layers(model, freeze_all=True, dora_state=True):
    """
    Freeze or unfreeze the model's parameters based on the presence of DoRA layers.
    If a DoRALayer is encountered, only its specific DoRA parameters are unfrozen.
    """
    for name, param in model.named_parameters():
        # Initially set requires_grad based on the freeze_all flag
        param.requires_grad = not freeze_all

    if freeze_all:
        # If freezing all parameters, selectively unfreeze DoRA parameters
        def recursive_unfreeze_dora(module):
            for child_name, child in module.named_children():
                if isinstance(child, DoRALayer):
                    # Unfreeze DoRA-specific parameters within DoRALayer
                    child.m.requires_grad = dora_state
                    child.delta_D_A.requires_grad = dora_state
                    child.delta_D_B.requires_grad = dora_state
                    # Keep the original layer's parameters frozen
                    if child.bias is not None:
                        child.bias.requires_grad = False
                else:
                    recursive_unfreeze_dora(child)

        # Apply selective unfreezing to the entire model
        if isinstance(model, torch.nn.DataParallel):
            recursive_unfreeze_dora(model.module)
        else:
            recursive_unfreeze_dora(model)



def count_trainable_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
    # return sum(p.numel() for p in model.parameters())


def unfreeze_image_layers(model):
    # Handle DataParallel wrapper
    if isinstance(model, torch.nn.DataParallel):
        model_module = model.module
    else:
        model_module = model

    # Unfreezing the last layer of the image encoder
        
    for param in model_module.clip_model.visual.layer3.parameters():
        param.requires_grad = True

    for param in model_module.clip_model.visual.layer4.parameters():
        param.requires_grad = True

    for param in model_module.clip_model.visual.attnpool.parameters():
        param.requires_grad = True


def unfreeze_image_layers_all(model):
    # Handle DataParallel wrapper
    if isinstance(model, torch.nn.DataParallel):
        model_module = model.module
    else:
        model_module = model

    # Unfreezing the last layer of the image encoder
        
    for param in model_module.clip_model.visual.parameters():
        param.requires_grad = True



def load_rdm(rdm_path):
    rdm = np.load(rdm_path)
    # Check for NaN values
    nan_check = np.isnan(rdm).any()

    if nan_check:
        rdm = np.nan_to_num(rdm, copy=False)

    # Check scale of the RDM
    min_val = np.min(rdm)
    max_val = np.max(rdm)


    if min_val != 0 or max_val != 1:
        rdm = (rdm - min_val) / (max_val - min_val)  # Scale to [0, 1]
        rdm_max = np.max(rdm)
        rdm_min = np.min(rdm)
        print(f"RDM scaled to {rdm_min}-{rdm_max}")

    # print(f"RDM loaded and preprocessed, shape: {rdm.shape}")

    return rdm


def calculate_pearson_rdm(predictions):
    # Calculate the mean for each prediction (batch of vectors)
    mean_predictions = torch.mean(predictions, dim=1, keepdim=True)
    
    # Subtract the mean from predictions (centering)
    centered_predictions = predictions - mean_predictions
    
    # Calculate the pairwise dot product of centered predictions
    dot_product = torch.mm(centered_predictions, centered_predictions.t())
    
    # Calculate the norms (magnitude) of each prediction
    norms = torch.norm(centered_predictions, dim=1, keepdim=True)
    
    # Calculate the Pearson correlation
    similarity_matrix = dot_product / (norms * norms.t())
    
    # Convert Pearson correlation to Pearson distance
    dissimilarity_matrix = 1 - similarity_matrix
    
    # Set the diagonal elements to zero
    rdm = dissimilarity_matrix.fill_diagonal_(0)
    
    return rdm


class PearsonMSELoss(nn.Module):
    def __init__(self, p_weight=1, m_weight=1, initial_p_loss=1, initial_m_loss=1):
        super(PearsonMSELoss, self).__init__()
        self.p_weight = p_weight
        self.m_weight = m_weight
        self.initial_p_loss = initial_p_loss
        self.initial_m_loss = initial_m_loss
    
    def pearson_loss(self, x_flat, y_flat):
        mean_x = torch.mean(x_flat)
        mean_y = torch.mean(y_flat)
        xm = x_flat - mean_x
        ym = y_flat - mean_y
        r_num = torch.sum(xm * ym)
        r_den = torch.sqrt(torch.sum(xm ** 2) * torch.sum(ym ** 2))
        correlation = r_num / r_den
        pearson_loss = 1 - correlation
        return pearson_loss

    def pearson_mse_loss(self, pred, target):

        # pred and target are all shaped [batch_size, batch_size]
    
        batch, _ = pred.shape
        device = pred.device
        triu_indices = torch.triu_indices(row=batch, col=batch, offset=1, device=device)
        
        pred_upper = pred[triu_indices[0], triu_indices[1]]
        target_upper = target[triu_indices[0], triu_indices[1]]

        # Compute Pearson loss across timepoints
        pearson_loss = self.pearson_loss(pred_upper, target_upper)
        # Compute MSE loss across each time point
        mse_loss = F.mse_loss(pred_upper, target_upper)

        return pearson_loss, mse_loss
    

    def forward(self, x, y):
        p_loss, mse_loss = self.pearson_mse_loss(x, y)

        total_loss = self.p_weight * p_loss/self.initial_p_loss + self.m_weight * mse_loss/self.initial_m_loss


        return total_loss, mse_loss, p_loss



class fmriDataset(Dataset):
    def __init__(self, csv_file, img_dir, rdm_dir, split='train', test_size=0.2, random_state=1):
        self.img_dir = img_dir
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)), 
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.52997664, 0.48070561, 0.41943838],
                                 std=[0.27608301, 0.26593025, 0.28238822])
        ])
        
        # Read the CSV file and group images by concept
        self.annotations = pd.read_csv(csv_file)
        self.image_concept_dict = self.annotations.groupby('concept')['stimulus'].apply(list).to_dict()
        self.unique_concepts = sorted(self.image_concept_dict.keys())

        # For each concept, split images into train and test sets
        self.split = split
        self.concept_image_split = {}  # dict of concept -> list of images (train or test)
        for concept, images in self.image_concept_dict.items():
            train_imgs, test_imgs = train_test_split(
                images, test_size=test_size, random_state=random_state)
            if split == 'train':
                self.concept_image_split[concept] = train_imgs
            elif split == 'test':
                self.concept_image_split[concept] = test_imgs
            else:
                raise ValueError("split must be 'train' or 'test'")

        # Remove concepts that have no images in the current split
        self.available_concepts = [concept for concept, imgs in self.concept_image_split.items() if len(imgs) > 0]

        # Load the full RDM matrix
        self.rdms = load_rdm(rdm_dir)

    def __len__(self):
        return len(self.available_concepts)

    def __getitem__(self, index):
        concept = self.available_concepts[index]
        image_names = self.concept_image_split[concept]
        image_name = random.choice(image_names)  # Randomly select one image per concept
        img_path = os.path.join(self.img_dir, concept, image_name)
        image = Image.open(img_path).convert("RGB")
        image = self.transform(image)
        concept_index = self.unique_concepts.index(concept)  # Consistent concept indexing

        return image_name, image, concept_index


def train_model_rdm(model, train_loader, test_loader, device, optimizer, criterion, p_weight, m_weight, epochs, rdms, early_stopping_patience=5, checkpoint_path='clip_hba_model_cv.pth', scheduler=None):
    best_test_loss = float('inf')
    epochs_no_improve = 0
    loss_data = []  # To store loss data for plotting
    if scheduler is not None:
        print("Using scheduler")

    train_rdms = rdms
    test_rdms = rdms

    # initial evaluation
    print("*********************************")
    print("Evaluating initial model")
    initial_mse_loss, initial_pearson_loss = evaluate_model_rdm(model, test_loader, device, criterion, test_rdms)
    best_pearson_loss = initial_pearson_loss
    print(f"Initial Validation Loss: MSE={initial_mse_loss:.4f}, Pearson={initial_pearson_loss:.4f}")
    print("*********************************\n")

    criterion = PearsonMSELoss(p_weight=p_weight, m_weight=m_weight, initial_p_loss=initial_pearson_loss, initial_m_loss=initial_mse_loss)

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        total_mse_loss = 0.0
        total_pearson_loss = 0.0

        total_iterations = len(train_loader)
        progress_bar = tqdm(total=total_iterations, desc=f"Epoch {epoch+1}/{epochs}")

        for batch_idx, (image_names, images, concept_indices) in enumerate(train_loader):
            images = images.to(device)
            concept_indices = concept_indices.to(device)

            optimizer.zero_grad()
            predictions = model(images)

            # Compute the predicted RDM over the batch of predictions
            pred_rdm = calculate_pearson_rdm(predictions)

            # Extract the corresponding target RDM submatrix using concept indices
            target_rdm = train_rdms[np.ix_(concept_indices.cpu().numpy(), concept_indices.cpu().numpy())]
            target_rdm = torch.tensor(target_rdm, dtype=torch.float32, device=device)

            loss, mse_loss, pearson_loss = criterion(pred_rdm, target_rdm)

            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            total_mse_loss += mse_loss.item()
            total_pearson_loss += pearson_loss.item()
            progress_bar.set_postfix({'Loss': loss.item(), 'MSE': mse_loss.item(), 'Pearson': pearson_loss.item()})
            progress_bar.update()
        progress_bar.close()

        avg_train_loss = total_loss / total_iterations

        # Evaluate after every epoch
        avg_mse_loss, avg_pearson_loss = evaluate_model_rdm(model, test_loader, device, criterion, test_rdms)
        print(f"Epoch {epoch+1}: Training Loss: {avg_train_loss:.4f}, Validation MSE Loss: {avg_mse_loss:.4f}, Validation Pearson Loss: {avg_pearson_loss:.4f}")

        loss_data.append({'epoch': epoch + 1, 'loss': avg_train_loss, 'type': 'Train'})
        loss_data.append({'epoch': epoch + 1, 'loss': avg_mse_loss + avg_pearson_loss, 'type': 'Test'})

        # Check for early stopping and saving checkpoint
        current_test_loss = avg_mse_loss + avg_pearson_loss
        if current_test_loss < best_test_loss:
            best_test_loss = current_test_loss
            epochs_no_improve = 0
            # Save the model checkpoint
            torch.save(model.state_dict(), checkpoint_path)
            print("\n\n-----------------------------------")
            print(f"Checkpoint saved for epoch {epoch+1}")
            print("-----------------------------------\n\n")
        else:
            epochs_no_improve += 1

        if epochs_no_improve == early_stopping_patience:
            print("\n\n*********************************")
            print(f"Early stopping triggered at epoch {epoch+1}")
            print("*********************************\n\n")
            break


def evaluate_model_rdm(model, data_loader, device, criterion, rdms):
    model.eval()
    total_mse_loss = 0.0
    total_pearson_loss = 0.0

    total_iterations = len(data_loader)
    progress_bar = tqdm(total=total_iterations, desc="Evaluating")

    with torch.no_grad():
        for batch_idx, (_, images, concept_indices) in enumerate(data_loader):
            images = images.to(device)
            concept_indices = concept_indices.to(device)

            predictions = model(images)

            # Compute the predicted RDM over the batch of predictions
            pred_rdm = calculate_pearson_rdm(predictions)

            # Extract the corresponding target RDM submatrix using concept indices
            target_rdm = rdms[np.ix_(concept_indices.cpu().numpy(), concept_indices.cpu().numpy())]
            target_rdm = torch.tensor(target_rdm, dtype=torch.float32, device=device)

            _, mse_loss, pearson_loss = criterion(pred_rdm, target_rdm)

            total_mse_loss += mse_loss.item()
            total_pearson_loss += pearson_loss.item()

            progress_bar.set_postfix({'MSE Loss': mse_loss.item(), 'Pearson Loss': pearson_loss.item()})
            progress_bar.update()
    progress_bar.close()

    avg_mse_loss = total_mse_loss / total_iterations
    avg_pearson_loss = total_pearson_loss / total_iterations

    return avg_mse_loss, avg_pearson_loss





if __name__ == '__main__':
    #########################################################
    img_dir = "../Data/Things_fmri/concept_stimuli"
    model_save_dir = "../models/Things_fMRI"
    backbone = 'ViT-L/14' #or options: RN50, ViT-B/32, ViT-B/16, ViT-L/14
    epochs = 500
    batch_size = 72
    train_portion = 0.8
    lr = 1e-5
    scheduler = False
    early_stopping_patience = 10
    random_seed = 1
    vision_layers = 24
    transormer_layers = 0
    p_weight = 1
    m_weight = 1
    rank = 8
    cuda = 1
    #########################################################

    # reinitialize the model_save_folder
    if os.path.exists(model_save_dir):
        shutil.rmtree(model_save_dir)
        print(f"Model save folder reinitialized: {model_save_dir}")
    os.makedirs(model_save_dir)

    classnames = classnames66
    classnames = [x[0] for x in classnames]

    rdm_files = os.listdir("../Data/Things_fmri/all_rdm/")
    model_names = [f.split("_")[0] + "_" + f.split("_")[1] for f in rdm_files if len(f.split("_")) > 1]

    print(f"training {len(model_names)} models in total. ")



    for model_name in model_names: 

        seed_everything(random_seed)

        checkpoint_path = f"{model_save_dir}/cliphba_fmri_{model_name}.pth"
        rdm_dir = f"../Data/Things_fmri/all_rdm/{model_name}_concept_rdm_4_fold.npy"
        subject = model_name.split("_")[0]
        csv_file = f"../Data/Things_fmri/{subject}_StimulusMetadata.csv"


        print(f"Training model for {model_name} with checkpoint path: {checkpoint_path}")
    

        # Create training and testing datasets
        train_dataset = fmriDataset(csv_file, img_dir, rdm_dir, split='train', test_size=0.2, random_state=random_seed)
        test_dataset = fmriDataset(csv_file, img_dir, rdm_dir, split='test', test_size=0.2, random_state=random_seed)

        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)


        rdms = train_dataset.rdms
        print(f"RDM loaded and preprocessed, shape: {rdms.shape}")
        print(f"Number of concepts: {len(train_dataset.available_concepts)}")
        print(f"Number of unique concepts: {len(train_dataset.unique_concepts)}")
        
        
        # Initialize your model
        if backbone == 'RN50':
            pos_embedding = False
            print("pos_embedding is False")
        if backbone == 'ViT-B/16' or backbone == 'ViT-B/32' or backbone == 'ViT-L/14': 
            pos_embedding = True
            print("pos_embedding is True")
        model = CLIPHBA(classnames=classnames, backbone_name=backbone, pos_embedding=pos_embedding)


        # Move the model to GPU
        if cuda == -1:
            device = torch.device("cuda")
        elif cuda == 0:
            device = torch.device("cuda:0")
        elif cuda == 1:
            device = torch.device("cuda:1")
        else:
            device = torch.device("cpu")


        apply_dora_to_ViT(model, n_vision_layers=vision_layers, n_transformer_layers=transormer_layers, r=rank, dora_dropout=0.1)
        switch_dora_layers(model, freeze_all=True, dora_state=True)

        # Use DataParallel to utilize multiple GPUs
        if cuda == -1:
            print(f"Using {torch.cuda.device_count()} GPUs")
            model = DataParallel(model)

        model.to(device)  # Move model to GPU if available

        # unfreeze_image_layers_all(model)

        # Set up optimizer to only update parameters where requires_grad is True
        optimizer = AdamW(model.parameters(), lr=lr)


        if scheduler == True:
            scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=5, min_lr=1e-6)
        else: 
            scheduler = None


        criterion = PearsonMSELoss(p_weight=p_weight, m_weight=m_weight)

        print("Updating layers:")
        for name, param in model.named_parameters():
            if param.requires_grad:
                print(name)
        print(f"Number of trainable parameters: {count_trainable_parameters(model)}\n\n")
        

        # print(model)
        train_model_rdm(model, train_loader, test_loader, device, optimizer, criterion, p_weight, m_weight, epochs, rdms, early_stopping_patience, checkpoint_path, scheduler=scheduler)