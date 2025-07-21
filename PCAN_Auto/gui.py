import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTextEdit
import can_tool  # Import the original can_tool script
import can

class CanToolGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.bus = None
        self.initUI()
        self.init_can_bus()

    def initUI(self):
        self.setWindowTitle('CAN Tool')

        # Layouts
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()

        # Widgets
        self.id_input = QLineEdit(self)
        self.id_input.setPlaceholderText("Enter Arbitration ID (e.g., 0x123)")
        self.send_button = QPushButton('Send', self)
        self.status_display = QTextEdit(self)
        self.status_display.setReadOnly(True)

        # Add widgets to layouts
        hbox.addWidget(self.id_input)
        hbox.addWidget(self.send_button)
        vbox.addLayout(hbox)
        vbox.addWidget(self.status_display)

        self.setLayout(vbox)

        # Connect signals
        self.send_button.clicked.connect(self.send_message_action)

    def init_can_bus(self):
        """Initializes the CAN bus."""
        try:
            self.bus = can_tool.get_bus()
            self.status_display.append("CAN bus initialized successfully.")
            self.status_display.append(f"Channel info: {self.bus.channel_info}")
        except Exception as e:
            self.status_display.append(f"Error initializing CAN bus: {e}")

    def send_message_action(self):
        """Handles the send button click event."""
        id_text = self.id_input.text()
        if not id_text:
            self.status_display.append("Error: Arbitration ID is required.")
            return

        try:
            arbitration_id = int(id_text, 0)
        except ValueError:
            self.status_display.append("Error: Invalid arbitration ID.")
            return

        if self.bus:
            try:
                message = can.Message(
                    arbitration_id=arbitration_id,
                    data=[0, 0, 0, 0, 0, 0, 0, 0],
                    is_extended_id=False
                )
                self.bus.send(message)
                self.status_display.append(f"Message sent: ID={hex(arbitration_id)}")
            except can.CanError as e:
                self.status_display.append(f"Error sending message: {e}")
        else:
            self.status_display.append("Error: CAN bus not initialized.")

    def closeEvent(self, event):
        """Shuts down the CAN bus when the application is closed."""
        if self.bus:
            self.bus.shutdown()
        event.accept()

def main():
    """Main function to run the GUI."""
    app = QApplication(sys.argv)
    ex = CanToolGUI()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
