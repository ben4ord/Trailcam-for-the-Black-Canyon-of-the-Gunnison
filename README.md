# Computer Vision Trail Camera App

This project provides a Python-based GUI application for managing, labeling, and running predictions on trail camera images. It supports YOLOv8 model training and integrates with a remote server for large-scale training workflows.

The primary objective of this application is to extract animal population statistics from trail camera imagery.

---

## Features

### Run YOLO Predictions Locally
- Automatically loads the most recent `best.pt` model  
- Runs predictions on images from any user-selected folder  

### Interactive Image Labeling
- Confirm or modify predicted labels  
- Scroll through images  
- Delete irrelevant or low-quality images  

### Automatic Dataset Management
- Newly labeled images are copied into a `training_images` folder  
- These images can later be used for retraining the YOLO model  

### Server-Based Training (WCU CS Faculty)
- Authorized users at Western Colorado University can utilize the university server for model training  
- The server contains **8 RTX 2080 GPUs**, significantly improving training time  

### Easy Local Installation
- Uses PyInstaller to create a standalone Windows or macOS executable  

---

## Repository Structure

| File / Folder | Description |
|---------------|-------------|
| `BCG-Vision/` | Contains the source code for the application |
| `Documentation.pdf` | Full documentation describing features, usage instructions, and known issues |
| `pipInstalls.txt` | Required pip packages for building the executable |
| `README.md` | Project documentation |

---

## Installation

### 1. Create a Virtual Environment

Create and activate a new virtual environment, then install all required pip packages listed in `pipInstalls.txt`.
- pip install -r pipInstalls.txt
You may need this extra install for Torch to work properly with a GPU 
- pip install -r pipInstalls.txt --extra-index-url https://download.pytorch.org/whl/cu121

### 2. Navigate to the Project Directory

cd BCG-Vision

### 3. Run PyInstaller

### Windows 
py -m PyInstaller --onedir --splash splash_image.jpg --collect-all ultralytics --hidden-import torch --hidden-import torchvision --add-data "classes.txt;." --add-data "data.yaml;." --add-data "Models;Models" --name "BCG-Vision" --icon=bcg_icon.ico main.py
### Mac 
python3 -m PyInstaller \
--onedir \
--windowed \
--clean \
--collect-all ultralytics \
--hidden-import torch \
--hidden-import torchvision \
--add-data="../classes.txt:." \
--add-data="../data.yaml:." \
--add-data="Models:Models" \
--name BCG-Vision --icon="bcg_icon.ico" \
main.py

### 4. Post-Build File Placement

After building, navigate to the dist directory.

Inside the _internal folder, move the following items into the main application directory:

- Models/ (entire folder)
- classes.txt
- data.yaml
- verified_image_cache.csv (optional — automatically generated at first launch)
   

           ┌─────────────────┐
           │  GUI on Local   │
           │  Machine        │
           └────────┬────────┘
                    │ Load images
                    ▼
           ┌─────────────────┐
           │  Image Folder   │
           │  (User Selected)│
           └────────┬────────┘
                    │ Run YOLO Prediction
                    ▼
           ┌─────────────────┐
           │  Predicted      │
           │  Labels         │
           └────────┬────────┘
                    │ Confirm / Modify
                    ▼
           ┌─────────────────┐
           │  training_images│
           │  (New Labels)   │
           └────────┬────────┘
                    │ Pull for Training
                    ▼
           ┌─────────────────┐
           │  YOLO Training  │
           │  Server         │
           |(Local or Lambda)|
           └────────┬────────┘
                    │ New best.pt Model
                    ▼
           ┌─────────────────┐
           │  GUI on Local   │
           │  Machine or     |
           | Hand off        |
           └─────────────────┘

