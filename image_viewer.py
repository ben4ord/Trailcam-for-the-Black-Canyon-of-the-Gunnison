import os
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QPushButton,
    QMainWindow,
    QLabel,
    QLineEdit,
    QFileDialog,
    QListWidget,
    QListWidgetItem
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import cv2
from model_prediction import ImageLabeler

class ImageLoader(QMainWindow):
    def __init__(self, drive):
        super().__init__()
        
        self.drive = drive
        self.images = self.get_imgs(self.drive)
        self.current_index = 0 # Track which image we are on
        self.labeler = ImageLabeler()

        self.setWindowTitle('Image Loader')
        self.setGeometry(100, 100, 600, 400) # Made it slightly larger to fit an image

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)

        # Directory Selection
        dir_btn = QPushButton('Browse')
        dir_btn.clicked.connect(self.open_dir_dialog)
        self.dir_name_edit = QLineEdit()


        # Create a QLabel to hold the image
        self.image_label = QLabel("No images found")
        self.image_label.setAlignment(Qt.AlignCenter) # Center the image in the label

        # Create QListWidget allowing user to click image and search for image
        self.image_list = QListWidget()     
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search images...")
        # If images exist, load the first one into the label
        if self.images:
            self.update_display()

        self.previousImage = QPushButton('<- Previous')
        self.previousImage.clicked.connect(self.previous_image)
        self.nextImage = QPushButton('Next ->')
        self.nextImage.clicked.connect(self.next_image)

        # 3. Add widgets to layout
        # (Row, Column, RowSpan, ColumnSpan)
        layout.setColumnStretch(3, 1)   # horizontal spacer
        layout.setRowStretch(1, 1)      # main content grows

        # top row
        layout.addWidget(QLabel('Current Directory:'), 0, 0)
        layout.addWidget(self.dir_name_edit, 0, 1)
        layout.addWidget(dir_btn, 0, 2)
        layout.addWidget(self.search_box, 0, 4)

        # image area
        layout.addWidget(self.image_label, 1, 0, 1, 3)
        layout.addWidget(self.previousImage, 2, 0)
        layout.addWidget(self.nextImage, 2, 2)

        # right panel image list
        layout.addWidget(self.image_list, 1, 4, 2, 1)

        # connect the signal for when user clicks image path
        self.image_list.itemClicked.connect(self.on_item_clicked)
        # Connect to search function
        self.search_box.textChanged.connect(self.filter_list)

        # Load in list of images 
        for image in self.images:
            item = QListWidgetItem(Path(image).name)   # show only filename
            item.setData(Qt.UserRole, image)           # store full path internally
            self.image_list.addItem(item)
            #print(image)
       
        # highlight first image in image list
        self.image_list.setCurrentRow(self.current_index)

        self.show()


    def on_item_clicked(self, item):
        self.current_index = self.image_list.row(item)
        self.update_display()
    

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
        labeled_path = self.labeler.label_image(path)
        color_correction = cv2.cvtColor(labeled_path,cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(color_correction)
        pixmap = QPixmap.fromImage(pil_image.toqimage())
        scaled_pixmap = pixmap.scaled(1000, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.image_label.setPixmap(scaled_pixmap)
        self.image_list.setCurrentRow(self.current_index)
        #print(f"Viewing: {os.path.basename(path)}")

    def get_imgs(self, drive, new_dir=False):
        if(new_dir):
            self.images.clear()
        imgs = []
        # print(f"Getting images from {drive}")
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

    def filter_list(self, text):
        text = text.lower()

        for row in range(self.image_list.count()):
            item = self.image_list.item(row)

            filename = item.text().lower()
            full_path = item.data(Qt.UserRole).lower()

            match = text in filename or text in full_path
            item.setHidden(not match)

