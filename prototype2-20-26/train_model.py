from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from nav_bar import NavBar

class TrainModel(QMainWindow):
    def __init__(self, drive):
        super().__init__()

        self.drive = drive
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
            new_folder=False
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
        self.trainNewModel = QPushButton('Train new Model')
        #self.trainNewModel.clicked.connect(self.train_new_model)
        layout.addWidget(self.trainNewModel, 1, 0, 2, 6)