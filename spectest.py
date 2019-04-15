"""
This demo demonstrates how to embed a matplotlib (mpl) plot 
into a PyQt4 GUI application, including:

* Using the navigation toolbar
* Adding data to the plot
* Dynamically modifying the plot's properties
* Processing mpl events
* Saving the plot to a file from a menu

The main goal is to serve as a basis for developing rich PyQt GUI
applications featuring mpl plots (using the mpl OO API).

Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Last modified: 19.01.2009
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
import time
import readspec
import busreader
import hp5971
import visa
import hp5971
import hp7673
import hp5890
import time
import datetime
import msfileread as msfr
from pyqt_led import Led
import traceback
import tune2meth

import peakdetect
import numpy as np
import pandas
import scipy
import scipy.interpolate
import copy
from qdictparms import QParamArea, QStatusArea

class AppForm(QMainWindow):
		MaxRecentFiles = 5
		logline = pyqtSignal(str)

		count = 0
		def __init__(self, parent=None):
				QMainWindow.__init__(self, parent)
				self.setWindowTitle('5971 Spectrum Control')
				self.recentFileActs = []
				
				self.scanWindow = None
				self.scan_mdi = None
				self.methodWindow = None
				self.method_mdi = None
				self.instWindow = None
				self.inst_mdi = None
				self.logWindow = None
				self.log_mdi = None			
				self.logText= None	
				self.method = None
				self.loadparam()
				self.create_recent_files()

				self.create_menu()
				self.updateRecentFileActions()

				self.create_main_frame()
				self.create_status_bar()



		
		def save_plot(self):
				file_choices = "PNG (*.png)|*.png"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save file', '', 
												file_choices)
				if path:
						self.canvas.print_figure(path, dpi=self.dpi)
						self.statusBar().showMessage('Saved to %s' % path, 2000)
		def save_tuning(self):
				file_choices = "JSON (*.json)|*.json"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save tuning file', '', 
												file_choices)
				if path:
						f = open(path, "w")
						f.write(json.dumps(self.msparms, indent=4))
						self.statusBar().showMessage('Saved to %s' % path, 2000)
		def load_tuning(self):
				file_choices = "JSON (*.json);Tuning (*.U);All Files (*)"
				
				path, choices = QFileDialog.getOpenFileName(self, 
												'Load tuning file', '', 
												file_choices)
				if path:
						if path.endswith(".json"): 
							f = open(path, "r")
							tparms = f.read()
							self.msparms = json.loads(tparms)
							self.method['Method']['MSParms'] = self.msparms
						elif path.endswith(".U"):
							f = open(path, "rb")
							tbin = f.read()
							tparms = self.method['Method']['MSParms']['Tuning']
							mparms = self.method['Method']['MSParms']['Mass']

							tune2meth.updatefromTuning(tbin, tparms)
							tune2meth.updatefromTuning(tbin, mparms)

						if self.methodWindow:
							self.updMethodTabs()		
						if self.scanWindow:
							self.scanWindow.paramtabs.updatepboxes()
		def save_method(self):
				file_choices = "JSON (*.json)|*.json"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save method file', '', 
												file_choices)
				if path:
						f = open(path, "w")
						f.write(json.dumps(self.method, indent=4))
						f.close()
						self.statusBar().showMessage('Saved to %s' % path, 2000)
						
		def load_method(self):
				file_choices = "JSON (*.json);;All Files (*)"
				
				path, choices = QFileDialog.getOpenFileName(self, 
												'Load method file', '', 
												file_choices)
				if path:
						self.loadMethFile(path)
		
		def loadMethFile(self, path):
			f = open(path, "r")
			mparms = f.read()
			self.method = json.loads(mparms)
			self.msparms = self.method['Method']['MSParms']
			self.methpath = path
			self.methname = AppForm.strippedName(self.methpath)
			if self.methodWindow:
				self.updMethodTabs()		
			if self.scanWindow:
				self.scanWindow.paramtabs.updatepboxes()
			self.setCurrentFile(path)
			
		def save_spectrum(self):
				file_choices = "BIN (*.bin)|*.bin"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save file', '', 
												file_choices)
				if path:
						f = open(path, "w+b");
						f.write(self.spectrum.getData())
		
		def load_spectrum(self):
				file_choices = "BIN (*.bin);;All Files (*)"
				
				path, choices = QFileDialog.getOpenFileName(self, 
												'Load file', '', 
												file_choices)
				if path and self.scanWindow:
						#self.canvas.print_figure(path, dpi=self.dpi)
						self.scanWindow.spectrum = readspec.FileSpec(path)
						self.statusBar().showMessage('Loaded %s' % path, 2000)
						self.scanWindow.on_draw()
		
		def on_about(self):
				msg = """ HP 5971 spectrum reader:
				
				 *Pretty much implements all the features 
				 *In the Diagnostics/Vacuum Control->Edit MS Parm Screen
				 *Obviously needs a 5971 connected
				 *on a GPIB bus accessible to PyVISA
				"""
				QMessageBox.about(self, "About the demo", msg.strip())
	
	
		def loadparam(self):
				f = open("parms.json", "r")
				tparms = f.read()
				self.msparms = json.loads(tparms)
		def tune_window(self):
			if not self.scanWindow:
				AppForm.count = AppForm.count+1
				sub = QMdiSubWindow()
				submain = QTuneWindow(sub, self, params=self.msparms)
				sub.setWidget(submain)
				sub.setWindowTitle(str(AppForm.count) + ": " + "Tuning")
				self.mdi.addSubWindow(sub)
				sub.show()
				self.tuningWindow = submain
				self.tuning_mdi = sub
			else:
				self.tuning_mdi.show()
				self.tuningWindow.show()

		def scan_window(self):
			if not self.scanWindow:
				AppForm.count = AppForm.count+1
				sub = QMdiSubWindow()
				submain = QSpectrumScan(sub, self, params=self.msparms)
				sub.setWidget(submain)
				sub.setWindowTitle(str(AppForm.count) + ": " + "Scan Control")
				self.mdi.addSubWindow(sub)
				sub.show()
				self.scanWindow = submain
				self.scan_mdi = sub
			else:
				self.scan_mdi.show()
				self.scanWindow.show()
		def updMethodTabs(self):
			for s in self.paramTabList:
				s.updatepboxes()
		def method_window(self):
			if not self.method:
				self.statusBar().showMessage('Error: No Method Loaded', 1000)
			else:
				path = self.methpath
				meth = self.method['Method']
				AppForm.count = AppForm.count+1
				sub = QMdiSubWindow()
				submain = QScrollArea()
				tabs = QTabWidget()
				sub.setWidget(submain)
				sub.setWindowTitle(str(AppForm.count) + ": Method : " + AppForm.strippedName(path))
			
				#hbox = QHBoxLayout()
				self.paramTabList = []
				for heading in meth:
					#gbox = QGroupBox(heading)
					paramarea = QParamArea(tabs, meth[heading], heading)
					#gboxl = QVBoxLayout()
					#gboxl.addWidget(paramarea)
					#gbox.setLayout(gboxl)
					#hbox.addWidget(gbox)
					tabs.addTab(paramarea, heading)
					self.paramTabList.append(paramarea)
				#submain.setLayout(hbox)
				submain.setWidget(tabs)
				self.mdi.addSubWindow(sub)
				sub.show()
				self.methodWindow = submain
				self.method_mdi = sub
		def log_window(self, q):
			if not self.logWindow:
				AppForm.count = AppForm.count+1
				self.logText = QPlainTextEdit()
				sub = QMdiSubWindow()
				sub.setWidget(self.logText)
				sub.setWindowTitle("Log: "+str(AppForm.count))
				self.mdi.addSubWindow(sub)
				sub.show()	
				self.logWindow = self.logText
				self.log_mdi = sub
				self.logline.connect(self.doLog)
			else:
				self.log_mdi.show()
				self.logWindow.show()
		
		def doLog(self, logls):
			if self.logText:
				self.logText.appendPlainText(logls)
	
		def inst_window(self, q):
			if not self.method:
				self.statusBar().showMessage('Error: No Method Loaded', 1000)
			else:
				if not self.instWindow:
					AppForm.count = AppForm.count+1
					sub = QMdiSubWindow()
					self.instrument = QInstControl(sub, self, self.method, self.methname)
					sub.setWidget(self.instrument)
					sub.setWindowTitle("Instrument: "+str(AppForm.count))
					self.mdi.addSubWindow(sub)
					sub.show()	
					self.instWindow = self.instrument
					self.inst_mdi = sub
				else:
					self.inst_mdi.show()
					self.instWindow.show()
		def cascade_window(self, q):
			self.mdi.cascadeSubWindows()

		def tile_window(self, q):
			self.mdi.tileSubWindows()
		
		def strippedName(fullFileName):
			return QFileInfo(fullFileName).fileName()
		def create_main_frame(self):
				#self.main_frame = QSpectrumScan(self, self, self.msparms)
				self.mdi = QMdiArea()
				self.setCentralWidget(self.mdi)

		def create_status_bar(self):
				self.status_text = QLabel("This is a demo")
				self.progress = QProgressBar(self)
				#self.progress.setGeometry(, 80, 250, 20)
				self.statusBar().addWidget(self.status_text, 1)
				self.statusBar().addWidget(self.progress, 2)
			
		def recentfileaction(self, q):
			action = self.sender()
			if action:
				self.loadMethFile(action.data())
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
				del files[AppForm.MaxRecentFiles:]

				settings.setValue('recentFileList', files)

				for widget in QApplication.topLevelWidgets():
						if isinstance(widget, AppForm):
								widget.updateRecentFileActions()
		
		def updateRecentFileActions(self):
				settings = QSettings('Muppetastic', 'SpecControl')
				files = settings.value('recentFileList')
				if files:
					l = len(files)
				else:
					l = 0
				numRecentFiles = min(l, AppForm.MaxRecentFiles)

				for i in range(numRecentFiles):
						text = "&%d %s" % (i + 1, AppForm.strippedName(files[i]))
						self.recentFileActs[i].setText(text)
						self.recentFileActs[i].setData(files[i])
						self.recentFileActs[i].setVisible(True)

				for j in range(numRecentFiles, AppForm.MaxRecentFiles):
						self.recentFileActs[j].setVisible(False)

				self.separatorAct.setVisible((numRecentFiles > 0))
				
		def create_recent_files(self):
			for i in range(AppForm.MaxRecentFiles):
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
						load_tuning_action, save_tuning_action, None, quit_action))
				self.separatorAct = self.file_menu.addSeparator() 
				self.separatorAct.setVisible(False)
				
				for i in range(AppForm.MaxRecentFiles):
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
				cascade_window_action = self.create_action("&Cascade", shortcut=None, 
					slot=self.cascade_window, tip=None) 
				tile_window_action = self.create_action("&Tile", shortcut=None, 
					slot=self.tile_window, tip=None) 
				log_window_action = self.create_action("Show Log", shortcut=None, 
					slot=self.log_window, tip=None)
				self.add_actions(self.window_menu, (new_instrument_action, new_scan_action, new_tune_action, 
						new_method_action, cascade_window_action, 
						tile_window_action, log_window_action))
				self.help_menu = self.menuBar().addMenu("&Help")
				about_action = self.create_action("&About", 
						shortcut='F1', slot=self.on_about, 
						tip='About the demo')
				
				self.add_actions(self.help_menu, (about_action,))

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
				
class initThread(QObject):
		init_status = pyqtSignal(bool,str)
		progress_update = pyqtSignal(int)
		inst_status = pyqtSignal(bool, bool, bool)
		run_init = pyqtSignal()
		update_init = pyqtSignal()

		def __init__(self, method, logl, forRun=False):
				QObject.__init__(self)
				self.reboot = False
				self.method = method
				self.init_msd = False
				self.init_gc = False
				self.init_inj = False
				self.init = False
				self.logl = logl
				self.forRun = forRun
				#self.run_init.connect(self.doInit)

				
		def __del__(self):
				pass
				#self.wait()
				
		def doUpdateMethod(m):
			self.method = m
			self.init_gc = False
			self.init_inj = False
			self.init = False
			self.doInit()
			
		def doInit(self):
			#init = False
			time.sleep(2)
			stime = 2.0
			while not self.init:
					try:
						self.br = busreader.BusReader(logl=self.logl)
						self.progress_update.emit(10)
					except Exception as e:
						self.logl (e)
						self.init_status.emit(False, str(e))
						time.sleep(stime)
						continue
					if not self.init_msd:
						try:
							
							self.msd = self.br.deviceByName('5971')
							if (self.br.isSmartCardDevice(self.msd) and self.br.needsLoading(self.msd)) or self.reboot:
								self.br.loadSmartCard(self.msd, self.reboot, self.progress_update.emit)
								time.sleep(3)
							
	 						
							self.hpmsd = hp5971.HP5971(self.msd, self.br, self.logl)
							
							self.hpmsd.msdInit(self.progress_update.emit)
							self.hpmsd.scanSeqInit(True)
							cd = self.hpmsd.getConfig()
							if cd ['Fault'] == 33:
									self.br.loadSmartCard(self.msd, reboot=True)
							self.reboot = True
							self.init_msd = True
							self.inst_status.emit(self.init_msd, self.init_gc, self.init_inj)
						except Exception as e:
							self.logl (e)
							self.logl(traceback.format_exc())
							self.reboot = True
							try:
								self.msd.clear()
							except Exception as e2:
								self.logl("Could not clear")
							finally:
								self.init_status.emit(False, str(e))
								time.sleep(stime)
					if not self.init_gc and self.method and self.forRun:
						try:
							self.gac = self.br.deviceByName('5890')
							self.hpgc= hp5890.HP5890(self.gac, self.br, self.method['Method']['GCParms'], self.logl)
							self.hpgc.upload(self.progress_update.emit)
							self.init_gc = True
							self.inst_status.emit(self.init_msd, self.init_gc, self.init_inj)

						except Exception as e:
								self.logl (e)
								self.logl(traceback.format_exc())

								self.init_status.emit(False, str(e))
								time.sleep(stime)
					if not self.init_inj and self.method and self.forRun:
						try:	 
							self.inj = self.br.deviceByName('7673')
							self.hpi = hp7673.HP7673(self.inj, self.br, self.method['Method']['Injector']['UseInjector'], self.hpgc.addr, self.logl)
							self.logl(self.hpi.reset())
							self.init_inj = True
							self.inst_status.emit(self.init_msd, self.init_gc, self.init_inj)
						except Exception as e:
							self.logl (e)
							self.logl(traceback.format_exc())
							self.init_status.emit(False, str(e))
							time.sleep(stime)
					if (self.init_inj or not self.method or not self.forRun) and self.init_msd and (self.init_gc or not self.method or not self.forRun):
						self.progress_update.emit(100)
						self.init = True
						self.init_status.emit(True, 'OK')

		def getMsd(self):
			return self.hpmsd
			
		def getMsdDevice(self):
			return self.msd		
			
		def getGc(self):
			return self.hpgc
			
		def getInj(self):
			return self.hpi


class configThread(QObject):
		config_update = pyqtSignal(dict)
		progress_update = pyqtSignal(int)
		run_config = pyqtSignal()

		update_config = pyqtSignal(hp5971.HP5971)
		
		def __init__(self, hpmsd, logl=print):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				#self.run_config.connect(self.do_gc)
				self.logl = logl
		def __del__(self):
			pass
			#self.wait()
		def updateDevices(self, hpmsd):
				self.hpmsd = hpmsd

		def do_gc(self):
					try:
						ret = self.hpmsd.getConfig(self.progress_update.emit)
						self.config_update.emit(ret)
						self.progress_update.emit(100)

					except Exception as e:
						self.logl ('Exc ' + str(e))
						self.logl(traceback.format_exc())
						self.config_update.emit({'Error' : str(e)})
		#def run(self):
		#		time.sleep(1)

class statusThread(QObject):
		ms_status_update = pyqtSignal(dict)
		gc_status_update = pyqtSignal(dict)

		progress_update = pyqtSignal(int)
		run_status = pyqtSignal(bool)
		update_status = pyqtSignal(hp5971.HP5971, hp5890.HP5890, hp7673.HP7673)
		
		def __init__(self, hpmsd, hpgc, logl=print):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				self.hpgc = hpgc
				self.logl = logl
		def __del__(self):
				pass
				#self.wait()

		def updateDevices(self, hpmsd, hpgc, hpinj):
				self.hpmsd = hpmsd
				self.hpgc = hpgc
				self.hpinj = hpinj
					
		def do_st(self,gc):
					try:
						ret = self.hpmsd.getConfig(self.progress_update.emit)
						ret2 = self.hpmsd.getRunStat(self.progress_update.emit)
						ret.update(ret2)
						self.ms_status_update.emit(ret)
						
						ret3 = self.hpgc.statcmds(self.progress_update.emit)
						self.gc_status_update.emit(ret3)

						self.progress_update.emit(100)

					except Exception as e:
						self.logl ('Exc ' + str(e))
						self.logl(traceback.format_exc())

						self.ms_status_update.emit({'Error' : str(e)})
		#def run(self):
		#		time.sleep(1)
					 
					 

class scanThread(QObject):
		progress_update = pyqtSignal(int)
		scan_done = pyqtSignal(readspec.ReadSpec)
		scan_status = pyqtSignal(bool, str)
		run_scan = pyqtSignal()
		update_scan = pyqtSignal(hp5971.HP5971)

		def __init__(self, hpmsd, parms, logl=print):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				self.parms = parms
				self.logl = logl
				#self.run_scan.connect(self.doScan)

		def updateDevices(self, hpmsd):
				self.hpmsd = hpmsd
			
				
		def __del__(self):
				pass
				#self.wait()


		def doScan(self):
				try:
					#self.scan_status.emit(True, 'Starting Scan')
					self.hpmsd.getAScan(self.parms, self.progress_update.emit)	
					self.scan_done.emit(self.hpmsd.getSpec())
					self.scan_status.emit(True, 'Complete')

				except hp5971.HP5971Exception as e1:
						print ('5971 ' + str(e1))
						try:
							 errstr = str(self.hpmsd.getErrors())
						except Exception as e2:
							 errstr = str(e)
						finally:
							 self.scan_status.emit(False, errstr)
				except Exception as e:
						self.logl ('Exc ' + str(e))
						self.logl(traceback.format_exc())

						self.scan_status.emit(False, str(e))


class tripleScanThread(QObject):
		progress_update = pyqtSignal(int)
		tscan_done = pyqtSignal(list)
		scan_status = pyqtSignal(bool, str)
		scan_info = pyqtSignal(str)
		run_scan = pyqtSignal()
		update_scan = pyqtSignal(hp5971.HP5971)

		def __init__(self, hpmsd, parms, logl=print):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				self.parms = parms
				self.logl = logl
				#self.run_scan.connect(self.doScan)

		def updateDevices(self, hpmsd):
				self.hpmsd = hpmsd
			
				
		def __del__(self):
				pass
				#self.wait()


		def doScan(self):
				try:
					self.hpmsd.calValve(1)
					self.hpmsd.readyOn()

					self.scan_info.emit('Waiting for PFTBA to stabilise')
					time.sleep(30)
					self.scan_info.emit('Run Scan')
					#self.scan_status.emit(True, 'Starting Scan')
					old_sparms = copy.deepcopy(self.parms['Scan'])
					self.hpmsd.adjScanParms(self.parms['Scan'], self.hpmsd.tunePeak(self.parms, 1))
					self.hpmsd.getPartialScan(self.parms, self.progress_update.emit, moreScans=True)
					spec1 = self.hpmsd.getSpec()
					#time.sleep(1)
					self.hpmsd.adjScanParms(self.parms['Scan'], self.hpmsd.tunePeak(self.parms, 2))
					self.hpmsd.getPartialScan(self.parms, self.progress_update.emit, moreScans=True)	
					spec2 = self.hpmsd.getSpec()
					#time.sleep(1)

					self.hpmsd.adjScanParms(self.parms['Scan'], self.hpmsd.tunePeak(self.parms, 3))
					self.hpmsd.getPartialScan(self.parms, self.progress_update.emit, moreScans=False)	
					spec3 = self.hpmsd.getSpec()

					self.tscan_done.emit([spec1, spec2, spec3])
					self.parms['Scan'].update(old_sparms)
					self.scan_status.emit(True, 'Complete')

				except hp5971.HP5971Exception as e1:
						print ('5971 ' + str(e1))
						try:
							 errstr = str(self.hpmsd.getErrors())
						except Exception as e2:
							 errstr = str(e)
						finally:
							 self.scan_status.emit(False, errstr)
				except Exception as e:
						self.logl ('Exc ' + str(e))
						self.logl(traceback.format_exc())

						self.scan_status.emit(False, str(e))




class runProgressThread(QObject):
		progress_update = pyqtSignal(int)
		run_done = pyqtSignal(bool, str)
		gc_status_update = pyqtSignal(dict)
		ms_status_update = pyqtSignal(dict)
		inj_status_update = pyqtSignal(dict)
		run_spec = pyqtSignal(readspec.ReadSpec)
		run_progress = pyqtSignal()
		run_stop = pyqtSignal()
		update_run = pyqtSignal(hp5971.HP5971, hp5890.HP5890, hp7673.HP7673)
		update_method = pyqtSignal(dict)
		
		def __init__(self, fname, methname, hpmsd, hpgc, hpinj, method, logl):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				self.hpgc = hpgc
				self.hpinj = hpinj
				self.method = method
				self.specs = []
				self.logl = logl
				self.fname = fname
				self.methname = methname
				#self.run_progress.connect(self.doRun)
				#self.run_stop.connect(self.endRun)

				self.last_rt = 0.0
				self.running = False
				
		def __del__(self):
				pass
				#self.wait()

		def updateDevices(self, hpmsd, hpgc, hpinj):
				self.hpmsd = hpmsd
				self.hpgc = hpgc
				self.hpinj = hpinj
				
		def updateMethod(self, name, m):
			self.method = m
			self.methname = name

		def datProc(self, m):
				self.hpmsd.readData()
				self.stb = self.hpmsd.statusb
				spec  = self.hpmsd.getSpec()
				if spec:
					sp2 = spec.getSpectrum()
					if sp2:
						rt = sp2['RetTime']
						self.specs.append((rt, spec))
						#if (rt - self.last_rt) > 0.1: 
						self.run_spec.emit(spec)
						#self.last_rt = rt
					else:
						self.logl("Empty spec")
				else:
					self.logl("No spec")

		def movel(self, i, n, vial):
				if n == 1:
					self.injstat.update( i.status())
					i.apStart()
					self.injstat.update(i.apFinish())
					self.logl(self.injstat)
					self.inj_status_update.emit(self.injstat)
					st = i.moveStart(vial, "RR")
				elif n == 2:
					st = i.moveStart("RR", "I%i" % i.injnum)
				elif n == 5:
					st = i.moveStart("I%i" % i.injnum, vial)
				else:
					st = False
				return st
		
		def statl(self, i, d):
			fns = [self.hpgc.statRI, self.hpgc.statTemps, self.hpgc.statCV, self.hpgc.statDS, 
						self.hpgc.statEndSearch, self.hpgc.statRL, lambda : self.hpgc.statSig(0), 
							lambda : self.hpgc.statSig(1)]
			fnl = len(fns)
			if i >= fnl:
				return False
			d.update(fns[i]())
			return True

		def specheader(self):
			d = datetime.datetime.now()
			hdr = {
					'Data_name': bytes(self.method['Method']['Header']['SampleName'].rjust(30),'ascii'), 
					'Misc_info': bytes(self.method['Method']['Header']['Info'].rjust(25), 'ascii'),
					'Operator': bytes(self.method['Method']['Header']['Operator'].ljust(9)[0:9], 'ascii'),
					'Date_time': bytes(d.strftime('%d %b %y  %I:%m %p'), 'ascii'),
					'Inst_model': bytes(self.method['Method']['Header']['Inst'].ljust(9)[0:9], 'ascii'),
					'Inlet': b'GC', 
					'Method_File': bytes(self.methname.ljust(19), 'ascii'),
					'Als_bottle': self.method['Method']['Header']['Vial'], 
			}
			self.logl(hdr)
			return hdr	
			
		def endRun(self):
			self.running = False
			
		def doRun(self):
				try:
					self.running = True
					self.hpmsd.scanStartSeq(self.method['Method']['MSParms'], self.progress_update.emit)
					rs = self.hpmsd.getRunStat() 	
					cd = self.hpmsd.getConfig()
					cd.update(rs)
					self.ms_status_update.emit(cd)
					self.injstat = {}
					self.logl(cd)
					hdr = self.specheader()
					idx = 0
					doData = False
					doStat = False
					injecting = False
					injected = False
					moving = False
					doingAP = False
					movpos = 1
					flt = 0
					stv = 8
					self.last_rt  = 0.0
					#stv = 0
					while self.running:
						if not injected and not moving and not injecting and not doingAP:
							moving = self.movel(self.hpinj, movpos, self.method['Method']['Header']['Vial'])
							movpos += 1
						if moving:
							moving = not self.hpinj.injDone()
							if not moving:
								if not injecting and not doingAP:
									mvst = self.hpinj.moveFinish()
									self.logl (movpos, mvst)
									self.injstat.update(mvst)
									self.inj_status_update.emit(self.injstat)
								elif not doingAP:
									ijst = self.hpinj.injectFinish()
									self.logl (movpos, ijst)
									self.injstat.update(ijst)
									self.inj_status_update.emit(self.injstat)

								elif doingAP:
									apst = self.hpinj.apFinish()
									self.logl (movpos, apst)
									self.injstat.update(apst)
									self.inj_status_update.emit(self.injstat)

								else:
									self.logl("unknown injector state")
								if movpos == 2:
									rd = self.hpinj.read()
									self.logl("Reader: ", rd)
									l1 = rd.rfind('"')
									l2 = rd[:l1].rfind('"')
									rd2 = rd[l2+1:l1]
									self.injstat.update({'Read': rd2})
									self.inj_status_update.emit(self.injstat)
								elif movpos == 3:
									self.hpmsd.runReady()
									parms = self.method['Method']['Injector']
									self.hpinj.injectStart( prewash=parms['Prewash'], visc=parms['Viscosity'], pumps = parms['Pumps'], 
									quant=parms['Quantity'], solvwasha=parms['SolvWashA'], solvwashb=parms['SolvWashB'])
									injecting = True
									moving = True
									movpos += 1
								elif movpos == 4:
									self.injstat.update(self.hpinj.status(dosi=True))
									self.logl(self.injstat)
									self.inj_status_update.emit(self.injstat)

									self.hpinj.apStart()
									injecting = False
									doingAP = True
									moving = True
									movpos += 1
								elif movpos == 5:
									doingAP = False
								elif movpos == 6:
									injected = True
						if injected and not self.hpgc.isRunning():
							break
						self.stb = self.hpmsd.status()
						self.logl ('5971 Pre Data st: ', self.stb)
						if doData:
							readmax = 4
							while self.stb == stv and readmax > 0:
							#while  readmax > 0:
								self.datProc(self.hpmsd)
								idx+=1
								#stb = self.stb
								self.logl('5971 st: ', self.stb)
								readmax -= 1
						runstat =  self.hpmsd.getRunStat()
						self.logl(runstat)
						self.stb = self.hpmsd.status()
						self.logl ('5971 Run st: ', self.stb)
						if ((self.stb != stv and ((self.hpmsd.runtime - self.last_rt)  > 6)) or not injected) and not doStat: 
							doStat = True
							self.last_rt = self.hpmsd.runtime
							statIdx = 0
							gcst = {}
							#QThread.yieldCurrentThread()
							#gcst = self.hpgc.statcmds()
							#self.gc_status_update.emit(gcst)
							#self.logl(gcst)
						if doStat:
							doStat = self.statl(statIdx, gcst)
							statIdx += 1
							if not doStat:
								self.gc_status_update.emit(gcst)
								self.logl(gcst)
							
						if not doData:
							msst = self.hpmsd.getConfig()
							msst.update(runstat)
							self.ms_status_update.emit(msst)
							self.logl(msst)
							flt = msst['Fault']
						else :
							if self.stb != stv:
								flt = self.hpmsd.getFaultStat()
								self.stb = self.hpmsd.status()
								self.logl ('5971 st: ', self.stb, ' Fault: ', flt)
								runstat.update({'Fault' : flt})
								self.ms_status_update.emit(runstat)
							else:
								flt = 0
						if flt != 0:
							break
						if float(self.hpmsd.runtime) > self.method['Method']['MSParms']['Run']['SolventDelay']['value']:
							if runstat['RunStat'] == 2 and runstat['AER'] == 64:
								doData=True
						QThread.yieldCurrentThread()
					if flt != 0:
						self.logl ('Fault %i. Terminating.' % flt)
						self.logl(hp5971.HP5971.faultmsgs(flt))
						self.hpgc.endRun()
						self.hpmsd.endRun()
						self.hpmsd.runReadyOff()
						self.run_done.emit(True, 'MSD Fault: ' + str(flt))
					elif not self.hpgc.isRunning() or not self.running:
						self.hpgc.endRun()
						nr = self.hpmsd.endRun()
						while nr > 0:
							self.stb = self.hpmsd.status()
							self.logl(self.stb)
							self.datProc(self.hpmsd)
							idx += 1
							nr -= 1
							self.hpmsd.runReadyOff()
						if self.running:
							self.run_done.emit(True, 'Complete')
						else:
							self.run_done.emit(True, 'Aborted')
					else:
						self.run_done.emit(False, 'Unexpected Termination')

				except hp5971.HP5971Exception as e1:
						self.logl ('5971 ' + str(e1))
						self.logl(traceback.format_exc())
						try:
							 errstr = str(self.hpmsd.getErrors())
						except Exception as e2:
							 errstr = "Could not get Error: " + str(e2)
							 self.logl ('5971 er2 ' + str(e2))
						finally:
							self.logl ('5971 error ' + errstr)
							self.run_done.emit(False, errstr)
				except hp7673.HP7673Exception as e3:
						self.logl ('7673 ' + str(e3))
						self.logl(traceback.format_exc())
						self.run_done.emit(False, str(e3))
				except Exception as e4:
						self.logl ('Exc ' + str(e4))
						self.logl(traceback.format_exc())
						self.run_done.emit(False, str(e4))
				finally:
					self.running = False
					sl = len(self.specs)
					self.logl("Spec Len: ", sl)
					if sl > 0:
						msf = msfr.ReadMSFile(spectra=self.specs)
						msf.setHeader(hdr)
						#msf.plotit()
						#x, ions = spectra[0]
						#ions.plotit()
						self.logl(msf.theRun)
						msf.writeFile(self.fname)



class QTuneWindow(QWidget):
		def __init__(self, parent = None, main=None, params=None):
			super().__init__(parent)
			self.msparms = params
			self.main = main
			self.spectrum = [None, None, None]

			# Create the mpl Figure and FigCanvas objects. 
			# 5x4 inches, 100 dots-per-inch
			#
			self.dpi = 100
			self.fig1 = Figure((2.0, 9.0), dpi=self.dpi)
			self.canvas1 = FigureCanvas(self.fig1)
			self.canvas1.setParent(self)
			self.plt1 = self.fig1.add_subplot(111)

			self.fig2 = Figure((2.0, 9.0), dpi=self.dpi)
			self.canvas2 = FigureCanvas(self.fig2)
			self.canvas2.setParent(self)
			self.plt2 = self.fig2.add_subplot(111)

			self.fig3 = Figure((2.0, 9.0), dpi=self.dpi)
			self.canvas3 = FigureCanvas(self.fig3)
			self.canvas3.setParent(self)
			self.plt3 = self.fig3.add_subplot(111)
			
			self.figs = [self.fig1, self.fig2, self.fig3]
			self.plts = [self.plt1, self.plt2, self.plt3]
			self.canvases = [self.canvas1, self.canvas2, self.canvas3]
			
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
			# Other GUI controls
			# 
			#self.textbox = QLineEdit()
			#self.textbox.setMinimumWidth(200)
			#self.connect(self.textbox, SIGNAL('editingFinished ()'), self.on_draw)
			#self.textbox.editingFinished.connect(self.on_draw)
			self.reinit_button = QPushButton("&Init")
			self.reinit_button.clicked.connect(self.on_init)
			self.reinit_button.setEnabled(False)

			#self.draw_button = QPushButton("&Draw")
			#self.draw_button.clicked.connect(self.on_draw)
			self.scan_button = QPushButton("&Scan")
			self.scan_button.clicked.connect(self.on_scan)


			
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
			for w in [  self.reinit_button, self.scan_button]:
					#        slider_label, self.slider]:
					hbox.addWidget(w)
					hbox.setAlignment(w, Qt.AlignVCenter)
			
			
			#self.paramtabs = QParamArea(self, self.msparms)
			
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

			#bighbox = QHBoxLayout()
			#bighbox.addLayout(vbox)
			#bighbox.addLayout(phbox) 
			#bighbox.addWidget(self.paramtabs)
			
			self.setLayout(vbox)
			self.init_thread = QThread()
			self.progress_thread = QThread()

			self.init_thread_o = initThread(None, self.logl, forRun=False)
			self.scan_button.setEnabled(False)
			self.scanning = False
			self.init = False
			self.anns = []
			self.on_draw()
			self.on_init()
		
		def logl(self,*args):
			strl = [ str(x) for x in args] 
			news = ''.join(strl)
			if	self.main.logText:
				self.main.logline.emit(news)
			
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
				
		def showNewScans(self, rs):
				self.spectrum = rs
				self.on_draw()
				self.peak_detect()
				
		def peak_detect(self):
			self.maxima = [None, None, None]
			self.minima = [None, None, None]
			self.spline = [None, None, None]
			self.fwhm = [0.0, 0.0, 0.0]
			self.maxab =  [0.0, 0.0, 0.0]
			for x in range(3):
				i = self.spectrum[x].getSpectrum()['ions']
				self.maxab[x]=i['abundance'].max()
				maxtab, mintab = peakdetect.peakdet(i['abundance'],(i['abundance'].max() - i['abundance'].min())/100, i['m/z'])
				self.maxima[x] = pandas.DataFrame(np.array(maxtab), columns=['m/z', 'abundance'])
				if len(mintab) > 0:
					self.minima[x] = pandas.DataFrame(np.array(mintab), columns=['m/z', 'abundance'])
				#sels= []
				#for idx, r in self.maxima.iterrows():
					#sels.append((False, None, None))
				#self.sels = sels
				#from scipy.interpolate import UnivariateSpline
				self.spline[x] = scipy.interpolate.UnivariateSpline(i['m/z'],i['abundance'] - i['abundance'].max()/2,s=0)
				self.fwhm[x] = abs(self.spline[x].roots()[1]-self.spline[x].roots()[0])
				self.canvases[x].draw()
			self.draw_peak_detect()

		def draw_peak_detect(self):
			for x in range(3):
				self.plts[x].scatter(self.maxima[x]['m/z'] , self.maxima[x]['abundance'], color='blue', marker='v', picker=5)
				anns = []
				for idx, r in self.maxima[x].iterrows():
						anns.append(self.plts[x].annotate('%i:%.2f' % ( idx+1, r['m/z']), xy=(r['m/z'] + 0.05, r['abundance'] + self.maxab[x]*0.05)))
				anns.append(self.plts[x].annotate("Ab %.0f Pw50 %.3f" % (self.maxima[x]['abundance'].max(), self.fwhm[x]) , xy=(0.5, 0.75), xycoords='axes fraction'))

				for a in self.anns:
					a.remove()
				self.anns = anns
				self.canvases[x].draw()

			
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
					self.plts[x].clear()        
					readspec.ReadSpec.axes(self.plts[x])
					self.plts[x].grid(True)
					if self.spectrum[x] != None:
						self.spectrum[x].smooth()	
						self.spectrum[x].plot(self.plts[x])
					self.canvases[x].draw()
					#self.vline = self.axes.axvline(x=0., color="k")
				
		def on_init(self):
				self.init =False
				self.reinit_button.setEnabled(False)
				self.main.statusBar().showMessage('Initializing..', 1000)
				QThread.yieldCurrentThread()
				if not self.init_thread.isRunning():
					self.init_thread_o.progress_update.connect(self.updateProgressBar)
					self.init_thread_o.init_status.connect(self.setInitialized)
					self.init_thread_o.moveToThread(self.init_thread)
					self.init_thread_o.run_init.connect(self.init_thread_o.doInit)
					self.init_thread.start()
					self.init_thread_o.run_init.emit()

				else:
					self.init_thread_o.init_msd = False
					self.init_thread_o.init_gc = False
					self.init_thread_o.init_inj = False
					self.init_thread_o.init = False
					self.init_thread_o.run_init.emit()
				
		def on_scan(self):
				self.scanning =True
				self.scan_button.setEnabled(False)
				self.main.progress.setValue(0)
				self.main.statusBar().showMessage('Scanning..', 2000)

				if not self.progress_thread.isRunning():
					self.progress_thread_o = tripleScanThread(self.hpmsd, self.msparms)
					self.progress_thread_o.progress_update.connect(self.updateProgressBar)
					self.progress_thread_o.tscan_done.connect(self.showNewScans)
					self.progress_thread_o.scan_status.connect(self.showScanStatus)
					self.progress_thread_o.scan_info.connect(self.showScanInfo)

					self.progress_thread_o.moveToThread(self.progress_thread)
					#self.progress_thread.started.connect(self.progress_thread_o.doScan)
					self.progress_thread_o.run_scan.connect(self.progress_thread_o.doScan)
					self.progress_thread.start()
					self.progress_thread_o.run_scan.emit()
				else:
					self.progress_thread_o.run_scan.emit()
					 
		 
		def setInitialized(self,ok, emsg):
				if ok:
					self.main.statusBar().showMessage('Init Done: ' + emsg, 2000)
					self.hpmsd = self.init_thread_o.getMsd()
					self.main.progress.setValue(100)
					self.scan_button.setEnabled(True)
					self.reinit_button.setEnabled(True)
					self.init = True
					#self.doConfigThread()
				else:
					self.main.statusBar().showMessage('Init Failed: ' + emsg, 2000)
					self.main.progress.setValue(0)
					
		def showScanStatus(self,ok, emsg):
				self.scan_button.setEnabled(True)
				if ok:
					self.main.statusBar().showMessage('Scan Done: ' + emsg, 2000)
					self.main.progress.setValue(100)
				else:
					self.main.statusBar().showMessage('Scan Failed: ' + emsg, 10000)
					self.main.progress.setValue(0)
				self.scanning = False
				
		def showScanInfo(self, emsg):
					self.main.statusBar().showMessage('Scan Info: ' + emsg, 4000)
	
				
		def updateProgressBar(self, maxVal):
				uv = self.main.progress.value() + maxVal
				if maxVal == 0:
					 uv = 0
				if uv > 100:
					 uv = 100
				self.main.progress.setValue(uv)

						
class QSpectrumScan(QWidget):
		def __init__(self, parent = None, main=None, params=None):
			super().__init__(parent)
			self.msparms = params
			#self.method = method
			self.main = main
			self.spectrum = None

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
			self.reinit_button.clicked.connect(self.on_init)
			self.reinit_button.setEnabled(False)

			self.draw_button = QPushButton("&Draw")
			self.draw_button.clicked.connect(self.on_draw)
			self.scan_button = QPushButton("&Scan")
			self.scan_button.clicked.connect(self.on_scan)


			
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
			
			
			self.paramtabs = QParamArea(self, self.msparms)
			
			vbox = QVBoxLayout()
			vbox.addWidget(self.mpl_toolbar)
			vbox.addWidget(self.canvas)
			vbox.addLayout(hbox)
			
			bighbox = QHBoxLayout()
			bighbox.addLayout(vbox)
			#bighbox.addLayout(phbox) 
			bighbox.addWidget(self.paramtabs)
			
			self.setLayout(bighbox)
			self.init_thread = QThread()
			self.progress_thread = QThread()

			self.init_thread_o = initThread(None, self.logl, forRun=False)
			self.scan_button.setEnabled(False)
			self.scanning = False
			self.init = False
			self.on_draw()
			self.on_init()
		
		def logl(self,*args):
			strl = [ str(x) for x in args] 
			news = ''.join(strl)
			if	self.main.logText:
				self.main.logline.emit(news)
			
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
				
		def showNewScan(self, rs):
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
					self.spectrum.plot(self.plt)
				self.canvas.draw()
				self.vline = self.plt.axvline(x=0., color="k")
				
		def on_init(self):
				self.init =False
				self.reinit_button.setEnabled(False)
				self.main.statusBar().showMessage('Initializing..', 1000)
				QThread.yieldCurrentThread()
				if not self.init_thread.isRunning():
					self.init_thread_o.progress_update.connect(self.updateProgressBar)
					self.init_thread_o.init_status.connect(self.setInitialized)
					self.init_thread_o.moveToThread(self.init_thread)
					self.init_thread_o.run_init.connect(self.init_thread_o.doInit)
					self.init_thread.start()
					self.init_thread_o.run_init.emit()

				else:
					self.init_thread_o.init_msd = False
					self.init_thread_o.init_gc = False
					self.init_thread_o.init_inj = False
					self.init_thread_o.init = False
					self.init_thread_o.run_init.emit()
				
		def on_scan(self):
				self.scanning =True
				self.scan_button.setEnabled(False)
				self.main.progress.setValue(0)
				self.main.statusBar().showMessage('Scanning..', 2000)

				if not self.progress_thread.isRunning():
					self.progress_thread_o = scanThread(self.hpmsd, self.msparms)
					self.progress_thread_o.progress_update.connect(self.updateProgressBar)
					self.progress_thread_o.scan_done.connect(self.showNewScan)
					self.progress_thread_o.scan_status.connect(self.showScanStatus)
					self.progress_thread_o.moveToThread(self.progress_thread)
					#self.progress_thread.started.connect(self.progress_thread_o.doScan)
					self.progress_thread_o.run_scan.connect(self.progress_thread_o.doScan)
					self.progress_thread.start()
					self.progress_thread_o.run_scan.emit()
				else:
					self.progress_thread_o.run_scan.emit()
				
		def doGetConfig(self):
				if (not self.scanning) and self.init:
					self.main.progress.setValue(0)
					self.scan_button.setEnabled(False)
					self.reinit_button.setEnabled(False)
					self.config_thread_o.run_config.emit()

		def doConfigThread(self):
				self.config_thread = QThread()
				self.config_thread_o = configThread(self.hpmsd, self.logl)
				self.config_thread_o.progress_update.connect(self.updateProgressBar)
				self.config_thread_o.config_update.connect(self.onConfigUpdate)
				self.config_thread_o.moveToThread(self.config_thread)
				#self.config_thread.started.connect(self.config_thread.run)
				self.config_thread_o.run_config.connect(self.config_thread_o.do_gc)

				self.config_thread.start()
				self.config_timer = QTimer()
				self.config_timer.setSingleShot(False)        
				self.config_timer.timeout.connect(self.doGetConfig)
				self.config_timer.start(5000)
				
		def onConfigUpdate(self, conf):
				self.scan_button.setEnabled(True)
				self.reinit_button.setEnabled(True)

				if not 'Error' in conf:
					self.paramtabs.config_panel(conf)
				else:
					self.main.statusBar().showMessage('Config Error: ' + conf['Error'], 2000)
					self.main.progress.setValue(0)
					 
		 
		def setInitialized(self,ok, emsg):
				if ok:
					self.main.statusBar().showMessage('Init Done: ' + emsg, 2000)
					self.hpmsd = self.init_thread_o.getMsd()
					self.main.progress.setValue(100)
					self.scan_button.setEnabled(True)
					self.reinit_button.setEnabled(True)
					self.init = True
					self.doConfigThread()
				else:
					self.main.statusBar().showMessage('Init Failed: ' + emsg, 2000)
					self.main.progress.setValue(0)
					
		def showScanStatus(self,ok, emsg):
				self.scan_button.setEnabled(True)
				if ok:
					self.main.statusBar().showMessage('Scan Done: ' + emsg, 2000)
					self.main.progress.setValue(100)
				else:
					self.main.statusBar().showMessage('Scan Failed: ' + emsg, 2000)
					self.main.progress.setValue(0)
				self.scanning = False
						
		def updateProgressBar(self, maxVal):
				uv = self.main.progress.value() + maxVal
				if maxVal == 0:
					 uv = 0
				if uv > 100:
					 uv = 100
				self.main.progress.setValue(uv)
					 
			
				

class QInstControl(QWidget):
		def __init__(self, parent = None, main=None, method=None, methname =''):
			super().__init__(parent)
			self.method = method
			self.methname = methname
			self.fname = ''
			
			self.main = main

			self.msled = Led(self, on_color=Led.green, shape=Led.capsule)
			self.gcled = Led(self, on_color=Led.green, shape=Led.capsule)
			self.injled = Led(self, on_color=Led.green, shape=Led.capsule)
			self.logfile = open('MSD.LOG', "a+")
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

			grid = QGridLayout()
			grid.addWidget(QLabel('HP5971'), 0, 1)
			grid.addWidget(QLabel('HP5890'), 0, 2)
			grid.addWidget(QLabel('HP7673'), 0, 3)

			grid.addWidget(self.msled, 1, 1)
			grid.addWidget(self.gcled, 1, 2)
			grid.addWidget(self.injled, 1, 3)
			
			vbox.addLayout(grid)
			vbox.addWidget(dummy)
			hb2 = QHBoxLayout()
			self.path_field = QLineEdit()
			self.path_field.editingFinished.connect(self.setPath)
			self.path_button = QPushButton ('Browse')
			self.path_button.clicked.connect(self.fileDlg)
			
			hb2.addWidget(self.path_field)
			hb2.addWidget(self.path_button)
			
			vbox.addLayout(hb2)
			
			self.reinit_button =QPushButton('Reinit')
			self.reinit_button.clicked.connect(self.on_init)

			vbox.addWidget(self.reinit_button)
			self.run_button = QPushButton('Run')
			self.run_button.clicked.connect(self.on_run)

			vbox.addWidget(self.run_button)
			self.stop_button = QPushButton('Stop')
			self.stop_button.clicked.connect(self.on_stop)

			vbox.addWidget(self.stop_button)
			
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
			
			self.gc_status_area = QStatusArea(self, heading="GC")
			vboxsgc.addWidget(self.gc_status_area)
			
			dummy = QGroupBox()
			vboxsgc.addWidget(dummy)
			
			hbox.addLayout(vboxsms)
			hbox.addLayout(vboxsgc)
			
			
			#hbox.addLayout (vboxscan)
			
			self.setLayout(hbox)
			
			self.progress_thread = QThread()
			self.progress_thread_o = None
			
			self.init_thread = QThread()
			self.init_thread_o = None
			
			self.status_thread = QThread()
			self.status_thread_o = None
			
			self.on_init()
			self.running = False
			self.last_rt = 0.0
			self.on_draw()
			
		def setPath(self):
			self.fname = self.path_field.text()
		
		def fileDlg(self):
			file_choices = "MS (*.MS)|*.ms"
			path, choice = QFileDialog.getSaveFileName(self, 
										'Set results file', '', 
										file_choices)
			self.fname = path
			self.path_field.setText(path)
			
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

		def on_init(self):
				#self.logl("Reinit")
				self.init =False
				self.reinit_button.setEnabled(False)
				self.run_button.setEnabled(False)
				self.msled.turn_off()
				self.gcled.turn_off()
				self.injled.turn_off()
				self.main.statusBar().showMessage('Initializing..', 1000)
				QThread.yieldCurrentThread()
				
				if not self.init_thread.isRunning():
					#self.logl("No init Thread")
					self.init_thread_o = initThread(self.method, self.logl, forRun=True)
					self.init_thread_o.progress_update.connect(self.updateProgressBar)
					self.init_thread_o.inst_status.connect(self.instStatus)
					self.init_thread_o.init_status.connect(self.setInitialized)
					self.init_thread_o.inst_status.connect(self.instStatus)
					self.init_thread_o.moveToThread(self.init_thread)
					self.init_thread_o.run_init.connect(self.init_thread_o.doInit)
					#self.init_thread.started.connect(self.init_thread_o.doInit)
					self.init_thread.start()
					self.init_thread_o.run_init.emit()
				else:
					#self.logl("Restart Init Thread")
					self.init_thread_o.init_msd = False
					self.init_thread_o.init_gc = False
					self.init_thread_o.init_inj = False
					self.init_thread_o.init = False
					self.init_thread_o.run_init.emit()
					
		def on_run(self):
			if len(self.fname) > 0:
				self.running =True
				self.run_button.setEnabled(False)
				self.main.progress.setValue(0)
				self.main.statusBar().showMessage('Run..', 2000)
				if not self.progress_thread.isRunning():
					
					self.progress_thread_o = runProgressThread(self.fname, self.methname, self.hpmsd, self.hpgc, self.hpinj, self.method, self.logl)
					self.progress_thread_o.progress_update.connect(self.updateProgressBar)
					self.progress_thread_o.run_spec.connect(self.showNewScan)
					self.progress_thread_o.run_done.connect(self.showRunStatus)
					self.progress_thread_o.ms_status_update.connect(self.onStatusUpdate)
					self.progress_thread_o.gc_status_update.connect(self.onStatusUpdateGc)
					self.progress_thread_o.inj_status_update.connect(self.onStatusUpdateInj)

					self.progress_thread_o.moveToThread(self.progress_thread)
					#self.progress_thread.started.connect(self.progress_thread_o.doRun)
					self.progress_thread_o.run_progress.connect(self.progress_thread_o.doRun)
					self.progress_thread_o.run_stop.connect(self.progress_thread_o.endRun)
					#self.run_stop.connect(self.endRun)

					self.progress_thread.start()
					self.progress_thread_o.run_progress.emit()

				else:
					self.progress_thread_o.run_progress.emit()
					
		def on_stop(self):
			if self.progress_thread_o:
				self.progress_thread_o.run_stop.emit()

			
		def instStatus(self, hpms, hpgc, hpinj):
			#print(hpms, hpgc, hpinj)
			self.msled.turn_on(hpms)
			self.gcled.turn_on(hpgc)
			self.injled.turn_on(hpinj)

		def setInitialized(self,ok, emsg):
				if ok:
					self.main.statusBar().showMessage('Init Done: ' + emsg, 2000)
					self.hpmsd = self.init_thread_o.getMsd()
					self.hpgc = self.init_thread_o.getGc()
					self.hpinj = self.init_thread_o.getInj()

					self.main.progress.setValue(100)
					self.run_button.setEnabled(True)
					self.reinit_button.setEnabled(True)
					self.init = True
					self.doStatusThread()
				else:
					self.main.statusBar().showMessage('Init Failed: ' + emsg, 2000)
					self.main.progress.setValue(0)
		
		def updateProgressBar(self, maxVal):
			uv = self.main.progress.value() + maxVal
			if maxVal == 0:
				 uv = 0
			if uv > 100:
				 uv = 100
			self.main.progress.setValue(uv)
			
		def doStatusThread(self):
			if not self.status_thread.isRunning():
				self.status_thread_o = statusThread(self.hpmsd, self.hpgc, self.logl)
				self.status_thread_o.progress_update.connect(self.updateProgressBar)
				self.status_thread_o.ms_status_update.connect(self.onStatusUpdate)
				self.status_thread_o.gc_status_update.connect(self.onStatusUpdateGc)

				self.status_thread_o.moveToThread(self.status_thread)
				self.status_thread_o.run_status.connect(self.status_thread_o.do_st)
				self.status_thread.start()
			self.status_timer = QTimer()
			self.status_timer.setSingleShot(False)        
			self.status_timer.timeout.connect(self.doGetStatus)
			self.status_timer.start(5000)
			
		
		def doGetStatus(self):
				if (not self.running) and self.init:
					self.main.progress.setValue(0)
					self.run_button.setEnabled(False)
					self.reinit_button.setEnabled(False)
					self.status_thread_o.run_status.emit(True)
				
		def onStatusUpdate(self, conf):
				if not self.running:
					self.run_button.setEnabled(True)
					self.reinit_button.setEnabled(True)

				if not 'Error' in conf:
					self.ms_status_area.status_panel(conf)
					#self.on_draw()

				else:
					self.main.statusBar().showMessage('Status  Error: ' + conf['Error'], 10000)
					self.main.progress.setValue(0)

		def onStatusUpdateGc(self, conf):
				if not self.running:
					self.run_button.setEnabled(True)
					self.reinit_button.setEnabled(True)

				if not 'Error' in conf:
					self.gc_status_area.status_panel(conf)
					#self.on_draw()

				else:
					self.main.statusBar().showMessage('Status Error: ' + conf['Error'], 10000)
					self.main.progress.setValue(0)

		def onStatusUpdateInj(self, conf):
				if not 'Error' in conf:
					self.inj_status_area.status_panel(conf)
					#self.on_draw()
				else:
					self.main.statusBar().showMessage('Status Error: ' + conf['Error'], 10000)
					self.main.progress.setValue(0)

		def showRunStatus(self,ok, emsg):
				self.run_button.setEnabled(True)
				if ok:
					self.main.statusBar().showMessage('Run Done: ' + emsg, 2000)
					self.hpmsd = self.init_thread_o.getMsd()
					self.hpgc = self.init_thread_o.getGc()
					self.main.progress.setValue(100)
				else:
					self.main.statusBar().showMessage('Scan Failed: ' + emsg, 10000)
					self.main.progress.setValue(0)
				self.running = False				
		
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

	
		def showNewScan(self, rs):
			self.spectrum = rs	
			ti = self.spectrum.getTotIons()
			rt = self.spectrum.getSpectrum()['RetTime']
			self.totI.append((rt, ti))
			if rt - self.last_rt > 0.1:
				self.on_draw()
				self.last_rt = rt
			
def main():
	app = QApplication(sys.argv)
	form = AppForm()
	form.show()
	app.exec_()


if __name__ == "__main__":
	main()


