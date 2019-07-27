"""
PyQt5 GUI appliaction for contorlling an HP 5890/5971 GC/MS system
Dirk Niggemann <dirk.niggemann@gmail.com>
License: MIT
Last modified: 16.07.2019
"""
import sys, os, random
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import json

import pygcms.msfile.msfileread as msfr
from pyqt_led import Led
import pygcms.msfile.tune2meth as tune2meth
import pygcms.msfile.readspec as readspec

import pygcms.calc.putil as putil
import numpy as np
import pandas
import scipy
import scipy.interpolate

from pygcms.gui.qdictparms import QParamArea, QStatusArea
from pygcms.gui.qdictionarytree import DictionaryTreeWidget
from pygcms.gui.qdictlisteditor import QDictListEditor
import pygcms.gui.util as gutil 

from pygcms.device.specthreads import threadRunner, initThread, statusThread, scanThread, tripleScanThread, runProgressThread
import copy

class MainWindow(QMainWindow):
		MaxRecentFiles = 5
		logline = pyqtSignal(str)

		count = 0
		def __init__(self, parent=None):
				QMainWindow.__init__(self, parent)
				self.setWindowTitle('5971 Spectrum Control')
				self.recentFileActs = []
				
				self.scanWindow = None
				self.tuningWindow = None
				self.tuning_mdi = None
				self.scan_mdi = None
				self.methodWindow = None
				self.method_mdi = None
				self.instWindow = None
				self.inst_mdi = None
				self.logWindow = None
				self.log_mdi = None			
				self.logText= None	
				self.method = None
				self.sequence = None
				self.seqname = ''
				self.tuning_modified = False
				self.method_modified = False
				self.sequence_modified = False
				self.devs = None
				self.loadparam()
				self.create_recent_files()
				self.create_menu()
				self.updateRecentFileActions()

				self.create_main_frame()
				self.create_status_bar()
				#self.loadpath = 'c:\\users\\dirk\\Desktop\\pyspec'
				#self.rmthost = '192.168.29.102'
				self.rmthost=''
				self.loadpath=''
				self.rmtport=18812
				cdefs = {
					"Enabled": False,
					"Host":"",
					"Port": 18812,
					"Path":""
				}
				ddefs = {
					"AutoDetect": True,
					"Board": 0,
					"5971":0,
					"5890":0,
					"7673":0
				}
				self.csettings = QKeySettings('Connection', cdefs, 65535, self.setConn )
				self.dsettings = QKeySettings('Devs', ddefs , 31, self.setDevs)
				self.setDevs()
				self.setConn()
				
		def buildDev(board, addr):
			return 'GPIB'+ str(board) + '::' + str(addr) + '::INSTR'
		
		def setDevs(self):
			board = self.dsettings.getSetting("Board")
			#print (self.dsettings.getSetting("AutoDetect"))
			enbl = self.dsettings.getSetting("AutoDetect")
			devs = [ MainWindow.buildDev(board, self.dsettings.getSetting("5971")),
				MainWindow.buildDev(board, self.dsettings.getSetting("5890")), 
				MainWindow.buildDev(board, self.dsettings.getSetting("7673")) ]
			if enbl:
				self.devs = None
			else:
				self.devs = devs
			if self.scanWindow:
				self.scanWindow.runner.updateDevs(devs)
			if self.tuningWindow:
				self.tuningWindow.runner.updateDevs(devs)
			if self.instWindow:
				self.instWindow.runner.updateDevs(devs)

		def setConn(self):
			if self.csettings.getSetting("Enabled"):
				self.rmthost= self.csettings.getSetting("Host")
				self.loadpath=self.csettings.getSetting("Path")
				self.rmtport=self.csettings.getSetting("Port")
			else:
				self.rmthost=''
				self.loadpath=''
				self.rmtport=18812
			if self.scanWindow:
				self.scanWindow.runner.updateConn(self.rmthost, self.rmtport, self.loadpath)
			if self.tuningWindow:
				self.tuningWindow.runner.updateConn(self.rmthost, self.rmtport, self.loadpath)
			if self.instWindow:
				self.instWindow.runner.updateConn(self.rmthost, self.rmtport, self.loadpath)
	
		def upd_tuning(self, parms):
			self.msparms = parms
			if self.method:
				self.method['Method']['MSParms'] = self.msparms
			self.tuning_modified = True
			
		def save_plot(self):
				file_choices = "PNG (*.png)|*.png"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save file', '', 
												file_choices)
				if path:
					if self.scanWindow:
						self.scanWindow.canvas.print_figure(path, dpi=self.scanWindow.dpi)
						self.statusBar().showMessage('Saved to %s' % path, 2000)
					else:
						self.statusBar().showMessage('No plot to save...', 2000)

		def save_tuning(self):
				file_choices = "JSON (*.json)|*.json"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save tuning file', '', 
												file_choices)
				if path:
					self.saveTunFile(path)
					
		def load_tuning(self):
				file_choices = "JSON (*.json);Tuning (*.U);All Files (*)"
				
				path, choices = QFileDialog.getOpenFileName(self, 
												'Load tuning file', '', 
												file_choices)
				if path:
					self.loadFile(path)

		def save_method(self):
				file_choices = "JSON (*.json)|*.json"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save method file', '', 
												file_choices)
				if path:
					self.saveMethFile(path)

		def load_method(self):
				file_choices = "JSON (*.json);;All Files (*)"
				
				path, choices = QFileDialog.getOpenFileName(self, 
												'Load method file', '', 
												file_choices)
				if path:
						self.loadFile(path)

		def save_sequence(self):
				file_choices = "JSON (*.json)|*.json"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save sequence file', '', 
												file_choices)
				if path:
					self.saveSeqFile(path)

		def load_sequence(self):
				file_choices = "JSON (*.json);;All Files (*)"
				
				path, choices = QFileDialog.getOpenFileName(self, 
												'Load sequnce file', '', 
												file_choices)
				if path:
						self.loadFile(path)
	
		def upd_parms(self):
			if self.methodWindow:
				self.updMethodParams()		
			if self.scanWindow:
				self.updScanParams()
			if self.tuningWindow:
				self.updTuningParams()
			if self.instWindow:
				self.updInstParams()
				self.updSeqParams()
				
		def saveTunFile(self, path):
			try:
				f = open(path, "w")
				f.write(json.dumps({"MSParms" : self.msparms}, indent=4))
				f.close()
			except Exception as e:
				self.statusBar().showMessage('Failed to save %s : %s' % (path, str(e)), 4000)
				return
			self.statusBar().showMessage('Saved to %s' % path, 2000)
			self.tuning_modified = False
			
		def saveMethFile(self, path):
			if self.method:
				try:
					f = open(path, "w")
					f.write(json.dumps(self.method, indent=4))
					f.close()
				except Exception as e:
					self.statusBar().showMessage('Failed to save %s : %s' % (path, str(e)), 4000)
					return
				self.statusBar().showMessage('Saved to %s' % path, 2000)
				self.tuning_modified = False
				self.method_modified = False
			else:
				self.statusBar().showMessage('No method to save...', 2000)
		def loadFile(self, path):
			if path.endswith(".json"): 
				try:
					f = open(path, "r")
					parms = f.read()
					f.close()
				except Exception as e:
					self.statusBar().showMessage('Failed to load %s : %s' % (path, str(e)), 4000)
					return
				jparms = json.loads(parms)
				if "Method" in jparms:
					ftype = "Method File"
					self.method  = jparms
					self.msparms = self.method['Method']['MSParms']
					self.tuning_modified = False
					self.method_modified = False
					self.methpath = path
					self.methname = gutil.strippedName(self.methpath)
					self.upd_parms()
				elif "MSParms" in jparms:
					ftype = "Tuning File"
					self.upd_tuning(jparms['MSParms'])
					self.tuning_modified = False
					self.tunpath = path
					self.upd_parms()
				elif "Sequence" in jparms:
					ftype = "Sequence File"
					self.sequence = jparms
					self.sequence_modified = False
					self.seqpath = path
					self.seqname = gutil.strippedName(self.seqpath)
					self.upd_parms()
				else:
					self.statusBar().showMessage('Unknown file %s : %s' % (path, ' '.join(jparms.keys()) ), 4000)
					return
			elif path.endswith(".U"):
				try:
					f = open(path, "rb")
					bparms = f.read()
					f.close()
				except Exception as e:
					self.statusBar().showMessage('Failed to load %s : %s' % (path, str(e)), 4000)
					return
				ftype = "Chemstation Tuning File"
				lparms = copy.deepcopy(self.msparms)
				tparms = lparms['Tuning']
				mparms = lparms['Mass']
				tune2meth.updatefromTuning(bparms, tparms)
				tune2meth.updatefromTuning(bparms, mparms)
				self.upd_tuning(lparms)
				pre, ext = os.path.splitext(path)
				self.tunpath = pre + '.json'
				self.upd_parms()
			self.setCurrentFile(path)
			self.statusBar().showMessage('Loaded %s : %s' % (ftype, path), 2000)
				

		def saveSeqFile(self, path):
			if self.sequence:
				try:
					f = open(path, "w")
					f.write(json.dumps(self.sequence, indent=4))
					f.close()
				except Exception as e:
					self.statusBar().showMessage('Failed to save %s : %s' % (path, str(e)), 4000)
					return
				self.statusBar().showMessage('Saved to %s' % path, 2000)
				self.sequence_modified = False
			else:
				self.statusBar().showMessage('No sequence to save...', 2000)

		
		def save_spectrum(self):
				file_choices = "BIN (*.bin)|*.bin"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save file', '', 
												file_choices)
				if path:
					if self.scanWindow:
						f = open(path, "w+b");
						f.write(self.scanWindow.spectrum[0].getData())
						f.close()
					self.statusBar().showMessage('No spectrum to save...', 2000)

		
		def load_spectrum(self):
				file_choices = "BIN (*.bin);;All Files (*)"
				
				path, choices = QFileDialog.getOpenFileName(self, 
												'Load file', '', 
												file_choices)
				if path:
					if self.scanWindow:
						#self.canvas.print_figure(path, dpi=self.dpi)
						self.scanWindow.spectrum = [readspec.FileSpec(path)]
						self.statusBar().showMessage('Loaded %s' % path, 2000)
						self.scanWindow.on_draw()
					else:
						self.statusBar().showMessage('No scan window...', 2000)

		
		def on_about(self):
				msg = """ 
 *          PyGCMS 0.2			
 *HP 5890/ 5971 GC/MS control program:
 *Pretty much implements all the features 
 *In the Diagnostics/Vacuum Control Screen
 *Obviously needs a 5971 connected
 *on a GPIB bus accessible to PyVISA
 *can also control a 5890 and 7673 autosampler
 *  (C) 2019 Dirk Niggemann
"""
				QMessageBox.about(self, "About PyGCMS", msg.strip())
	
	
		def loadparam(self):
				fl = "parms.json"
				f = open(fl, "r")
				tparms = f.read()
				f.close()
				self.msparms = json.loads(tparms)['MSParms']
				self.tunpath = fl

		def tune_window(self):
			if not self.tuningWindow:
				MainWindow.count = MainWindow.count+1
				sub = QMdiSubWindow()
				self.setDevs()
				self.setConn()
				submain = QTuneWindow(sub, self, params=self.msparms, devs=self.devs, 
					host=self.rmthost, lpath=self.loadpath, port=self.rmtport)
				sub.setWidget(submain)
				sub.setWindowTitle(str(MainWindow.count) + ": " + "Tuning")
				self.mdi.addSubWindow(sub)
				sub.show()
				self.tuningWindow = submain
				self.tuning_mdi = sub
			else:
				self.tuning_mdi.show()
				self.tuningWindow.show()
			if self.scan_mdi:
				self.scan_mdi.close()
			if self.inst_mdi:
				self.inst_mdi.close()
		def scan_window(self):
			if not self.scanWindow:
				MainWindow.count = MainWindow.count+1
				sub = QMdiSubWindow()
				self.setDevs()
				self.setConn()
				#print(self.devs)
				submain = QSpectrumScan(sub, self, params=self.msparms, devs=self.devs, 
						host=self.rmthost, lpath=self.loadpath, port=self.rmtport)
				sub.setWidget(submain)
				sub.setWindowTitle(str(MainWindow.count) + ": " + "Scan Control")
				self.mdi.addSubWindow(sub)
				sub.show()
				self.scanWindow = submain
				self.scan_mdi = sub
			else:
				self.scan_mdi.show()
				self.scanWindow.show()
			if self.tuning_mdi:
				self.tuning_mdi.close()
			if self.inst_mdi:
				self.inst_mdi.close()
		def updMethodParams(self):
			self.methodWindow.load_dictionary(self.method)
		def updScanParams(self):
			self.scanWindow.runner.updateMsParms(self.msparms)
			self.scanWindow.config_area.load_dictionary(self.msparms)
		def updTuningParams(self):
			#print(self.msparms)
			self.tuningWindow.runner.updateMsParms(self.msparms)
			self.tuningWindow.config_area.load_dictionary(self.msparms)
		def updInstParams(self):
			self.instWindow.runner.updateMethod(self.method, self.methname)
		def updSeqParams(self):
			self.instWindow.updateSequence(self.sequence,  self.seqname)
			self.instWindow.runner.updateSequence(self.sequence)
			
	#for s in self.paramTabList:
			#	s.updatepboxes()
		def method_window(self):
			if not self.method:
				self.statusBar().showMessage('Error: No Method Loaded', 10000)
			else:
				path = self.methpath
				meth = self.method['Method']
				MainWindow.count = MainWindow.count+1
				sub = QMdiSubWindow()
				#submain = QScrollArea()
				#sub.setWidget(submain)
				sub.setWindowTitle(str(MainWindow.count) + ": Method : " + gutil.strippedName(path))
				self.tree = DictionaryTreeWidget(meth)
				self.tree.getModel().dataChanged.connect(self.treeUpdated)
				sub.setWidget(self.tree)
				
				#	tabs = QTabWidget()
					
				#	#hbox = QHBoxLayout()
				#	self.paramTabList = []
				#	for heading in meth:
				#		#gbox = QGroupBox(heading)
				#		paramarea = QParamArea(tabs, meth[heading], heading)
				#		#gboxl = QVBoxLayout()
				#		#gboxl.addWidget(paramarea)
				#		#gbox.setLayout(gboxl)
				#		#hbox.addWidget(gbox)
				#		tabs.addTab(paramarea, heading)
				#		self.paramTabList.append(paramarea)
					#submain.setLayout(hbox)
				#	submain.setWidget(tabs)
				self.mdi.addSubWindow(sub)
				#self.methodWindow = submain
				self.methodWindow = self.tree
				self.method_mdi = sub
				sub.show()
		def treeUpdated(self):
			#print("tree updated")
			self.method['Method'] = self.tree.to_dict()
			self.tuning_modified = True
			self.method_modified = True
			self.upd_parms()

		def sequence_window(self):
			if not self.sequence:
				self.statusBar().showMessage('Error: No Sequence Loaded', 10000)
			else:
				path = self.seqpath
				seq = self.sequence['Sequence']
				defn = self.sequence ['Definition']
				MainWindow.count = MainWindow.count+1
				sub = QMdiSubWindow()
				#submain = QScrollArea()
				#sub.setWidget(submain)
				sub.setWindowTitle(str(MainWindow.count) + ": Sequence : " + gutil.strippedName(path))
				sub.setGeometry(70, 150, 1326, 291)
				self.editor = QDictListEditor("Sequence Editor", seq, defn)
				self.editor.getModel().dataChanged.connect(self.seqUpdated)
				sub.setWidget(self.editor)
				
				#	submain.setWidget(tabs)
				self.mdi.addSubWindow(sub)
				#self.methodWindow = submain
				self.sequenceWindow = self.editor
				self.sequence_mdi = sub
				sub.show()
		def seqUpdated(self):
			self.sequence_modified = True
			print("seq updated")
	
		def log_window(self, q):
			if not self.logWindow:
				MainWindow.count = MainWindow.count+1
				self.logText = QPlainTextEdit()
				sub = QMdiSubWindow()
				sub.setWidget(self.logText)
				sub.setWindowTitle("Log: "+str(MainWindow.count))
				self.mdi.addSubWindow(sub)
				sub.show()	
				self.logWindow = self.logText
				self.log_mdi = sub
				self.logline.connect(self.doLog)
			else:
				self.log_mdi.show()
				self.logWindow.show()
		def preferences_window(self, q):
			tabs = {
				"Remote Connection" : self.csettings,
				"Devices": self.dsettings
			}
			prefdlg = QPrefsDialog(tabs, self)
			for t in tabs.keys():
				tabs[t].setParent(prefdlg)
			prefdlg.show()

		def doLog(self, logls):
			if self.logText:
				self.logText.appendPlainText(logls)
	
		def inst_window(self, q):
			if not self.method:
				self.statusBar().showMessage('Error: No Method Loaded', 10000)
			else:
				if not self.instWindow:
					MainWindow.count = MainWindow.count+1
					sub = QMdiSubWindow()
					self.setDevs()
					self.setConn()
					self.instrument = QInstControl(sub, self, self.method, self.sequence, 
							self.methname, self.seqname,
							devs=self.devs, host=self.rmthost, lpath=self.loadpath, port=self.rmtport)
					sub.setWidget(self.instrument)
					sub.setWindowTitle("Instrument: "+str(MainWindow.count))
					self.mdi.addSubWindow(sub)
					sub.show()	
					self.instWindow = self.instrument
					self.inst_mdi = sub
				else:
					self.inst_mdi.show()
					self.instWindow.show()
				if self.tuning_mdi:
					self.tuning_mdi.close()
				if self.scan_mdi:
					self.scan_mdi.close()
		def cascade_window(self, q):
			self.mdi.cascadeSubWindows()

		def tile_window(self, q):
			self.mdi.tileSubWindows()
		
		def create_main_frame(self):
				#self.main_frame = QSpectrumScan(self, self, self.msparms)
				self.mdi = QMdiArea()
				self.setCentralWidget(self.mdi)

		def create_status_bar(self):
				self.status_text = QLabel("PyGCMS 0.2")
				self.progress = QProgressBar(self)
				#self.progress.setGeometry(, 80, 250, 20)
				self.statusBar().addWidget(self.status_text, 1)
				self.statusBar().addWidget(self.progress, 2)
			
		def recentfileaction(self, q):
			action = self.sender()
			if action:
				self.loadFile(action.data())
				
		def setCurrentFile(self, fileName):
				self.curFile = fileName
				#if self.curFile:
				#    self.setWindowTitle("%s - Recent Files" % self.strippedName(self.curFile))
				#else:
				#    self.setWindowTitle("Recent Files")

				settings = QSettings('Muppetastic', 'SpecControl')
				files = settings.value('recentFileList')
				if files is None:
					files = []

				try:
						files.remove(fileName)
				except ValueError:
						pass

				files.insert(0, fileName)
				del files[MainWindow.MaxRecentFiles:]

				settings.setValue('recentFileList', files)

				for widget in QApplication.topLevelWidgets():
						if isinstance(widget, MainWindow):
								widget.updateRecentFileActions()
		
		def updateRecentFileActions(self):
				settings = QSettings('Muppetastic', 'SpecControl')
				files = settings.value('recentFileList')
				if files:
					l = len(files)
				else:
					l = 0
				numRecentFiles = min(l, MainWindow.MaxRecentFiles)

				for i in range(numRecentFiles):
						text = "&%d %s" % (i + 1, gutil.strippedName(files[i]))
						self.recentFileActs[i].setText(text)
						self.recentFileActs[i].setData(files[i])
						self.recentFileActs[i].setVisible(True)

				for j in range(numRecentFiles, MainWindow.MaxRecentFiles):
						self.recentFileActs[j].setVisible(False)

				self.separatorAct.setVisible((numRecentFiles > 0))
				
		def create_recent_files(self):
			for i in range(MainWindow.MaxRecentFiles):
				self.recentFileActs.append(
					QAction(self, visible=False,
					triggered=self.recentfileaction))

					
		def create_menu(self):        
				self.file_menu = self.menuBar().addMenu("&File")
				
				load_file_action = self.create_action("&Load spectrum",
						shortcut="Ctrl+R", slot=self.load_spectrum, 
						tip="Load the spectrum")
						
				save_spectrum_action = self.create_action("&Save spectrum",
						shortcut="Ctrl+S", slot=self.save_spectrum, 
						tip="Save the spectrum")

				save_file_action = self.create_action("&Save plot",
						shortcut="Ctrl+P", slot=self.save_plot, 
						tip="Save the plot")
				load_method_action = self.create_action("&Load Method",
						shortcut=None, slot=self.load_method, 
						tip="Load method parameters")
				save_method_action = self.create_action("&Save Method",
						shortcut=None, slot=self.save_method, 
						tip="Save method parameters")
				load_sequence_action = self.create_action("&Load Sequence",
						shortcut=None, slot=self.load_sequence, 
						tip="Load sequence parameters")
				save_sequence_action = self.create_action("&Save Sequence",
						shortcut=None, slot=self.save_sequence, 
						tip="Save sequence parameters")

				load_tuning_action = self.create_action("&Load Tuning",
						shortcut=None, slot=self.load_tuning, 
						tip="Load tuning parameters")
				save_tuning_action = self.create_action("&Save Tuning",
						shortcut=None, slot=self.save_tuning, 
						tip="Save tuning parameters")
				quit_action = self.create_action("&Quit", slot=self.close, 
						shortcut="Ctrl+Q", tip="Close the application")
				
				self.add_actions(self.file_menu, 
						(load_file_action, save_spectrum_action, save_file_action, 
						load_method_action,save_method_action,
						load_sequence_action,save_sequence_action,
						load_tuning_action, save_tuning_action, None, quit_action))
				self.separatorAct = self.file_menu.addSeparator() 
				self.separatorAct.setVisible(False)
				
				for i in range(MainWindow.MaxRecentFiles):
					self.file_menu.addAction(self.recentFileActs[i])
				
				self.window_menu = self.menuBar().addMenu("&Window")
				
				new_scan_action = self.create_action("&Scan Window", shortcut=None, 
					slot=self.scan_window, 
					tip="Launch spectrum single scan window")
				new_tune_action = self.create_action("&Tuning Window", shortcut=None, 
					slot=self.tune_window, 
					tip="Launch spectrum tuning  window")
				new_instrument_action = self.create_action("&Instrument Window", shortcut=None, 
					slot=self.inst_window, 
					tip="Launch instrument window")
				new_method_action = self.create_action("&Method Window", shortcut=None, 
					slot=self.method_window, 
					tip="Launch method window")
				new_sequence_action = self.create_action("&Sequence Window", shortcut=None, 
					slot=self.sequence_window, 
					tip="Launch sequence window")
				cascade_window_action = self.create_action("&Cascade", shortcut=None, 
					slot=self.cascade_window, tip=None) 
				tile_window_action = self.create_action("&Tile", shortcut=None, 
					slot=self.tile_window, tip=None) 
				log_window_action = self.create_action("Show Log", shortcut=None, 
					slot=self.log_window, tip=None)
				self.add_actions(self.window_menu, (new_instrument_action, new_scan_action, new_tune_action, 
						new_method_action, new_sequence_action,
						cascade_window_action, tile_window_action, log_window_action))
				self.help_menu = self.menuBar().addMenu("&Help")
				about_action = self.create_action("&About", 
						shortcut='F1', slot=self.on_about, 
						tip='About the demo')
				self.add_actions(self.help_menu, (about_action,))
				self.application_menu = self.menuBar().addMenu("&Application")
				preferences_action = self.create_action("Preferences", shortcut=None, 
					slot=self.preferences_window, tip=None)
				self.add_actions(self.application_menu, (preferences_action,))

		def add_actions(self, target, actions):
				for action in actions:
						if action is None:
								target.addSeparator()
						else:
								target.addAction(action)

		def create_action(  self, text, slot=None, shortcut=None, 
												icon=None, tip=None, checkable=False, 
												signal="triggered()"):
				action = QAction(text, self)
				if icon is not None:
						action.setIcon(QIcon(":/%s.png" % icon))
				if shortcut is not None:
						action.setShortcut(shortcut)
				if tip is not None:
						action.setToolTip(tip)
						action.setStatusTip(tip)
				if slot is not None:
						#self.connect(action, SIGNAL(signal), slot)
						action.triggered.connect(slot)
				if checkable:
						action.setCheckable(True)
				return action

		def closeEvent(self, event):
			if self.method_modified or self.tuning_modified:
				msg = QMessageBox()
				msg.setIcon(QMessageBox.Warning)
			
				msg.setText("Save file before exiting?")
				if self.method_modified:
					pth = self.methpath
					mt = "Method"
				elif self.tuning_modified:
					pth = self.tunpath
					mt = "Tuning"
				msg.setInformativeText("file: " + pth)
				msg.setWindowTitle("Save %s" % mt)
				#msg.setDetailedText("The details are as follows:")
				msg.setStandardButtons(QMessageBox.Save |QMessageBox.Close | QMessageBox.Cancel)
				#msg.buttonClicked.connect(msgbtn)
			
				retval = msg.exec_()
				#print "value of pressed message box button:", retval
				if retval == QMessageBox.Save:
					if self.method_modified:
						self.saveMethFile(self.methpath)
					elif self.tuning_modified:
						self.saveTunFile(self.tunpath)
					event.accept()
				elif retval == QMessageBox.Close:
					event.accept()	
				else:
					event.ignore() # let the window close
			if self.sequence_modified:
				msg = QMessageBox()
				msg.setIcon(QMessageBox.Warning)
				msg.setText("Save file before exiting?")
				msg.setInformativeText("file: " + self.seqpath)
				msg.setWindowTitle("Save Sequence")
				#msg.setDetailedText("The details are as follows:")
				msg.setStandardButtons(QMessageBox.Save |QMessageBox.Close | QMessageBox.Cancel)
				#msg.buttonClicked.connect(msgbtn)
			
				retval = msg.exec_()
				#print "value of pressed message box button:", retval
				if retval == QMessageBox.Save:
					self.saveSeqFile(self.seqpath)
					event.accept()
				elif retval == QMessageBox.Close:
					event.accept()	
				else:
					event.ignore() # let the window close

class QPrefsDialog(QDialog):
		def __init__(self, tabs,  parent = None):
			super().__init__(parent)
			self.setWindowTitle("Preferences")
			box = QVBoxLayout()
			self.tabs = QTabWidget()
			for k in tabs.keys():
				self.tabs.addTab(tabs[k], k)
			box.addWidget(self.tabs)
			self.setLayout(box)

class QKeySettings(QWidget):
		def __init__(self, key, default, intrange, applyer=None, parent = None, *args):
			super().__init__(parent, *args)
			self.key = key
			self.settings = QSettings('Muppetastic', 'PyGCMS')
			self.applyer = applyer
			val = self.settings.value(key)
			#val = None
			#spaths = None
			if not val:
				self.ksettings = default
				self.settings.setValue(key, self.ksettings)
			else:
				self.ksettings = val
			self.editksettings = self.ksettings

			self.parent = parent
			n = 0
			plist = []
			group = QGroupBox(key)
			pg = QGridLayout()
			for k in self.ksettings.keys():
				pl = QLabel (k)
				v = self.ksettings[k]
				if isinstance(v, str):
					pt = QLineEdit(v)
					pt.setMinimumWidth(200)
					pt.editingFinished.connect(self.on_parm_update)
					pg.addWidget(pl, n, 0)
					pg.addWidget(pt, n, 1)
				elif isinstance(v, bool):
					pt = QCheckBox(k)
					pt.setChecked(v)
					pt.stateChanged.connect(self.on_parm_update)
					pg.addWidget(pt, n, 0)
				elif isinstance(v, int):
					pt = QSpinBox()
					pt.setMaximum(intrange)
					pt.setValue(v)
					pt.valueChanged.connect(self.on_parm_update)
					pg.addWidget(pl, n, 0)
					pg.addWidget(pt, n, 1)
				else:
					print("bad type: ", v)
				plist.append((key, k, pl, pt))
				n += 1
			group.setLayout(pg)
			self.plist = plist
			bbox = QDialogButtonBox(QDialogButtonBox.Ok |
															QDialogButtonBox.Apply |
															QDialogButtonBox.Cancel
															)
	 
			bbox.accepted.connect(self.onOk)
			bbox.rejected.connect(self.onCancel)
			btn = bbox.button(QDialogButtonBox.Apply)
			btn.clicked.connect(self.onApply)
			layout = QVBoxLayout(self)
			layout.addWidget(group)
			layout.addWidget(bbox)
			self.setLayout(layout)
		 

		def getSetting(self, name):
			return self.ksettings[name]
		
		def on_parm_update(self):
			for g, k, wtl, wtb in self.plist:
				v = self.editksettings[k]
				if isinstance(v, str):
					self.editksettings[k] = wtb.text()
				elif isinstance(v, bool):
					self.editksettings[k] = bool(wtb.isChecked())
					#print(wtb.text(), self.editksettings[k])
				elif isinstance(v, int):
					self.editksettings[k] = int(wtb.value())
					
		def onApply(self):
			self.ksettings = self.editksettings
			self.settings.setValue(self.key, self.ksettings)
			self.applyer()

		def onOk(self):
			self.onApply()
			self.parent.close()
		def onCancel(self):
			self.parent.close()
		def setParent(self, parent):
			self.parent = parent

class Loggable:
	def __init__(self):
		self.logfile = open('MSD.LOG', "a+")

	def logl(self,*args):
			strl = [ str(x) for x in args] 
			news = ''.join(strl)
			try:
				self.logfile.write(news+'\n')
			except Exception as e:
				print("Bad Log: ", news)
			if	self.main.logText:
				self.main.logline.emit(news)
				#self.main.logText.moveCursor (QTextCursor.End);
				#self.main.logText.moveCursor (QTextCursor.End);
			#else:
			#	print("Log: ", news)


class QTuneWindow(QWidget, Loggable):
		def __init__(self, parent = None, main=None, params=None, devs=None, host=None, lpath=None, port=18812):
			super().__init__()
			#self.msparms = params
			self.closed = False
			self.main = main
			self.spectrum = [None, None, None]
			self.ledbox = QLedPanel()

			self.runner = threadRunner(self, main, devs, None, None, params, None, None, tripleScanThread, 
				self.showNewScan, self.showNewTune, logl=self.logl, forRun=False, host=host, loadpath=lpath, port=port)
			# Create the mpl Figure and FigCanvas objects. 
			# 5x4 inches, 100 dots-per-inch
			#
			self.dpi = 100
			self.fig1 = Figure((2.0, 7.0), dpi=self.dpi)
			self.canvas1 = FigureCanvas(self.fig1)
			self.canvas1.setParent(self)
			self.plt1 = self.fig1.add_subplot(111)

			self.fig2 = Figure((2.0, 7.0), dpi=self.dpi)
			self.canvas2 = FigureCanvas(self.fig2)
			self.canvas2.setParent(self)
			self.plt2 = self.fig2.add_subplot(111)

			self.fig3 = Figure((2.0, 7.0), dpi=self.dpi)
			self.canvas3 = FigureCanvas(self.fig3)
			self.canvas3.setParent(self)
			self.plt3 = self.fig3.add_subplot(111)
			
			self.figs = [self.fig1, self.fig2, self.fig3]
			self.plts = [self.plt1, self.plt2, self.plt3]
			self.canvases = [self.canvas1, self.canvas2, self.canvas3]
			#for c in self.canvases:
			#	c.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

			# Bind the 'pick' event for clicking on one of the bars
			#
			#self.canvas.mpl_connect('pick_event', self.on_pick)
			#self.canvas1.mpl_connect('button_press_event', self.on_click)
			#self.canvas1.mpl_connect('motion_notify_event', self.on_mouse_move)

			
			# Create the navigation toolbar, tied to the canvas
			#
			self.mpl_toolbar1 = NavigationToolbar(self.canvas1, self)
			self.mpl_toolbar2 = NavigationToolbar(self.canvas2, self)
			self.mpl_toolbar3 = NavigationToolbar(self.canvas3, self)
			
			#self.toolbars = [self.mpl_toolbar1, self.mpl_toolbar2, self.mpl_toolbar3]
			#for t in self.toolbars:
			#	t.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
			# Other GUI controls
			# 
			#self.textbox = QLineEdit()
			#self.textbox.setMinimumWidth(200)
			#self.connect(self.textbox, SIGNAL('editingFinished ()'), self.on_draw)
			#self.textbox.editingFinished.connect(self.on_draw)
			self.reinit_button = QPushButton("&Init")
			self.reinit_button.clicked.connect(self.runner.on_init)
			self.reinit_button.setEnabled(False)

			#self.draw_button = QPushButton("&Draw")
			#self.draw_button.clicked.connect(self.on_draw)
			self.scan_button = QPushButton("&Scan")
			self.scan_button.clicked.connect(self.runner.on_scan)

			self.run_button = None
			self.seq_button = None
			self.tune_button = QPushButton("&Tune")
			self.tune_button.clicked.connect(self.runner.on_tune)

			
			#self.grid_cb = QCheckBox("Show &Grid")
			#self.grid_cb.setChecked(True)
			#self.grid_cb.stateChanged.connect(self.on_draw)
		
			#slider_label = QLabel('Bar width (%):')
			#self.slider = QSlider(Qt.Horizontal)
			#self.slider.setRange(1, 100)
			#self.slider.setValue(20)
			#self.slider.setTracking(True)
			#self.slider.setTickPosition(QSlider.TicksBothSides)
			#self.connect(self.slider, SIGNAL('valueChanged(int)'), self.on_draw)
			#self.slider.valueChanged.connect(self.on_draw)
			#
			# Layout with box sizers
			# 
			hbox = QHBoxLayout()
			
			#for w in [  self.textbox, self.draw_button, self.grid_cb]:
			for w in [  self.reinit_button, self.scan_button, self.tune_button]:
					#        slider_label, self.slider]:
					hbox.addWidget(w)
					hbox.setAlignment(w, Qt.AlignVCenter)
			
			
			#self.ms_status_area = QParamArea(self, params)
			self.ms_status_area = QStatusArea(self, heading="MS")
			self.config_area = DictionaryTreeWidget(params)
			self.config_area.getModel().dataChanged.connect(self.treeUpdated)

			self.config_area.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)

			vbox1 = QVBoxLayout()
			vbox1.addWidget(self.canvas1)
			vbox1.addWidget(self.mpl_toolbar1)

			vbox2 = QVBoxLayout()
			vbox2.addWidget(self.canvas2)
			vbox2.addWidget(self.mpl_toolbar2)
			
			vbox3 = QVBoxLayout()
			vbox3.addWidget(self.canvas3)
			vbox3.addWidget(self.mpl_toolbar3)
			
			hboxg = QHBoxLayout()
			hboxg.addLayout(vbox1)
			hboxg.addLayout(vbox2)
			hboxg.addLayout(vbox3)
		
			vbox = QVBoxLayout()
			vbox.addLayout(hboxg)
			vbox.addLayout(hbox)

			bighbox = QHBoxLayout()
			bighbox.addLayout(vbox)
			#bighbox.addLayout(phbox) 
			
			vbox4 = QVBoxLayout()
			vbox4.addWidget(self.ledbox)
			vbox4.addWidget(self.ms_status_area)
			
			dummy = QWidget()
			dummy.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
			vbox4.addWidget(dummy)

			bighbox.addLayout(vbox4)
			bighbox.addWidget(self.config_area)
			
			self.setLayout(bighbox)
			self.scan_button.setEnabled(False)
			self.anns = [[],[],[]]
			self.init_peak_detect()
			self.on_draw()
			self.runner.on_init()
			
		def on_pick(self, event):
				# The event received here is of the type
				# matplotlib.backend_bases.PickEvent
				#
				# It carries lots of information, of which we're using
				# only a small amount here.
				# 
				box_points = event.artist.get_bbox().get_points()
				msg = "You've clicked on a peak with coords:\n %s" % box_points
				
				QMessageBox.information(self, "Click!", msg)
				
		def on_click(self, event):
				x = event.xdata
				y = event.ydata
				msg = "You've clicked on a spectrum with coords:\n  click=%s button=%d,\n x=%d, y=%d,\n xdata=%f, ydata=%f" % (
					 'double' if event.dblclick else 'single', event.button,
					 event.x, event.y, event.xdata, event.ydata)
				QMessageBox.information(self, "Click!", msg)
		def on_mouse_move(self, event):
				xe = event.xdata
				if xe is not None:
					#print('mouse x: ' + str(xe))
					#self.axes.lines = [self.axes.lines[0]]
					self.vline.set_data([xe, xe], [0,1] )
					self.canvas.draw()
				
		def showNewScan(self, rs, pk):
				self.spectrum = rs
				self.ramps = [False, False, False]
				for n in range(3):
					self.pk[n] =pk[n]
				self.on_draw()
				for n in range(3):
					self.peak_detect(n)
					self.draw_peak_detect(n, True)

		def showNewTune(self, n, ramp, axis, rs):
				self.spectrum[n] = rs[0]
				if ramp:
					self.ramps[n] = True
					self.rparm[n] = rs[1]
					self.ovolt[n] = rs[2]
					self.nvolt[n] = rs[3]
					self.pk[n] = rs[4]
				else:
					self.pk[n] = rs[1]
				self.draw_int(n)
				if not ramp and not axis:
					self.peak_detect(n)
					self.draw_peak_detect(n, True)
				if ramp:
					self.ramp_peak(n)
					
		def init_peak_detect(self):
			self.maxima = [pandas.DataFrame(), pandas.DataFrame(), pandas.DataFrame()]
			self.minima = [pandas.DataFrame(), pandas.DataFrame(), pandas.DataFrame()]
			self.spline = [None, None, None]
			self.fwhm = [0.0, 0.0, 0.0]
			self.maxab =  [0.0, 0.0, 0.0]
			self.ramps = [False, False, False]
			self.rparm = ["", "", ""]
			self.ovolt = [0, 0, 0]
			self.nvolt = [0, 0, 0]
			self.pk = [0,0,0]
			
		def peak_detect(self, x):
			if self.spectrum[x] != None:
				i = self.spectrum[x].getSpectrum()['ions']
				self.maxab[x]=i['abundance'].max()
				self.maxima[x], self.minima[x] = putil.PUtil.peaksfr(i, 'abundance', 'm/z')
				#sels= []
				#for idx, r in self.maxima.iterrows():
					#sels.append((False, None, None))
				#self.sels = sels
				#from scipy.interpolate import UnivariateSpline
				self.spline[x] = scipy.interpolate.UnivariateSpline(i['m/z'],i['abundance'] - i['abundance'].max()/2,s=0)
				self.fwhm[x] = abs(self.spline[x].roots()[1]-self.spline[x].roots()[0])
				self.canvases[x].draw()

		def ramp_peak(self, x):
			if self.spectrum[x] != None:
				i = self.spectrum[x].ramp
				self.maxima[x], self.minima[x] = putil.PUtil.peaksfr(i, 'abundance','voltage')
				#if not self.maxima[x].empty:
				#	self.plts[x].axvline(x=self.maxima[x].iloc[self.maxima[x]['abundance'].idxmax()]['voltage'], color='r')
				#else:
				#	voltofmax = i.iloc[i['abundance'].idxmax()]['voltage']
				#	self.plts[x].axvline(x=voltofmax, color='r')
				self.plts[x].axvline(x=self.ovolt[x], color='b')
				self.plts[x].axvline(x=self.nvolt[x], color='r')
				self.plts[x].grid()
				self.canvases[x].draw()

		def draw_peak_detect(self, x, one=False):
			if not self.maxima[x].empty:
				anns = []
				maxid = self.maxima[x]['abundance'].idxmax
				maxmz = self.maxima[x].iloc[maxid]['m/z']
				maxab = self.maxima[x].iloc[maxid]['abundance']
				if one:
					self.plts[x].scatter(maxmz ,maxab, color='blue', marker='v', picker=5)
				else:
					self.plts[x].scatter(self.maxima[x]['m/z'] , self.maxima[x]['abundance'], color='blue', marker='v', picker=5)
					for idx, r in self.maxima[x].iterrows():
						anns.append(self.plts[x].annotate('%i:%.2f' % ( idx+1, r['m/z']), xy=(r['m/z'] + 0.05, r['abundance'] + self.maxab[x]*0.05)))
				anns.append(self.plts[x].annotate("Ab %.0f Pw50 %.3f" % (self.maxima[x].iloc[maxid]['abundance'], self.fwhm[x]) , xy=(0.5, 0.75), xycoords='axes fraction'))

				for a in self.anns[x]:
					a.remove()
				self.anns[x] = anns
				self.canvases[x].draw()
		def treeUpdated(self):
			#self.logl("tree updated")
			tparms = self.config_area.to_dict()
			self.runner.updateMsParms(tparms)
			self.main.upd_tuning(tparms)
		def on_draw(self):
				""" Redraws the figure
				"""
				#strg = str(self.textbox.text())
				#self.data = list(map(int, strg.split()))
				#self.data = strg.split()
				
				#x = range(len(self.data))
				#print(x)

				# clear the axes and redraw the plot anew
				#
				for x in range(3):
					self.draw_int(x)
					
					#self.vline = self.axes.axvline(x=0., color="k")
		def draw_int(self, x):
			self.plts[x].clear()
			self.anns[x] = []
			readspec.ReadSpec.axes(self.plts[x],  ' ' + str(self.pk[x]))
			self.plts[x].grid(True)
			if self.spectrum[x] != None:
				#f = open('mass%i.bin' % x, "w+b")
				#f.write(self.spectrum[x].getData())
				#self.spectrum[x].smooth()	
				if self.ramps[x]:
					self.spectrum[x].plotramp(self.plts[x], ' ' + self.rparm[x] + ' ' + str(self.pk[x]))
				else:
					self.spectrum[x].plot(self.plts[x])
			self.canvases[x].draw()

		def closeEvent(self, event):
			# do stuff
			self.runner.on_close()
			can_exit = True
			self.closed = True

			if can_exit:
				event.accept() # let the window close
			else:
				event.ignore()
		
		def showEvent(self, event):
			#print ("tuneWindow show")
			if self.closed:
				self.runner.on_init()
				self.closed = False

			event.accept()
						
class QSpectrumScan(QWidget, Loggable):
		def __init__(self, parent = None, main=None, params=None, devs=None, host=None, lpath=None, port=18812):
			super().__init__()
			#self.msparms = params
			#self.method = method
			self.closed = False
			self.ledbox = QLedPanel()
			self.main = main
			self.spectrum = None
		
			self.runner = threadRunner(self, main, devs, None, None, params, None, None, scanThread, 
				self.showNewScan, None, logl=self.logl, forRun=False, host=host, loadpath=lpath, port=port)
			# Create the mpl Figure and FigCanvas objects. 
			# 5x4 inches, 100 dots-per-inch
			#
			self.dpi = 100
			self.fig = Figure((6.0, 4.0), dpi=self.dpi)
			self.canvas = FigureCanvas(self.fig)
			self.canvas.setParent(self)
			
			# Since we have only one plot, we can use add_axes 
			# instead of add_subplot, but then the subplot
			# configuration tool in the navigation toolbar wouldn't
			# work.
			#
			#self.axes = self.fig.add_subplot(111)
			self.plt = self.fig.add_subplot(111)
			# Bind the 'pick' event for clicking on one of the bars
			#
			#self.canvas.mpl_connect('pick_event', self.on_pick)
			self.canvas.mpl_connect('button_press_event', self.on_click)
			#self.canvas.pick_event.connect(self.on_pick)
			self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

			
			# Create the navigation toolbar, tied to the canvas
			#
			self.mpl_toolbar = NavigationToolbar(self.canvas, self)
			
			# Other GUI controls
			# 
			#self.textbox = QLineEdit()
			#self.textbox.setMinimumWidth(200)
			#self.connect(self.textbox, SIGNAL('editingFinished ()'), self.on_draw)
			#self.textbox.editingFinished.connect(self.on_draw)
			self.reinit_button = QPushButton("&Init")
			self.reinit_button.clicked.connect(self.runner.on_init)
			self.reinit_button.setEnabled(False)

			self.draw_button = QPushButton("&Draw")
			self.draw_button.clicked.connect(self.on_draw)
			self.scan_button = QPushButton("&Scan")
			self.scan_button.clicked.connect(self.runner.on_scan)

			self.run_button = None
			self.tune_button = None
			self.seq_button = None


			
			self.grid_cb = QCheckBox("Show &Grid")
			self.grid_cb.setChecked(True)
			self.grid_cb.stateChanged.connect(self.on_draw)
		
			#slider_label = QLabel('Bar width (%):')
			#self.slider = QSlider(Qt.Horizontal)
			#self.slider.setRange(1, 100)
			#self.slider.setValue(20)
			#self.slider.setTracking(True)
			#self.slider.setTickPosition(QSlider.TicksBothSides)
			#self.connect(self.slider, SIGNAL('valueChanged(int)'), self.on_draw)
			#self.slider.valueChanged.connect(self.on_draw)
			#
			# Layout with box sizers
			# 
			hbox = QHBoxLayout()
			
			#for w in [  self.textbox, self.draw_button, self.grid_cb]:
			for w in [  self.reinit_button, self.draw_button, self.scan_button, self.grid_cb]:
					#        slider_label, self.slider]:
					hbox.addWidget(w)
					hbox.setAlignment(w, Qt.AlignVCenter)
			
			
			#self.ms_status_area = QParamArea(self, params)
			self.ms_status_area = QStatusArea(self, heading="MS")
			self.config_area = DictionaryTreeWidget(params)
			self.config_area.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
			self.config_area.getModel().dataChanged.connect(self.treeUpdated)


			dummy = QWidget()
			dummy.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

			vbox2 = QVBoxLayout()
			vbox2.addWidget(dummy)
			
			vbox = QVBoxLayout()

			vbox.addWidget(self.mpl_toolbar)
			vbox.addWidget(self.canvas)
			vbox.addLayout(hbox)
			vbox.addLayout(vbox2)
			
			bighbox = QHBoxLayout()
			bighbox.addLayout(vbox)
			#bighbox.addLayout(phbox)
			vbox3 = QVBoxLayout()
			vbox3.addWidget(self.ledbox)
			vbox3.addWidget(self.ms_status_area)

			dummy2 = QWidget()
			dummy2.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
			vbox3.addWidget(dummy2)
			bighbox.addLayout(vbox3)
			bighbox.addWidget(self.config_area)
			self.setLayout(bighbox)
			self.scan_button.setEnabled(False)
			self.on_draw()
			self.runner.on_init()
		
			
		def on_pick(self, event):
				# The event received here is of the type
				# matplotlib.backend_bases.PickEvent
				#
				# It carries lots of information, of which we're using
				# only a small amount here.
				# 
				box_points = event.artist.get_bbox().get_points()
				msg = "You've clicked on a peak with coords:\n %s" % box_points
				
				QMessageBox.information(self, "Click!", msg)
				
		def on_click(self, event):
				x = event.xdata
				y = event.ydata
				msg = "You've clicked on a spectrum with coords:\n  click=%s button=%d,\n x=%d, y=%d,\n xdata=%f, ydata=%f" % (
					 'double' if event.dblclick else 'single', event.button,
					 event.x, event.y, event.xdata, event.ydata)
				QMessageBox.information(self, "Click!", msg)
		def on_mouse_move(self, event):
				xe = event.xdata
				if xe is not None:
					#print('mouse x: ' + str(xe))
					#self.axes.lines = [self.axes.lines[0]]
					self.vline.set_data([xe, xe], [0,1] )
					self.canvas.draw()
				
		def showNewScan(self, rs, pk):
				self.spectrum = rs	
				self.on_draw()
	
		def on_draw(self):
				""" Redraws the figure
				"""
				#strg = str(self.textbox.text())
				#self.data = list(map(int, strg.split()))
				#self.data = strg.split()
				
				#x = range(len(self.data))
				#print(x)

				# clear the axes and redraw the plot anew
				#
				self.plt.clear()        
				readspec.ReadSpec.axes(self.plt)
				self.plt.grid(self.grid_cb.isChecked())

				if self.spectrum != None:
					self.spectrum[0].plot(self.plt)
				self.canvas.draw()
				self.vline = self.plt.axvline(x=0., color="k")
		def treeUpdated(self):
			tparms = self.config_area.to_dict()
			self.runner.updateMsParms(tparms)
			self.main.upd_tuning(tparms)			#self.logl("tree updated")
		
		def closeEvent(self, event):
			# do stuff
			self.closed = True
			self.runner.on_close()
			can_exit = True
			if can_exit:
				event.accept() # let the window close
			else:
				event.ignore()
		def showEvent(self, event):
			#print ("ScanWindow show")
			if self.closed:
				self.runner.on_init()
				self.closed = False
			event.accept()

			
				
class QLedPanel(QWidget):
	def __init__(self, parent=None):
			super().__init__(parent)
			self.leds = []
			self.leds.append(Led(self, on_color=Led.green, shape=Led.capsule))
			self.leds.append(Led(self, on_color=Led.green, shape=Led.capsule))
			self.leds.append(Led(self, on_color=Led.green, shape=Led.capsule))

			grid = QGridLayout()
			grid.addWidget(QLabel('HP5971'), 0, 1)
			grid.addWidget(QLabel('HP5890'), 0, 2)
			grid.addWidget(QLabel('HP7673'), 0, 3)

			grid.addWidget(self.leds[0], 1, 1)
			grid.addWidget(self.leds[1], 1, 2)
			grid.addWidget(self.leds[2], 1, 3)
			self.setLayout(grid)
			
	def turnOn(self, ledno):
		self.leds[ledno].turn_on()
		
	def turnOn(self, ledno, status):
		self.leds[ledno].turn_on(status)
			
	def turnOff(self, ledno):
		self.leds[ledno].turn_off()

class QInstControl(QWidget,Loggable):
		def __init__(self, parent = None, main=None, method=None, sequence = None, methname ='', seqname='', devs=None, host=None, lpath=None, port=18812):
			super().__init__(parent)
			self.method = method
			self.methname = methname
			self.fname = ''
			self.closed = False
			self.main = main
			self.sequence = sequence
			self.seqname = seqname
			self.runner = threadRunner(self, main, devs,  method, sequence, None, self.methname, self.fname, None, self.showNewScan, 
																None, logl=self.logl, forRun=True, host=host, loadpath=lpath, port=port)

			vboxscan = QVBoxLayout()
			
			self.totI = []
			
			self.spectrum = None
					# Create the mpl Figure and FigCanvas objects. 
			# 5x4 inches, 100 dots-per-inch
			#
			self.dpi = 100
			self.figi = Figure((2.5, 1.5), dpi=self.dpi)
			self.canvasi = FigureCanvas(self.figi)
			self.canvasi.setParent(self)
			
			# Since we have only one plot, we can use add_axes 
			# instead of add_subplot, but then the subplot
			# configuration tool in the navigation toolbar wouldn't
			# work.
			#
			#self.axesi = self.figi.add_subplot(111)
			self.plti = self.figi.add_subplot(111)	
			
			self.figs = Figure((2.5, 1.5), dpi=self.dpi)
			self.canvass = FigureCanvas(self.figs)
			self.canvass.setParent(self)
			
			# Since we have only one plot, we can use add_axes 
			# instead of add_subplot, but then the subplot
			# configuration tool in the navigation toolbar wouldn't
			# work.
			#
			#self.axess = self.figs.add_subplot(111)
			self.plts = self.figs.add_subplot(111)	
			
			vboxscan.addWidget(self.canvasi)
			vboxscan.addWidget(self.canvass)

			
			hbox = QHBoxLayout()
			vbox = QVBoxLayout()
			dummy = QWidget()
			dummy.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

			self.ledbox = QLedPanel()
			
			vbox.addWidget(self.ledbox)
			
			vbox.addWidget(dummy)
			hb2 = QHBoxLayout()
			plabel = QLabel ("Sample File")
			self.path_field = QLineEdit()
			self.path_field.editingFinished.connect(self.setPath)
			self.path_button = QPushButton ('Browse')
			self.path_button.clicked.connect(self.fileDlg)
			
			hb2.addWidget(plabel)
			hb2.addWidget(self.path_field)
			hb2.addWidget(self.path_button)
			
			vbox.addLayout(hb2)
	
			hb3 = QHBoxLayout()
			self.seqlabel = QLabel ("Sequence")

			self.sequence_field = QLineEdit(seqname)
			self.sequence_field.setDisabled(True)
		
			hb3.addWidget (self.seqlabel)
			hb3.addWidget (self.sequence_field)
			vbox.addLayout(hb3)

			hb4 = QHBoxLayout()
			self.methlabel = QLabel ("Method")

			self.method_field = QLineEdit(methname)
			self.method_field.setDisabled(True)
		
			hb4.addWidget (self.methlabel)
			hb4.addWidget (self.method_field)		
			vbox.addLayout(hb4)
			
			hb5 = QHBoxLayout()
			self.samplabel = QLabel ("Sample")

			self.sample_field = QLineEdit(self.method['Method']['Header']['SampleName'])
			self.sample_field.setDisabled(True)
		
			hb5.addWidget (self.samplabel)
			hb5.addWidget (self.sample_field)		
			vbox.addLayout(hb5)
		
		
			self.reinit_button =QPushButton('Reinit')
			self.reinit_button.clicked.connect(self.runner.on_init)
			vbox.addWidget(self.reinit_button)
			
			
			self.seq_button = QPushButton('Run Sequence')
			self.seq_button.clicked.connect(self.runner.on_seq)
			vbox.addWidget(self.seq_button)
			
			
			self.run_button = QPushButton('Run')
			self.run_button.clicked.connect(self.runner.on_run)
			vbox.addWidget(self.run_button)
			
			self.stop_button = QPushButton('Stop')
			self.stop_button.clicked.connect(self.runner.on_stop)
			vbox.addWidget(self.stop_button)
			
			if not sequence:
				self.sequence_field.setVisible(False)
				self.seqlabel.setVisible(False)
				self.seq_button.setVisible(False)

			self.scan_button = None
			self.tune_button = None

			#hbox.addLayout (vboxscan)

			vbox2 = QVBoxLayout()
			vbox2.addLayout(vbox)
			vbox2.addLayout(vboxscan)
			
			hbox.addLayout(vbox2)
			#hbox.addLayout (vbox)
			vboxsgc = QVBoxLayout()
			vboxsms = QVBoxLayout()
			
			self.ms_status_area = QStatusArea(self, heading="MS")
			vboxsms.addWidget(self.ms_status_area)
			
			self.inj_status_area = QStatusArea(self, heading="Inj")
			vboxsms.addWidget(self.inj_status_area)
			
			self.gc_labels = { 'Temps': ['Oven', 'InlA', 'InlB', 'DetA', 'DetB', 'PrA', 'PrB'] }
			self.gc_status_area = QStatusArea(self, heading="GC", labels=self.gc_labels)
			vboxsgc.addWidget(self.gc_status_area)
			
			dummy = QGroupBox()
			vboxsgc.addWidget(dummy)
			
			hbox.addLayout(vboxsms)
			hbox.addLayout(vboxsgc)
			
			
			#hbox.addLayout (vboxscan)
			
			self.setLayout(hbox)
			
			self.runner.on_init()
			self.last_rt = 0.0
			self.on_draw()
			
		def setPath(self):
			self.fname = self.path_field.text()
			self.runner.updateFname(self.fname)
		
		def fileDlg(self):
			file_choices = "MS (*.MS)|*.ms"
			path, choice = QFileDialog.getSaveFileName(self, 
										'Set results file', '', 
										file_choices)
			self.path_field.setText(path)
			self.setPath()

			
	
			

		
		def on_draw(self):
			""" Redraws the figures
			"""
			#strg = str(self.textbox.text())
			#self.data = list(map(int, strg.split()))
			#self.data = strg.split()
			
			#x = range(len(self.data))
			#print(x)

			# clear the axes and redraw the plot anew
			#
			self.plts.clear()        
			readspec.ReadSpec.axes(self.plts)
			self.plts.grid(True)

			if self.spectrum != None:
				self.spectrum.plot(self.plts)
				
			self.canvass.draw()
			
			self.plti.clear()
			msfr.ReadMSFile.axes(self.plti)
			self.plti.grid(True)
			self.plti.plot(*zip(*self.totI), linewidth=0.5)

			#self.vline = self.axesi.axvline(x=0., color="k")
			self.canvasi.draw()
		
		def closeEvent(self, event):
			# do stuff
			self.runner.on_close()
			self.closed = True
			can_exit = True
			if can_exit:
				event.accept() # let the window close
			else:
				event.ignore()
		
		def showEvent(self, event):
			#print ("InstWindow show")
			if self.closed:
				self.runner.on_init()
				self.closed = False
			event.accept()

		def showNewScan(self, rs):
			self.spectrum = rs	
			ti = self.spectrum.getTotIons()
			rt = self.spectrum.getSpectrum()['RetTime']
			self.totI.append((rt, ti))
			if rt - self.last_rt > 0.1:
				self.on_draw()
				self.last_rt = rt
		
		def updateSequence(self, sequence, seqname):
			if sequence:
				doSeq = True
			else:
				doSeq = False
			self.sequence = sequence
			self.seqname = seqname
			self.sequence_field.setText(seqname)
			self.sequence_field.setVisible(doSeq)
			self.seqlabel.setVisible(doSeq)
			self.seq_button.setVisible(doSeq)

		
def main():
	app = QApplication(sys.argv)
	form = MainWindow()
	form.show()
	app.exec_()


if __name__ == "__main__":
	main()


