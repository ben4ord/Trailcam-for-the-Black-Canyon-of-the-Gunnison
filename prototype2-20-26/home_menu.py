from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton
from PySide6.QtCore import Qt

from image_viewer import ImageLoader
from nav_bar import NavBar
from train_model import TrainModel
from window_utils import center_on_primary_screen

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
            new_folder=True
        )

        self.nav_bar.newFolderClicked.connect(self.open_dir_dialog)

        # central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # creating layout
        layout = QGridLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addWidget(self.nav_bar, 0, 0, 1, 6)
        
        # Add button to next window
        self.viewImages = QPushButton('View Images')
        self.viewImages.clicked.connect(self.view_image_window)
        layout.addWidget(self.viewImages, 1, 0, 2, 6)

        # Add button for training new model
        self.trainModel = QPushButton('Train Model')
        self.trainModel.clicked.connect(self.train_model_window)
        layout.addWidget(self.trainModel, 2, 0, 2, 6)

        center_on_primary_screen(self)
        self.show()


    def view_image_window(self):
        self.imageWindow = ImageLoader(self.drive)
        self.imageWindow.show()
        self.close()

    def train_model_window(self):
        self.imageWindow = TrainModel(self.drive)
        self.imageWindow.show()
        self.close()

    def open_dir_dialog(self):
        from window_utils import pick_directory
        self.drive = pick_directory(self)
        