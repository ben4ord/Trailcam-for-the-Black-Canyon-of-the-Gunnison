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
from torch import layout
from nav_bar import NavBar

class LabelEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__()

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
            new_folder=False
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
        self.selected_label.setAlignment(Qt.AlignCenter)
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

        self.stack.addWidget(selected_label_page)

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
        edit_button_bar.addStretch()
        edit_button_bar.addWidget(self.cancel_button)
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
        self.edit_confirm_button.clicked.connect(self.confirm_edit)

    # -----------------------------
    # Label Functions
    # -----------------------------

    def load_labels(self):
        label_file = "../classes.txt"
        try:
            with open(label_file, "r") as f:
                labels = [line.strip() for line in f if line.strip()]
                sorted_labels = sorted(labels, key=lambda x: x.lower())
                for label in sorted_labels:
                    self.label_list.addItem(QListWidgetItem(label))
        except FileNotFoundError:
            self.label_list.addItem(QListWidgetItem("No label file found"))

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

    def save_to_txt(self, new_label):
        with open("../classes.txt", "r") as f: #read
            labels = [line.strip() for line in f if line.strip()]

        labels.append(new_label)

        with open("../classes.txt", "w") as f:
            f.write("\n".join(labels))
    
    def save_to_yaml(self, new_label):
        with open("../data.yaml", "r") as f:
            data = f.read()
        current_nc = int(data.split("nc: ")[1].split("\n")[0])

        # Update nc
        data = data.replace(f"nc: {current_nc}", f"nc: {current_nc + 1}")

        # Get all label lines and their indices
        lines = data.split("\n")
        name_lines = [(i, line) for i, line in enumerate(lines) if line.startswith("  ") and ": " in line]

        # Extract just the names into a plain list and insert new label alphabetically
        names = [line.split(": ", 1)[1] for _, line in name_lines]
        names.append(new_label)

        # Rebuild the names block with correct indices
        new_name_lines = [f"  {i}: {name}" for i, name in enumerate(names)]

        # Find where old names block starts and ends, replace it entirely
        first_line_idx = name_lines[0][0]
        last_line_idx = name_lines[-1][0]
        lines[first_line_idx:last_line_idx + 1] = new_name_lines

        with open("../data.yaml", "w") as f:
            f.write("\n".join(lines))
    
    def confirm_add(self):
        new_label = self.new_label_input.text().strip()
        if new_label:
            self.label_list.addItem(QListWidgetItem(new_label))
            self.save_to_txt(new_label)
            self.save_to_yaml(new_label)
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
            self.update_txt(old_label, new_text)
            self.update_yaml(old_label, new_text)
            self.label_list.clear()
            self.load_labels()
            self.selected_label.setText(new_text)
        self.label_list.setEnabled(True)
        self.stack.setCurrentIndex(0)

    def update_txt(self, old_label, new_label):
        with open("../classes.txt", "r") as f:
            labels = [line.strip() for line in f if line.strip()] #get list of labels from file
        labels = [new_label if l == old_label else l for l in labels] #replace old label with new label, otherwise keep looping through/keep same
        with open("../classes.txt", "w") as f: #write
            f.write("\n".join(labels))

    def update_yaml(self, old_label, new_label):
        with open("../data.yaml", "r") as f:
            data = f.read()
        lines = data.split("\n") #get lines
        name_lines = [(i, line) for i, line in enumerate(lines) if line.startswith("  ") and ": " in line] #get list of label lines
        names = [line.split(": ", 1)[1] for _, line in name_lines] #get list of labels only
        names = [new_label if n == old_label else n for n in names] #replace old label with new label 
        new_name_lines = [f"  {i}: {name}" for i, name in enumerate(names)] #create new label lines
        first_line_idx = name_lines[0][0] #index of first label line
        last_line_idx = name_lines[-1][0] #index of last label line
        lines[first_line_idx:last_line_idx + 1] = new_name_lines #replace old label lines with new label lines
        with open("../data.yaml", "w") as f: #write
            f.write("\n".join(lines))

    def delete_label(self):
        current_item = self.label_list.currentItem()
        if not current_item:
            return
        reply = QMessageBox.question(
            self,
            "Delete Label",
            f"Are you sure you want to delete '{current_item.text()}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.remove_from_txt(current_item.text())
            self.remove_from_yaml(current_item.text())
            self.label_list.clear()
            self.load_labels()
            self.selected_label.setText("No label selected")

    def remove_from_txt(self, label):
        with open("../classes.txt", "r") as f:
            labels = [line.strip() for line in f if line.strip()] #get list of labels
        filtered_labels = []
        for l in labels:
            if l != label:
                filtered_labels.append(l)
        labels = filtered_labels #create new list without deleted label
        with open("../classes.txt", "w") as f: #write
            f.write("\n".join(labels))

    def remove_from_yaml(self, label):
        with open("../data.yaml", "r") as f:
            data = f.read()
        current_nc = int(data.split("nc: ")[1].split("\n")[0])
        data = data.replace(f"nc: {current_nc}", f"nc: {current_nc - 1}")
        lines = data.split("\n")
        name_lines = [(i, line) for i, line in enumerate(lines) if line.startswith("  ") and ": " in line]
        names = [line.split(": ", 1)[1] for _, line in name_lines]
        filtered_names = []
        for name in names:
            if name != label:
                filtered_names.append(name)
        names = filtered_names #create new list of names without deleted label
        new_name_lines = [f"  {i}: {name}" for i, name in enumerate(names)] #make new lines
        first_line_idx = name_lines[0][0]
        last_line_idx = name_lines[-1][0]
        lines[first_line_idx:last_line_idx + 1] = new_name_lines #replace old lines with new lines based on new indices
        with open("../data.yaml", "w") as f: #write
            f.write("\n".join(lines))




