from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QPushButton,
    QSlider,
    QLabel,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import Qt

from Window_Screen_Classes.image_viewer import ImageLoader
from Helper_Classes.nav_bar import NavBar
from Helper_Classes.window_utils import center_on_primary_screen
from Helper_Classes.ui_dialogs import show_help_dialog
from Prediction_Classes.data_extraction import DataExtraction
from datetime import datetime, timedelta
class ExportWindow(ResizableMixin, QMainWindow):
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
            new_folder=True
        )
        self.setMenuWidget(self.nav_bar)

        self.nav_bar.homeClicked.connect(self.menu_window)
        self.nav_bar.newFolderClicked.connect(self.open_dir_dialog)
        self.nav_bar.infoClicked.connect(self.show_info_dialog)

        # central widget
        central_widget = QWidget(self)
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)
        
        # creating layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)

        layout.addStretch(1)

        content = QWidget()
        content.setMaximumWidth(760)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(24)

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
        self.time_selection.addItem("None (0 Seconds)",userData=timedelta(seconds=0))

        time_col = QVBoxLayout()
        time_col.setSpacing(8)
        time_label = QLabel("Time Interval")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_selection.setMinimumHeight(38)
        self.time_selection.setMinimumWidth(240)
        time_col.addWidget(time_label)
        time_col.addWidget(self.time_selection)
        controls_row.addLayout(time_col, 1)

        # Add slider to adjust model thresh hold
        self.thresh_hold_slider = QSlider(Qt.Orientation.Horizontal)
        self.thresh_hold_slider.setRange(0, 100)
        self.thresh_num = QLabel("Confidence Value: 0")
        self.thresh_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thresh_hold_slider.valueChanged.connect(self.update_confidence)
        self.thresh_hold_slider.setValue(0)

        confidence_col = QVBoxLayout()
        confidence_col.setSpacing(8)
        confidence_col.addWidget(self.thresh_num)
        confidence_col.addWidget(self.thresh_hold_slider)
        controls_row.addLayout(confidence_col, 2)

        content_layout.addLayout(controls_row)

        # Add button for exporting data
        self.exportData = QPushButton('Export Data')
        self.exportData.clicked.connect(self.start_data_extraction)
        self.exportData.setMinimumHeight(44)
        self.exportData.setMinimumWidth(220)
        content_layout.addWidget(self.exportData, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(content, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

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
        from Helper_Classes.window_utils import pick_directory
        self.drive = pick_directory(self)

    def menu_window(self):
        from Window_Screen_Classes.home_menu import MenuWindow
        self.imageWindow = MenuWindow(self.drive)
        self.imageWindow.show()
        self.close()

    def show_info_dialog(self):
        show_help_dialog(
        self,
        sections=[
            (
                "Data Export Tips",
                "- Select a time interval to specify the frequency of image extraction\n"
                "- A confidence value of zero will include all model predictions\n"
                "- Decreasing the time interval will increase the processing time\n"
            ),
        ],
        window_title="Help and Tips",
        )
        
