import os
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
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
    QInputDialog,
    QGroupBox,
    QTabWidget,
    QSplitter,
    QScrollArea,
    QTabWidget,
)
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QPixmap, QShortcut,QGuiApplication
from PySide6.QtCore import Qt
import qtawesome as qta
from Prediction_Classes.model_prediction import ImageLabeler
from Helper_Classes.nav_bar import NavBar
from Helper_Classes.verified_images_manager import TrainingManager
from Helper_Classes.clickable_label import ClickableLabel
from Window_Screen_Classes.label_editor import LabelEditor
from Helper_Classes.label_store import LabelStore
from Helper_Classes.ui_dialogs import confirm_action, show_info, show_no_images_popup
from Helper_Classes.window_utils import pick_directory, center_on_primary_screen
from Helper_Classes.image_scanner import ImageScanner
import shutil

LIST_PAGE_SIZE = 500

class ImageLoader(QMainWindow):
    def __init__(self, drive,model_verified=None,model_discarded=None):
        super().__init__()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.activateWindow()
        self.setFocus()

        # -----------------------------
        # Dataset state
        # -----------------------------
        self.images: list[str] = []
        self.filtered_images: list[str] = []
        self.labels = []
        self.active_labels = []
        self.drive = drive
        self.detections = []
        self.detection_combos = []
        self.deletion_bounding_box_cords = []
        self.label_store = LabelStore()
        self.model_verified = model_verified
        self.model_discarded = model_discarded
        self.species_filter: set = set()
        self.species_cache: dict = {}
        self.creation_boxes = []
        self.temp_point = None
        self.original_height = None
        self.original_width = None
        if model_verified:
            self.model_verified = model_verified
        if model_discarded:
            self.model_discarded = model_discarded
        self.current_base_bgr: np.ndarray | None = None
        self.current_unverified_bgr: np.ndarray | None = None
        self.current_image_path = None
        self.scanner: ImageScanner | None = None
        self.list_page_start = 0
        self.scan_complete = False
        self.search_text: str = ""
        self.base_filtered: list[str] = []  # filtered_images before search is applied
        self.page_loading = False  # guard against scroll signals firing during page reload (caused the scroll to jump from 500 -> 2000 in cases)

        self.load_labels()
        self.current_index = 0
        self.filter_mode = "all"
        self.verified = False
        self.total_verified_count = 0
        self.total_removed_count = 0
        self.newly_verified_count = 0
        self.recently_deleted_count = 0
        self.last_verified_label = None
        self.last_changed_label = None

        # -----------------------------
        # Model / backend logic
        # -----------------------------
        self.labeler = ImageLabeler()
        self.active_model_path = ""
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
        self.nav_bar.newBatchClicked.connect(self.start_batch_prediction)
        self.nav_bar.modelSelected.connect(self.on_model_selected)
        # Sync the labeler to whatever the navbar already selected during its __init__
        # (the signal fires before this connection is made, so we apply it manually).
        # Only update the labeler here — skip refresh_filter since the UI isn't fully
        # built yet (delete_button etc. don't exist until later in __init__).
        initial_model = self.nav_bar.selected_model_path()
        if initial_model:
            self.active_model_path = initial_model
            self.labeler = ImageLabeler(initial_model)

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
        self.unverify_image_btn.setEnabled(False)

        self.confirm_toggle = QCheckBox("Enable prompts and popups")
        self.confirm_toggle.setChecked(True)

        # Filter dropdown
        self.filter_dropdown = QComboBox()
        self.filter_dropdown.addItems([
            "All Images",
            "Verified Only",
            "Unverified Only",
            "Model Verified",
            "Model Discarded",
            "Recently Deleted"
        ])
        self.filter_dropdown.currentIndexChanged.connect(
            self.on_image_filter_changed
        )

        # Species filter panel — grid of toggle buttons, one per label
        self.species_filter_group = QGroupBox("Filter by Species")
        species_vbox = QVBoxLayout()
        species_vbox.setContentsMargins(4, 4, 4, 4)
        species_vbox.setSpacing(4)
        self.species_buttons: list = []
        self.species_btn_widget = QWidget()
        self.species_grid = QGridLayout(self.species_btn_widget)
        self.species_grid.setContentsMargins(0, 0, 0, 0)
        self.species_grid.setSpacing(3)
        self.clear_species_btn = QPushButton("Clear All")
        self.clear_species_btn.clicked.connect(self.clear_species_filter)
        # Wrap buttons in a scroll area so the grid doesn't force a minimum
        # panel width — the user can shrink the left panel freely.
        species_scroll = QScrollArea()
        species_scroll.setWidget(self.species_btn_widget)
        species_scroll.setWidgetResizable(True)
        species_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        species_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        species_vbox.addWidget(species_scroll)
        species_vbox.addWidget(self.clear_species_btn)
        self.species_filter_group.setLayout(species_vbox)

        # -----------------------------
        # Image display
        # -----------------------------
        self.image_label = QLabel("No images found")
        self.image_label = ClickableLabel()
        self.image_label.clicked.connect(self.on_image_clicked)
        self.image_label.resized.connect(self.update_display)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(1, 1)

        self.image_list = QListWidget()

        self.detection_label = QLabel("Detections:") 

        # -----------------------------
        # Verification Box (Below Label box)
        # -----------------------------
        self.verification_summary_box = QGroupBox("Verification Summary")
        summary_layout = QGridLayout()
        summary_label_total_verified = QLabel("Total verified images:")
        summary_label_newly_verified = QLabel("Newly verified images:")
        summary_label_total_removed = QLabel("Total removed images:")
        summary_label_recently_removed = QLabel("Recently removed images:")
        self.summary_total_verified_value = QLabel("120")
        self.summary_newly_verified_value = QLabel("8")
        self.summary_total_removed_value = QLabel("35")
        self.summary_recently_removed_value = QLabel("3")
        self.summary_total_verified_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.summary_newly_verified_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.summary_total_removed_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.summary_recently_removed_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.summary_total_verified_value.setStyleSheet("font-weight: bold;")
        self.summary_newly_verified_value.setStyleSheet("color: green; font-weight: bold;")
        self.summary_total_removed_value.setStyleSheet("font-weight: bold;")
        self.summary_recently_removed_value.setStyleSheet("color: red; font-weight: bold;")

        summary_layout.addWidget(summary_label_total_verified, 0, 0)
        summary_layout.addWidget(self.summary_total_verified_value, 0, 1)
        summary_layout.addWidget(summary_label_newly_verified, 1, 0)
        summary_layout.addWidget(self.summary_newly_verified_value, 1, 1)
        summary_layout.addWidget(summary_label_total_removed, 2, 0)
        summary_layout.addWidget(self.summary_total_removed_value, 2, 1)
        summary_layout.addWidget(summary_label_recently_removed, 3, 0)
        summary_layout.addWidget(self.summary_recently_removed_value, 3, 1)
        self.verification_summary_box.setLayout(summary_layout)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search images...")
        self.search_box.setClearButtonEnabled(True)

        self.scan_status_label = QLabel("")
        self.scan_status_label.setStyleSheet("color: #c8dff0; font-size: 14px; font-weight: bold; margin-left: 16px;")

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
        QShortcut(Qt.Key_Backspace, self, self.delete_image) # type: ignore
        QShortcut(Qt.Key_L, self, self.apply_last_verified_label) # type: ignore

        # -----------------------------
        # Layout placement
        # -----------------------------
        # Left-panel tab widget
        # Consolidates detections, species filter, and summary into one area
        # so the image can use the full available height.
        # -----------------------------
        self.left_tabs = QTabWidget()

        det_tab = QWidget()
        det_layout = QVBoxLayout(det_tab)
        det_layout.setContentsMargins(2, 2, 2, 2)
        det_layout.addWidget(self.detection_label)
        det_layout.addWidget(self.detection_editor)
        self.left_tabs.addTab(det_tab, "Detections")

        self.left_tabs.addTab(self.species_filter_group, "Species Filter")

        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        summary_layout.setContentsMargins(2, 2, 2, 2)
        summary_layout.addWidget(self.verification_summary_box)
        summary_layout.addStretch()
        self.left_tabs.addTab(summary_tab, "Summary")

        # -----------------------------
        # Bottom action bar
        # Edit the HBoxLayout order below to rearrange buttons.
        # -----------------------------
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(4, 4, 4, 4)
        bottom_layout.setSpacing(6)
        bottom_layout.addWidget(self.previousImage)
        bottom_layout.addWidget(self.delete_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.verification_status)
        bottom_layout.addWidget(self.verify_image)
        bottom_layout.addWidget(self.unverify_image_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.nextImage)

        # -----------------------------
        # Main content splitter
        # Drag the dividers at runtime to give the image more/less space.
        # -----------------------------
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.addWidget(self.left_tabs)
        content_splitter.addWidget(self.image_label)
        content_splitter.addWidget(self.image_list)
        content_splitter.setCollapsible(0, False)
        content_splitter.setCollapsible(1, False)
        content_splitter.setCollapsible(2, False)
        # Give the image panel the majority of space on first open.
        # setSizes uses pixel values; the splitter normalises them to fit the window.
        content_splitter.setSizes([180, 900, 160])

        # -----------------------------
        # Grid: 4 columns, stretch col 2 to push search box right
        # -----------------------------
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(2, 1)  # splitter row expands
        # Nav Bar
        layout.addWidget(self.nav_bar, 0, 0, 1, 4)
        # Controls row
        layout.addWidget(self.filter_dropdown, 1, 0)
        layout.addWidget(self.confirm_toggle, 1, 1)
        layout.addWidget(self.scan_status_label, 1, 2)
        layout.addWidget(self.search_box, 1, 3)
        # Content splitter
        layout.addWidget(content_splitter, 2, 0, 1, 4)
        # Bottom bar
        layout.addWidget(bottom_bar, 3, 0, 1, 4)

        # Image list button assignments
        self.image_list.itemClicked.connect(self.on_list_item_clicked)
        self.image_list.verticalScrollBar().valueChanged.connect(self.on_list_scroll)
        self.search_box.textChanged.connect(self.filter_list)

        # Populate species filter list now that widgets and labels exist
        self.populate_species_filter_list()
        self.cache_model_verified_species()

        self.total_verified_count = self.count_images_in_dir(self.training_manager.images_dir)
        self.total_removed_count = self.count_images_in_dir(self.recently_deleted_root())
        self.update_verification_summary()

        # Kick off background scan — first batch triggers the initial display
        self.start_scan(self.drive)

        self.center_window()
        self.show()

    # Center the window when they open it
    def center_window(self):
        center_on_primary_screen(self)

    # -----------------------------
    # Background scanner
    # -----------------------------
    def start_scan(self, path: str):
        """Stop any running scan and start a fresh one for *path*."""
        self.stop_scan()
        self.images.clear()
        self.filtered_images.clear()
        self.list_page_start = 0
        self.scan_complete = False
        self.scan_status_label.setText("Scanning…")

        self.species_filter_group.setEnabled(False)
        self.species_filter_group.setToolTip("Species filter is available after scanning completes.")

        self.scanner = ImageScanner(path, parent=self)
        self.scanner.batch_ready.connect(self.on_scan_batch)
        self.scanner.scan_done.connect(self.on_scan_done)
        self.scanner.start()

    def stop_scan(self):
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()
            self.scanner.wait()
        self.scanner = None

    def on_scan_batch(self, batch: list):
        was_empty = len(self.images) == 0
        self.images.extend(batch)
        self.scan_status_label.setText(f"Scanning… {len(self.images):,} found")

        # Extend filtered_images incrementally instead of rebuilding the whole
        # list on every batch — rebuilding becomes O(n²) over 1.7M images.
        if self.filter_mode == "all":
            self.filtered_images.extend(batch)
        elif self.filter_mode == "unverified":
            self.filtered_images.extend(
                p for p in batch if not self.training_manager.is_verified_cached(p)
            )
        elif self.filter_mode == "verified":
            self.filtered_images.extend(
                p for p in batch if self.training_manager.is_verified_cached(p)
            )
        # model_verified / model_discarded / recently_deleted are not driven by
        # the background scan, so don't touch filtered_images for those modes.

        # Show the first image as soon as the first batch arrives
        if was_empty and self.filtered_images:
            self.current_index = 0
            self.list_page_start = 0
            self.load_image_list()
            self.load_current_image_data()
            self.update_display()
        else:
            # Refresh the list to reflect new items (only if current page is the last one)
            page_end = self.list_page_start + LIST_PAGE_SIZE
            if page_end >= len(self.filtered_images) - len(batch):
                self.load_image_list()

    def on_scan_done(self, total: int):
        self.scan_complete = True
        self.scan_status_label.setText(f"{total:,} images")
        self.species_filter_group.setEnabled(True)
        self.species_filter_group.setToolTip("")
        self.load_image_list()

    def rebuild_filtered(self):
        """Re-apply the current filter_mode to self.images in place."""
        if self.filter_mode == "all":
            self.filtered_images = list(self.images)
        elif self.filter_mode == "verified":
            self.filtered_images = [
                p for p in self.images if self.training_manager.is_verified_cached(p)
            ]
        elif self.filter_mode == "unverified":
            self.filtered_images = [
                p for p in self.images if not self.training_manager.is_verified_cached(p)
            ]
        # model_verified / model_discarded / recently_deleted filters are not affected
        # by the background scan, so leave them unchanged when active.

    # -----------------------------
    # Image handle functions
    # -----------------------------
    def load_image_list(self):
        """Populate the list widget with one page of filtered_images."""
        self.image_list.clear()

        page_end = min(self.list_page_start + LIST_PAGE_SIZE, len(self.filtered_images))
        for image in self.filtered_images[self.list_page_start:page_end]:
            item = QListWidgetItem(Path(image).name)
            item.setData(Qt.UserRole, image)  # type: ignore
            self.image_list.addItem(item)

    def on_list_scroll(self, value: int):
        """Advance or retreat the page when the user scrolls to the edge."""
        if self.page_loading:
            return
        sb = self.image_list.verticalScrollBar()
        if value == sb.maximum() and sb.maximum() > 0 and not self.at_last_page():
            self.page_loading = True
            self.list_page_start += LIST_PAGE_SIZE
            self.load_image_list()
            self.image_list.verticalScrollBar().setValue(0)
            self.page_loading = False
        elif value == sb.minimum() and self.list_page_start > 0:
            self.page_loading = True
            self.list_page_start = max(0, self.list_page_start - LIST_PAGE_SIZE)
            self.load_image_list()
            self.image_list.verticalScrollBar().setValue(
                self.image_list.verticalScrollBar().maximum()
            )
            self.page_loading = False

    def at_last_page(self) -> bool:
        return self.list_page_start + LIST_PAGE_SIZE >= len(self.filtered_images)

    def ensure_index_in_page(self, abs_index: int):
        """If abs_index is outside the current page, shift the page to include it."""
        if abs_index < self.list_page_start or abs_index >= self.list_page_start + LIST_PAGE_SIZE:
            self.list_page_start = (abs_index // LIST_PAGE_SIZE) * LIST_PAGE_SIZE
            self.load_image_list()

    def list_row(self, abs_index: int) -> int:
        """Convert an absolute filtered_images index to a QListWidget row."""
        return abs_index - self.list_page_start

    def filter_list(self, text):
        self.search_text = text.lower()

        if not self.search_text:
            # Restore the pre-search list
            if self.base_filtered:
                self.filtered_images = list(self.base_filtered)
                self.base_filtered = []
        else:
            # Snapshot current filtered_images the first time a search starts
            if not self.base_filtered:
                self.base_filtered = list(self.filtered_images)
            self.filtered_images = [
                p for p in self.base_filtered
                if self.search_text in Path(p).name.lower()
            ]

        self.list_page_start = 0
        self.current_index = 0
        self.load_image_list()
        if self.filtered_images:
            self.load_current_image_data()
            self.update_display()
        else:
            self.image_label.setText("No images match search")

    def delete_image(self):
        if not self.images:
          return

        if not confirm_action(
            self,
            "Confirm Image Deletion?",
            "Delete this image? (This could take a minute)\n(Image will be moved to Recently Deleted folder)",
            self.confirm_toggle.isChecked()
        ):
            return

        file_path = self.filtered_images[self.current_index] #type: ignore

        if Path(file_path).is_file():
            self.move_to_recently_deleted(file_path)
            self.total_removed_count += 1
            self.recently_deleted_count += 1
            self.update_verification_summary()
            
        # Remove from master list and filtered list in-place (avoids re-walking the drive)
        if file_path in self.images:
            self.images.remove(file_path)
        if file_path in self.filtered_images:
            self.filtered_images.remove(file_path)

        show_info(
            self,
            "Image Deleted",
            f"Deleted from:\n{file_path}\n Move to Recently Deleted Folder"
        )

        if self.filtered_images:
            self.current_index = min(self.current_index, len(self.filtered_images) - 1)
            self.ensure_index_in_page(self.current_index)
            self.load_image_list()
            self.load_current_image_data()
            self.update_display()
        else:
            self.current_index = -1
            show_no_images_popup(self)

    def move_to_recently_deleted(self, original_path_str):
        original_path = Path(original_path_str).resolve()

        # Windows: use drive (D:\)
        # macOS/Linux: detect /Volumes/<DriveName>
        if original_path.drive:  # Windows
            root = Path(original_path.drive + "\\")
        else:  # macOS/Linux
            # Expecting /Volumes/DriveName/...
            if original_path.parts[1] == "Volumes":
                root = Path(original_path.parts[0]) / original_path.parts[1] / original_path.parts[2]
            else:
                print("File is not on an external drive.")
                return

        deleted_root = root / "Recently Deleted"

        relative_path = original_path.relative_to(root)
        destination = deleted_root / relative_path

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(original_path), str(destination))

        print(f"Moved to: {destination}")

    def count_images_in_dir(self, root: Path) -> int:
        if not root.exists():
            return 0
        image_exts = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')
        return sum(
            1
            for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in image_exts
        )

    def recently_deleted_root(self) -> Path:
        root = Path(self.drive).anchor
        return Path(root) / "Recently Deleted"

    def update_verification_summary(self):
        self.summary_total_verified_value.setText(str(self.total_verified_count))
        self.summary_total_removed_value.setText(str(self.total_removed_count))
        self.summary_newly_verified_value.setText(str(self.newly_verified_count))
        self.summary_recently_removed_value.setText(str(self.recently_deleted_count))

    def on_list_item_clicked(self, item):
        self.current_index = self.image_list.row(item) + self.list_page_start
        self.load_current_image_data()
        self.update_display()
        
    def next_image(self):
        if not self.filtered_images:
            return

        self.current_index = (self.current_index + 1) % len(self.filtered_images)
        self.load_current_image_data()
        self.creation_boxes.clear()
        self.update_display()

    def previous_image(self):
        if not self.filtered_images:
            return

        self.current_index = (self.current_index - 1) % len(self.filtered_images)
        self.load_current_image_data()
        self.creation_boxes.clear()
        self.update_display()

    
    def populate_detections(self, detections, class_list):
        self.detection_editor.clear()
        self.detection_combos.clear()

        label_id_map = {name: idx for idx, name in enumerate(self.labels)}
        sorted_options = sorted(
            [(name, label_id_map[name]) for name in class_list if name in label_id_map],
            key=lambda item: item[0].lower(),
        )
        if self.last_verified_label and self.last_verified_label in label_id_map:
            sorted_options = [
                item for item in sorted_options if item[0] != self.last_verified_label
            ]
            sorted_options.insert(0, (self.last_verified_label, label_id_map[self.last_verified_label]))

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
            options = list(sorted_options)
            if det["class_name"] not in label_id_map:
                options.insert(0, (det["class_name"], det["class_id"]))

            for name, class_id in options:
                combo.addItem(name, class_id)

            current_index = combo.findData(det["class_id"])
            if current_index >= 0:
                combo.setCurrentIndex(current_index)
            else:
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
            self.active_labels
        )
        yoloBoxes = [x1,y1,x2,y2]
        self.deletion_bounding_box_cords.append(yoloBoxes)
        # Redraw bounding box
        self.update_display(creation=True)

    def get_verified_label_path(self, source_path):
        """Map source image path to its verified dataset label txt file."""
        train_image_path = self.training_manager.generate_train_name(source_path)
        return self.training_manager.labels_dir / f"{Path(train_image_path).stem}.txt"

    def load_detections_from_label_file(self, image_path, label_path, image_shape=None):
        """Load YOLO txt labels and convert normalized boxes back to pixel boxes."""
        if image_shape is None:
            image = cv2.imread(image_path)
            if image is None:
                return []
            img_h, img_w = image.shape[:2]
        else:
            img_h, img_w = image_shape[:2]
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
        if not self.filtered_images:
            return

        self.deletion_bounding_box_cords.clear()
        path = self.filtered_images[self.current_index]
        self.current_image_path = path
        self.current_base_bgr = None
        self.current_unverified_bgr = None

        if self.training_manager.is_verified_cached(path):
            # Verified images are ground-truth: prefer saved labels over inference.
            self.verified = True
            self.current_base_bgr = cv2.imread(path)
            if self.current_base_bgr is None:
                self.image_label.setText("Unable to load image")
                self.detections = []
                self.populate_detections(self.detections, self.active_labels)
                return
            label_path = self.get_verified_label_path(path)
            self.detections = self.load_detections_from_label_file(
                path,
                label_path,
                self.current_base_bgr.shape,
            )
        else:
            # Unverified images show current model predictions as a starting point.
            self.verified = False
            result = self.labeler.predict(path)
            if result is None:
                # Prediction failed or returned nothing
                self.detections = []
                self.current_unverified_bgr = None
            else:
                self.detections = self.labeler.detections_from_result(result)
                # Safely call plot() if available; otherwise fall back to None
                if hasattr(result, "plot") and callable(result.plot):
                    try:
                        plotted = result.plot()
                        if isinstance(plotted, np.ndarray):
                            self.current_unverified_bgr = plotted
                        else:
                            self.current_unverified_bgr = None
                    except Exception:
                        self.current_unverified_bgr = None
                else:
                    self.current_unverified_bgr = None
        if self.detections:
            self.populate_detections(self.detections, self.active_labels)

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

        combo = self.detection_combos[index]
        new_id = combo.currentData()
        if new_id is None:
            if new_label not in self.labels:
                return
            new_id = self.labels.index(new_label)

        self.detections[index]['class_name'] = new_label
        self.detections[index]['class_id'] = new_id
        self.last_changed_label = new_label

    def get_current_or_last_label(self):
        row = self.detection_editor.currentRow()
        if 0 <= row < len(self.detections):
            return self.detections[row]["class_name"]
        if self.last_changed_label:
            return self.last_changed_label
        if len(self.detections) == 1:
            return self.detections[0]["class_name"]
        return None

    def apply_last_verified_label(self):
        if not self.last_verified_label:
            return
        if not self.detections:
            return
        row = self.detection_editor.currentRow()
        if row < 0 and len(self.detections) == 1:
            row = 0
        if row < 0 or row >= len(self.detections):
            return
        combo = self.detection_combos[row]
        target_index = combo.findText(self.last_verified_label)
        if target_index >= 0:
            combo.setCurrentIndex(target_index)
        else:
            combo.insertItem(0, self.last_verified_label)
            combo.setCurrentIndex(0)

    def update_display(self, yoloBoxes=None, selection=False, creation=False):
        # Centralized logic to refresh the image label
        if not self.filtered_images:
            return
 
        if self.current_base_bgr is None and self.current_unverified_bgr is None:
            return

        self.ensure_index_in_page(self.current_index)
        row = self.list_row(self.current_index)
        if 0 <= row < self.image_list.count():
            self.image_list.setCurrentRow(row)

        # At this point either current_base_bgr or current_unverified_bgr is available,
        # so there's no need to re-read the image from disk here.
        if self.verified:
            if self.current_base_bgr is None:
                self.image_label.setText("Unable to load image")
                return

            image = self.current_base_bgr.copy()

            # Verified images: draw green boxes from saved labels.
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
        else:
            # Unverified images should keep YOLO's native plotting behavior.
            if self.current_image_path is None:
                self.image_label.setText("Unable to load image")
                return
            if self.current_unverified_bgr is None:
                self.image_label.setText("Unable to load image")
                return

            # Unverified images: keep YOLO's native plot styling.
            image = self.current_unverified_bgr.copy()
            self.original_height, self.original_width = image.shape[:2]
        # Draw box around users selected object
        if selection:
            if self.verified:
                color = (255, 0, 0) # Green color (BGR format)
            else:
                color = (0, 255, 0) # Blue color (BGR format)
            thickness = 4
            cv2.rectangle(image, (yoloBoxes[0], yoloBoxes[1]), (yoloBoxes[2], yoloBoxes[3]), color, thickness) #type: ignore

        if self.creation_boxes:
            color = (0, 255, 0)
            thickness = 5
            for box in self.creation_boxes:
                x1, y1, x2, y2 = box
                cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

        if creation:
            self.refresh_labels_ui()


        if len(self.deletion_bounding_box_cords):
            color = (0, 0, 255) # Red color (BGR format)
            thickness = 5
            for box in self.deletion_bounding_box_cords:
                cv2.rectangle(image, (box[0], box[1]), (box[2], box[3]), color, thickness)

        color_correction = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(color_correction)
        pixmap = QPixmap.fromImage(pil_image.toqimage())
        scaled_pixmap = pixmap.scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.display_width = scaled_pixmap.width()
        self.display_height = scaled_pixmap.height()
        self.image_label.setPixmap(scaled_pixmap)
      
        if self.verified:
            self.verification_status.setText("Verified")
            self.verification_status.setStyleSheet("color: green; font-weight: bold;")
            self.verify_image.setEnabled(False)
            self.unverify_image_btn.setEnabled(True)
            self.image_label.setStyleSheet("border: 4px solid green;")
        else:
            self.verification_status.setText("Not Verified")
            self.verification_status.setStyleSheet("color: red;")
            self.verify_image.setEnabled(True)
            self.unverify_image_btn.setEnabled(False)
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
        last_label = self.get_current_or_last_label()
        if last_label:
            self.last_verified_label = last_label
        self.total_verified_count += 1
        self.newly_verified_count += 1
        self.update_verification_summary()

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
        self.total_verified_count = max(0, self.total_verified_count - 1)
        self.newly_verified_count = max(0, self.newly_verified_count - 1)
        self.update_verification_summary()

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
        self.refresh_filter(keep_current=True) # refresh the current image after we unverify it
  
    def get_imgs(self, path, new_dir=False, deleted_folder=False) -> list[str]:
        if(new_dir):
            self.images.clear()
            self.deletion_bounding_box_cords.clear()
        imgs = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                    # Get the full path of the file
                    file_path = os.path.join(root, file)
                    imgs.append(file_path)

        if deleted_folder:
            return imgs 
        
        self.images = imgs
        self.filtered_images = list(imgs)
        if not imgs:
            show_no_images_popup(self)
        return []
    
    def open_dir_dialog(self):
        dir_name = pick_directory(self, "Select a Directory")
        if dir_name:
            path = Path(dir_name)
            self.current_index = 0
            self.drive = str(path)
            self.filter_dropdown.setCurrentIndex(0)
            self.filter_mode = "all"
            if self.model_verified:
                self.model_verified.clear()
            if self.model_discarded:
                self.model_discarded.clear()
            self.training_manager = TrainingManager(self.drive)
            self.image_list.clear()
            self.image_label.setText("Scanning...")
            self.start_scan(self.drive)

    def menu_window(self):
        from Window_Screen_Classes.home_menu import MenuWindow
        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()

    def update_labels_window(self):
        if self.images:
            editor = LabelEditor(self)
            editor.exec()
            self.refresh_labels_ui()


    # -----------------------------
    def refresh_labels_ui(self):
        self.load_labels()
        if self.detections:
            self.populate_detections(self.detections, self.active_labels)
        self.update_display()

    # Filtering functions
    # -----------------------------
    def on_image_filter_changed(self, index):
        mode = "all"

        # Map dropdown index to filter mode
        if index == 1:
            mode = "verified"
        elif index == 2:
            mode = "unverified"
        elif index == 3:
            mode = "model_verified"
        elif index == 4:
            mode = "model_discarded"
        elif index == 5:
            mode = "recently_deleted"

        self.apply_filter(mode)

    def apply_filter(self, mode):
        self.filter_mode = mode
        # Clear any active search so base_filtered doesn't hold stale data
        self.base_filtered = []
        self.search_text = ""
        self.search_box.blockSignals(True)
        self.search_box.clear()
        self.search_box.blockSignals(False)
        self.refresh_filter()

    def refresh_filter(self, keep_current: bool = False):
        current_path = None
        if keep_current and self.filtered_images and 0 <= self.current_index < len(self.filtered_images):
            current_path = self.filtered_images[self.current_index]

        self.filtered_images.clear() #type: ignore
        self.delete_button.setVisible(True)
        if self.filter_mode == "all":
            self.filtered_images = list(self.images)
        elif self.filter_mode == "verified":
            self.filtered_images = [
                img for img in self.images
                if self.training_manager.is_verified_cached(img)
            ]
        elif self.filter_mode == "unverified":
            self.filtered_images = [
                img for img in self.images
                if not self.training_manager.is_verified_cached(img)
            ]
        elif self.filter_mode == "model_verified":
            if self.model_verified:
                for det in self.model_verified:
                    path = det["image_path"]
                    if not self.training_manager.is_verified_cached(path):
                        self.filtered_images.append(path) #type: ignore                   
        elif self.filter_mode == "model_discarded":
            if self.model_discarded:
                # model_discarded may be None; only iterate if it's truthy
                self.filtered_images = [
                    img for img in self.model_discarded
                    if not self.training_manager.is_verified_cached(img)
                ]
            else:
                self.filtered_images = []
        elif self.filter_mode == "recently_deleted":
            original_path = Path(self.drive).resolve()
            if original_path.drive:  # Windows
                root = Path(original_path.drive + "\\")
            else:  # macOS/Linux
                # Expecting /Volumes/DriveName/...
                if original_path.parts[1] == "Volumes":
                    root = Path(original_path.parts[0]) / original_path.parts[1] / original_path.parts[2]
                else:
                    print("File is not on an external drive.")
                    return
            deleted_root = Path(root) / "Recently Deleted"
            self.filtered_images = self.get_imgs(deleted_root,False,True)
            self.delete_button.setVisible(False)

        # Apply species sub-filter (only for images with known detection data)
        if self.species_filter:
            filtered_by_species = []
            for img in self.filtered_images: #type: ignore
                species = self.get_image_species(img)
                if species is not None and self.species_filter & species:
                    filtered_by_species.append(img)
            self.filtered_images = filtered_by_species

        if current_path:
            try:
                self.current_index = self.filtered_images.index(current_path)  # type: ignore
            except ValueError:
                self.current_index = 0
        else:
            self.current_index = 0

        self.list_page_start = (self.current_index // LIST_PAGE_SIZE) * LIST_PAGE_SIZE
        self.load_image_list()

        if self.filtered_images:
            self.load_current_image_data()
            self.update_display()
        else:
            self.image_label.setText("No images match filter")

    def load_labels(self):
        self.labels.clear()
        self.active_labels.clear()
        labels = self.label_store.read_labels()
        inactive = set(self.label_store.read_inactive_labels())
        self.labels.extend(labels)
        self.active_labels.extend(
            [label for label in labels if label not in inactive]
        )
        self.populate_species_filter_list()

    # -----------------------------
    # Species filter helpers
    # -----------------------------
    def populate_species_filter_list(self):
        """Rebuild the species toggle-button grid from the current label set."""
        if not hasattr(self, "species_grid"):
            return
        for btn in self.species_buttons:
            self.species_grid.removeWidget(btn)
            btn.deleteLater()
        self.species_buttons.clear()

        # Drop any previously selected species that are now inactive
        self.species_filter &= set(self.active_labels)

        cols = 5
        for i, label in enumerate(self.active_labels):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.blockSignals(True)
            btn.setChecked(label in self.species_filter)
            btn.blockSignals(False)
            btn.toggled.connect(
                lambda checked, lbl=label: self.on_species_btn_toggled(lbl, checked)
            )
            self.species_grid.addWidget(btn, i // cols, i % cols)
            self.species_buttons.append(btn)

    def cache_model_verified_species(self):
        """Pre-populate species cache from batch prediction results."""
        if not self.model_verified:
            return
        for det in self.model_verified:
            path = det.get("image_path")
            if not path:
                continue
            if path not in self.species_cache:
                self.species_cache[path] = set()
            for class_id in det.get("class_ids", []):
                try:
                    cid = int(class_id)
                    if 0 <= cid < len(self.labels):
                        self.species_cache[path].add(self.labels[cid])
                except (ValueError, TypeError):
                    pass

    def get_image_species(self, path: str) -> "set | None":
        """Return the set of species present in an image, or None if unknown.

        Returns None for images that have no detection data (not verified and
        not processed by batch prediction), which causes them to be excluded
        when a species filter is active.
        """
        if path in self.species_cache:
            return self.species_cache[path]

        if self.training_manager.is_verified_cached(path):
            label_path = self.get_verified_label_path(path)
            species: set = set()
            if label_path.exists():
                for line in label_path.read_text(encoding="utf-8").splitlines():
                    parts = line.strip().split()
                    if parts:
                        try:
                            cid = int(parts[0])
                            if 0 <= cid < len(self.labels):
                                species.add(self.labels[cid])
                        except ValueError:
                            pass
            self.species_cache[path] = species
            return species

        return None  # No detection data available

    def on_species_btn_toggled(self, label: str, checked: bool):
        """Add or remove a species from the active filter and refilter."""
        if checked:
            self.species_filter.add(label)
        else:
            self.species_filter.discard(label)
        self.refresh_filter()

    def clear_species_filter(self):
        """Uncheck all species buttons and remove the species filter."""
        self.species_filter.clear()
        for btn in self.species_buttons:
            btn.blockSignals(True)
            btn.setChecked(False)
            btn.blockSignals(False)
        self.refresh_filter()
    
    def on_model_selected(self, model_path: str):
        """Reload the labeler and re-run inference on the current image."""
        self.active_model_path = model_path
        self.labeler = ImageLabeler(model_path)
        self.refresh_filter(keep_current=True)

    def start_batch_prediction(self):
        from Prediction_Classes.batch_prediction import BatchPrediction
        confidence_value, ok = QInputDialog.getInt(
            self,
            "Set Confidence Threshold",
            "Enter confidence value (0–100):",
            0,      # default value
            0,
            100,
            1
             )

        if not ok:
            return  # user cancelled

        self.predictionWindow = BatchPrediction(self.drive, confidence_value, model_path=self.active_model_path)
        self.predictionWindow.show()
        self.close()
    
    def closeEvent(self, event):
        self.stop_scan()
        event.accept()

    def on_image_clicked(self, x, y):
        img_x, img_y = self.map_to_image_coordinates(x, y)

        if img_x is None:
            return  # Click was outside image

        if self.temp_point is None:
            self.temp_point = (img_x, img_y)
        else:
            x1, y1 = self.temp_point
            x2, y2 = img_x, img_y

            x_min = min(x1, x2)
            y_min = min(y1, y2) #type: ignore
            x_max = max(x1, x2)
            y_max = max(y1, y2) #type: ignore

            # Covert to YOLO normalized
            img_w = self.original_width
            img_h = self.original_height
            box_w = x_max - x_min
            box_h = y_max - y_min

            x_center = x_min + box_w / 2
            y_center = y_min + box_h / 2

            x_center_n = x_center / img_w #type: ignore
            y_center_n = y_center / img_h
            box_w_n = box_w / img_w #type: ignore
            box_h_n = box_h / img_h

            self.detections.append({
                "class_id": 0,
                "class_name": "None",
                "confidence": 1.0,
                "bbox_xyxy": [x_min, y_min, x_max, y_max],
                "bbox_xywhn": [x_center_n, y_center_n, box_w_n, box_h_n],
            })
            self.creation_boxes.append([x_min, y_min, x_max, y_max])
            self.temp_point = None

            self.update_display(creation=True, )

    def map_to_image_coordinates(self, click_x, click_y):
        """
        Converts QLabel click coordinates to original image coordinates.
        Handles KeepAspectRatio scaling + centering.
        """

        if not hasattr(self, "original_width"):
            return None, None

        label_width = self.image_label.width()
        label_height = self.image_label.height()

        # Calculate offsets (letterboxing)
        x_offset = (label_width - self.display_width) / 2
        y_offset = (label_height - self.display_height) / 2

        # Check if click is inside actual image area
        if (
            click_x < x_offset
            or click_x > x_offset + self.display_width
            or click_y < y_offset
            or click_y > y_offset + self.display_height
        ):
            return None, None  # Clicked padding area

        # Remove offset
        adjusted_x = click_x - x_offset
        adjusted_y = click_y - y_offset

        # Compute scaling factor
        scale_x = self.original_width / self.display_width #type: ignore
        scale_y = self.original_height / self.display_height #type: ignore

        # Map back to original image coordinates
        image_x = int(adjusted_x * scale_x)
        image_y = int(adjusted_y * scale_y)

        return image_x, image_y