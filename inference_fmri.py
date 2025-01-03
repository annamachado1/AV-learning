# Code written by Stephen Zhao, Nov 2024

from train_static_no_softmax import  *
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from PIL import Image
import numpy as np


from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
import torch
from torch.nn import DataParallel
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.functional")
import shutil
from sklearn.metrics.pairwise import cosine_similarity
import h5py

class ImageDataset(Dataset):
    def __init__(self, img_path):
        """
        img_path can be either a directory containing images or a path to a single image.
        """
        if os.path.isdir(img_path):
            self.img_dir = img_path
            self.image_names = [img for img in sorted(os.listdir(img_path))
                                if img.lower().endswith(('.png', '.jpg', '.jpeg'))]
        elif os.path.isfile(img_path) and img_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.img_dir, single_image_name = os.path.split(img_path)
            self.image_names = [single_image_name]  # Single image in a list
        else:
            raise ValueError(f"Provided path '{img_path}' is neither a directory nor a file, or file type is not supported.")

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.52997664, 0.48070561, 0.41943838],
                                 std=[0.27608301, 0.26593025, 0.28238822])
        ])

    def __len__(self):
        return len(self.image_names)

    def __getitem__(self, index):
        image_name = self.image_names[index]
        img_path = os.path.join(self.img_dir, image_name)
        image = Image.open(img_path).convert('RGB')  # Ensure image is RGB
        image = self.transform(image)
        
        return image_name, image
    
def run_image(model, data_loader, embedding_save_folder, rdm_save_folder, device=torch.device("cuda:0")):
    model.eval()
    model.to(device)
    image_names = []
    predictions = []
    
    progress_bar = tqdm(enumerate(data_loader), total=len(data_loader), desc=f"Processing images")
    
    with torch.no_grad():
        for batch_idx, (batch_image_names, batch_images) in progress_bar:
            batch_images = batch_images.to(device)
            batch_outputs = model(batch_images)
            
            predictions.extend(batch_outputs.cpu().numpy())
            image_names.extend(batch_image_names)

        # min max to 0-1
        predictions = np.array(predictions)
        predictions = (predictions - predictions.min()) / (predictions.max() - predictions.min())

        hba_embedding = pd.DataFrame(predictions)
        hba_embedding['image'] = image_names
        hba_embedding = hba_embedding[['image'] + [col for col in hba_embedding if col != 'image']]
        emb_save_path = f"{embedding_save_folder}/static_embedding.csv"
        hba_embedding.to_csv(emb_save_path, index=False)
        print(f"Embedding saved to {emb_save_path}")

        #rdm generation
        rdm = 1 - np.corrcoef(np.array(predictions))
        np.fill_diagonal(rdm, 0)
        rdm_save_path = f"{rdm_save_folder}/static_rdm.hdf5"
        with h5py.File(rdm_save_path, 'w') as f:
            # Create a dataset and write the rdm array
            f.create_dataset('rdm', data=rdm)
        print(f"RDM saved to {rdm_save_path}")
        print(f"-----------------------------------------------\n")


if __name__ == '__main__':

############################################################################################################
    img_dir = './Data/Things1854'
    save_parent_folder = f'../output/things_fmri/Things1854'
    model_folder = './models/Things_fMRI/'
    n_dim = 66 # options: 49, 66
    batch_size = 927
    rank = 8 # rank follows how the model was trained. 
    vision_layers = 24
    transormer_layers = 0
    cuda = 'cuda:1'
############################################################################################################


    # reinitialize save_parent_folder
    if os.path.exists(save_parent_folder):
        shutil.rmtree(save_parent_folder)
        print(f"\n{save_parent_folder} reinitialized\n")
    os.makedirs(save_parent_folder)

    
    sub_id = ['01', '02', '03']
    region = ['lEBA', 'lFFA', 'lLOC','LOC', 'lOFA', 'lPPA', 'lRSC', 'lTOS', 'rEBA', 'rFFA', 'rLOC', 'rOFA', 'rPPA', 'rRSC', 'rTOS']
    for sub in sub_id:
        for reg in region:

            print("\n\n<><><><><><><><><><><><><><><><><><><><><><><><>")
            print(f"Inferencing for sub-{sub}: region {reg}")
            print("<><><><><><><><><><><><><><><><><><><><><><><><>\n\n")
            
            load_hba = True
            backbone = 'ViT-L/14'
            model_path = f'{model_folder}/cliphba_fmri_sub-{sub}_{reg}.pth'

            if not os.path.exists(model_path):
                print(f"Model not found at {model_path}")
                continue

            save_folder = f'{save_parent_folder}/sub-{sub}/{reg}/'

            # Create the directory if it doesn't exist
            embedding_save_folder = f"{save_folder}"
            # print(f"\nEmbedding will be saved to folder: {embedding_save_folder}\n")
            if os.path.exists(embedding_save_folder):
                shutil.rmtree(embedding_save_folder)
            os.makedirs(embedding_save_folder)

            rdm_save_folder = f"{save_folder}"
            # print(f"\nRDM will be saved to folder: {rdm_save_folder}\n")
            if os.path.exists(rdm_save_folder):
                shutil.rmtree(rdm_save_folder)
            os.makedirs(rdm_save_folder)

            if n_dim == 49:
                classnames = classnames49
            elif n_dim == 66:
                classnames = classnames66
            else: 
                raise ValueError("n_dim must be either 49 or 66")
            
            classnames = [x[0] for x in classnames]
            
            if backbone == 'RN50':
                pos_embedding = False
                # print("pos_embedding is False")
            if backbone == 'ViT-B/16' or backbone == 'ViT-B/32' or backbone == 'ViT-L/14': 
                pos_embedding = True
                # print("pos_embedding is True")

            model = CLIPHBA(classnames=classnames, backbone_name=backbone, pos_embedding=pos_embedding)


            if load_hba:
                apply_dora_to_ViT(model, n_vision_layers=vision_layers, n_transformer_layers=transormer_layers, r=rank, dora_dropout=0.1)
                model_state_dict = torch.load(model_path)
                adjusted_state_dict = {key.replace("module.", ""): value for key, value in model_state_dict.items()}
                model.load_state_dict(adjusted_state_dict)
                # print(f"image weight: {model_state_dict['clip_model.contribution_weight']}, text weight: {2 - model_state_dict['clip_model.contribution_weight']}")
                # print(f"logit scale: {model_state_dict['clip_model.logit_scale'].exp()}")
            else:
                print(f"Using Original CLIP {backbone}")

            device = torch.device(cuda)
            
            # Load the dataset
            dataset = ImageDataset(img_dir)
            data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
            
            # Run the model and save output embeddings
            # print(model)
            hba_output = run_image(model, data_loader, embedding_save_folder, rdm_save_folder, device=device)
    print("- - - - - - Inference complete - - - - - -")
