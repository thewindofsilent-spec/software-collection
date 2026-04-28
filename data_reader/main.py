import sys
from PySide6.QtWidgets import QApplication
from models import DataModel
from views import MainWindow
from controllers import DataController


def main():
    app = QApplication(sys.argv)

    model = DataModel()
    view = MainWindow()
    controller = DataController(model, view)

    view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
