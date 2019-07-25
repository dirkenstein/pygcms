''' pqt_tableview3.py
explore PyQT's QTableView Model
using QAbstractTableModel to present tabular data
allow table sorting by clicking on the header title

used the Anaconda package (comes with PyQt4) on OS X
(dns)
'''

#coding=utf-8
import json
import os
import operator  # used for sorting
import copy

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import *

"""
Types:
f: float
i: integer
c: choice list (dropdown)
F: file 
d: sublespinbox(float)
p: spinbox (int)
a: string
x: checkbox
n: index column (1..n)
"""
class QDictListEditor(QWidget):
		def __init__(self, dataList, defaultLine, header, theTypes, choices, editables, ranges, saves, *args):
				QWidget.__init__(self, *args)
				# setGeometry(x_pos, y_pos, width, height)
				#self.setGeometry(70, 150, 1326, 291)
				
				self.setWindowTitle("Sequence Editor")

				self.table_model = QDictListTableModel(self, dataList, header, theTypes, editables)
				self.table_view = QTableView()
				self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

				#self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
				self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
				self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
				self.defaultLine = defaultLine
				for x in range(len(header)):
					if theTypes[x] == "c":
						self.table_view.setItemDelegateForColumn(x, ComboDelegate(self,choices[x]))
					elif  theTypes[x] == "p":
						self.table_view.setItemDelegateForColumn(x, SpinDelegate(self,ranges[x]))
					elif  theTypes[x] == "d":
						self.table_view.setItemDelegateForColumn(x, SpinDelegate(self,ranges[x], True))
					elif  theTypes[x] == "F":
						self.table_view.setItemDelegateForColumn(x, FileSelectionDelegate(self, directory=False, save= x in saves))
					if theTypes[x] in ["c", "p", "d"]:
						for row in range( len(dataList) ):
							self.table_view.openPersistentEditor(self.table_model.index(row, x))
				# make combo boxes editable with a single-click:
				
				# bind cell click to a method reference
				self.table_view.clicked.connect(self.showSelection)
				self.table_view.clicked.connect(self.selectRow)

				self.table_view.setModel(self.table_model)
				# enable sorting
				self.table_view.setSortingEnabled(True)

				layout = QVBoxLayout(self)
				self.addButton = QPushButton("+")
				self.addButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
				self.delButton = QPushButton("-")
				self.delButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
				layout.addWidget(self.table_view)
				hbl = QHBoxLayout()
				hbl.addWidget(self.addButton)
				hbl.addWidget(self.delButton)
				hbl.addStretch()
				#hb2 = QHBoxLayout()
				#hbl.addLayout(hb2)
				layout.addLayout(hbl)
				self.addButton.clicked.connect(self.addLine)
				self.delButton.clicked.connect(self.delLines)				
				
				self.setLayout(layout)

		def update_model(self, dataList, header, theTypes, editables):
				self.table_model2 = QDictListTableModel(self, dataList, header, theTypes, editables)
				self.table_view.setModel(self.table_model2)
				self.table_view.update()

		def showSelection(self, item):
				cellContent = item.data()
				# print(cellContent)  # test
				sf = "You clicked on {}".format(cellContent)
				# display in title bar for convenience
				self.setWindowTitle(sf)

		def selectRow(self, index):
				# print("current row is %d", index.row())
				pass
		
		def addLine(self):
				newLine = copy.deepcopy(self.defaultLine)
				#newLine["Line"] = self.table_model.rowCount(self) + 1
				self.table_model.addRow(newLine)
			
		def delLines(self):
				self.table_model.delRows()
		def getModel(self):
				return self.table_model


class ComboDelegate(QItemDelegate):
		def __init__(self, owner, choices):
				super().__init__(owner)
				self.items = choices
		def createEditor(self, parent, option, index):
				self.editor = QComboBox(parent)
				self.editor.addItems(self.items)
				return self.editor
		def paint(self, painter, option, index):
				value = index.data(Qt.DisplayRole)
				#print("pvalue>>:",value)
				style = QApplication.style()
				opt = QStyleOptionComboBox()
				opt.text = str(value)
				opt.rect = option.rect
				style.drawComplexControl(QStyle.CC_ComboBox, opt, painter)
				QItemDelegate.paint(self, painter, option, index)
		def setEditorData(self, editor, index):
				value = index.data(Qt.DisplayRole)
				#print("value>>:",value)
				num = self.items.index(value)
				editor.setCurrentIndex(num)
		def setModelData(self, editor, model, index):
				value = editor.currentText()
				model.setData(index, QVariant(value), Qt.DisplayRole)
		def updateEditorGeometry(self, editor, option, index):
				editor.setGeometry(option.rect)


class SpinDelegate(QItemDelegate):
		def __init__(self, owner, numrange, double=False):
				super().__init__(owner)
				self.numrange = numrange
				self.double = double
		def createEditor(self, parent, option, index):
				if self.double:
					self.editor = QDoubleSpinBox(parent)
					self.editor.setDecimals(self.numrange[3])
				else:
					self.editor = QSpinBox(parent)
				self.editor.setRange(self.numrange[0], self.numrange[1])
				self.editor.setSingleStep(self.numrange[2])
				return self.editor
		def paint(self, painter, option, index):
				value = index.data(Qt.DisplayRole)
				#print("pvalue>>:",value)
				style = QApplication.style()
				opt = QStyleOptionSpinBox()
				opt.text = str(value)
				opt.rect = option.rect
				style.drawComplexControl(QStyle.CC_SpinBox, opt, painter)
				QItemDelegate.paint(self, painter, option, index)
		def setEditorData(self, editor, index):
				value = index.data(Qt.DisplayRole)
				#print("value>>:",value)
				editor.setValue(value)
		def setModelData(self, editor, model, index):
				value = editor.value()
				model.setData(index, QVariant(value), Qt.DisplayRole)
		def updateEditorGeometry(self, editor, option, index):
				editor.setGeometry(option.rect)

class FileSelectionDelegate(QStyledItemDelegate):    
		def __init__(self, owner, directory=True, save=False):
			super().__init__(owner)
			self.isdir = directory
			self.save = save
		def createEditor(self, parent, option, index):
				editor = QFileDialog(parent)
				if self.isdir:
					editor.setFileMode(QFileDialog.Directory)
				#editor.setNameFilter("Method files (*json)")
				if self.save:
					#editor.setFileMode(QFileDialog.AnyFile)
					editor.setAcceptMode(QFileDialog.AcceptSave) 
				editor.setOption(QFileDialog.DontUseNativeDialog, True)      
				#editor.setModal(True)
				editor.filesSelected.connect(
						lambda: editor.setResult(QDialog.Accepted))
				#editor.show()
				return editor    

		def setEditorData(self, editor, index):
				val = index.model().data(index, Qt.DisplayRole)
				fs = val.rsplit(os.path.sep, 1)
				if len(fs) == 2:
						bdir, vdir = fs
				else:
						bdir = "."
						vdir = fs[0]

				editor.setDirectory(bdir)        
				editor.selectFile(vdir)
				#editor.show()        

		def setModelData(self, editor, model, index):
				#print(editor.result())
				if editor.result() == QDialog.Accepted:
						model.setData(index, editor.selectedFiles()[0], QtCore.Qt.EditRole)
		def updateEditorGeometry(self, editor, option, index):
				r = option.rect
				r.setHeight(600)
				r.setWidth(600)            
				editor.setGeometry(r)
			
				
				
				
				
class QDictListTableModel(QAbstractTableModel):
		"""
		keep the method names
		they are an integral part of the model
		"""
		def __init__(self, parent, mylist, header, theTypes,editables,  *args):
				QAbstractTableModel.__init__(self, parent, *args)
				self.mylist = mylist
				self.header = header
				self.change_flag = True
				self.tlist = theTypes
				self.editables = editables
				# self.rowCheckStateMap = {}

		def setDataList(self, mylist):
				self.mylist = mylist
				self.layoutAboutToBeChanged.emit()
				self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
				self.layoutChanged.emit()

		def updateModel(self):
				#self.mylist = dataList
				self.layoutAboutToBeChanged.emit()
				self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
				self.layoutChanged.emit()
		
		def lastSel(self):
			for i in reversed(self.mylist):
				if i["Sel"]: 
					return self.mylist.index(i) +1
			return len(self.mylist)
			
		def addRow(self, line):
			#print (self.lastSel())
			self.mylist.insert(self.lastSel(), line)
			self.renumber()
			self.updateModel()
		
		def delRows(self):
				for i in reversed(self.mylist):
					if i["Sel"]: 
						self.mylist.remove(i)
				self.renumber()
				self.updateModel()
			
		def renumber(self):
			idxs = [self.header[c] for c, t in enumerate(self.tlist) if t == "n"]
			n = 1
			for l in self.mylist:
				for i in idxs:
					l[i] = n
				n += 1
		
		def rowCount(self, parent):
				return len(self.mylist)

		def columnCount(self, parent):
				return len(self.mylist[0])

		def data(self, index, role):
				if not index.isValid():
						return None
				if (self.tlist[index.column()] == "x"):
						value = ""
						#value = self.mylist[index.row()][self.header[index.column()]].text()
						#value = self.mylist[index.row()][self.header[index.column()]]
				else:
						value = self.mylist[index.row()][self.header[index.column()]]
				if role == QtCore.Qt.EditRole:
						return value
				elif role == QtCore.Qt.DisplayRole:
						return value
				elif role == QtCore.Qt.CheckStateRole:
						if self.tlist[index.column()] == "x":
								# print(">>> data() row,col = %d, %d" % (index.row(), index.column()))
								#if self.mylist[index.row()][self.header[index.column()]].isChecked():
								if self.mylist[index.row()][self.header[index.column()]]:
										return QtCore.Qt.Checked
								else:
										return QtCore.Qt.Unchecked

		def headerData(self, col, orientation, role):
				if orientation == Qt.Horizontal and role == Qt.DisplayRole:
						return self.header[col]
				return None

		def sort(self, col, order):
				"""sort table by given column number col"""
				# print(">>> sort() col = ", col)
				if self.tlist[col] != "x":
						self.layoutAboutToBeChanged.emit()
						self.mylist = sorted(self.mylist, key=operator.itemgetter(self.header[col]))
						if order == Qt.DescendingOrder:
								self.mylist.reverse()
						self.layoutChanged.emit()

		def flags(self, index):
				if not index.isValid():
						return None
				# print(">>> flags() index.column() = ", index.column())
				if self.tlist[index.column()] ==  "x":
						# return Qt::ItemIsEnabled | Qt::ItemIsSelectable | Qt::ItemIsUserCheckable
						return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable
				elif index.column() in self.editables and self.tlist[index.column()] != "n":
						return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

				else:
						return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

		def setData(self, index, value, role):
				if not index.isValid():
						return False
				# print(">>> setData() role = ", role)
				# print(">>> setData() index.column() = ", index.column())
				# print(">>> setData() value = ", value)
				if role == QtCore.Qt.CheckStateRole and self.tlist[index.column()] == "x":
						#print(">>> setData() role = ", role)
						#print(">>> setData() index.column() = ", index.column())
						if value == QtCore.Qt.Checked:
								#self.mylist[index.row()][self.header[index.column()]].setChecked(True)
								self.mylist[index.row()][self.header[index.column()]] = True
								#self.mylist[index.row()][index.column()].setText("A")
								# if studentInfos.size() > index.row():
								#     emit StudentInfoIsChecked(studentInfos[index.row()])     
						else:
								#self.mylist[index.row()][self.header[index.column()]].setChecked(False)
								self.mylist[index.row()][self.header[index.column()]] = False
								#self.mylist[index.row()][index.column()].setText("B")
				elif self.tlist[index.column()] in  ["i", "f","c", "p", "d", "s","F", "n"]:
						#print(">>> setData() role = ", str(role))
						#print(">>> setData() index.column() = ", index.column())
						#print(">>> setData() value = ", value)
						self.mylist[index.row()][self.header[index.column()]] = value
				#print(">>> setData() index.row = ", index.row())
				#print(">>> setData() index.column = ", index.column())
				self.dataChanged.emit(index, index)
				return True

def getSequenceEditorWindow(seqlist):
	header = ["Sel", "Line", "Location", "Injector", "SampleName", "Method","SampleType", "DataFile", 
		"SampleAmount", "ISTDAmount", "Multiplier", "Dilution", "InjVolume"]
	sampleTypes = ["Sample", "Blank","Calibration", "Keyword", "QC", "RearSamp", "RearCal"]
	defline={
					"Sel":False,
					"Line": 1,
					"Location": 1,
					"Injector": 1,
					"SampleName": "",
					"Method": "",
					"SampleType": "Sample",
					"DataFile": "",
					"SampleAmount": 0.0,
					"ISTDAmount": 0.0,
					"Multiplier": 1,
					"Dilution": 1,
					"InjVolume": 1
			}

	for s in seqlist:
		s.update ({"Sel": False})
	theTypes = ["x", "n", "p", "p", "s", "F", "c", "F", "d", "d", "d", "d", "p"] 
	theChoices = { 6: sampleTypes }
	editables = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  
	defFloatRange = [0, 1000, 0.01, 5]
	theRanges = { 2: [1, 100, 1], 3: [1, 2, 1], 8:defFloatRange, 9:defFloatRange, 
		10:defFloatRange, 11:defFloatRange, 12:[1, 10, 1]}
	theSaves = [7]
	return QDictListEditor(seqlist, defline, header, theTypes, theChoices, editables, theRanges, theSaves )

if __name__ == '__main__':
		app = QApplication([])
		# Process a JSON file to create this data
		f = open ("sequence.json", "r")
		seqs = f.read()
		seq = json.loads(seqs)
		seqlist = seq['Sequence']

		win = getSequenceEditorWindow(seqlist)
		win.show()
		app.exec_()