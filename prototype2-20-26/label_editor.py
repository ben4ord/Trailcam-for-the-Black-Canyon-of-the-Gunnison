from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QWidget,
    QMessageBox
)

from PySide6.QtCore import Qt
import qtawesome as qta
from nav_bar import NavBar
from label_store import LabelStore

class LabelEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.label_store = LabelStore()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setContentsMargins(0, 0, 0, 0)

        # -----------------------------
        # Window Setup
        # -----------------------------
        outer_layout = QVBoxLayout(self)
        self.setLayout(outer_layout)
        layout = QHBoxLayout()

        self.resize(500, 400)

        # nav bar
        self.nav_bar = NavBar(self)
        self.nav_bar.set_button_visibility(
            home=False,
            update_labels=False,
            new_folder=False,
            training_status=False,
        )

        outer_layout.addWidget(self.nav_bar)
        outer_layout.addLayout(layout)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # -----------------------------
        # Left Panel
        # -----------------------------
        left_panel = QVBoxLayout()
        self.label_list = QListWidget()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search labels...")
        self.search_box.setClearButtonEnabled(True)
        left_panel.addWidget(self.search_box)
        left_panel.addWidget(self.label_list)

        # -----------------------------
        # Right Panel
        # -----------------------------
        right_panel = QVBoxLayout()
        top_bar = QHBoxLayout()

        self.add_button = QPushButton()
        self.add_button.setIcon(qta.icon('fa6s.plus'))
        self.add_button.setToolTip('Add Label')
        top_bar.addStretch()
        top_bar.addWidget(self.add_button)

        # Right panel - stacked widget with content
        self.stack = QStackedWidget()

        #PANEL 1: View labels, select label to edit/delete

        # View selected label, edit label
        selected_label_page = QWidget()
        selected_label_layout = QVBoxLayout(selected_label_page)
        self.stack.addWidget(selected_label_page)

        self.selected_label = QLabel("No label selected")
        self.selected_label.setAlignment(Qt.AlignCenter) # type: ignore
        selected_label_layout.addWidget(self.selected_label)

        # Edit/Delete buttons
        self.edit_button = QPushButton()
        self.edit_button.setIcon(qta.icon('fa6s.pen-to-square'))
        self.edit_button.setToolTip('Edit Label')
        self.delete_button = QPushButton()
        self.delete_button.setIcon(qta.icon('fa6s.trash'))
        self.delete_button.setToolTip('Delete Label')
        button_bar_selected_label = QHBoxLayout()
        button_bar_selected_label.addStretch()
        button_bar_selected_label.addWidget(self.edit_button)
        button_bar_selected_label.addWidget(self.delete_button)
        selected_label_layout.addLayout(button_bar_selected_label)

        #PANEL 2: Add new label

        # Add label page
        input_page = QWidget()
        input_layout = QVBoxLayout(input_page)
        self.new_label_input = QLineEdit()
        self.new_label_input.setPlaceholderText("Enter label name...")
        input_layout.addStretch()
        input_layout.addWidget(self.new_label_input)
        input_layout.addStretch()

        # Confirmation buttons
        self.confirm_button = QPushButton("Add")
        self.cancel_button = QPushButton("Cancel")
        button_bar = QHBoxLayout()
        button_bar.addStretch()
        button_bar.addWidget(self.cancel_button)
        button_bar.addWidget(self.confirm_button)
        input_layout.addLayout(button_bar)
        self.stack.addWidget(input_page)

        #PANEL 3: Edit existing label
        edit_page = QWidget()
        edit_layout = QVBoxLayout(edit_page)
        self.edit_label_input = QLineEdit()
        edit_layout.addStretch()
        edit_layout.addWidget(self.edit_label_input)
        edit_layout.addStretch()

        edit_button_bar = QHBoxLayout()
        self.edit_confirm_button = QPushButton("Save")
        self.edit_cancel_button = QPushButton("Cancel")
        edit_button_bar.addStretch()
        edit_button_bar.addWidget(self.edit_cancel_button)
        edit_button_bar.addWidget(self.edit_confirm_button)
        edit_layout.addLayout(edit_button_bar)
        self.stack.addWidget(edit_page)

        
        right_panel.addLayout(top_bar)
        right_panel.addWidget(self.stack, stretch=1)

        # -----------------------------
        # Add Panels to Main, Connect Buttons
        # -----------------------------

        # Add panels to main layout
        layout.addLayout(left_panel)
        layout.addLayout(right_panel, stretch=1)

        # Load labels, connect buttons
        self.load_labels()
        self.label_list.itemClicked.connect(self.on_label_clicked)
        self.search_box.textChanged.connect(self.filter_list)
        self.add_button.clicked.connect(self.show_input)
        self.confirm_button.clicked.connect(self.confirm_add)
        self.cancel_button.clicked.connect(self.cancel_input)
        self.edit_button.clicked.connect(self.edit_label)
        self.delete_button.clicked.connect(self.delete_label)
        self.edit_cancel_button.clicked.connect(self.cancel_input)
        self.edit_confirm_button.clicked.connect(self.confirm_edit)

    # -----------------------------
    # Label Functions
    # -----------------------------

    def load_labels(self):
        labels = self.label_store.read_labels()
        if not labels:
            self.label_list.addItem(QListWidgetItem("No label file found"))
            return

        sorted_labels = sorted(labels, key=lambda x: x.lower())
        for label in sorted_labels:
            self.label_list.addItem(QListWidgetItem(label))

    def on_label_clicked(self, item):
        self.selected_label.setText(item.text())

    def filter_list(self, text):
        text = text.lower()
        for row in range(self.label_list.count()):
            item = self.label_list.item(row)
            item.setHidden(text not in item.text().lower())

    def show_input(self):
        self.new_label_input.clear()
        self.stack.setCurrentIndex(1) #show label input page

    def cancel_input(self):
        self.label_list.setEnabled(True)
        self.stack.setCurrentIndex(0) #go back to label viewing

    def confirm_add(self):
        new_label = self.new_label_input.text().strip()
        if new_label:
            self.label_store.add_label(new_label)
            self.label_list.clear()
            self.load_labels()

        self.stack.setCurrentIndex(0) #go back to label viewing

    def edit_label(self):
        current_item = self.label_list.currentItem() #get currently selected label 
        if not current_item:
            return
        self.edit_label_input.setText(current_item.text()) #set edit label page text
        self.label_list.setEnabled(False) #disable label list to prevent changing incorrect label bug
        self.stack.setCurrentIndex(2) #show edit page

    def confirm_edit(self):
        new_text = self.edit_label_input.text().strip() #get text from edit label input
        current_item = self.label_list.currentItem() #get currently selected label in list (before edit)
        if new_text and current_item:
            old_label = current_item.text()
            self.label_store.update_label(old_label, new_text)
            self.label_list.clear()
            self.load_labels()
            self.selected_label.setText(new_text)
        self.label_list.setEnabled(True)
        self.stack.setCurrentIndex(0)

    def delete_label(self):
        current_item = self.label_list.currentItem()
        if not current_item:
            return
        reply = QMessageBox.question(
            self,
            "Delete Label",
            f"Are you sure you want to delete '{current_item.text()}'?",
            QMessageBox.Yes | QMessageBox.No # type: ignore
        )
        if reply == QMessageBox.Yes: #type: ignore
            self.label_store.remove_label(current_item.text())
            self.label_list.clear()
            self.load_labels()
            self.selected_label.setText("No label selected")



