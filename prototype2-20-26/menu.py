from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton
from image_viewer import ImageLoader

from PySide6.QtCore import Qt
from nav_bar import NavBar

class MenuWindow(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        # ADD container
        self.drive = drive
        self.setGeometry(100, 100, 400, 100)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.nav_bar = NavBar(self)

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
        self.viewImages.clicked.connect(self.next_window)
        layout.addWidget(self.viewImages, 1, 0, 2, 6)

        print("Drive received:")
        print(self.drive)
        print(self.drive)
        self.show()


    def next_window(self):
        self.nextWindow = ImageLoader(self.drive)
        self.nextWindow.show()
        self.close()


        