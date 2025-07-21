import sys
from PyQt5.QtWidgets import QApplication
from gui import CanToolGUI

def main():
    """Main function to run the GUI."""
    app = QApplication(sys.argv)
    ex = CanToolGUI()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
