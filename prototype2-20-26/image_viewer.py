import os
from pathlib import Path
from PIL import Image
import cv2

from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QPushButton,
    QMainWindow,
    QLabel,
    QLineEdit,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QHBoxLayout,
    QMessageBox
)

from PySide6.QtGui import QPixmap, QKeySequence,QKeyEvent
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
import qtawesome as qta
from model_prediction import ImageLabeler
from nav_bar import NavBar

class ImageLoader(QMainWindow):
    def __init__(self, drive):
        super().__init__()
        
        self.drive = drive
        self.images = []
        self.get_imgs(self.drive)
        self.current_index = 0 # Track which image we are on
        self.labeler = ImageLabeler()

        self.setWindowTitle('Image Loader')
        self.setGeometry(100, 100, 600, 400) # Made it slightly larger to fit an image
        self.setGeometry(
            QGuiApplication.primaryScreen().availableGeometry().center().x() - self.width() // 2,
            QGuiApplication.primaryScreen().availableGeometry().center().y() - self.height() // 2,
            self.width(),
            self.height()
        )
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.nav_bar = NavBar(self)
        self.nav_bar.homeClicked.connect(self.menu_window)
        self.nav_bar.updateLabelsClicked.connect(self.update_labels_window)
        self.nav_bar.newFolderClicked.connect(self.open_dir_dialog)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create a QLabel to hold the image
        self.image_label = QLabel("No images found")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center the image in the label

        # Create QListWidget allowing user to click image and search for image
        self.image_list = QListWidget()     
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search images...")
        self.clear_search = QPushButton()
        self.clear_search.setIcon(qta.icon("fa6s.x"))
        self.clear_search.setToolTip("Clear Image Search")
        self.clear_search.clicked.connect(self.clear_search_bar)

        # Creating PushButton for user to delete image.
        self.delete_button = QPushButton()
        self.delete_button.setIcon(qta.icon('fa6s.trash'))
        self.delete_button.setToolTip("Delete Image")
        # connect to delete function
        self.delete_button.clicked.connect(self.delete_image)

        # If images exist, load the first one into the label
        if self.images:
            self.update_display()

        self.previousImage = QPushButton('<- Previous')
        self.previousImage.clicked.connect(self.previous_image)
        self.nextImage = QPushButton('Next ->')
        self.nextImage.clicked.connect(self.next_image)
        self.nextImage.setShortcut(Qt.Key.Key_Right)
        self.previousImage.setShortcut(Qt.Key.Key_Left)

        # Add widgets to layout
        # (Row, Column, RowSpan, ColumnSpan)
        layout.setColumnStretch(3, 1)   # horizontal spacer
        layout.setRowStretch(2, 1)      # main content grows

        # nav bar
        layout.addWidget(self.nav_bar, 0, 0, 1, 7)

        # top row
        layout.addWidget(self.search_box, 1, 5)
        layout.addWidget(self.clear_search, 1, 6)

        # image area
        layout.addWidget(self.previousImage, 4, 0)
        layout.addWidget(self.image_label, 2, 1, 1, 3)
        layout.addWidget(self.nextImage, 4, 4,1,1)

        # Verification Buttons
        layout.addWidget(self.delete_button,3,1)

        # right panel image list
        layout.addWidget(self.image_list, 2, 5, 2, 2)

        # connect the signal for when user clicks image path
        self.image_list.itemClicked.connect(self.on_list_item_clicked)
        # Connect to search function
        self.search_box.textChanged.connect(self.filter_list)
       
        # highlight first image in image list
        self.load_image_list()
        self.image_list.setCurrentRow(self.current_index)

        self.show()

    def load_image_list(self):
        # Load in list of images 
        for image in self.images:
            item = QListWidgetItem(Path(image).name)   # show only filename
            item.setData(Qt.UserRole, image)           # store full path internally
            self.image_list.addItem(item)
            #print(image)   

    def delete_image(self):
        if not self.images:
          return

        file_path = self.images[self.current_index]

        if os.path.exists(file_path):
            os.remove(file_path)

        self.get_imgs(self.drive, True)
        self.image_list.takeItem(self.current_index)

        if self.images:
            self.current_index = min(self.current_index, len(self.images) - 1)
            self.update_display()
        else:
            self.current_index = -1
            self.show_no_images_popup()

    def show_no_images_popup(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("No Images")
        msg.setText("This folder contains no images.\n Select a new working directory.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def on_list_item_clicked(self, item):
        self.current_index = self.image_list.row(item)
        print(self.current_index)
        self.update_display()
    
    def clear_search_bar(self):
        self.search_box.setText('')
        item = self.image_list.item(self.current_index)
        self.image_list.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
        
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
        labeled_image = self.labeler.label_image(path)
        color_correction = cv2.cvtColor(labeled_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(color_correction)
        pixmap = QPixmap.fromImage(pil_image.toqimage())
        scaled_pixmap = pixmap.scaled(
            1000,
            700,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

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

        self.images = imgs
        if not imgs:
            self.show_no_images_popup()
            return

        return 
    
    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            print(f"Entering {dir_name}")
            path = Path(dir_name)
            self.current_index = 0
            self.drive = str(path)
            self.get_imgs(self.drive,True)
            self.update_display()
            self.load_image_list()

    def filter_list(self, text):
        text = text.lower()

        for row in range(self.image_list.count()):
            item = self.image_list.item(row)

            filename = item.text().lower()
            #full_path = item.data(Qt.UserRole).lower()

            match = text in filename
            item.setHidden(not match)

    def menu_window(self):
        from menu import MenuWindow
        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()

    def update_labels_window(self):
        from label_updater import LabelUpdater
        self.labelUpdateWindow = LabelUpdater(self.drive)
        self.labelUpdateWindow.show()
        self.close()
