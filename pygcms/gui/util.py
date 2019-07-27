from PyQt5.QtCore import QFileInfo

def strippedName(fullFileName):
			return QFileInfo(fullFileName).fileName()