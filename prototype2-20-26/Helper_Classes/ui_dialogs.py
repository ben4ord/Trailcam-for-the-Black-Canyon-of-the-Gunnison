from PySide6.QtWidgets import QMessageBox
from html import escape


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


def show_help_dialog(parent, sections, window_title="Help"):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)  # type: ignore
    msg.setWindowTitle(window_title)
    msg.setStandardButtons(QMessageBox.Ok)  # type: ignore

    parts = []
    for header, body in sections:
        sec_header = escape(header)
        sec_body = escape(body).replace("\n", "<br>")
        parts.append(f"<p><b>{sec_header}</b><br>{sec_body}</p>")

    # Key change here:
    msg.setText("")  # keeps main text empty (no bold block)
    msg.setInformativeText("".join(parts))  # normal-weight content

    msg.exec()