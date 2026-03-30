from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton,QSlider,QLabel
from PySide6.QtCore import Qt

from image_viewer import ImageLoader
from nav_bar import NavBar
from batch_prediction import BatchPrediction
from window_utils import center_on_primary_screen

class BatchWindow(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        self.drive = drive
        self.confidence_value = 0
        self.resize(600, 200)

        # This removes the original top navbar since we are using a custom one
        # Without this it adds the new nav bar under the original
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.nav_bar = NavBar(self)
        self.nav_bar.set_button_visibility(
            home=False,
            update_labels=False,
            new_folder=True
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
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(4, 1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)
        
        # Add button to next window
        self.viewImages = QPushButton('View Images')
        self.viewImages.clicked.connect(self.view_image_window)
        layout.addWidget(self.viewImages, 3, 0,1,3)

        # Add button for training new model
        self.trainModel = QPushButton('Batch Training')
        self.trainModel.clicked.connect(self.start_batch_prediction)
        layout.addWidget(self.trainModel, 3, 4,1,3)

        # Add slider to adjust model thresh hold 
        self.thresh_hold_slider = QSlider(Qt.Orientation.Horizontal)
        self.thresh_hold_slider.setRange(0, 100)
        # Label to display value 
        self.thresh_num = QLabel("Confidence Value: 0")
        # Connect signal to slot
        self.thresh_hold_slider.valueChanged.connect(self.update_confidence)
        self.thresh_hold_slider.setValue(0)
        layout.addWidget(self.thresh_hold_slider,5,4,1,2)
        layout.addWidget(self.thresh_num,4,4,1,1)
        center_on_primary_screen(self)
        self.show()

    def update_confidence(self, value: int):
        self.confidence_value = value
        self.thresh_num.setText(f"Confidence Value: {value}")

    def view_image_window(self):
        self.imageWindow = ImageLoader(self.drive)
        self.imageWindow.show()
        self.close()

    def start_batch_prediction(self):
        self.predictionWindow = BatchPrediction(self.drive,True)
        self.predictionWindow.show()
        self.close()
    
    def open_dir_dialog(self):
        from window_utils import pick_directory
        self.drive = pick_directory(self)
        