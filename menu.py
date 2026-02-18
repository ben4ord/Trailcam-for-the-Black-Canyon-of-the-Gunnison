from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton
from image_loader import ImageLoader


class MenuWindow(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        # ADD container
        self.drive = drive
        self.setWindowTitle('Menu')
        self.setGeometry(100, 100, 400, 100)

        # central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # creating layout
        layout = QGridLayout(central_widget)
        self.setLayout(layout)
        
        # Add button to next window
        self.viewImages = QPushButton('View Images')
        self.viewImages.clicked.connect(self.next_window)
        layout.addWidget( self.viewImages)

        print("Drive received:")
        print(self.drive)
        print(self.drive)
        self.show()


    def next_window(self):
        self.nextWindow = ImageLoader(self.drive)
        self.nextWindow.show()
        self.close()


        