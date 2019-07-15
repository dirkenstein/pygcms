import sys
import operator 
#from time import time
import time
import codecs 
import re

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pygcms.msfile.msfileread as mr
import pygcms.msfile.readspec as readspec
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pygcms.calc.putil as putil
import peakutils
import numpy as np
import pandas
import scipy
import scipy.interpolate
import copy
from mol import skeleton
import os

class MainWindow(QMainWindow):
	count = 0
	MaxRecentFiles = 5

	def __init__(self, parent = None):
			super(MainWindow, self).__init__(parent)
			self.mdi = QMdiArea()
			self.setCentralWidget(self.mdi)
			self.recentFileActs = []

			for i in range(MainWindow.MaxRecentFiles):
				self.recentFileActs.append(
				QAction(self, visible=False,
				triggered=self.recentfileaction))
			bar = self.menuBar()
			app = bar.addMenu("Application")
			prefact = app.addAction("Preferences")
			prefact.triggered.connect(self.preferences)
			file = bar.addMenu("&File")
			file.addAction("Load")
			file.addAction("Save MSP")
			file.addAction("Save Raw")

			self.separatorAct = file.addSeparator()
			for i in range(MainWindow.MaxRecentFiles):
				file.addAction(self.recentFileActs[i])
				
			file.addSeparator()
			file.triggered[QAction].connect(self.fileaction)
			self.updateRecentFileActions()
			window = bar.addMenu("&Window")
			#window.addAction("New")
			window.addAction("cascade")
			window.addAction("Tiled")
			window.triggered[QAction].connect(self.windowaction)
			self.create_status_bar()
			#self.mdi.subWindowActivated.connect(self.updateMenus)
			chrom = bar.addMenu("&Chromatogram")
			chrom.addAction("Peak Find")
			chrom.addAction("Baseline")
			chrom.addAction("Autointegrate")
			chrom.triggered[QAction].connect(self.doChromAction)
			spec = bar.addMenu("Spectrum")
			subact = spec.addAction("Subtract")
			subact.triggered.connect(self.subtractAction)
			nistact = spec.addAction("Launch NIST")
			nistact.triggered.connect(self.launchNISTAction)
			hlp = bar.addMenu("&Help")
			aboutact = hlp.addAction("About")
			aboutact.triggered.connect(self.on_about)

			self.paths = QPathSettings() 
			self.colors = QColorSettings()

			self.setWindowTitle("MSDisplay")
			self.registers = []
			self.running_subtract = False
	
	def on_about(self):
		msg = """
       MSDisplay
 * HP Chemstation .MS Reader:
 *Reads .MS spectrum files
 *Provides basic chromatogram analysis
 * (C)2019 Dirk Niggemann
"""
		QMessageBox.about(self, "About MSDisplay", msg.strip())
	
			
	def doChromAction(self, q):
			act = self.activeMdiChild()
			if act is not None:
				if q.text() == "Peak Find":
					act.peak_detect()
				elif q.text() == "Baseline":
					act.dobaseline()
				elif q.text() == "Autointegrate":
					act.autointegrate()
			
	def create_status_bar(self):
				self.status_text = QLabel("MS File display")
				self.progress = QProgressBar(self)
				#self.progress.setGeometry(, 80, 250, 20)
				self.statusBar().addWidget(self.status_text, 1)
				self.statusBar().addWidget(self.progress, 2)

	def windowaction(self, q):
			print ("triggered")
			
			if q.text() == "New":
				MainWindow.count = MainWindow.count+1
				sub = QMdiSubWindow()
				sub.setWidget(QTextEdit())
				sub.setWindowTitle("subwindow"+str(MainWindow.count))
				self.mdi.addSubWindow(sub)
				sub.show()

			if q.text() == "cascade":
				self.mdi.cascadeSubWindows()

			if q.text() == "Tiled":
				self.mdi.tileSubWindows()
	def recentfileaction(self, q):
				 action = self.sender()
				 if action:
					 self.loadMSFile(action.data())
	def fileaction(self, q):
			print ("triggered: ", q)

			if q.text() == "Load":
				file_choices = "MS (*.ms);;All Files (*)"
				
				path, choices = QFileDialog.getOpenFileName(self, 
												'Load file', '', 
												file_choices)
				if path:
					self.loadMSFile(path)
			if q.text() == "Save MSP":
				file_choices = "MSP (*.msp)"
				
				path, choice = QFileDialog.getSaveFileName(self, 
											'Save file', '', 
											file_choices)
				if path:
					self.saveMSPFile(path)
			if q.text() == "Save Raw":
				file_choices = "Raw (*.bin)"
				
				path, choice = QFileDialog.getSaveFileName(self, 
											'Save file', '', 
											file_choices)
				if path:
					self.saveRawFile(path)
	def launchNISTAction(self):
			self.launchNIST(True)
	def launchNIST(self, bgnd):
		win = self.getActiveTicArea()
		self.tic_win = win
		if win is not None:
			nistpath = self.paths.getPath('nistpath')
			#nistpath = '/Volumes/[C] Windows 7 1/NIST08/MSSEARCH/'

			#filepath = 'C:\\tmp\\'
			filepath = self.paths.getPath('filepath') #'C:\\MSREAD\\'

			specfile = self.paths.getPath('specfile') #filespec.fil
			usepath = self.paths.getPath('usepath') #/Users/dirk/.wine/drive_c/MSREAD/
			#usepath = '/Volumes/[C] Windows 7 1/MSREAD/'
			nistapp = self.paths.getPath('nistapp') #'nistms\$.exe'
			#winecmd ='open /Applications/Wine\ Stable.app/ --args '
			winecmd= self.paths.getPath('winecmd') #'/Applications/Wine\ Stable.app/Contents/Resources/wine/bin/wine '
			readyfile = self.paths.getPath('readyfile')
			resultfile = self.paths.getPath('resultfile')
			fname = 'datafile%i.msp' % MainWindow.count
			if bgnd:
				if os.path.isfile(nistpath + readyfile):
					 os.remove(nistpath + readyfile)
				if os.path.isfile(nistpath + resultfile):
					os.remove(nistpath + resultfile)
			self.saveMSPFile(usepath + fname)

			inifile = open(nistpath + 'autoimp.msd', "w")
			inifile.write(filepath + specfile + '\n')
			inifile.close()
			
			strfile = open (nistpath + 'autoimp.str', "w")
			strfile.write ('"MS Read" "' + filepath+'MSREAD.BAT" "%1"\n')
			strfile.close()
			
			specf  = open(usepath + 'filespec.fil', "w")
			specf.write (filepath + fname + ' OVERWRITE\n')
			specf.close()
			if bgnd:
				#time.sleep(1)
				os.system(winecmd + nistpath + nistapp + ' /instrument /par=2')
				self.file_timer = QTimer()
				self.file_timer.setSingleShot(False)        
				self.file_timer.timeout.connect(self.onFileTimer)
				self.file_timer.start(1000)
			else:
				os.system(winecmd + nistpath + nistapp + ' /INSTRUMENT')
	def onFileTimer(self):
		readyfile = self.paths.getPath('readyfile')
		resultfile = self.paths.getPath('resultfile')
		nistpath = self.paths.getPath('nistpath')
		if os.path.isfile(nistpath + readyfile):
			self.file_timer.stop()
			srchfile = codecs.open(nistpath + resultfile, 'r', 'cp437') #'iso-8859-1'
			
			te = []
			for x in srchfile:
				te.append(x)
			ts = ''.join(te)
			res = self.parseRes(ts)
			self.tic_win.compoundsList(res)
	def preferences(self):
		#MainWindow.count = MainWindow.count+1
		prefdlg = QPrefsDialog(self.paths, self.colors, self)
		self.paths.setParent(prefdlg)
		self.colors.setParent(prefdlg)

		prefdlg.show()
		
	def newTextWindow(self, t):
		MainWindow.count = MainWindow.count+1
		sub = QMdiSubWindow()
		te = QTextEdit(t)
		sub.setWidget(te)
		sub.setWindowTitle("Search Results "+str(MainWindow.count))
		self.mdi.addSubWindow(sub)
		sub.show()
	def parseRes(self, t):
		rdi = {}
		hhdi = []
		for l in t.splitlines():
			ls = l.strip()
			if ls.startswith('Unknown:'):
					if len(hhdi) > 0:
						rdi.update({ cn : { 'LibFact':lf, 'Hits': hhdi }})
						hhdi = []
					libstr = 'Compound in Library Factor ='
					p = ls.find(libstr)
					cn = ls[9:p].strip()
					#print(cn)
					lf = int(ls[p+len(libstr):].strip())
					#print (lf)
					
			elif ls.startswith('Hit '):
				hdi = {}
				desc = ls[4:].split(';')
				first = True
				for t in desc:
					vs = t.split(':')
					if first:
						 first = False
						 hn = vs[0].strip()
						 hdi.update({'Hit' : hn})
						 n = 'Name'
						 v = vs[1].strip().strip('<>')
					else:
						if len(vs) == 1:
							n = 'Formula'
							v = vs[0].strip().strip('<>')
						else:
							n = vs[0].strip()
							v = vs[1].strip().strip('<>')
					hdi.update({n :v })
				hhdi.append(hdi)
			else:
				pass
		if len(hhdi) > 0:
			rdi.update({ cn : { 'LibFact':lf, 'Hits': hhdi }})
		return rdi
	 
			
	def getActiveTicArea(self):
			act = self.activeMdiChild()
			if isinstance(act, QPeaksWindow):
				win = act.ticArea
			elif isinstance(act, QTICArea):
				win = act
			else:
				win = None
			return win
	def saveMSPFile(self, path):
					act = self.activeMdiChild()
					if isinstance(act, QSpectrumArea):
						f = open(path, "w");
						act.spectrum.saveMsp(f, act.rt, "UNK-1")
						f.close()
					else:
						win = self.getActiveTicArea()
						if win is not None and win.maxima is not None:
							f = open(path, "w");
							sel = True
							for idx, m in win.maxima['retention_time'].iteritems():
								if win.peakw is not None:
									sel = win.peakw.table_model.isSelected(idx)
								else:
									sel, mkr, fil = win.sels[idx]
								if sel:
									win.runfile.setUseNew(win.subtract_cb.isChecked())
									tic = win.runfile.nearest_tic(m)                    
									s = win.runfile.getSpectra()
									rt, spectrum=s[tic.index[0]]
									spectrum.saveMsp(f, rt, "UNK-%i" % idx)
							f.close()
	def saveRawFile(self, path):
					act = self.activeMdiChild()
					if isinstance(act, QSpectrumArea):
						f = open(path, "wb");
						act.spectrum.saveRaw(f)
						f.close					
	def loadMSFile(self, path):
				#self.canvas.print_figure(path, dpi=self.dpi)
				theRun = mr.ReadMSFile(path)
				self.statusBar().showMessage('Loaded %s' % path, 2000)
				#self.on_draw()
				MainWindow.count = MainWindow.count+1
				sub = QMdiSubWindow()
				submain = QTICArea(sub, self)
				submain.setFile(theRun)
				submain.setPath(path)
				sub.setWidget(submain)
				sub.setWindowTitle(str(MainWindow.count) + ": " + self.strippedName(path))
				self.mdi.addSubWindow(sub)
				sub.show()
				self.setCurrentFile(path)
				
	def activeMdiChild(self):
				activeSubWindow = self.mdi.activeSubWindow()
				if activeSubWindow:
						return activeSubWindow.widget()
				return None
	def strippedName(self, fullFileName):
				return QFileInfo(fullFileName).fileName()
	def setCurrentFile(self, fileName):
				self.curFile = fileName
				#if self.curFile:
				#    self.setWindowTitle("%s - Recent Files" % self.strippedName(self.curFile))
				#else:
				#    self.setWindowTitle("Recent Files")

				settings = QSettings('Muppetastic', 'MSRead')
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
				settings = QSettings('Muppetastic', 'MSRead')
				files = settings.value('recentFileList')
				if files:
					l = len(files)
				else:
					l = 0
				numRecentFiles = min(l, MainWindow.MaxRecentFiles)


				for i in range(numRecentFiles):
						text = "&%d %s" % (i + 1, self.strippedName(files[i]))
						self.recentFileActs[i].setText(text)
						self.recentFileActs[i].setData(files[i])
						self.recentFileActs[i].setVisible(True)

				for j in range(numRecentFiles, MainWindow.MaxRecentFiles):
						self.recentFileActs[j].setVisible(False)

				self.separatorAct.setVisible((numRecentFiles > 0))
	def subtractAction(self):
			act = self.activeMdiChild()
			if act is not None and not self.running_subtract:
				if isinstance(act, QSpectrumArea) or isinstance(act, QTICArea):
					self.registers.append(act)
				if len(self.registers) == 2:
					a1 = self.registers[0]
					a2 = self.registers[1]
					t1 = isinstance(a1, QSpectrumArea)
					t2 = isinstance(a2, QSpectrumArea)
					if t2:
						t = subtractThread(a1, a2)
						self.statusBar().showMessage('Subtracting..', 2000)
						t.progress_update.connect(self.updateProgressBar)
						t.subtract_done.connect(self.onSubtractComplete)
						#t.scan_status.connect(self.showScanStatus)
						self.running_subtract = True
						t.start(priority=QThread.LowestPriority)
					else:
						self.statusBar().showMessage('Can''t subtract TIC from spectrum', 2000)
						registers = []
				else:
					self.statusBar().showMessage("Added to registers")
	def onSubtractComplete(self, res):
				a1 = self.registers[0]
				a2 = self.registers[1]
				t1 = isinstance(a1, QSpectrumArea)
				t2 = isinstance(a2, QSpectrumArea) 
				self.running_subtract = False

				registers = []
				if t1:
					a1.launchSpectrumArea(res[0], a1.getRT(), ' Sub:' + str(a2.getRT()) + ': ')
	def updateProgressBar(self, maxVal):
				uv = self.progress.value() + maxVal
				if maxVal == 0:
					 uv = 0
				if uv > 100:
					 uv = 100
				self.progress.setValue(uv)


class QTICArea(QWidget):
	def __init__(self, parent = None, main=None):
			super().__init__(parent)
			self.dpi = 100
			self.fig = Figure((6.0, 4.0), dpi=self.dpi)
			self.canvas = FigureCanvas(self.fig)
			self.canvas.setParent(parent)
			self.axes = self.fig.add_subplot(111)
			#self.plt = self.fig.add_subplot(111)
				# Bind the 'pick' event for clicking on one of the bars
			#
			#self.canvas.mpl_connect('pick_event', self.on_pick)
			self.canvas.mpl_connect('button_press_event', self.on_click)
			self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
			self.canvas.mpl_connect('pick_event', self.on_pick)

			# Create the navigation toolbar, tied to the canvas
			#
			self.mpl_toolbar = NavigationToolbar(self.canvas, self)
			
			self.grid_cb = QCheckBox("Show &Grid")
			self.grid_cb.setChecked(True)
			self.grid_cb.stateChanged.connect(self.on_draw)
			self.minima_cb = QCheckBox("Show &Minima")
			self.minima_cb.setChecked(False)
			self.minima_cb.stateChanged.connect(self.on_draw)
			self.baseline_cb = QCheckBox("Show &Baseline")
			self.baseline_cb.setChecked(True)
			self.baseline_cb.stateChanged.connect(self.on_draw)
			self.areas_cb = QCheckBox("Show &Areas")
			self.areas_cb.setChecked(True)
			self.areas_cb.stateChanged.connect(self.on_draw)
			self.tic_cb = QCheckBox("Show Computed &TIC")
			self.tic_cb.setChecked(False)
			self.tic_cb.stateChanged.connect(self.on_draw)
			self.subtract_cb = QCheckBox("Subtracted Spectra")
			self.subtract_cb.setChecked(False)
			self.subtract_cb.stateChanged.connect(self.on_draw)
			self.subtract_cb.hide()
			self.slider_label = QLabel('Baseline Degree :')
			self.slider = QSlider(Qt.Horizontal)
			self.slider.setRange(1, 10)
			self.slider.setValue(6)
			self.slider.setTracking(True)
			self.slider.setTickInterval(1)
			self.slider.setTickPosition(QSlider.TicksBothSides)
			self.slider.valueChanged.connect(self.redo_baseline)
			
			self.main = main
			hbox = QHBoxLayout()
			hbox.addWidget(self.grid_cb)
			hbox.addWidget(self.minima_cb)
			hbox.addWidget(self.baseline_cb)
			hbox.addWidget(self.areas_cb)
			hbox.addWidget(self.tic_cb)
			hbox.addWidget(self.subtract_cb)
			
			sbox = QHBoxLayout()
			sbox.addWidget(self.slider_label)
			sbox.addWidget(self.slider)

			cbox = QVBoxLayout()
			cbox.addLayout(hbox)
			cbox.addLayout(sbox)
			
			vbox = QVBoxLayout()
			vbox.addWidget(self.mpl_toolbar)
			vbox.addWidget(self.canvas)
			vbox.addLayout(cbox)
			self.setLayout(vbox)
			self.anns = []
			#self.setCentralWidget(self.main_frame)
			self.maxima = None
			self.base_abundance = None
			self.peakw = None
			self.ranges = None
			self.path = ""
			self.baseline =None
			self.baseline_plt =None
			self.baseline_order = 6
	def redo_baseline(self):
			self.baseline_order = self.slider.sliderPosition()
			self.calc_baseline()
			self.on_draw()
	def on_click(self,event):
			x = event.xdata
			y = event.ydata
			if event.dblclick:
				
				tic = self.runfile.nearest_tic(x)
				self.runfile.setUseNew(self.subtract_cb.isChecked())    
				s = self.runfile.getSpectra()
				rt, spectrum=s[tic.index[0]]
				self.launchSpectrumArea(spectrum, rt, '')
			else:
				pass
				
	def launchSpectrumArea(self, spectrum, rt, special):
			MainWindow.count = MainWindow.count+1
			sub = QMdiSubWindow()
			submain = QSpectrumArea(sub, self.main)
			submain.setSpectrum(spectrum)
			submain.setRT(rt)
			sub.setWidget(submain)
			sub.setWindowTitle(str(MainWindow.count) + ": " + special + "Spectrum at: " + str(rt) + " : " + self.main.strippedName(self.path))
			self.main.mdi.addSubWindow(sub)
			sub.show()

	def on_mouse_move(self, event):
				xe = event.xdata
				if xe is not None:
					#print('mouse x: ' + str(xe))
					#self.axes.lines = [self.axes.lines[0]]
					self.vline.set_data([xe, xe], [0,1] )
					self.canvas.draw()
	def draw_sel_peak(self, idx, dosel, flip, keep):
					hcolor = self.main.colors.getColorFor('Highlight').name()
					m = self.maxima.iloc[idx]
					sel, mkr, fil = self.sels[idx]
					if sel and flip:
						selct = False
					elif flip:
						selct = True
					elif keep:
						selct = sel
					else:
						selct = dosel
					#print(idx, sel, selct, dosel, flip, keep)
					if mkr is not None:
						mkr.remove()
						mkr = None
					if fil is not None:
						fil.remove()
						fil = None
					if selct:
						mkr = self.axes.scatter(m['retention_time'] , m['abundance'], color='red', marker='v')
						if self.ranges is not None:
							it, ie = self.ranges[idx]
							#print("Sel it, ie ",it, ie)
							i = self.runfile.getTic()
							#print(i['retention_time'][it:ie])
							#print(i['abundance'][it:ie])
							#print(self.baseline['abundance'][it:ie])
							fil = self.axes.fill_between(i['retention_time'][it:ie],i['abundance'][it:ie], self.baseline['abundance'][it:ie], color=hcolor)
						
					self.sels[idx] = (selct, mkr, fil)
					return selct
	def draw_all_sel_peaks(self, clr, value, keep):
		for idx, v in self.maxima.iterrows():
			#print(idx)
			if clr:
				sel, mkr, fil = self.sels[idx]
				self.sels[idx] = (sel, None, None)
			self.draw_sel_peak(idx, value, False, keep)
			
	def on_pick(self,event):
					#print(event)
					mkr = event.artist
					#xdata = event.get_xdata()
					#ydata = event.get_ydata()
					ind = event.ind
					#points = tuple(zip(xdata[ind], ydata[ind]))
					#print('onpick points:', ind)
					#mkr.set_color("red")
					sel = self.draw_sel_peak(ind[0], False, True, False)
					self.canvas.draw()

					if self.peakw is not None:
						self.peakw.table_model.doSelect(ind[0], sel)
					# The event received here is of the type
				# matplotlib.backend_bases.PickEvent
				#
				# It carries lots of information, of which we're using
				# only a small amount here.
				# 
					#box_points = event.artist.get_bbox().get_points()
					#msg = "You've clicked on a peak with coords:\n %s" % box_points
				
				#QMessageBox.information(self, "Click!", msg)
	def setFile(self, runfile):
			self.runfile = runfile
			self.on_draw()
	def setPath(self, path):
			self.path = path
	def on_draw(self):
			self.axes.clear()  
			self.baseline_plt = None      
			self.runfile.setComputed(self.tic_cb.isChecked())
			self.runfile.setUseNew(self.subtract_cb.isChecked())    

			mr.ReadMSFile.axes(self.axes)
			self.axes.grid(self.grid_cb.isChecked())
			
			if self.runfile != None:
				self.runfile.plot(self.axes)
			if self.maxima is not None:
				self.draw_peak_detect()
			if self.base_abundance is not None:
				self.draw_baseline()
			if self.ranges is not None:
				self.draw_integration()
			if self.maxima is not None:
				self.draw_all_sel_peaks(True, False, True)
			self.vline = self.axes.axvline(x=self.runfile.getMinX(), color="k")
			self.canvas.draw()

	def peak_detect(self):
			i = self.runfile.getTic()
			self.maxima, self.minima = putil.PUtil.peaksfr(i, 'abundance','retention_time')
			#self.maxima = pandas.DataFrame(np.array(maxtab), columns=['retention_time', 'abundance'])
			#self.minima = pandas.DataFrame(np.array(mintab), columns=['retention_time', 'abundance'])
			sels= []
			for idx, r in self.maxima.iterrows():
				sels.append((False, None, None))
			self.sels = sels

			self.draw_peak_detect()
			self.canvas.draw()

	def draw_peak_detect(self):
			self.axes.scatter(self.maxima['retention_time'] , self.maxima['abundance'], color='blue', marker='v', picker=5)
			if self.minima_cb.isChecked():
				self.axes.scatter(self.minima['retention_time'] , self.minima['abundance'], color='green', marker='^')
			anns = []
			for idx, r in self.maxima.iterrows():
					anns.append(self.axes.annotate('%i:%.2f' % ( idx+1, r['retention_time']), xy=(r['retention_time'] + 0.05, r['abundance'] + 10000)))
			for a in self.anns:
				a.remove()
			self.anns = anns
			
	def peaksList(self):
			MainWindow.count = MainWindow.count+1
			sub = QMdiSubWindow()
			submain = QPeaksWindow( self.maxima, ["Sel", "RT", "Peak", "Area", "Norm"], self,  sub, self.main)
			sub.setWidget(submain)
			sub.setWindowTitle(str(MainWindow.count) + ": Peak List: " + self.main.strippedName(self.path) )
			self.main.mdi.addSubWindow(sub)
			sub.show()
			self.peakw = submain
	def compoundsList(self, search_res):
			MainWindow.count = MainWindow.count+1
			sub = QMdiSubWindow()
			submain = QCompoundsWindow(search_res, self, sub, self.main)
			sub.setWidget(submain)
			sub.setWindowTitle(str(MainWindow.count) + ": Compound List: " + self.main.strippedName(self.path) )
			self.main.mdi.addSubWindow(sub)
			sub.show()
			self.compundw = submain
	def dobaseline(self):
			self.calc_baseline()
			self.draw_baseline()
			self.canvas.draw()
	def calc_baseline(self):
			i = self.runfile.getTic()
			self.baseline = pandas.DataFrame()
			self.baseline['retention_time'] = i['retention_time']
			self.baseline['abundance'] = peakutils.baseline(i['abundance'], deg=self.baseline_order)
			self.base_abundance = pandas.DataFrame()
			self.base_abundance['retention_time'] = i['retention_time']
			self.base_abundance['abundance'] = i['abundance'] - self.baseline['abundance']
			
	def draw_baseline(self):
			bcolor = self.main.colors.getColorFor('Baseline').name()

			if self.baseline_plt is not None:
				print(self.baseline_plt)
				self.baseline_plt.remove()
			if self.baseline_cb.isChecked():
				self.baseline_plt, = self.axes.plot(self.baseline['retention_time'],  self.baseline['abundance'], color=bcolor)
	def autointegrate(self):
				if self.maxima is None:
					self.peak_detect()
				if self.base_abundance is None:
					self.dobaseline()
				i = self.runfile.getTic()
				ib = self.base_abundance
				areas = []
				ranges=[]
				
				for m in self.maxima['retention_time']:
					nearest = putil.PUtil.strad(self.minima, 'retention_time', m)
					#print (nearest)
					strt = nearest['retention_time'].min()
					end = nearest['retention_time'].max()
					#print("RTStr, end: ", strt, end)

					istrt = putil.PUtil.nearest(i, 'retention_time', strt).iloc[0].name
					iend = putil.PUtil.nearest(i, 'retention_time', end).iloc[0].name
					if istrt == iend:
						print ('0-width peak: ',m)
						if m == self.maxima['retention_time'].iloc[-1]:
							iend = i.iloc[-1].name
							print ('last peak, fixing, iend now: ', iend)
						elif m == self.maxima['retention_time'].iloc[0]:
							istrt = i.iloc[0].name
							print ('first peak, fixing, istrt now: ', istrt)
					iend += 1 # the slicer needs one more
					ranges.append((istrt, iend))
					#print("Str, end: ", istrt, iend)
					areas.append(scipy.integrate.trapz(ib['abundance'][istrt:iend], ib['retention_time'][istrt:iend]))
				aread = pandas.DataFrame(np.array(areas), columns=['area'])
				self.maxima['area'] = aread['area']
				self.maxima['normalized_area'] =  self.maxima['area'] /  self.maxima['area'].max()
				self.ranges = ranges
				self.draw_integration()
				self.draw_all_sel_peaks(False, False, True)
				self.canvas.draw()
				self.peaksList()
	def draw_integration(self):
				i = self.runfile.getTic()
				n = 0
				cls = ['yellow', 'cyan']
				area1 = self.main.colors.getColorFor('Area1')
				area2 = self.main.colors.getColorFor('Area2')
				cls = [area1.name(), area2.name()] 
				if self.areas_cb.isChecked():
					for it, ie in self.ranges:
						#print ("it, ie ", it,ie)
						self.axes.fill_between(i['retention_time'][it:ie],i['abundance'][it:ie], self.baseline['abundance'][it:ie], color=cls[n%2])
						n += 1
					anns = []
					for idx, r in self.maxima.iterrows():
						anns.append(self.axes.annotate('%i:%.3f' % (idx+1, r['normalized_area']), xy=(r['retention_time'] + 0.05, r['abundance'] + 10000)))
					for a in self.anns:
						a.remove()
					self.anns = anns
	def subtractBaselineSpec(self, specarea, progress=None):
			print ('subtract ', self.runfile , " - ",  specarea.spectrum )
			spectra = self.runfile.getSpectra()
			subspectra = []
			np2 = specarea.spectrum.getSpectrum()['ions']
			fn = scipy.interpolate.interp1d(np2['m/z'], np2['abundance'], kind='cubic', copy=True, bounds_error=False, fill_value=0, assume_sorted=False)
			p = len(spectra)/100
			for rt, spectrum in spectra:
				np1 = spectrum.getSpectrum()['ions']
				np3 = np1.copy() 
				np3['abundance'] = np3['abundance'] - np3['m/z'].apply(fn)
				np3 = np3[np3['abundance']>0].sort_values(by='m/z', ascending=True)
				newspec = copy.deepcopy(spectrum)
				newspec.setSpectrumIons(np3)
				subspectra.append((rt, newspec))
				progress(p) 
				#QThread.yieldCurrentThread()
				#QThread.msleep (50)
				time.sleep(0)

			self.runfile.setNewSpectra( subspectra)
			self.subtract_cb.show()
			return subspectra
			
class QSpectrumArea(QTICArea):
	def __init__(self, parent = None, main=None):
			super().__init__(parent, main)
			self.minima_cb.hide()
			self.baseline_cb.hide()
			self.areas_cb.hide()
			self.tic_cb.hide()
			self.subtract_cb.hide()
	def setSpectrum(self, spec):
			self.spectrum = spec
			self.on_draw()
	def setRT(self, rt):
			self.rt = rt
	def getRT(self):
			return self.rt
	def on_draw(self):
			self.axes.clear()        
			readspec.ReadSpec.axes(self.axes)
			self.axes.grid(self.grid_cb.isChecked())
			if self.spectrum != None:
				self.spectrum.plot(self.axes)
			self.canvas.draw()
			self.vline = self.axes.axvline(x=self.spectrum.getMinX(), color="k")
	def on_click(self,event):
			x = event.xdata
			y = event.ydata
			msg = "You've clicked on a spectrum with coords:\n  click=%s button=%d,\n x=%d, y=%d,\n xdata=%f, ydata=%f" % (
					 'double' if event.dblclick else 'single', event.button,
					 event.x, event.y, event.xdata, event.ydata)
			QMessageBox.information(self, "Click!", msg)
	def peak_detect(self):
			pass
	def subtractBaselineSpec(self, specarea, progress=None):
			print ('subtract ',self.spectrum, " - " , specarea.spectrum  )
			np2 = specarea.spectrum.getSpectrum()['ions']
			np1 = self.spectrum.getSpectrum()['ions']
			#np22 = np2.copy()
			#np22['abundance'] = -np22['abundance']
			#np3 = pandas.concat((np1, np22))
			#print(np2)
			fn = scipy.interpolate.interp1d(np2['m/z'], np2['abundance'], kind='cubic', copy=True, bounds_error=False, fill_value=0, assume_sorted=False)
			np3 = np1.copy() 
			np3['abundance'] = np3['abundance'] - np3['m/z'].apply(fn)
			progress(50)
			#print(np22)
			# np3 = np1
			#np3=np3.sort_values(by='m/z', ascending=True).groupby('m/z').sum()
			np3 = np3[np3['abundance']>0].sort_values(by='m/z', ascending=True)
			subspec = copy.deepcopy(self.spectrum)
			subspec.setSpectrumIons(np3)
			progress(50)
			return [subspec]
			



class QPeaksWindow(QWidget):
		def __init__(self, peakList, header, ticArea, parent = None, main=None, *args):
				super().__init__(parent, *args)
				self.main = main
				# setGeometry(x_pos, y_pos, width, height)
				#self.setGeometry(70, 150, 1326, 582)
				self.setWindowTitle("Peak List")

				self.table_model = PeaksTableModel(self, peakList, header, ticArea)
				self.table_view = QTableView()
				#self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
				self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
				self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
				# bind cell click to a method reference
				self.table_view.clicked.connect(self.showSelection)
				self.table_view.clicked.connect(self.selectRow)

				self.table_view.setModel(self.table_model)
				# enable sorting
				self.table_view.setSortingEnabled(True)

				layout = QVBoxLayout(self)
				layout.addWidget(self.table_view)
				self.setLayout(layout)
				#self.maxima = peakList
				self.ticArea = ticArea

#    def update_model(self, datalist, header):
#        self.table_model2 = PeaksTableModel(self, dataList, header)
#        self.table_view.setModel(self.table_model2)
#        self.table_view.update()

		def showSelection(self, item):
				cellContent = item.data()
				# print(cellContent)  # test
				sf = "You clicked on {}".format(cellContent)
				# display in title bar for convenience
				self.setWindowTitle(sf)

		def selectRow(self, index):
				# print("current row is %d", index.row())
				pass


class PeaksTableModel(QAbstractTableModel):
		"""
		keep the method names
		they are an integral part of the model
		"""
		def __init__(self, parent, peaks, header, tic, *args):
				QAbstractTableModel.__init__(self, parent, *args)
				self.peaks = peaks
				self.header = header
				self.ticArea = tic

				#self.timer = QTimer()
				self.change_flag = True
				#self.timer.timeout.connect(self.updateModel)
				#self.timer.start(1000)
				self.checkboxes = []
				self.isChecked = []
				#print("Cbox init")
				for idx, v in peaks.iterrows():
					self.checkboxes.append(QCheckBox(""))
					tf, mkr, fil = self.ticArea.sels[idx]
					self.isChecked.append(tf)
				#peaks['selected'] = False
				# self.rowCheckStateMap = {}
				
		def setPeaks(self, peaks):
				self.peaks = peaks
				self.layoutAboutToBeChanged.emit()
				self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
				self.layoutChanged.emit()

		#def updateModel(self):
		#    dataList2 = []
		#    self.change_flag = True

		#    self.peaks = dataList2
		#    self.layoutAboutToBeChanged.emit()
		#    self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
		#    self.layoutChanged.emit()

		def rowCount(self, parent):
				#print ("Rows: ", len(self.peaks))
				return len(self.peaks)

		def columnCount(self, parent):
				#print ("Cols: ", len(self.peaks.iloc[0]))
				return len(self.peaks.iloc[0])+1

		def data(self, index, role):
				if not index.isValid():
						return None
				if (index.column() == 0):
						n = self.peaks.iloc[index.row()].name
						self.checkboxes[index.row()].setChecked(self.isChecked[n])
						self.checkboxes[index.row()].setText(str(n+1))
						value = self.checkboxes[index.row()].text()
				else:
						fvalue = self.peaks.iloc[index.row()][index.column()-1]
						if (index.column() == 1):
							value = "%.2f" %fvalue
						elif (index.column() == 2 or index.column() == 3):
							value = "%.0f" % fvalue
						else:
							value = "%.3f" % fvalue
						#print("Value: ",value, self.peaks.iloc[index.row()])
				if role == Qt.EditRole:
						return value
				elif role == Qt.DisplayRole:
						return value
				elif role == Qt.CheckStateRole:
						if index.column() == 0:
								# print(">>> data() row,col = %d, %d" % (index.row(), index.column()))
								if self.checkboxes[index.row()].isChecked():
										return Qt.Checked
								else:
										return Qt.Unchecked

		def headerData(self, col, orientation, role):
				if orientation == Qt.Horizontal and role == Qt.DisplayRole:
						return self.header[col]
				return None

		def sort(self, col, order):
				"""sort table by given column number col"""
				# print(">>> sort() col = ", col)
				if col != 0:
						self.layoutAboutToBeChanged.emit()
						#self.mylist = sorted(self.mylist, key=operator.itemgetter(col))
						if order == Qt.DescendingOrder:
							asc=False
						else:
							asc=True
						#print ("col: ", self.peaks.columns)
						self.peaks = self.peaks.sort_values(by=self.peaks.columns[col-1], ascending=asc)

						self.layoutChanged.emit()

		def flags(self, index):
				if not index.isValid():
						return None
				# print(">>> flags() index.column() = ", index.column())
				if index.column() == 0:
						# return Qt::ItemIsEnabled | Qt::ItemIsSelectable | Qt::ItemIsUserCheckable
						return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
				else:
						return Qt.ItemIsEnabled | Qt.ItemIsSelectable

		def setData(self, index, value, role):
				if not index.isValid():
						return False
				# print(">>> setData() role = ", role)
				# print(">>> setData() index.column() = ", index.column())
				# print(">>> setData() value = ", value)
				if role == Qt.CheckStateRole and index.column() == 0:
						print(">>> setData() role = ", role)
						print(">>> setData() index.column() = ", index.column())
						n = self.peaks.iloc[index.row()].name
						if value == Qt.Checked:
								self.checkboxes[index.row()].setChecked(True)
								self.isChecked[n] = True
								self.checkboxes[index.row()].setText(str(n+1))
								# if studentInfos.size() > index.row():
								#     emit StudentInfoIsChecked(studentInfos[index.row()])     
						else:
								self.checkboxes[index.row()].setChecked(False)
								self.isChecked[n] = False
								self.checkboxes[index.row()].setText(str(n+1))
						self.ticArea.draw_sel_peak(n, self.isChecked[n], False, False)
						self.ticArea.canvas.draw()
								#self.checkboxes[index.row()].setText("U")
				else:
						print(">>> setData() role = ", role)
						print(">>> setData() index.column() = ", index.column())
				# self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"), index, index)
				print(">>> setData() index.row = ", index.row())
				print(">>> setData() index.column = ", index.column())
				self.dataChanged.emit(index, index)
				return True
		def isSelected(self, row):
				return self.isChecked[row]
		def doSelect(self, row, state):
				self.isChecked[row] = state
				#self.dataChanged.emit(
				n = self.peaks.index.get_loc(row)
				self.checkboxes[n].setChecked(state)
				self.dataChanged.emit(self.createIndex(n, 0), self.createIndex(n, 0))
		def doSelectOnly(self, row, state):
				for b in range(len(self.isChecked)):
					self.isChecked[b] = not state
				self.isChecked[row] = state
				for b in range(len(self.isChecked)):
					n = self.peaks.index.get_loc(b)
					self.checkboxes[n].setChecked(state)
				#self.dataChanged.emit(
				self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))

				
#def timer_func(win, mylist):
#    print(">>> timer_func()")
#    win.table_model.setDataList(mylist)
#    win.table_view.repaint()
#    win.table_view.update()

# def timer_func(num):
#     print(">>> timer_func() num = ", num)


class QCompoundsWindow(QWidget):
		def __init__(self, compounds, ticArea, parent = None, main=None, *args):
				super().__init__(parent, *args)
				self.main = main
				# setGeometry(x_pos, y_pos, width, height)
				#self.setGeometry(70, 150, 1326, 582)
				self.setWindowTitle("Compounds List")
				self.peaks_dropdown = QComboBox()
				
				
				self.cnames = list(compounds.keys())
				idns = []
				for k in self.cnames:
					idx = int(k[4:])
					idns.append(idx)
					idt = "%i: " % (idx+1)
					self.peaks_dropdown.addItem(idt + k)
				self.idns = idns
				self.peaks_dropdown.currentIndexChanged.connect(self.onDropdownChanged)
				self.peak_info = QLabel('LibFact: ' + str(compounds[self.cnames[self.peaks_dropdown.currentIndex()]]['LibFact']))
				self.table_model = CompoundsTableModel(self, compounds, self.cnames, ticArea)
				self.table_view = QTableView()
				#self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
				self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
				self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
				# bind cell click to a method reference
				self.table_view.clicked.connect(self.showSelection)
				self.table_view.clicked.connect(self.selectRow)

				self.table_view.setModel(self.table_model)
				# enable sorting
				self.table_view.setSortingEnabled(True)

				self.dpi = 100
				self.molfig = Figure((2.0, 2.0), dpi=self.dpi)
				self.molview = FigureCanvas(self.molfig)
				self.molview.setParent(parent)
				layout = QVBoxLayout(self)
				layout.addWidget(self.peaks_dropdown)
				layout.addWidget(self.peak_info)
				layout.addWidget(self.table_view)
				layout.addWidget(self.molview)
				self.setLayout(layout)
				#self.maxima = peakList
				self.ticArea = ticArea
				self.compounds = compounds
				self.fileFindStart()
		#def update_model(self, datalist, header):
		#    self.table_model2 = CompoundsTableModel(self, dataList, header)
		#    self.table_view.setModel(self.table_model2)
		#    self.table_view.update()
		def fileFindStart(self):
				self.file_timer = QTimer()
				self.file_timer.setSingleShot(False)        
				self.file_timer.timeout.connect(self.onFileTimer)
				self.file_timer.start(2000)
		def onFileTimer(self):
				usepath = self.main.paths.getPath('usepath') #/Users/dirk/.wine/drive_c/MSREAD/
				molfile = self.main.paths.getPath('molfile')
				molp = usepath + molfile
				#molp = usepath + 'nistms.mol'
				if os.path.isfile(molp):
					#self.file_timer.stop()
					#fig = self.molfig.add_subplot(111)
					ax = self.molfig.add_subplot(111)
					skeleton.draw_mol(self.molfig, ax, molp, 'cp437')
					self.molview.draw()
					os.remove(molp)

		def onDropdownChanged(self):
				p = self.peaks_dropdown.currentIndex()
				self.peak_info.setText('LibFact: ' + str(self.compounds[self.cnames[self.peaks_dropdown.currentIndex()]]['LibFact']))
				print (self.idns[p])
				self.table_model.changePeak(p)
				if self.ticArea.peakw:
					self.ticArea.peakw.table_model.doSelectOnly(self.idns[p], True)
				self.ticArea.draw_all_sel_peaks(False, False, False)
				self.ticArea.draw_sel_peak(self.idns[p], True, False, False)
				self.ticArea.canvas.draw()

		def showSelection(self, item):
				cellContent = item.data()
				# print(cellContent)  # test
				sf = "You clicked on {}".format(cellContent)
				# display in title bar for convenience
				self.setWindowTitle(sf)

		def selectRow(self, index):
				# print("current row is %d", index.row())
				pass
			 

class CompoundsTableModel(QAbstractTableModel):
		"""
		keep the method names
		they are an integral part of the model
		"""
		def __init__(self, parent, compounds, cnames, tic, *args):
				QAbstractTableModel.__init__(self, parent, *args)
				self.compounds = compounds
				#self.header = header
				self.ticArea = tic
				self.selectedPeak = 0
				#self.timer = QTimer()
				self.change_flag = True
				self.compound_names = cnames
				#self.timer.timeout.connect(self.updateModel)
				#self.timer.start(1000)
				#self.checkboxes = []
				#self.isChecked = []
				#print("Cbox init")
				#for idx, v in peaks.iterrows():
				# self.checkboxes.append(QCheckBox(""))
				#  tf, mkr, fil = self.ticArea.sels[idx]
				#  self.isChecked.append(tf)
				#peaks['selected'] = False
				# self.rowCheckStateMap = {}
				self.headings = list(self.compounds[self.peakName()]['Hits'][0].keys())
		def peakName(self):
				 return self.compound_names[self.selectedPeak]
		def setCompounds(self, compounds):
				self.compounds = compounds
				self.layoutAboutToBeChanged.emit()
				self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
				self.layoutChanged.emit()

		#def updateModel(self):
		#    dataList2 = []
		#    self.change_flag = True

		#    self.peaks = dataList2
		#    self.layoutAboutToBeChanged.emit()
		#    self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
		#    self.layoutChanged.emit()

		def rowCount(self, parent):
				#print ("Rows: ", len(self.peaks))
				#print(self.compounds[self.peakName()]['Hits'])
				#print(self.peakName())

				l = len(self.compounds[self.peakName()]['Hits'])
				#print("rc: ", l)
				return l
				
		def columnCount(self, parent):
				#print ("Cols: ", len(self.peaks.iloc[0]))
				#print(self.compounds[self.peakName()]['Hits'][0])
				l = len(self.compounds[self.peakName()]['Hits'][0])
				#print("cc: ", l)

				return l
		def data(self, index, role):
				if not index.isValid():
						return None
				kn = list(self.compounds[self.peakName()]['Hits'][0].keys())[index.column()]
				value = self.compounds[self.peakName()]['Hits'][index.row()][kn]
						
						#print("Value: ",value, self.peaks.iloc[index.row()])
				if role == Qt.EditRole:
						return value
				elif role == Qt.DisplayRole:
						return value
					 

		def headerData(self, col, orientation, role):
				if orientation == Qt.Horizontal and role == Qt.DisplayRole:
						return list(self.compounds[self.peakName()]['Hits'][0].keys())[col]
				return None

		def sort(self, col, order):
				"""sort table by given column number col"""
				# print(">>> sort() col = ", col)
				self.layoutAboutToBeChanged.emit()
				#self.mylist = sorted(self.mylist, key=operator.itemgetter(col))
				if order == Qt.DescendingOrder:
					 asc=False
				else:
					 asc=True
				kn=list(self.compounds[self.peakName()]['Hits'][0].keys())[col]
				print ("col: ", col, kn)
				
				self.compounds[self.peakName()]['Hits'] = sorted(self.compounds[self.peakName()]['Hits'], key=lambda x : x[kn], reverse=not asc)

				self.layoutChanged.emit()

		def flags(self, index):
				if not index.isValid():
						return None
				return Qt.ItemIsEnabled | Qt.ItemIsSelectable
		def changePeak(self, peak):
				self.selectedPeak = peak
				self.layoutAboutToBeChanged.emit()
				self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
				self.layoutChanged.emit()

		def setData(self, index, value, role):
				if not index.isValid():
						return False
				# print(">>> setData() role = ", role)
				# print(">>> setData() index.column() = ", index.column())
				# print(">>> setData() value = ", value)
				print(">>> setData() role = ", role)
				print(">>> setData() index.column() = ", index.column())
				# self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"), index, index)
				print(">>> setData() index.row = ", index.row())
				print(">>> setData() index.column = ", index.column())
				self.dataChanged.emit(index, index)
				return True
				
class QPathSettings(QWidget):
	 def __init__(self,  parent = None, *args):
		 super().__init__(parent, *args)
		 group = QGroupBox("NIST Paths")
		 self.settings = QSettings('Muppetastic', 'MSRead')
		
		 spaths = self.settings.value('NISTPaths')
		 #spaths = None
		 if not spaths:
			 self.defaults()
			 self.settings.setValue('NISTPaths', self.paths)
		 else:
				self.paths = spaths 
		 self.editpaths = self.paths
		 self.parent = parent
		 n = 0
		 plist = []
		 pg = QGridLayout()
		 for k in self.paths.keys():
			 pl = QLabel (k)
			 pt = QLineEdit(self.paths[k])
			 pt.setMinimumWidth(200)
			 pg.addWidget(pl, n, 0)
			 pg.addWidget(pt, n, 1)
			 pt.editingFinished.connect(self.on_parm_update)
			 plist.append((k, pl, pt))
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
		 
	 def defaults(self):
		 self.paths = {'nistpath' : '/Users/dirk/.wine/drive_c/NIST08/MSSEARCH/',
		 #nistpath = '/Volumes/[C] Windows 7 1/NIST08/MSSEARCH/'

		 #filepath = 'C:\\tmp\\'
		 'filepath' : 'C:\\MSREAD\\',

		 'specfile' : 'filespec.fil',
		 'usepath' : '/Users/dirk/.wine/drive_c/MSREAD/',
		 #usepath = '/Volumes/[C] Windows 7 1/MSREAD/'
		 'nistapp' : 'nistms\$.exe',
		 #winecmd ='open /Applications/Wine\ Stable.app/ --args '
		 'winecmd' : '/Applications/Wine\ Stable.app/Contents/Resources/wine/bin/wine ',
		 'autoimpfile' : 'autoimp.msd',
		 'readyfile' : 'SRCREADY.TXT',
		 'resultfile' : 'SRCRESLT.TXT', 
		 'molfile' : 'nistms.mol'}
	 def getPath(self, name):
		 return self.paths[name]
		 
	 def on_parm_update(self):
			 for k, wtl, wtb in self.plist:
				 self.editpaths[k]  = wtb.text()
	 def onApply(self):
		 self.paths = self.editpaths
		 self.settings.setValue('NISTPaths', self.paths)

	 def onOk(self):
		 self.paths = self.editpaths
		 self.settings.setValue('NISTPaths', self.paths)

		 self.parent.close()
	 def onCancel(self):
		 self.parent.close()
	 def setParent(self, parent):
		 self.parent = parent

class QColorSettings(QWidget):
	 def __init__(self,  parent = None, *args):
		 super().__init__(parent, *args)
		 group = QGroupBox("Colors")
		 self.settings = QSettings('Muppetastic', 'MSRead')
		 scolors = self.settings.value('Colors')
		 if not scolors:
			 self.defaults()
			 self.settings.setValue('Colors', self.colors)
		 else:
			 self.colors = scolors 
		 self.editcolors = self.colors

		 self.parent = parent     
		 box = QVBoxLayout()
		 tcbox = QGridLayout()
		 n = 0
		 self.plist = []
		 for c in self.colors.keys():
			 coln = QLabel (c) 
			 btn = QColorButton(self.colors[c])
			 btn.colorChanged.connect(self.onColorChanged)
			 tcbox.addWidget(coln, n, 0)
			 tcbox.addWidget(btn, n, 1)
			 self.plist.append((c, coln, btn))
			 n+= 1
		 
		 group.setLayout(tcbox)
		 bbox = QDialogButtonBox(QDialogButtonBox.Ok |
														 QDialogButtonBox.Apply |
														 QDialogButtonBox.Cancel
														 )
		 bbox.accepted.connect(self.onOk)
		 bbox.rejected.connect(self.onCancel)
		 btn = bbox.button(QDialogButtonBox.Apply)
		 btn.clicked.connect(self.onApply)
		 
		 box.addWidget(group)
		 box.addWidget(bbox)
		 self.setLayout(box)
	 def defaults(self):
		 self.colors = { "Baseline" : QColor("red"),
									 "Highlight" : QColor("red"),
									 "Area1" : QColor("cyan"),
									 "Area2" : QColor("yellow") }
	 
	 def getColorFor(self, name):
			return self.colors[name]
	 def onColorChanged(self):
			for k, wtl, wtb in self.plist:
				 self.editcolors[k]  = QColor(wtb.color())
				 
	 def onApply(self):
		 self.colors = self.editcolors
		 self.settings.setValue('Colors', self.colors)

	 def onOk(self):
		 self.colors = self.editcolors
		 self.settings.setValue('Colors', self.colors)

		 self.parent.close()
	 def onCancel(self):
		 self.parent.close() 
	 def setParent(self, parent):
		 self.parent = parent 
								 
class QPrefsDialog(QDialog):
	 def __init__(self,  paths, colors, parent = None):
		 super().__init__(parent)
		 self.setWindowTitle("Preferences")
		 box = QVBoxLayout()
		 self.tabs = QTabWidget()
		 
		 self.colors = colors
		
		 self.tabs.addTab(paths, "NIST Paths")
		 self.tabs.addTab(colors, "Colors")

		 box.addWidget(self.tabs)
		 self.setLayout(box)

class subtractThread(QThread):
		progress_update = pyqtSignal(int)
		subtract_done = pyqtSignal(list)
		subtract_status = pyqtSignal(bool, str)
		def __init__(self, a1, a2):
				QThread.__init__(self)
				self.a1 = a1
				self.a2 = a2
		def __del__(self):
				self.wait()


		def run(self):
				try:
					res = self.a1.subtractBaselineSpec(self.a2,self.progress_update.emit)
					#self.subtract_status.emit(True, 'Complete')
					self.subtract_done.emit(res)
				except Exception as e:
						print ('Exc ' + str(e))
						#self.scan_status.emit(False, str(e))     

class QColorButton(QPushButton):
		'''
		Custom Qt Widget to show a chosen color.

		Left-clicking the button shows the color-chooser, while
		right-clicking resets the color to None (no-color).    
		'''

		colorChanged = pyqtSignal()

		def __init__(self, color = None, *args, **kwargs):
				super().__init__(*args, **kwargs)

				if color:
					self._color = color.name()
				self.setMaximumWidth(32)
				self.pressed.connect(self.onColorPicker)
				if self._color:
						self.setStyleSheet("background-color: %s;" % self._color)
				else:
						self.setStyleSheet("")
						
		def setColor(self, color):
				if color != self._color:
						self._color = color
						self.colorChanged.emit()

				if self._color:
						self.setStyleSheet("background-color: %s;" % self._color)
				else:
						self.setStyleSheet("")

		def color(self):
				return self._color

		def onColorPicker(self):
				'''
				Show color-picker dialog to select color.

				Qt will use the native dialog by default.

				'''
				dlg = QColorDialog(self)
				if self._color:
						dlg.setCurrentColor(QColor(self._color))

				if dlg.exec_():
						self.setColor(dlg.currentColor().name())

		def mousePressEvent(self, e):
				if e.button() == Qt.RightButton:
						self.setColor(None)

				return super(QColorButton, self).mousePressEvent(e)
def main():
	 app = QApplication(sys.argv)
	 ex = MainWindow()
	 ex.show()
	 sys.exit(app.exec_())


if __name__ == '__main__':
	 main()
