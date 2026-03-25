from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton,QProgressBar,QApplication
from PySide6.QtCore import Qt,QTimer
import os
from image_viewer import ImageLoader
from nav_bar import NavBar
from window_utils import center_on_primary_screen
from model_prediction import ImageLabeler

class BatchPrediction(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        self.drive = drive
        self.images = []
        self.total_images = 0
        self.abort_requested = False

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

        # Progress bar for epoch tracking
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0.0%")
        layout.addWidget(self.progress_bar)

        # Abort Button
        self.abort_button = QPushButton("Abort")
        self.abort_button.clicked.connect(self.request_abort)
        layout.addWidget(self.abort_button)
        
        center_on_primary_screen(self)
        self.show()

        # Images with classification under model_threshold
        # will be put in the model_discarded
        self.model_threshold = 0.0 # Allow users to change
        self.model_discarded = []
        self.model_verified = []
        #load window first then start processing 
        QTimer.singleShot(0, self.start_processing)



    def start_processing(self):
        self.scan_folders_walk(self.drive)
        #print(f"Total Images Found {self.total_images}")
        self.labeler = ImageLabeler()
        self.predict_all_images()
        self.view_image_window()


    #Collect all images in folder and subfolders
    def scan_folders_walk(self,path):
        for root, dirs, files in os.walk(path):
            #print(f"Current directory: {root}")
            #print(f"Subdirectories: {dirs}")
            #print(f"Files: {files}")
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                    # Get the full path of the file
                    file_path = os.path.join(root, file)
                    #print(f"Found file: {file_path}")
                    self.images.append(file_path)
                    self.total_images +=1
  
    def predict_all_images(self):
        self.detections = []

        total = len(self.images)

        for i, img_path in enumerate(self.images):
            # Check abort flag
            if self.abort_requested:
                #print("Prediction aborted")
                return

            det = self.labeler.get_conf_scores_single(img_path)
            self.detections.append(det)

            # update progress
            percent = ((i + 1) / total) * 100
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{percent:.1f}%")
            # let UI breathe between predictions
            QApplication.processEvents()
            #Apply threshold to conf scores and only pass valid detections 
            
        path_index = 0 
        for det in self.detections: 
            if any(conf > self.model_threshold for conf in det['confidences']): 
                self.model_verified.append(det) 
            else: 
                self.model_discarded.append(self.images[path_index]) 
            path_index +=1 
        
    def open_dir_dialog(self):
            from window_utils import pick_directory
            self.drive = pick_directory(self)
    
    def view_image_window(self):
        self.imageWindow = ImageLoader(self.drive,model_verified=self.model_verified,model_discarded=self.model_discarded)
        self.imageWindow.show()
        self.close()
                    
    def request_abort(self):
        #print("Abort requested")
        self.abort_requested = True
            