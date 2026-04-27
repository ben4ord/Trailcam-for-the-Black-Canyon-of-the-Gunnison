from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton
from PySide6.QtCore import Qt

from Window_Screen_Classes.batch_selection_window import BatchWindow
from Helper_Classes.nav_bar import NavBar
from Training_Classes.train_model import TrainModel
from Helper_Classes.window_utils import center_on_primary_screen
from Window_Screen_Classes.export_data_window import ExportWindow
class MenuWindow(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        self.drive = drive

        self.resize(600, 200)

        # This removes the original top navbar since we are using a custom one
        # Without this it adds the new nav bar under the original
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.nav_bar = NavBar(self)
        self.nav_bar.set_button_visibility(
            home=False,
            update_labels=False,
            new_folder=True,
            model_selector=False,
            info_btn=False
        )

        self.nav_bar.newFolderClicked.connect(self.open_dir_dialog)

        # central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # create layout
        outer_layout = QGridLayout(central_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        self.setLayout(outer_layout)

        content_widget = QWidget()
        layout = QGridLayout(content_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(10)

        outer_layout.addWidget(self.nav_bar, 0, 0)
        outer_layout.addWidget(content_widget, 1, 0)

        # Add button to next window
        self.viewImages = QPushButton('View Images')
        self.viewImages.clicked.connect(self.batch_selection_window)
        layout.addWidget(self.viewImages, 0, 0, 1, 6)

        # Add button for training new model
        self.trainModel = QPushButton('Train Model')
        self.trainModel.clicked.connect(self.train_model_window)
        layout.addWidget(self.trainModel, 1, 0, 1, 6)

        # Export CSV with population data
        self.exportData = QPushButton('Export Data')
        self.exportData.clicked.connect(self.export_animal_data)
        layout.addWidget(self.exportData, 2, 0, 1, 6)

        center_on_primary_screen(self)
        self.show()


    def batch_selection_window(self):
        self.imageWindow = BatchWindow(self.drive)
        self.imageWindow.show()
        self.close()

    def train_model_window(self):
        self.imageWindow = TrainModel(self.drive)
        self.imageWindow.show()
        self.close()
    
    def export_animal_data(self):
        self.imageWindow = ExportWindow(self.drive)
        self.imageWindow.show()
        self.close()

    def open_dir_dialog(self):
        from Helper_Classes.window_utils import pick_directory
        self.drive = pick_directory(self)
        
