# Computer Vision Trail Camera App

This project provides a Python GUI application for managing, labeling, and running predictions on trail camera images, with support for YOLOv8 model training and server-based workflows. The app is designed for easy local installation and interaction with a remote server for model updates.

---

## Features

- **Run YOLO predictions locally**
  - Load the latest `best.pt` model automatically
  - Run predictions on images from any folder on the user’s machine
- **Interactive image labeling**
  - Confirm or modify predicted labels
  - Scroll through images
  - Delete irrelevant or low-quality images
- **Automatic dataset management**
  - Newly labeled images are copied to a folder called `training_images`
  - These images can later be pulled for retraining the YOLO model
- **Server integration**
  - Scripts and instructions for connecting to the Lambda server for training
  - Automatically fetch the latest trained model from the server
- **Easy local installation**
  - Use PyInstaller to create a standalone executable for Windows

---

## Repository Structure

| File / Folder | Description |
|---------------|-------------|
| `SSH Lambda Server stuff.md` | Instructions for connecting to the remote server and running commands |
| `Yolo Training Stuff.md` | Step-by-step guide for training YOLOv8 models on the server |
| `training_images/` | Folder for newly labeled images ready for retraining |
| `README.md` | This documentation |

---

## Installation
ADD STEPS HERE WHEN WE GET THERE



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
           │  Server (Lambda)│
           └────────┬────────┘
                    │ New best.pt Model
                    ▼
           ┌─────────────────┐
           │  GUI on Local   │
           │  Machine        │
           └─────────────────┘

