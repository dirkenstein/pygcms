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

import msfileread as msfr
from pyqt_led import Led
import tune2meth
import readspec

import peakdetect
import numpy as np
import pandas
import scipy
import scipy.interpolate

from qdictparms import QParamArea, QStatusArea
from specthreads import threadRunner, initThread, statusThread, scanThread, tripleScanThread, runProgressThread

class AppForm(QMainWindow):
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
							self.scanWindow.ms_status_area.updatepboxes()
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
				self.scanWindow.ms_status_area.updatepboxes()
			self.setCurrentFile(path)
			
		def save_spectrum(self):
				file_choices = "BIN (*.bin)|*.bin"
				
				path, choice = QFileDialog.getSaveFileName(self, 
												'Save file', '', 
												file_choices)
				if path and self.scanWindow:
						f = open(path, "w+b");
						f.write(self.scanWindow.spectrum.getData())
						
		
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
				msg = """ 
 *          PySpec 0.1			
 *HP 5890/ 5971 GC/MS control program:
 *Pretty much implements all the features 
 *In the Diagnostics/Vacuum Control Screen
 *Obviously needs a 5971 connected
 *on a GPIB bus accessible to PyVISA
 *can also control a 5890 and 7673 autosampler
 *  (C) 2019 Dirk Niggemann
"""
				QMessageBox.about(self, "About PySpec", msg.strip())
	
	
		def loadparam(self):
				f = open("parms.json", "r")
				tparms = f.read()
				self.msparms = json.loads(tparms)
		def tune_window(self):
			if not self.tuningWindow:
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
			if self.scan_mdi:
				self.scan_mdi.close()
			if self.inst_mdi:
				self.inst_mdi.close()
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
			if self.tuning_mdi:
				self.tuning_mdi.close()
			if self.inst_mdi:
				self.inst_mdi.close()
		def updMethodTabs(self):
			for s in self.paramTabList:
				s.updatepboxes()
		def method_window(self):
			if not self.method:
				self.statusBar().showMessage('Error: No Method Loaded', 10000)
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
				self.statusBar().showMessage('Error: No Method Loaded', 10000)
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
				if self.tuning_mdi:
					self.tuning_mdi.close()
				if self.scan_mdi:
					self.scan_mdi.close()
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
				self.status_text = QLabel("PySpec 0.1")
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
		def __init__(self, parent = None, main=None, params=None):
			super().__init__()
			#self.msparms = params
			self.closed = False
			self.main = main
			self.spectrum = [None, None, None]
			self.ledbox = QLedPanel()

			self.runner = threadRunner(self, main, None, params, None, None, tripleScanThread, self.showNewScan, logl=self.logl, forRun=False)
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
			self.reinit_button.clicked.connect(self.runner.on_init)
			self.reinit_button.setEnabled(False)

			#self.draw_button = QPushButton("&Draw")
			#self.draw_button.clicked.connect(self.on_draw)
			self.scan_button = QPushButton("&Scan")
			self.scan_button.clicked.connect(self.runner.on_scan)

			self.run_button = None

			
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
			
			
			self.ms_status_area = QParamArea(self, params)
			
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
			vbox.addWidget(self.ledbox)
			vbox.addLayout(hboxg)
			vbox.addLayout(hbox)

			#bighbox = QHBoxLayout()
			#bighbox.addLayout(vbox)
			#bighbox.addLayout(phbox) 
			#bighbox.addWidget(self.paramtabs)
			
			self.setLayout(vbox)
			self.scan_button.setEnabled(False)
			self.anns = []
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
				
		def showNewScan(self, rs):
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
						f = open('mass%i.bin' % x, "w+b")
						f.write(self.spectrum[x].getData())
						
						#self.spectrum[x].smooth()	
						self.spectrum[x].plot(self.plts[x])
					self.canvases[x].draw()
					#self.vline = self.axes.axvline(x=0., color="k")
		
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
			print ("tuneWindow show")
			if self.closed:
				self.runner.on_init()
				self.closed = False

			event.accept()
						
class QSpectrumScan(QWidget, Loggable):
		def __init__(self, parent = None, main=None, params=None):
			super().__init__()
			#self.msparms = params
			#self.method = method
			self.closed = False
			self.ledbox = QLedPanel()
			self.main = main
			self.spectrum = None

			self.runner = threadRunner(self, main, None, params, None, None, scanThread, self.showNewScan, logl=self.logl, forRun=False)
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
			
			
			self.ms_status_area = QParamArea(self, params)
			
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
			bighbox.addLayout(vbox3)

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
					self.spectrum[0].plot(self.plt)
				self.canvas.draw()
				self.vline = self.plt.axvline(x=0., color="k")
		
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
			print ("ScanWindow show")
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
		def __init__(self, parent = None, main=None, method=None, methname =''):
			super().__init__(parent)
			self.method = method
			self.methname = methname
			self.fname = ''
			self.closed = False
			self.main = main
			self.runner = threadRunner(self, main, method, None, self.methname, self.fname, None, self.showNewScan, logl=self.logl, forRun=True)

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
			self.path_field = QLineEdit()
			self.path_field.editingFinished.connect(self.setPath)
			self.path_button = QPushButton ('Browse')
			self.path_button.clicked.connect(self.fileDlg)
			
			hb2.addWidget(self.path_field)
			hb2.addWidget(self.path_button)
			
			vbox.addLayout(hb2)
			
			self.reinit_button =QPushButton('Reinit')
			self.reinit_button.clicked.connect(self.runner.on_init)
			vbox.addWidget(self.reinit_button)
			
			self.run_button = QPushButton('Run')
			self.run_button.clicked.connect(self.runner.on_run)
			vbox.addWidget(self.run_button)
			
			self.stop_button = QPushButton('Stop')
			self.stop_button.clicked.connect(self.runner.on_stop)
			vbox.addWidget(self.stop_button)
			
			self.scan_button = None
			
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
			print ("InstWindow show")
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
		
		
def main():
	app = QApplication(sys.argv)
	form = AppForm()
	form.show()
	app.exec_()


if __name__ == "__main__":
	main()

