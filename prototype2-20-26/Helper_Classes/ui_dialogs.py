from PySide6.QtWidgets import QMessageBox


# Confirm action (generic so we can use it in multiple files)
def confirm_action(parent, title, message, prompt_enabled=True):
    if not prompt_enabled:
        return True

    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.Yes | QMessageBox.No,  # type: ignore
    )
    return reply == QMessageBox.Yes  # type: ignore

# Show info (this is mainly for image_viewer for seeing the popups after confirmation)
def show_info(parent, title, message):
        if not parent.confirm_toggle.isChecked():
            return

        QMessageBox.information(
            parent,
            title,
            message
        )

# No Popups (this is used when changing directories to something without images inside)
def show_no_images_popup(parent):
        msg = QMessageBox(parent)
        msg.setIcon(QMessageBox.Information) # type: ignore
        msg.setWindowTitle("No Images")
        msg.setText("This folder contains no images.\n Select a new working directory.")
        msg.setStandardButtons(QMessageBox.Ok) # type: ignore
        msg.exec()