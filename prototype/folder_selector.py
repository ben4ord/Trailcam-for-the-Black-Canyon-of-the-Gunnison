from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PySide6.QtCore import Signal
from pathlib import Path

class FolderSelector(QWidget):
    directory_confirmed = Signal(Path)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Folder")
        self.setGeometry(100, 100, 400, 120)

        layout = QGridLayout(self)

        self.dir_name_edit = QLineEdit()
        browse_btn = QPushButton("Browse")
        confirm_btn = QPushButton("Confirm Directory")

        browse_btn.clicked.connect(self.open_dir_dialog)
        confirm_btn.clicked.connect(self.confirm_directory)

        layout.addWidget(QLabel("Directory:"), 0, 0)
        layout.addWidget(self.dir_name_edit, 0, 1)
        layout.addWidget(browse_btn, 0, 2)
        layout.addWidget(confirm_btn, 1, 1)

    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            self.dir_name_edit.setText(dir_name)

    def confirm_directory(self):
        if self.dir_name_edit.text():
            self.directory_confirmed.emit(Path(self.dir_name_edit.text()))
