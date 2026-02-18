from PySide6.QtWidgets import QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QApplication
from PySide6.QtCore import Qt
from image_loader import ImageLoader
from folder_selector import FolderSelector
from pathlib import Path

#create a main window class so we can customize our window
class MainWindow(QMainWindow):
    def __init__(self):
        # Standard window setup
        super().__init__()

        # Set a title
        self.setWindowTitle("Trailcam App")
        self.resize(400, 400)

        # Create a label
        self.label = QLabel()

        # Create an input field that updates label
        self.input = QLineEdit()
        self.input.textChanged.connect(self.label.setText)
        
        # # Create a button
        # self.button = QPushButton("Select image")
        # # Connect button to slot
        # self.button.clicked.connect(self.the_button_was_clicked)

        self.loader = ImageLoader() #load in another class from another file
        self.loader.image_loaded.connect(self.display_image) #connect signal to slot

        self.folder_selector = FolderSelector()
        self.folder_selector.directory_confirmed.connect(self.load_directory)

        # Buttons to use 
        self.next_btn = QPushButton("Next Image")
        self.prev_btn = QPushButton("Previous Image")
        self.change_dir_btn = QPushButton("Change Directory")

        # Connect buttons to slots
        self.next_btn.clicked.connect(self.loader.next_image)
        self.prev_btn.clicked.connect(self.loader.prev_image)
        self.change_dir_btn.clicked.connect(self.show_folder_selector)

        # self.setFixedSize(QSize(400, 300))

        # Note: You must use self. to make these accessible in other methods
        # or to check their state later, otherwise they are just local variables

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.change_dir_btn)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

        # Start by showing folder selector
        self.show_folder_selector()
    
    def show_folder_selector(self):
        #hide main window and show folder selector
        self.hide()
        self.folder_selector.show()

    def load_directory(self, path: Path):
        #load directory, show main window
        self.folder_selector.hide()
        self.loader.image_files.clear()  # clear previous images
        self.loader.load_directory(path)
        self.show()


    # This is called a slot, which is a function that is called in response to a signal
    # Basically, what happens when the button is clicked
    # def the_button_was_clicked(self):
    #     print("Clicked!")
    #     self.loader.load_image(self)

    def display_image(self, pixmap):
        #set label to pixmap, scale to fit max size of 600x600
        scaled_pixmap = pixmap.scaled(600, 600, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(scaled_pixmap)

# Create application, [] passes in an empty list (can also do sys.argv for command line args)
app = QApplication([])

# Create main window (folder selector will be shown first via __init__)
window = MainWindow()

# Start app 
app.exec()