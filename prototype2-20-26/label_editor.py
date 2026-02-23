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
    QWidget
)

from PySide6.QtCore import Qt
import qtawesome as qta

class LabelEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("Edit Labels")
        # Here you would add widgets to edit the label, such as QLineEdit for text input
        # and QPushButton to save changes. You would also need to connect the button to a slot that updates the label.

        # window setup
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        self.resize(500, 400)

        # Left panel
        left_panel = QVBoxLayout()
        self.label_list = QListWidget()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search labels...")
        self.search_box.setClearButtonEnabled(True)
        left_panel.addWidget(self.search_box)
        left_panel.addWidget(self.label_list)

        # Right panel - top bar
        right_panel = QVBoxLayout()
        top_bar = QHBoxLayout()

        self.add_button = QPushButton()
        self.add_button.setIcon(qta.icon('fa6s.plus'))
        self.add_button.setToolTip('Add Label')
        top_bar.addStretch()
        top_bar.addWidget(self.add_button)

        # Right panel - stacked widget with content
        self.stack = QStackedWidget()

        # View selected label, edit label
        self.selected_label = QLabel("No label selected")
        self.selected_label.setAlignment(Qt.AlignCenter)
        self.stack.addWidget(self.selected_label)

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

        
        right_panel.addLayout(top_bar)
        right_panel.addWidget(self.stack, stretch=1)

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

    def load_labels(self):
        label_file = "../classes.txt"
        try:
            with open(label_file, "r") as f:
                for line in f:
                    label = line.strip()
                    if label:
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

    def save_to_txt(self, new_label):
        with open("../classes.txt", "r") as f: #read
            labels = [line.strip() for line in f if line.strip()]

        labels.append(new_label)
        labels.sort(key=lambda x: x.lower())

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

        # Extract just the label names and find insertion position
        insert_pos = len(name_lines)  # default to end
        for i, (line_idx, line) in enumerate(name_lines):
            label = line.split(": ", 1)[1]
            if new_label.lower() < label.lower():
                insert_pos = i
                break

        # Rebuild all labels with correct indices after insertion
        names = [line.split(": ", 1)[1] for _, line in name_lines]
        names.insert(insert_pos, new_label)
        for i, (line_idx, line) in enumerate(name_lines):
            lines[line_idx] = f"  {i}: {names[i]}"

        # Insert the new label line after the last existing name line TODO: change this
        last_line_idx = name_lines[-1][0]
        lines.insert(last_line_idx + 1, f"  {len(name_lines)}: {names[-1]}")
        # Fix the last existing line which got shifted
        lines[last_line_idx] = f"  {len(name_lines) - 1}: {names[-2]}"

        with open("../data.yaml", "w") as f:
            f.write("\n".join(lines))
    
    def confirm_add(self):
        new_label = self.new_label_input.text().strip()
        if new_label:
            self.label_list.addItem(QListWidgetItem(new_label))
            self.save_to_txt(new_label)
            self.save_to_yaml(new_label)

        self.stack.setCurrentIndex(0) #go back to label viewing

    def cancel_input(self):
        self.stack.setCurrentIndex(0) #go back to label viewing




