import sys
import os
from PySide6.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QMainWindow, QLabel,QLineEdit, QFileDialog
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from labelImage import ImageLabeler
from pathlib import Path

class ImageLoader(QMainWindow):
    def __init__(self, drive):
        super().__init__()
        
        self.drive = drive
        self.images = self.get_imgs(self.drive)
        self.current_index = 0 # Track which image we are on

        self.setWindowTitle('Image Loader')
        self.setGeometry(100, 100, 600, 400) # Made it slightly larger to fit an image

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)

        # Directory Selection
        dir_btn = QPushButton('Browse')
        dir_btn.clicked.connect(self.open_dir_dialog)
        self.dir_name_edit = QLineEdit()


        # 1. Create a QLabel to hold the image
        self.image_label = QLabel("No images found")
        self.image_label.setAlignment(Qt.AlignCenter) # Center the image in the label
        
        # 2. If images exist, load the first one into the label
        if self.images:
            self.display_image(self.images[self.current_index])

        self.previousImage = QPushButton('<- Previous')
        self.previousImage.clicked.connect(self.previous_image)
        self.nextImage = QPushButton('Next ->')
        self.nextImage.clicked.connect(self.next_image)

        # 3. Add widgets to layout
        # (Row, Column, RowSpan, ColumnSpan)
        layout.addWidget(self.image_label, 1, 0, 1, 3) # Span across 3 columns
        layout.addWidget(self.previousImage, 2, 0)
        layout.addWidget(self.nextImage, 2, 2)
        
        # New Directory Selection
        layout.addWidget(QLabel('Current Directory:'), 0, 0)
        layout.addWidget(self.dir_name_edit, 0, 1)
        layout.addWidget(dir_btn, 0, 2)

        self.show()

    def next_image(self):
        # Moves forward and wraps to 0 if at the end
        self.current_index = (self.current_index + 1) % len(self.images)
        self.update_display()

    def previous_image(self):
        # Moves backward and wraps to the last index if at 0
        self.current_index = (self.current_index - 1) % len(self.images)
        self.update_display()

    def update_display(self):
        # Centralized logic to refresh the image label
        path = self.images[self.current_index]
        labeler = ImageLabeler()
        labeled_path = labeler.label_image(path)
        pixmap = QPixmap(labeled_path)
        scaled_pixmap = pixmap.scaled(500, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.image_label.setPixmap(scaled_pixmap)
        print(f"Viewing: {os.path.basename(path)}")

    #sets initial  image 
    def display_image(self, path):
        labeler = ImageLabeler()
        labeled_path = labeler.label_image(path)
        pixmap = QPixmap(labeled_path)
        # Optional: Scale image to fit the window while keeping aspect ratio
        scaled_pixmap = pixmap.scaled(500, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def get_imgs(self, drive, new_dir=False):
        if(new_dir):
            self.images.clear()
        imgs = []
        print(f"Getting images from {drive}")
        if os.path.exists(drive):
            for filename in os.listdir(drive):
                # Check for image extension AND ensure it doesn't start with '.'
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                    if not filename.startswith('.'): 
                        img_path = os.path.join(drive, filename)   
                        imgs.append(img_path)
        return imgs
    
    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            print(f"Entering {dir_name}")
            path = Path(dir_name)
            self.dir_name_edit.setText(str(path))
            self.current_index = 0
            self.drive = str(path)
            self.images = self.get_imgs(self.drive,True)
            self.update_display()

