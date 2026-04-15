from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt,QTimer
import os
from pathlib import Path
from sympy import root
from Helper_Classes.nav_bar import NavBar
from Helper_Classes.window_utils import center_on_primary_screen
from Prediction_Classes.model_prediction import ImageLabeler
import pandas as pd
from datetime import datetime, timedelta
from Helper_Classes.label_store import LabelStore
from pathlib import PureWindowsPath
from time import perf_counter


class DataExtraction(QMainWindow):
    def __init__(self,drive,confidence_value,in_image_viewer=False,image_time_period=None):
        super().__init__()
        self.drive = drive
        self.images = []
        self.total_images = 0
        self.abort_requested = False
        self.in_image_viewer = in_image_viewer
        self.label_store = LabelStore()
        self.labels = []
        self.active_labels = []
        self.opp_system = os.name
        self.total_images = 0
        self.image_time_period = image_time_period
        self.counting_dialog = None
        self.counting_label = None

        self.resize(600, 200)
        self.setContentsMargins(0, 0, 0, 0)

        # This removes the original top navbar since we are using a custom one
        # Without this it adds the new nav bar under the original
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.nav_bar = NavBar(self)
        self.nav_bar.set_button_visibility(
            home=False,
            update_labels=False,
            new_folder=False
        )
        self.setMenuWidget(self.nav_bar)

        self.nav_bar.newFolderClicked.connect(self.open_dir_dialog)

        # central widget
        central_widget = QWidget(self)
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)
        
        # creating layout
        layout = QGridLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Time estimation label
        self.time_estimation_label = QLabel("Estimated Time Remaining: Calculating...")
        layout.addWidget(self.time_estimation_label, 1, 0, 1, 6)

        # Progress bar for data extraction tracking
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0.0%")
        layout.addWidget(self.progress_bar, 2, 0, 1, 6)

        # Abort Button
        self.abort_button = QPushButton("Abort")
        self.abort_button.clicked.connect(self.request_abort)
        layout.addWidget(self.abort_button, 3, 0, 1, 6)
        
        center_on_primary_screen(self)
        self.show()

        # Images with classification under model_threshold
        # will be put in the model_discarded

        self.model_threshold = confidence_value/100 # Allow users to change
        self.model_discarded = []
        self.model_verified = []
        #load window first then start processing 
        QTimer.singleShot(0, self.start_processing)

    def start_processing(self):
        self.labeler = ImageLabeler()
        self.show_counting_images_popup()
        self.total_images = self.count_images(self.drive)
        self.close_counting_images_popup()
        if self.total_images == 0:
            self.counting_images_popup(False)
            return
        self.extract_data()
        self.view_menu_window()

    def show_counting_images_popup(self):
        if self.counting_dialog is not None:
            return

        self.counting_dialog = QDialog(self)
        self.counting_dialog.setWindowTitle("Counting Images")
        self.counting_dialog.setModal(False)
        self.counting_dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self.counting_dialog)
        message = QLabel(
            "Please wait while we count the total number of images to process.\n"
            "This could take a few minutes depending on the number of images."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        self.counting_label = QLabel("Images found so far: 0")
        layout.addWidget(self.counting_label)

        self.counting_dialog.resize(420, 120)
        self.counting_dialog.show()
        QApplication.processEvents()

    def update_counting_images_popup(self, count):
        if self.counting_label is None:
            return

        self.counting_label.setText(f"Images found so far: {count}")
        QApplication.processEvents()

    def close_counting_images_popup(self):
        if self.counting_dialog is None:
            return

        self.counting_dialog.close()
        self.counting_dialog.deleteLater()
        self.counting_dialog = None
        self.counting_label = None

    def counting_images_popup(self,initial=True):
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        if not initial and self.total_images == 0:
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("No Images Found")
            msg.setInformativeText("No images were found in the selected directory. Please select a different directory with images to process.")
            msg.setWindowTitle("No Images Found")
            msg.exec()
            self.open_dir_dialog()

    def extract_data(self):
        self.detections = []
        self.last_image_time = None
        self.last_camera_site = None
        image_counter = 0
        estimated_time_remaining = "Calculating..."

        if self.total_images == 0:
            print("No images found in the directory.")
            return
        animal_stats = pd.DataFrame(columns=["Filepath", "Site", "Date", "Time", "TotalAnimals", "AnimalNumber", "Species", "class_id", "Confidence", "BBox_XYXY", "BBox_XYWHN"])
        rows = []
        self.load_labels() 
        self.start_time = perf_counter()     
        for root, dirs, files in os.walk(self.drive):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                    # Get the full path of the file
                    file_path = os.path.join(root, file)
                    image_counter +=1
                    # Check abort flag
                    if self.abort_requested:
                        return
                    dt_obj,img_date, img_time = self.labeler.get_date_time(file_path)
                    camera_site = self.get_camera_site(file_path)

                    if camera_site != self.last_camera_site:
                        self.last_camera_site = camera_site # Change last camera site to current camera site
                        self.last_image_time = None # reset last image time when camera site changes
                    
                    if dt_obj and img_date and img_time:

                        # Check if the image time is within the specified period
                        if self.last_image_time == None or (dt_obj - self.last_image_time) >= self.image_time_period:
                            self.last_image_time = dt_obj
                            detections = self.labeler.get_extraction_animal_data(file_path)
                            if detections:
                                total_animals = len(detections['class_ids'])
                                if self.opp_system == 'nt':
                                    date_str = dt_obj.strftime("%#m/%#d/%Y")
                                    time_str = dt_obj.strftime("%#I:%M:%S %p")
                                elif self.opp_system == 'posix':
                                    date_str = dt_obj.strftime("%-m/%-d/%Y")
                                    time_str = dt_obj.strftime("%-I:%M:%S %p")  
                                det_index = 0
                                animal_number = 1
                                for conf in detections['confidences']:
        

                                    if conf >= self.model_threshold: 
                                        
                                        rows.append({
                                            "Filepath": detections["image_path"],
                                            "Site": self.get_camera_site(detections["image_path"]),
                                            "Date": date_str,
                                            "Time": time_str,
                                            "TotalAnimals": total_animals,
                                            "AnimalNumber": animal_number,
                                            "Species": self.labels[detections["class_ids"][det_index]],
                                            "class_id": detections["class_ids"][det_index],
                                            "Confidence": detections["confidences"][det_index],
                                            "BBox_XYXY": detections["bbox_xyxy"][det_index],
                                            "BBox_XYWHN": detections["bbox_xywhn"][det_index]
                                        })
                                        animal_number += 1
                                        det_index += 1
                                        if det_index >= len(detections['class_ids']):
                                            det_index = 0
                                        if animal_number > len(detections['class_ids']):
                                            animal_number = 1
                                
                            # update progress
                            percent = round(((image_counter) / self.total_images) * 100,4)
                            self.progress_bar.setValue(percent)
                            self.progress_bar.setFormat(f"{percent:.1f}%")
                           
                else:
                    image_counter -= 1 # if file is not an image, remove from count for progress bar accuracy
                    self.total_images -= 1 # if no date time found, remove from total count for progress bar accuracy
                # let UI breathe between predictions
                QApplication.processEvents()
                if image_counter % 100 == 0:
                    elapsed_time = perf_counter() - self.start_time
                    images_left = self.total_images - image_counter

                    if image_counter > 0:
                        time_per_image = elapsed_time / image_counter
                        estimated_seconds = time_per_image * images_left
                        estimated_time_remaining = str(timedelta(seconds=int(estimated_seconds)))

                        self.time_estimation_label.setText(
                            f"Estimated Time Remaining: {estimated_time_remaining}"
                        )

        root = Path(self.drive).anchor
        animal_stats = pd.DataFrame(rows)
        # Define the path to the Downloads folder
        downloads_path = str(Path.home() / "Downloads" / "BCG_Animal_Stats.csv")
        try:
            animal_stats.to_csv(downloads_path, index=False)
            self.alert_download_location(downloads_path)

        except PermissionError as e:
            if e.errno == 13 and os.name == 'nt':  # Windows-specific error code for permission denied
                self.alert_download_location("ERROR: Unable to save file. Please close any open instances of 'BCG_Animal_Stats.csv' and try again.")
        

    def get_camera_site(self,file_path: str) -> str | None:
        """
        Extracts the camera site from a file path.
        The camera site is the folder immediately after 'GGNCA'."""
        parts = PureWindowsPath(file_path).parts
        for i, part in enumerate(parts):
            if part.upper() == "GGNCA" and i + 1 < len(parts):
                return parts[i + 1]
        return None
    

    def alert_download_location(self, path):
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("Data Extraction Complete")
        msg.setInformativeText(f"Animal stats have been saved to: {path}")
        msg.setWindowTitle("Data Extraction")
        msg.exec()

    def open_dir_dialog(self):
            from Helper_Classes.window_utils import pick_directory
            self.drive = pick_directory(self)
    
    def view_menu_window(self):
        from Window_Screen_Classes.home_menu import MenuWindow
        self.imageWindow = MenuWindow(self.drive)
        self.imageWindow.show()
        self.close()
                    
    def request_abort(self):
        self.abort_requested = True

    def load_labels(self):
        labels = self.label_store.read_labels()
        inactive = set(self.label_store.read_inactive_labels())
        self.labels.extend(labels)
        self.active_labels.extend(
            [label for label in labels if label not in inactive]
        )
    def count_images(self, drive):
        exts = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')
        count = 0
        for _, _, files in os.walk(drive):
            for file_name in files:
                if file_name.lower().endswith(exts):
                    count += 1
                    if count == 1 or count % 25 == 0:
                        self.update_counting_images_popup(count)

        self.update_counting_images_popup(count)
        return count
