import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGridLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QWidget
)

from PySide6.QtCore import Qt

from home_menu import MenuWindow
from nav_bar import NavBar
from window_utils import center_on_primary_screen, pick_directory

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(600, 200)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setContentsMargins(0, 0, 0, 0)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setCentralWidget(central)

        self.nav_bar = NavBar(self)
        self.nav_bar.set_button_visibility(
            home=False,
            update_labels=False,
            new_folder=False
        )
        self.setMenuWidget(self.nav_bar)

        layout = QGridLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # directory selection
        dir_btn = QPushButton('Browse')
        dir_btn.clicked.connect(self.open_dir_dialog)
        self.dir_name_edit = QLineEdit()

        # Add button to next window
        secondaryWindowButton = QPushButton('Next')
        secondaryWindowButton.clicked.connect(self.next_window)
        layout.addWidget(secondaryWindowButton, 0, 0, 1, 1)

        layout.addWidget(QLabel('Directory:'), 1, 0)
        layout.addWidget(self.dir_name_edit, 1, 1, 1, 4)
        layout.addWidget(dir_btn, 1, 5)

        self.show()
        self.center_window()

    def open_dir_dialog(self):
        dir_name = pick_directory(self, "Select a Directory")
        if dir_name:
            path = Path(dir_name)
            self.dir_name_edit.setText(str(path))

    def next_window(self):
        if not self.dir_name_edit.text():
            return

        self.nextWindow = MenuWindow(self.dir_name_edit.text())
        self.nextWindow.show()
        self.close()

    def center_window(self):
        center_on_primary_screen(self)


if __name__ == '__main__':
    if "--training-subprocess" in sys.argv:
        from training_subprocess import main as training_subprocess_main

        sys.exit(training_subprocess_main())

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
