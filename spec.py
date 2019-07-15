from PyQt5.QtWidgets import QApplication
from pygcms.dispspec import MainWindow
import sys

def main():
	 app = QApplication(sys.argv)
	 af = MainWindow()
	 af.show()
	 sys.exit(app.exec_())


if __name__ == '__main__':
	 main()
