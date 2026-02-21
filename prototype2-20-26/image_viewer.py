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
    QListWidgetItem,
    QHBoxLayout
)

import qtawesome as qta

from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QEvent, QPoint
import cv2
from model_prediction import ImageLabeler

class ImageLoader(QMainWindow):
    def __init__(self, drive):
        super().__init__()
        
        self.drive = drive
        self.images = self.get_imgs(self.drive)
        self.current_index = 0 # Track which image we are on
        self.labeler = ImageLabeler()
        self._drag_active = False
        self._drag_position = QPoint()
        self._press_pos = QPoint()

        self.setGeometry(100, 100, 600, 400) # Made it slightly larger to fit an image
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)


        # Menu bar buttons
        # Icons can be found here: https://fontawesome.com/v6/search?ic=free-collection
        self.home_btn = QPushButton()
        self.home_btn.setIcon(qta.icon('fa6s.house'))
        self.home_btn.setToolTip('Home')
        self.home_btn.clicked.connect(self.menu_window)
        self.home_btn.setFlat(True)

        self.update_labels_btn = QPushButton()
        self.update_labels_btn.setIcon(qta.icon('fa6s.file-pen'))
        self.update_labels_btn.setToolTip('Update Labels')
        self.update_labels_btn.clicked.connect(self.update_labels_window)
        self.update_labels_btn.setFlat(True)

        self.new_folder_btn = QPushButton()
        self.new_folder_btn.setIcon(qta.icon('fa6s.folder'))
        self.new_folder_btn.setToolTip('Select New Folder')
        self.new_folder_btn.clicked.connect(self.open_dir_dialog)
        self.new_folder_btn.setFlat(True)

        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.setStyleSheet("""
        #titleBar {
            background-color: #1f2a36;   /* bar color */
            border-bottom: 1px solid #3b4b5f;
        }
        #titleBar QLabel {
            color: #ffffff;
            font-weight: 600;
        }
        #titleBar QPushButton {
            background: transparent;
            color: #ffffff;
            border: none;
            padding: 4px 8px;
        }
        #titleBar QPushButton:hover {
            background-color: #2f3e4f;
        }
        """)

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(8, 4, 8, 4)
        title_layout.setSpacing(6)


        title_layout.addWidget(self.home_btn)
        title_layout.addWidget(self.update_labels_btn)
        title_layout.addWidget(self.new_folder_btn)
        title_layout.addStretch()

        self.min_btn = QPushButton()
        self.min_btn.setIcon(qta.icon('fa6s.minus'))
        self.min_btn.setToolTip('Minimize')

        self.max_btn = QPushButton()
        self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
        self.max_btn.setToolTip('Maximize')

        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon('fa6s.xmark'))
        self.close_btn.setToolTip('Close')

        self.min_btn.setFixedWidth(36)
        self.max_btn.setFixedWidth(36)
        self.close_btn.setFixedWidth(36)
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_max_restore)
        self.close_btn.clicked.connect(self.close)
        title_layout.addWidget(self.min_btn)
        title_layout.addWidget(self.max_btn)
        title_layout.addWidget(self.close_btn)
        self.title_bar.installEventFilter(self)


        # Create a QLabel to hold the image
        self.image_label = QLabel("No images found")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center the image in the label

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
        layout.setRowStretch(2, 1)      # main content grows

        layout.addWidget(self.title_bar, 0, 0, 1, 5)

        # top row
        layout.addWidget(self.search_box, 1, 4)

        # image area
        layout.addWidget(self.image_label, 2, 0, 1, 3)
        layout.addWidget(self.previousImage, 3, 0)
        layout.addWidget(self.nextImage, 3, 2)

        # right panel image list
        layout.addWidget(self.image_list, 2, 4, 2, 1)

        # connect the signal for when user clicks image path
        self.image_list.itemClicked.connect(self.on_item_clicked)
        # Connect to search function
        self.search_box.textChanged.connect(self.filter_list)

        # Load in list of images 
        for image in self.images:
            item = QListWidgetItem(Path(image).name)   # show only filename
            item.setData(Qt.ItemDataRole.UserRole, image)           # store full path internally
            self.image_list.addItem(item)
            #print(image)
       
        # highlight first image in image list
        self.image_list.setCurrentRow(self.current_index)

        self.show()

    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
            self.max_btn.setToolTip('Maximize')
        else:
            self.showMaximized()
            self.max_btn.setIcon(qta.icon('fa6s.window-restore'))
            self.max_btn.setToolTip('Restore')

    def eventFilter(self, obj, event):
        if obj is self.title_bar:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self.toggle_max_restore()
                return True
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                clicked_child = self.title_bar.childAt(event.position().toPoint())
                if clicked_child in (
                    self.min_btn,
                    self.max_btn,
                    self.close_btn,
                    self.home_btn,
                    self.update_labels_btn,
                    self.new_folder_btn,
                ):
                    return False
                self._drag_active = True
                self._press_pos = event.position().toPoint()
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_active:
                global_pos = event.globalPosition().toPoint()
                if self.isMaximized() or self.isFullScreen():
                    # Use pre-maximize geometry to avoid transient width values after showNormal().
                    normal_rect = self.normalGeometry()
                    target_width = normal_rect.width() if normal_rect.width() > 0 else self.width()

                    self.showNormal()
                    # Keep cursor anchored to the same relative point on the title bar after restore.
                    press_ratio_x = self._press_pos.x() / max(1, self.title_bar.width())
                    anchor_x = int(press_ratio_x * target_width)
                    anchor_x = max(0, min(anchor_x, max(0, target_width - 1)))
                    anchor_y = max(0, min(self._press_pos.y(), max(0, self.title_bar.height() - 1)))
                    self.move(global_pos.x() - anchor_x, global_pos.y() - anchor_y)

                    self._drag_position = global_pos - self.frameGeometry().topLeft()
                    self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
                    self.max_btn.setToolTip('Maximize')
                    return True

                self.move(global_pos - self._drag_position)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_active = False
                return True
        return super().eventFilter(obj, event)


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
        return imgs
    
    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            print(f"Entering {dir_name}")
            path = Path(dir_name)
            self.current_index = 0
            self.drive = str(path)
            self.images = self.get_imgs(self.drive,True)
            self.update_display()

    def filter_list(self, text):
        text = text.lower()

        for row in range(self.image_list.count()):
            item = self.image_list.item(row)

            filename = item.text().lower()
            full_path = item.data(Qt.ItemDataRole.UserRole).lower()

            match = text in filename or text in full_path
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
