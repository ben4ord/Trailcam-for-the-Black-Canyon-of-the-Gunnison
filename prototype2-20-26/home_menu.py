from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from image_viewer import ImageLoader
from nav_bar import NavBar
from train_model import TrainModel

class MenuWindow(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        # ADD container
        self.drive = drive
        #self.setGeometry(100, 100, 400, 100)
        self.setGeometry(
            QGuiApplication.primaryScreen().availableGeometry().center().x() - self.width() // 2,
            QGuiApplication.primaryScreen().availableGeometry().center().y() - self.height() // 2,
            self.width(),
            self.height()
        )

        self.resize(600, 200)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.nav_bar = NavBar(self)
        self.nav_bar.set_button_visibility(
            home=False,
            update_labels=False,
            new_folder=True
        )

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

        # Debugging prints
        print("Drive received:")
        print(self.drive)
        print(self.drive)
        self.show()


    def view_image_window(self):
        self.imageWindow = ImageLoader(self.drive)
        self.imageWindow.show()
        self.close()

    def train_model_window(self):
        self.imageWindow = TrainModel(self.drive)
        self.imageWindow.show()
        self.close()

        