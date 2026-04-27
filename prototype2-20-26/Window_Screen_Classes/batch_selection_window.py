from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton, QSlider, QLabel
from PySide6.QtCore import Qt

from Window_Screen_Classes.image_viewer import ImageLoader
from Helper_Classes.nav_bar import NavBar
from Prediction_Classes.batch_prediction import BatchPrediction
from Helper_Classes.window_utils import center_on_primary_screen

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
            home=True,
            update_labels=False,
            new_folder=True,
            info_btn=False,
        )
        self.setMenuWidget(self.nav_bar)

        self.nav_bar.homeClicked.connect(self.menu_window)
        self.nav_bar.newFolderClicked.connect(self.open_dir_dialog)

        # central widget
        central_widget = QWidget(self)
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)
        
        # creating layout
        layout = QGridLayout(central_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 2)
        layout.setRowStretch(5, 2)
        self.setLayout(layout)
        
        # Add button to next window
        self.viewImages = QPushButton('View Images')
        self.viewImages.clicked.connect(self.view_image_window)
        layout.addWidget(self.viewImages, 1, 0)

        # Add button for training new model
        self.trainModel = QPushButton('Batch Prediction')
        self.trainModel.clicked.connect(self.start_batch_prediction)
        layout.addWidget(self.trainModel, 1, 1)

        # Add slider to adjust model thresh hold 
        self.thresh_hold_slider = QSlider(Qt.Orientation.Horizontal)
        self.thresh_hold_slider.setRange(0, 100)
        # Label to display value 
        self.thresh_num = QLabel("Confidence Value: 0")
        self.thresh_num.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Connect signal to slot
        self.thresh_hold_slider.valueChanged.connect(self.update_confidence)
        self.thresh_hold_slider.setValue(0)
        layout.addWidget(self.thresh_num, 3, 1)
        layout.addWidget(self.thresh_hold_slider, 4, 1)
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
        self.predictionWindow = BatchPrediction(self.drive,confidence_value=self.confidence_value)
        self.predictionWindow.show()
        self.close()
    
    def open_dir_dialog(self):
        from Helper_Classes.window_utils import pick_directory
        self.drive = pick_directory(self)

    def menu_window(self):
        from Window_Screen_Classes.home_menu import MenuWindow

        self.imageWindow = MenuWindow(self.drive)
        self.imageWindow.show()
        self.close()
        
