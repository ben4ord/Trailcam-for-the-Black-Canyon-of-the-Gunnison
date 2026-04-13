from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton,QSlider,QLabel,QComboBox
from PySide6.QtCore import Qt

from image_viewer import ImageLoader
from nav_bar import NavBar
from data_extraction import DataExtraction
from datetime import datetime, timedelta
from window_utils import center_on_primary_screen

class ExportWindow(QMainWindow):
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

        # Select time interval between photos 
        self.time_selection = QComboBox()
        self.time_selection.addItem("30 Seconds",userData=timedelta(seconds=30))
        self.time_selection.addItem("1 Minute",userData=timedelta(minutes=1))
        self.time_selection.addItem("3 Minutes",userData=timedelta(minutes=3))
        self.time_selection.addItem("5 Minutes",userData=timedelta(minutes=5))
        self.time_selection.addItem("10 Minutes",userData=timedelta(minutes=10))
        self.time_selection.addItem("15 Minutes",userData=timedelta(minutes=15))
        self.time_selection.addItem("30 Minutes",userData=timedelta(minutes=30))
        self.time_selection.addItem("1 Hour",userData=timedelta(hours=1))
        layout.addWidget(self.time_selection, 2, 2,1,2)

        # Add button for training new model
        self.exportData = QPushButton('Export Data')
        self.exportData.clicked.connect(self.start_data_extraction)
        layout.addWidget(self.exportData, 3, 2,1,2)

        # Add slider to adjust model thresh hold 
        self.thresh_hold_slider = QSlider(Qt.Orientation.Horizontal)
        self.thresh_hold_slider.setRange(0, 100)
        # Label to display value 
        self.thresh_num = QLabel("Confidence Value: 0")
        # Connect signal to slot
        self.thresh_hold_slider.valueChanged.connect(self.update_confidence)
        self.thresh_hold_slider.setValue(0)
        layout.addWidget(self.thresh_hold_slider,5,2,1,2)
        layout.addWidget(self.thresh_num,4,2,1,1)
        center_on_primary_screen(self)
        self.show()

    def update_confidence(self, value: int):
        self.confidence_value = value
        self.thresh_num.setText(f"Confidence Value: {value}")

    def start_data_extraction(self):
        self.image_time_period = self.time_selection.currentData()
        self.predictionWindow = DataExtraction(self.drive,confidence_value=self.confidence_value,image_time_period=self.image_time_period)
        self.predictionWindow.show()
        self.close()
    
    def open_dir_dialog(self):
        from window_utils import pick_directory
        self.drive = pick_directory(self)
        