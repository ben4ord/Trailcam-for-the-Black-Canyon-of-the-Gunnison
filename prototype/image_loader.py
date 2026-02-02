from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap #Pixmap is used to display images
from PySide6.QtWidgets import QFileDialog #File chooser dialog

class ImageLoader(QObject):
    image_loaded = Signal(QPixmap) #can emit signal named image_loaded with QPixmap type

    def load_image(self, parent=None):
        #getOpenFileName works for one file - getExistingDirectory() will be helpful in future for getting a folder
        path, _ = QFileDialog.getOpenFileName( #call static method to open file dialog, returns path and filter (_)
            #arguments: parent, dialog title, starting directory, file filters
            parent,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif)"
        )

        #if cancelled, path will be empty, exit function
        if not path:
            return

        # get pixmap from path, emit signal with pixmap
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.image_loaded.emit(pixmap)