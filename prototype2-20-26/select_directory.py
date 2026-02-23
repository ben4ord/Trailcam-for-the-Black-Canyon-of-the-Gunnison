import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QGridLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QFileDialog,
)

from PySide6.QtCore import Qt

from menu import MenuWindow
from nav_bar import NavBar

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setGeometry(100, 100, 400, 100)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self.nav_bar = NavBar(self)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # directory selection
        dir_btn = QPushButton('Browse')
        dir_btn.clicked.connect(self.open_dir_dialog)
        self.dir_name_edit = QLineEdit()

        layout.addWidget(self.nav_bar, 0, 0, 1, 6)

        # Add button to next window
        secondaryWindowButton = QPushButton('Next')
        secondaryWindowButton.clicked.connect(self.next_window)
        layout.addWidget(secondaryWindowButton, 1, 0)

        layout.addWidget(QLabel('Directory:'), 2, 0)
        layout.addWidget(self.dir_name_edit, 2, 1)
        layout.addWidget(dir_btn, 2, 2)

        self.show()

    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            path = Path(dir_name)
            self.dir_name_edit.setText(str(path))

    def next_window(self):
        if not self.dir_name_edit.text():
            print("No drive selected")
            return

        self.nextWindow = MenuWindow(self.dir_name_edit.text())
        self.nextWindow.show()
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    app.setStyleSheet("""
        #navBar {
            background-color: #1f2a36;
            border-bottom: 1px solid #3b4b5f;
        }
        #navBar QPushButton {
            background: transparent;
            color: #ffffff;
            border: none;
            padding: 4px 8px;
        }
        #navBar QPushButton:hover {
            background-color: #2f3e4f;
        }
        """)
    
    sys.exit(app.exec())