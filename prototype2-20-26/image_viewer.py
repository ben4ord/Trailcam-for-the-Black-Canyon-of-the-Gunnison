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
    QMessageBox,
    QCheckBox,
    QComboBox,
)

from PySide6.QtGui import QPixmap, QShortcut,QGuiApplication
from PySide6.QtCore import Qt, QSortFilterProxyModel,QStringListModel
import qtawesome as qta
from model_prediction import ImageLabeler
from nav_bar import NavBar
from training_manager import TrainingManager
from label_editor import LabelEditor

class ImageLoader(QMainWindow):
    def __init__(self, drive):
        super().__init__()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.activateWindow()
        self.setFocus()

        # -----------------------------
        # Dataset state
        # -----------------------------
        self.images = []
        self.filtered_images = []
        self.labels = []
        self.drive = drive

        # Load dataset BEFORE UI filtering
        self.get_imgs(self.drive, new_dir=True)
        self.load_labels()
        print(self.labels)
        self.current_index = 0
        self.filter_mode = "all"

        # -----------------------------
        # Model / backend logic
        # -----------------------------
        self.labeler = ImageLabeler()
        self.training_manager = TrainingManager(self.drive)

        # -----------------------------
        # Window setup
        # -----------------------------
        self.setWindowTitle('Image Loader')
        self.setGeometry(100, 100, 600, 400)

        self.setGeometry(
            QGuiApplication.primaryScreen().availableGeometry().center().x() - self.width() // 2,
            QGuiApplication.primaryScreen().availableGeometry().center().y() - self.height() // 2,
            self.width(),
            self.height()
        )

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        # -----------------------------
        # Central widget + layout
        # -----------------------------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QGridLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -----------------------------
        # Navbar
        # -----------------------------
        self.nav_bar = NavBar(self)
        self.nav_bar.homeClicked.connect(self.menu_window)
        self.nav_bar.updateLabelsClicked.connect(self.update_labels_window)
        self.nav_bar.newFolderClicked.connect(self.open_dir_dialog)

        # -----------------------------
        # Controls
        # -----------------------------
        self.verify_image = QPushButton()
        self.verify_image.setIcon(qta.icon('fa6s.circle-check'))
        self.verify_image.setToolTip("Verify Image Label")
        self.verify_image.clicked.connect(self.mark_verified)

        self.verification_status = QLabel()

        self.unverify_image_btn = QPushButton()
        self.unverify_image_btn.setIcon(qta.icon('fa6s.circle-xmark'))
        self.unverify_image_btn.setToolTip("Unverify Image")
        self.unverify_image_btn.clicked.connect(self.unverify_image)

        self.confirm_toggle = QCheckBox("Enable prompts and popups")
        self.confirm_toggle.setChecked(True)

        # Filter dropdown
        self.filter_dropdown = QComboBox()
        self.filter_dropdown.addItems([
            "All Images",
            "Verified Only",
            "Unverified Only"
        ])
        self.filter_dropdown.currentIndexChanged.connect(
            self.on_image_filter_changed
        )


        # -----------------------------
        # Image display
        # -----------------------------
        self.image_label = QLabel("No images found")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_list = QListWidget()

        self.label_dropdown = QComboBox()
        self.label_dropdown.setEditable(True)
        self.label_dropdown.setInsertPolicy(QComboBox.NoInsert)
        self.label_dropdown.setCompleter(None)
        self.model = QStringListModel(self.labels)
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterRole(Qt.DisplayRole)

        self.label_dropdown.setModel(self.proxy)
        self.label_dropdown.lineEdit().textEdited.connect(self.filter_labels)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search images...")

        self.clear_search = QPushButton()
        self.clear_search.setIcon(qta.icon("fa6s.x"))
        self.clear_search.setToolTip("Clear Image Search")
        self.clear_search.clicked.connect(self.clear_search_bar)

        self.delete_button = QPushButton()
        self.delete_button.setIcon(qta.icon('fa6s.trash'))
        self.delete_button.setToolTip("Delete Image")
        self.delete_button.clicked.connect(self.delete_image)

        # Navigation
        self.previousImage = QPushButton('<- Previous')
        self.previousImage.clicked.connect(self.previous_image)

        self.nextImage = QPushButton('Next ->')
        self.nextImage.clicked.connect(self.next_image)

        # Keyboard shortcuts
        QShortcut(Qt.Key_Right, self, self.next_image)
        QShortcut(Qt.Key_Left, self, self.previous_image)
        QShortcut(Qt.Key_Return, self, self.mark_verified)
        QShortcut(Qt.Key_Enter, self, self.mark_verified)

        # -----------------------------
        # Layout placement
        # -----------------------------
        layout.setColumnStretch(3, 1)
        layout.setRowStretch(2, 1)
        
        # Nav Bar Row
        layout.addWidget(self.nav_bar, 0, 0, 1, 7)

        # First Row
        layout.addWidget(self.filter_dropdown, 1, 0, 1, 2)
        layout.addWidget(self.confirm_toggle, 1, 2)
        layout.addWidget(self.label_dropdown,1,3)
        layout.addWidget(self.search_box, 1, 5)
        layout.addWidget(self.clear_search, 1, 6)

        # Image Layout (and next/previous buttons)
        layout.addWidget(self.previousImage, 4, 0)
        layout.addWidget(self.image_label, 2, 1, 1, 3)
        layout.addWidget(self.nextImage, 4, 4, 1, 1)

        # Lower Layout
        layout.addWidget(self.delete_button, 3, 1)
        layout.addWidget(self.verification_status, 3, 2)
        layout.addWidget(self.verify_image, 3, 3)
        layout.addWidget(self.unverify_image_btn, 3, 4)

        # Side panel (image list)
        layout.addWidget(self.image_list, 2, 5, 2, 2)

        # Image list button assignments
        self.image_list.itemClicked.connect(self.on_list_item_clicked)
        self.search_box.textChanged.connect(self.filter_list)

        # Final dataset initialization after widgets exist
        self.apply_filter("all")

        self.load_image_list()

        if self.filtered_images:
            self.image_list.setCurrentRow(self.current_index)
            self.update_display()

        self.show()


    # -----------------------------
    # Helpful UI Functions
    # -----------------------------
    def _confirm_action(self, title, message):
        if not self.confirm_toggle.isChecked():
            return True

        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No
        )

        return reply == QMessageBox.Yes
    
    def _show_info(self, title, message):
        if not self.confirm_toggle.isChecked():
            return

        QMessageBox.information(
            self,
            title,
            message
        )

    def show_no_images_popup(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("No Images")
        msg.setText("This folder contains no images.\n Select a new working directory.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()


    # -----------------------------
    # Image handle functions
    # -----------------------------
    def load_image_list(self):
        self.image_list.clear()

        for image in self.filtered_images:
            item = QListWidgetItem(Path(image).name)
            item.setData(Qt.UserRole, image)
            self.image_list.addItem(item)

    def filter_list(self, text):
        text = text.lower()

        for row in range(self.image_list.count()):
            item = self.image_list.item(row)

            filename = item.text().lower()
            #full_path = item.data(Qt.UserRole).lower()

            match = text in filename
            item.setHidden(not match)

    def delete_image(self):
        if not self.images:
          return

        if not self._confirm_action(
            "Confirm Image Deletion?",
            "Delete this image? (This could take a minute)"
        ):
            return

        file_path = self.filtered_images[self.current_index]

        if os.path.exists(file_path):
            os.remove(file_path)

        self.get_imgs(self.drive, True)
        self.image_list.takeItem(self.current_index)

        self._show_info(
            "Image Deleted",
            f"Deleted from:\n{file_path}\n"
        )

        if self.images:
            self.current_index = min(self.current_index, len(self.images) - 1)
            self.update_display()
        else:
            self.current_index = -1
            self.show_no_images_popup()

    def next_image(self):
        if not self.filtered_images:
            return

        self.current_index = (self.current_index + 1) % len(self.filtered_images)
        self.update_display()

    def previous_image(self):
        if not self.filtered_images:
            return

        self.current_index = (self.current_index - 1) % len(self.filtered_images)
        self.update_display()

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
        self.filtered_images = list(imgs)
        if not imgs:
            self.show_no_images_popup()
            return

        return 


    # -----------------------------
    # Button press functions
    # -----------------------------
    def on_list_item_clicked(self, item):
        self.current_index = self.image_list.row(item)
        print(self.current_index)
        self.update_display()
    
    def clear_search_bar(self):
        self.search_box.setText('')
        item = self.image_list.item(self.current_index)
        self.image_list.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
        

    def update_display(self):
        # Centralized logic to refresh the image label
        if not self.filtered_images:
            return

        path = self.filtered_images[self.current_index]
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
        
        if self.current_index < self.image_list.count():
            self.image_list.setCurrentRow(self.current_index)

        if self.training_manager.is_verified_cached(path):
            self.verification_status.setText("✔ Verified")
            self.verification_status.setStyleSheet("color: green; font-weight: bold;")
            self.verify_image.setEnabled(False)
            self.image_label.setStyleSheet("border: 4px solid green;")
        else:
            self.verification_status.setText("Not Verified")
            self.verification_status.setStyleSheet("color: red;")
            self.verify_image.setEnabled(True)
            self.image_label.setStyleSheet("")
    
    def mark_verified(self):
        if not self.filtered_images:
            return
        
        source = self.filtered_images[self.current_index]
        
        # Return is the image is already verified (doesn't allow a second 'Enter' keypress)
        if self.training_manager.is_verified_cached(source):
            return
        
        if not self._confirm_action(
            "Confirm Verification",
            "Verify this image?"
        ):
            return
    
        prediction = self.labeler.predict(source)
        label_lines = self.labeler.to_yolo_label_lines(prediction)
        new_path, label_path = self.training_manager.verify_image(source, label_lines)

        self._show_info(
            "Verified",
            f"Copied to:\n{new_path.name}\n\nLabel saved:\n{label_path.name}"
        )
        self.verification_status.setText("✔ Verified")
        self.verification_status.setStyleSheet("color: green; font-weight: bold;")
        self.verify_image.setEnabled(False)
        self.image_label.setStyleSheet("border: 4px solid green;")

        self.next_image() # automatically scroll to next image (less button clicking)

    def unverify_image(self):
        if not self.filtered_images:
            return
        
        if not self._confirm_action(
            "Confirm Unverify",
            "Remove verified dataset copy?"
        ):
            return

        source = self.filtered_images[self.current_index]

        # Delete verified training dataset copy + label file
        self.training_manager.unverify_image(source)

        self._show_info(
            "Unverified",
            "Image removed from training dataset."
        )

        # Refresh UI state
        self.verify_image.setEnabled(True)
        self.verification_status.setText("Not Verified")
        self.verification_status.setStyleSheet("color: red;")
        self.image_label.setStyleSheet("")
  
    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            print(f"Entering {dir_name}")
            path = Path(dir_name)
            self.current_index = 0
            self.drive = str(path)

            self.get_imgs(self.drive, True)
            self.load_image_list()

            if self.images:
                self.image_list.setCurrentRow(0)
                self.update_display()
            else:
                self.image_label.setText("No images found")
            
            self.training_manager = TrainingManager(self.drive)
            self.training_manager._build_cache()

    def menu_window(self):
        from menu import MenuWindow
        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()

    def update_labels_window(self):
        if self.images:
            editor = LabelEditor(self)
            editor.exec()


    # -----------------------------
    # Filtering functions
    # -----------------------------
    def on_image_filter_changed(self, index):
        # Map dropdown index to filter mode
        if index == 0:
            mode = "all"
        elif index == 1:
            mode = "verified"
        else:
            mode = "unverified"

        self.apply_filter(mode)

    def apply_filter(self, mode):
        self.filter_mode = mode

        if mode == "all":
            self.filtered_images = list(self.images)
        elif mode == "verified":
            self.filtered_images = [
                img for img in self.images
                if self.training_manager.is_verified_cached(img)
            ]
        elif mode == "unverified":
            self.filtered_images = [
                img for img in self.images
                if not self.training_manager.is_verified_cached(img)
            ]

        self.current_index = 0

        self.load_image_list()

        if self.filtered_images:
            self.update_display()
        else:
            self.image_label.setText("No images match filter")
    
    def load_labels(self):
        try:
            with open("../classes.txt", "r") as file:
                for line in file:
                    self.labels.append(line.strip())
                    print(line)
        except Exception as e:
            print(e)
    
    def filter_labels(self,text):
        # Prevent combo from changing selection during filtering
        self.proxy.setFilterFixedString(text)

        if self.proxy.rowCount() == 0:
            self.label_dropdown.hidePopup()
            return

        # Only show popup if it's not already visible
        if not self.label_dropdown.view().isVisible():
            self.label_dropdown.showPopup()
