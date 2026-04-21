import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGridLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QWidget,
)
from PySide6.QtCore import Qt
from Window_Screen_Classes.home_menu import MenuWindow
from Helper_Classes.nav_bar import NavBar
from Helper_Classes.window_utils import center_on_primary_screen, pick_directory
from pathlib import Path
import platform
import os

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
            new_folder=False,
            model_selector=False,
            training_status=False,
            info_btn=False
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
        self.ensure_delete_folder()
        self.nextWindow = MenuWindow(self.dir_name_edit.text())
        self.nextWindow.show()
        self.close()

    def center_window(self):
        center_on_primary_screen(self)


    def ensure_delete_folder(self):
        # 1. Get the path from the UI and resolve it
        input_path = Path(self.dir_name_edit.text()).resolve()
        
        if platform.system() == "Windows":
            # Windows: The 'anchor' is the drive letter (e.g., D:\)
            drive_root = Path(input_path.anchor)
        else:
            # Mac/Linux: Find the mount point (e.g., /Volumes/ExternalDrive)
            drive_root = input_path
            while not os.path.ismount(drive_root) and drive_root.parent != drive_root:
                drive_root = drive_root.parent

        # 2. Create the target path at that specific root
        target_path = drive_root / "Recently Deleted"
        
        try:
            target_path.mkdir(parents=True, exist_ok=True)
            print(f"Verified: {target_path}")
        except Exception as e:
            print(f"Error creating folder on {platform.system()}: {e}")



if __name__ == '__main__':
    # Look for training in the background 
    if "--training-subprocess" in sys.argv:
        from Training_Classes.training_subprocess import main as training_subprocess_main

        sys.exit(training_subprocess_main())

    app = QApplication(sys.argv)
    window = MainWindow()

    try:
        import pyi_splash
        # Close the splash screen
        pyi_splash.close()
    except ImportError:
        pass

    app.setStyleSheet("""
        /* ── Base surfaces ── */
        QMainWindow, QDialog {
            background: #202020;
        }
        QWidget {
            background: #2b2b2b;
            color: #e5e5e5;
            font-size: 13px;
        }

        /* ── Buttons ── */
        QPushButton {
            background: #3d3d3d;
            color: #e5e5e5;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 4px 10px;
        }
        QPushButton:hover    { background: #4d4d4d; }
        QPushButton:pressed  { background: #272727; }
        QPushButton:checked  { background: #0078d4; color: #ffffff; border-color: #0078d4; }
        QPushButton:disabled { background: #2b2b2b; color: #6a6a6a; border-color: #3a3a3a; }

        /* ── Text inputs ── */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background: #1e1e1e;
            color: #e5e5e5;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 3px 6px;
            selection-background-color: #0078d4;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #0078d4;
        }

        /* ── Combo box ── */
        QComboBox {
            background: #3d3d3d;
            color: #e5e5e5;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 3px 8px;
        }
        QComboBox:hover { background: #4d4d4d; }
        QComboBox QAbstractItemView {
            background: #2b2b2b;
            color: #e5e5e5;
            selection-background-color: #0078d4;
            border: 1px solid #555555;
            font-size: 13px;
        }

        /* ── Lists ── */
        QListWidget {
            background: #1e1e1e;
            color: #e5e5e5;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
        }
        QListWidget::item:selected  { background: #0078d4; color: #ffffff; }
        QListWidget::item:hover     { background: #3a3a3a; }

        /* ── Group box ── */
        QGroupBox {
            border: 1px solid #4a4a4a;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 6px;
            color: #b0b0b0;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 4px;
            color: #b0b0b0;
        }

        /* ── Tabs ── */
        QTabWidget::pane {
            border: 1px solid #3a3a3a;
            background: #2b2b2b;
        }
        QTabBar::tab {
            background: #3d3d3d;
            color: #b0b0b0;
            padding: 5px 12px;
            border: 1px solid #3a3a3a;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected { background: #2b2b2b; color: #e5e5e5; }
        QTabBar::tab:hover    { background: #4d4d4d; }

        /* ── Scrollbars ── */
        QScrollBar:vertical {
            background: #2b2b2b;
            width: 10px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            border-radius: 5px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover { background: #707070; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            background: #2b2b2b;
            height: 10px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background: #555555;
            border-radius: 5px;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover { background: #707070; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

        /* ── Progress bar ── */
        QProgressBar {
            background: #1e1e1e;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            text-align: center;
            color: #e5e5e5;
        }
        QProgressBar::chunk { background: #0078d4; border-radius: 4px; }

        /* ── Checkbox ── */
        QCheckBox { color: #e5e5e5; spacing: 6px; }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #555555;
            border-radius: 3px;
            background: #3d3d3d;
        }
        QCheckBox::indicator:checked { background: #0078d4; border-color: #0078d4; }

        /* ── Splitter handle ── */
        QSplitter::handle { background: #3a3a3a; }
        QSplitter::handle:horizontal { width: 4px; }
        QSplitter::handle:vertical   { height: 4px; }

        /* ── Nav bar (override base QWidget background) ── */
        #navBar {
            background: #1f2a36;
            border-bottom: 1px solid #3b4b5f;
        }
        #navBar QPushButton {
            background: transparent;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 2px 6px;
        }
        #navBar QPushButton:hover    { background: #4e606f; }
        #navBar QPushButton:pressed  { background: #1d2a37; }
        #navBar QPushButton:disabled { background: transparent; color: #6a7a87; }
    """)
    
    sys.exit(app.exec())
