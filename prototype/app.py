from PySide6.QtWidgets import *
from PySide6.QtCore import *
from image_loader import ImageLoader

#create a main window class so we can customize our window
class MainWindow(QMainWindow):
    def __init__(self):
        # Standard window setup
        super().__init__()

        # Set a title
        self.setWindowTitle("My App")

        # Create a label
        self.label = QLabel()

        # Create an input field that updates label
        self.input = QLineEdit()
        self.input.textChanged.connect(self.label.setText)
        
        # Create a button
        self.button = QPushButton("Select image")
        # Connect button to slot
        self.button.clicked.connect(self.the_button_was_clicked)

        self.setFixedSize(QSize(400, 300))

        # Note: You must use self. to make these accessible in other methods
        # or to check their state later, otherwise they are just local variables

        layout = QVBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.label)
        layout.addWidget(self.button)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

        self.loader = ImageLoader() #load in another class from another file
        self.loader.image_loaded.connect(self.display_image) #connect signal to slot


    # This is called a slot, which is a function that is called in response to a signal
    # Basically, what happens when the button is clicked
    def the_button_was_clicked(self):
        print("Clicked!")
        self.loader.load_image(self)

    def display_image(self, pixmap):
        #set label to pixmap
        self.label.setPixmap(pixmap)
        self.label.setScaledContents(True)

# Create application, [] passes in an empty list (can also do sys.argv for command line args)
app = QApplication([])

# Create main window
window = MainWindow()
window.show()

# Start app 
app.exec()