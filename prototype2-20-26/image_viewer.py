import os
from pathlib import Path
from PIL import Image
import cv2
import shutil
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QPushButton,
    QMainWindow,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
)
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtGui import QPixmap, QShortcut,QGuiApplication
from PySide6.QtCore import Qt
import qtawesome as qta
from model_prediction import ImageLabeler
from nav_bar import NavBar
from verified_images_manager import TrainingManager
from label_editor import LabelEditor
from label_store import LabelStore
from ui_dialogs import confirm_action, show_info, show_no_images_popup
from window_utils import pick_directory, center_on_primary_screen

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
        self.detections = []
        self.detection_combos = []
        self.deletion_bounding_box_cords = []
        self.label_store = LabelStore()

        # Load dataset BEFORE UI filtering
        self.get_imgs(self.drive, new_dir=True)
        self.load_labels()
        self.current_index = 0
        self.filter_mode = "all"
        self.verified = False

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

        self.detection_editor = QListWidget()
        self.detection_editor.setSelectionMode(QAbstractItemView.SingleSelection) #type: ignore

        self.detection_editor.currentRowChanged.connect(
            self.on_detection_selected
        )
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

        self.detection_label = QLabel("Detections:") 

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search images...")
        self.search_box.setClearButtonEnabled(True)

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
        QShortcut(Qt.Key_Right, self, self.next_image) # type: ignore
        QShortcut(Qt.Key_Left, self, self.previous_image) # type: ignore
        QShortcut(Qt.Key_Return, self, self.mark_verified) # type: ignore
        QShortcut(Qt.Key_Enter, self, self.mark_verified) # type: ignore

        # -----------------------------
        # Layout placement
        # -----------------------------
        # Make image area expand
        layout.setColumnStretch(3, 1)
        layout.setRowStretch(3, 1)   # detection scroll expands
        # -----------------------------
        # Nav Bar
        # -----------------------------
        layout.addWidget(self.nav_bar, 0, 0, 1, 7)
        # -----------------------------
        # Top Controls Row
        # -----------------------------
        layout.addWidget(self.filter_dropdown, 1, 0, 1, 2)
        layout.addWidget(self.confirm_toggle, 1, 2)
        layout.addWidget(self.search_box, 1, 5)
        # -----------------------------
        # Main Content Area
        # -----------------------------
        # Detection label
        layout.addWidget(self.detection_label, 2, 0)
        # Image in center
        layout.addWidget(self.image_label, 2, 1, 2, 3)
        # Image list on right
        layout.addWidget(self.image_list, 2, 5, 3, 2)
        # -----------------------------
        # Detection Scroll Area
        # -----------------------------
        layout.addWidget(self.detection_editor, 3, 0)
        # -----------------------------
        # Verification Controls (moved down one row)
        # -----------------------------
        layout.addWidget(self.delete_button, 4, 1)
        layout.addWidget(self.verification_status, 4, 2)
        layout.addWidget(self.verify_image, 4, 3)
        layout.addWidget(self.unverify_image_btn, 4, 4)
        # -----------------------------
        # Navigation Row
        # -----------------------------
        layout.addWidget(self.previousImage, 5, 0)
        layout.addWidget(self.nextImage, 5, 4)

        # Image list button assignments
        self.image_list.itemClicked.connect(self.on_list_item_clicked)
        self.search_box.textChanged.connect(self.filter_list)

        # Final dataset initialization after widgets exist
        self.apply_filter("all")

        self.load_image_list()

        if self.filtered_images:
            self.image_list.setCurrentRow(self.current_index)
            self.load_current_image_data()
            self.update_display()

        self.center_window()
        self.show()

    # Center the window when they open it
    def center_window(self):
        center_on_primary_screen(self)

    # -----------------------------
    # Image handle functions
    # -----------------------------
    def load_image_list(self):
        self.image_list.clear()

        for image in self.filtered_images:
            item = QListWidgetItem(Path(image).name)
            item.setData(Qt.UserRole, image) # type: ignore
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

        if not confirm_action(
            self,
            "Confirm Image Deletion?",
            "Delete this image? (This could take a minute)",
            self.confirm_toggle.isChecked()
        ):
            return

        file_path = self.filtered_images[self.current_index]

        if os.path.exists(file_path):
            os.remove(file_path)

        self.get_imgs(self.drive, True)
        self.image_list.takeItem(self.current_index)

        show_info(
            self,
            "Image Deleted",
            f"Deleted from:\n{file_path}\n"
        )

        if self.images:
            self.current_index = min(self.current_index, len(self.images) - 1)
            self.update_display()
        else:
            self.current_index = -1
            show_no_images_popup(self)

    def on_list_item_clicked(self, item):
        self.current_index = self.image_list.row(item)
        self.load_current_image_data()
        self.update_display()
        
    def next_image(self):
        if not self.filtered_images:
            return

        self.current_index = (self.current_index + 1) % len(self.filtered_images)
        self.load_current_image_data()
        self.update_display()

    def previous_image(self):
        if not self.filtered_images:
            return

        self.current_index = (self.current_index - 1) % len(self.filtered_images)
        self.load_current_image_data()
        self.update_display()

    
    def populate_detections(self, detections, class_list):
        self.detection_editor.clear()
        self.detection_combos.clear()

        for i, det in enumerate(detections):

            item = QListWidgetItem()
            self.detection_editor.addItem(item)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(5, 2, 5, 2)

            info_label = QLabel(
                f"{i+1}: {det['class_name']} "
                f"({det['confidence']:.2f})"
            )
            delete_btn = QPushButton()
            delete_btn.setIcon(qta.icon('fa6s.x'))
            # Pass through object 
            delete_btn.clicked.connect(
                lambda _, det=det: self.delete_detection_object(det)
            )
            combo = QComboBox()
            combo.addItems(class_list)
            combo.setCurrentText(det["class_name"])
            combo.currentTextChanged.connect(
                lambda text, i=i: self.on_detection_label_change(i,text)
            )
            row_layout.addWidget(delete_btn)
            row_layout.addWidget(info_label)
            row_layout.addStretch()
            row_layout.addWidget(combo)

            item.setSizeHint(row_widget.sizeHint())
            self.detection_editor.setItemWidget(item, row_widget)

            self.detection_combos.append(combo)
    
    def delete_detection_object(self, det):

        # Extract coordinates BEFORE removing
        x1, y1, x2, y2 = map(int, det["bbox_xyxy"])

        # Remove detection
        self.detections.remove(det)

        # Refresh UI
        self.populate_detections(
            self.detections,
            self.labels
        )
        yoloBoxes = [x1,y1,x2,y2]
        self.deletion_bounding_box_cords.append(yoloBoxes)
        # Redraw bounding box
        self.update_display()

    def get_verified_label_path(self, source_path):
        """Map source image path to its verified dataset label txt file."""
        train_image_path = self.training_manager.generate_train_name(source_path)
        return self.training_manager.labels_dir / f"{Path(train_image_path).stem}.txt"

    def load_detections_from_label_file(self, image_path, label_path):
        """Load YOLO txt labels and convert normalized boxes back to pixel boxes."""
        image = cv2.imread(image_path)
        if image is None:
            return []

        img_h, img_w = image.shape[:2]
        detections = []

        if not label_path.exists():
            return detections

        for raw_line in label_path.read_text(encoding="utf-8").splitlines():
            parts = raw_line.strip().split()
            if len(parts) != 5:
                continue

            try:
                class_id = int(parts[0])
                x_center, y_center, width, height = map(float, parts[1:])
            except ValueError:
                continue

            # Convert YOLO normalized center/size to image-space corner coordinates.
            x1 = (x_center - width / 2.0) * img_w
            y1 = (y_center - height / 2.0) * img_h
            x2 = (x_center + width / 2.0) * img_w
            y2 = (y_center + height / 2.0) * img_h

            class_name = (
                self.labels[class_id]
                if 0 <= class_id < len(self.labels)
                else str(class_id)
            )

            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": 1.0,
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "bbox_xywhn": [x_center, y_center, width, height],
                }
            )

        return detections

    def load_current_image_data(self):
        """Load detections from verified labels or live model inference."""
        self.deletion_bounding_box_cords.clear()
        path = self.filtered_images[self.current_index]

        if self.training_manager.is_verified_cached(path):
            # Verified images are ground-truth: prefer saved labels over inference.
            self.verified = True
            label_path = self.get_verified_label_path(path)
            self.detections = self.load_detections_from_label_file(path, label_path)
        else:
            # Unverified images show current model predictions as a starting point.
            self.verified = False
            self.detections = self.labeler.get_detections(path)

        self.populate_detections(self.detections, self.labels)

    def on_detection_selected(self, index):
        if index < 0 or index >= len(self.detections):
            return

        det = self.detections[index]
        x1, y1, x2, y2 = map(int, det["bbox_xyxy"])

        combo = self.detection_combos[index]
        combo.setFocus()

        self.update_display([x1, y1, x2, y2], True)

    def on_detection_label_change(self, index, new_label):
        if index < 0 or index >= len(self.detections):
            return

        if new_label not in self.labels:
            return

        self.detections[index]['class_name'] = new_label
        new_id = self.labels.index(new_label)
        self.detections[index]['class_id'] = new_id


    def update_display(self, yoloBoxes=None, selection=False):
        # Centralized logic to refresh the image label
        if not self.filtered_images:
            return
        
        path = self.filtered_images[self.current_index]
        if self.verified:
            image = cv2.imread(path)
            if image is None:
                self.image_label.setText("Unable to load image")
                return

            # Verified images use saved labels, not model inference.
            for det in self.detections:
                x1, y1, x2, y2 = map(int, det["bbox_xyxy"])
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 6)

                label_text = f"{det['class_name']}"
                text_y = y1 - 8 if y1 > 12 else y1 + 16
                cv2.putText(
                    image,
                    label_text,
                    (x1, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.5,
                    (0, 255, 0),
                    3,
                    cv2.LINE_AA,
                )

            color_correction = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            # Unverified images should keep YOLO's native plotting behavior.
            labeled_image = self.labeler.label_image(path)
            color_correction = cv2.cvtColor(labeled_image, cv2.COLOR_BGR2RGB)
        # Draw box around users selected object
        if selection:
            if self.verified:
                color = (255, 0, 0) # Green color (BGR format)
            else:
                color = (0, 255, 0) # Blue color (BGR format)
            thickness = 4
            cv2.rectangle(color_correction, (yoloBoxes[0], yoloBoxes[1]), (yoloBoxes[2], yoloBoxes[3]), color, thickness) #type: ignore
        if len(self.deletion_bounding_box_cords):
            color = (255, 0, 0) # Red color (BGR format)
            thickness = 5
            for box in self.deletion_bounding_box_cords:
                cv2.rectangle(color_correction, (box[0], box[1]), (box[2], box[3]), color, thickness)


            
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

        if self.verified:
            self.verification_status.setText("Verified")
            self.verification_status.setStyleSheet("color: green; font-weight: bold;")
            self.verify_image.setEnabled(False)
            self.image_label.setStyleSheet("border: 4px solid green;")
        else:
            self.verification_status.setText("Not Verified")
            self.verification_status.setStyleSheet("color: red;")
            self.verify_image.setEnabled(True)
            self.image_label.setStyleSheet("")
    
    def mark_verified(self):
        """Persist current detections as YOLO labels in the training dataset."""
        if not self.filtered_images:
            return
        
        source = self.filtered_images[self.current_index]
        
        # Return is the image is already verified (doesn't allow a second 'Enter' keypress)
        if self.verified:
            return
        
        if not confirm_action(
            self,
            "Confirm Verification",
            "Verify this image?",
            self.confirm_toggle.isChecked()
        ):
            return
        # Convert edited detections to YOLO txt lines before writing to dataset.
        label_lines = self.labeler.to_yolo_label_lines(self.detections)
        new_path, label_path = self.training_manager.verify_image(source, label_lines)

        show_info(
            self,
            "Verified",
            f"Copied to:\n{new_path.name}\n\nLabel saved:\n{label_path.name}"
        )
        self.verification_status.setText("Verified")
        self.verification_status.setStyleSheet("color: green; font-weight: bold;")
        self.verify_image.setEnabled(False)
        self.image_label.setStyleSheet("border: 4px solid green;")

        self.next_image() # automatically scroll to next image (less button clicking)

    def unverify_image(self):
        """Remove image/label pair from verified training dataset."""
        if not self.filtered_images:
            return
        
        if not confirm_action(
            self,
            "Confirm Unverify",
            "Remove verified dataset copy?",
            self.confirm_toggle.isChecked()
        ):
            return

        source = self.filtered_images[self.current_index]

        # Delete verified training dataset copy + label file
        self.training_manager.unverify_image(source)

        show_info(
            self,
            "Unverified",
            "Image removed from training dataset."
        )

        # Refresh UI state
        self.verify_image.setEnabled(True)
        self.verification_status.setText("Not Verified")
        self.verification_status.setStyleSheet("color: red;")
        self.image_label.setStyleSheet("")
  

    def get_imgs(self, drive, new_dir=False):
        if(new_dir):
            self.images.clear()
            self.deletion_bounding_box_cords.clear()
        imgs = []
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
            show_no_images_popup(self)
            return

        return 
    
    def open_dir_dialog(self):
        dir_name = pick_directory(self, "Select a Directory")
        if dir_name:
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

    def menu_window(self):
        from home_menu import MenuWindow
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
            self.load_current_image_data()
            self.update_display()
        else:
            self.image_label.setText("No images match filter")
    
    def load_labels(self): #self.labels = self.label_store.read_labels()
        path = Path.cwd() / "classes.txt"
        if not path.exists():
         raise FileNotFoundError(f"{path} not found.")

        try:
            with open(path, "r") as file:
                for line in file:
                    self.labels.append(line.strip())
                    print(line)
        except Exception as e:
            print(e)
    

