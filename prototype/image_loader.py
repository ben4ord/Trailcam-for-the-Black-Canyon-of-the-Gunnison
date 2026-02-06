from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap #Pixmap is used to display images
from PySide6.QtWidgets import QFileDialog #File chooser dialog
from pathlib import Path
import cv2
from PIL import Image
from yolo import detect_objects

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif"}

class ImageLoader(QObject):
    image_loaded = Signal(QPixmap) #can emit signal named image_loaded with QPixmap type

    # be able to track images to scroll through multiple
    def __init__(self):
        super().__init__()
        self.image_files = []
        self.index = 0

    def load_directory(self, directory:Path): 
        #go through directory
        for item in directory.iterdir():
            if item.suffix.lower() in IMAGE_EXTENSIONS:
                self.image_files.append(item)

        self.image_files.sort()
        #display first image
        self.index = 0
        self.emit_current()
    
    def next_image(self):
        if not self.image_files:
            return
        self.index = (self.index + 1) % len(self.image_files)
        self.emit_current()

    def prev_image(self):
        if not self.image_files:
            return
        self.index = (self.index - 1) % len(self.image_files)
        self.emit_current()
    
    def emit_current(self):
        #load and emit pixmap with YOLO detection

        #if not in image files
        if not self.image_files:
            return

        #get current path
        current_path = self.image_files[self.index]
        
        # Run YOLO detection using yolo module
        detected_img = detect_objects(str(current_path), conf=0.4)
        
        # Convert BGR to RGB (OpenCV uses BGR, PIL/Qt expect RGB)
        detected_img_rgb = cv2.cvtColor(detected_img, cv2.COLOR_BGR2RGB)
        
        # Convert numpy array to PIL Image, then to QPixmap
        pil_image = Image.fromarray(detected_img_rgb)
        pixmap = QPixmap.fromImage(pil_image.toqimage())

        if not pixmap.isNull():
            self.image_loaded.emit(pixmap)

    # def load_image(self, parent=None):
    #     #getOpenFileName works for one file - getExistingDirectory() will be helpful in future for getting a folder
    #     path, _ = QFileDialog.getOpenFileName( #call static method to open file dialog, returns path and filter (_)
    #         #arguments: parent, dialog title, starting directory, file filters
    #         parent,
    #         "Open Image",
    #         "",
    #         "Images (*.png *.jpg *.jpeg *.bmp *.tif)"
    #     )

    #     #if cancelled, path will be empty, exit function
    #     if not path:
    #         return

    #     # get pixmap from path, emit signal with pixmap
    #     pixmap = QPixmap(path)
    #     if not pixmap.isNull():
    #         self.image_loaded.emit(pixmap)