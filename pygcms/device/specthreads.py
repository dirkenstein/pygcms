
from PyQt5.QtCore import *
import pygcms.msfile.readspec as readspec
import pygcms.device.busreader as busreader
import visa
import pygcms.device.hp5971 as hp5971
import pygcms.device.hp7673 as hp7673
import pygcms.device.hp5890 as hp5890
import copy
import time
import datetime
import traceback
import pygcms.device.tuning as tuning
import json
import pygcms.msfile.msfileread as msfr
import rpyc

class threadRunner():
		def __init__(self,  parent, main, devs, method, msparms, methname, fname, scan_thread, showNewScan, showTuning, logl=print, forRun=False, loadpath='', host='', port=18812):
			self.progress_thread = QThread()
			self.progress_thread_o = None
			
			self.init_thread = QThread()
			self.init_thread_o = None
			
			self.status_thread = QThread()
			self.status_thread_o = None
	
			self.tune_thread = QThread()
			self.tune_thread_o = None
			
			
			self.status_timer = None
			self.init = False
			self.scanning = False
			self.running = False
			self.tuning = False
			self.parent = parent
			self.main = main
			self.method = method
			self.msparms = msparms
			self.logl = logl
			self.scan_thread = scan_thread
			self.showNewScan = showNewScan
			self.showTuning = showTuning
			self.forRun = forRun
			self.devs = devs 
			self.fname = fname
			self.methname = methname
			self.loadpath = loadpath
			self.rmthost = host
			self.rmtport = port
			
		def disableAllButtons(self):
			if self.parent.reinit_button:
				self.parent.reinit_button.setEnabled(False)
			if self.parent.run_button:
				self.parent.run_button.setEnabled(False)
			if self.parent.scan_button:
				self.parent.scan_button.setEnabled(False)
			if self.parent.tune_button:
				self.parent.tune_button.setEnabled(False)

		def disableStartButtons(self):
			if self.parent.run_button:
				self.parent.run_button.setEnabled(False)
			if self.parent.scan_button:
				self.parent.scan_button.setEnabled(False)
			if self.parent.tune_button:
				self.parent.tune_button.setEnabled(False)
				
		def enableAllButtons(self):
			if self.parent.run_button:
				self.parent.run_button.setEnabled(True)
			if self.parent.scan_button:
				self.parent.scan_button.setEnabled(True)
			if self.parent.reinit_button:
				self.parent.reinit_button.setEnabled(True)
			if self.parent.tune_button:
				self.parent.tune_button.setEnabled(True)

		def enableStartButtons(self):
			if self.parent.run_button:
				self.parent.run_button.setEnabled(True)
			if self.parent.scan_button:
				self.parent.scan_button.setEnabled(True)
			if self.parent.tune_button:
				self.parent.tune_button.setEnabled(True)

		def disableIndicators(self):
			if self.parent.ledbox:
				self.parent.ledbox.turnOff(0)
				self.parent.ledbox.turnOff(1)
				self.parent.ledbox.turnOff(2)
		
		def indicators(self, hpms, hpgc,hpinj):
			if self.parent.ledbox:
				self.parent.ledbox.turnOn(0, hpms)
				self.parent.ledbox.turnOn(1, hpgc)
				self.parent.ledbox.turnOn(2, hpinj)
		
		def on_init(self):
				#self.logl("Reinit")
				self.init =False
				self.disableAllButtons()
				self.disableIndicators()
				self.main.statusBar().showMessage('Initializing..', 1000)
				QThread.yieldCurrentThread()
				
				if not self.init_thread.isRunning():
					#self.logl("No init Thread")
					self.init_thread_o = initThread(self.method, self.logl, devs=self.devs, forRun=self.forRun, path=self.loadpath, host=self.rmthost, port=self.rmtport)
					self.init_thread_o.progress_update.connect(self.updateProgressBar)
					self.init_thread_o.inst_status.connect(self.instStatus)
					self.init_thread_o.init_status.connect(self.setInitialized)
					self.init_thread_o.moveToThread(self.init_thread)
					self.init_thread_o.run_init.connect(self.init_thread_o.doInit)
					self.init_thread_o.run_stop.connect(self.init_thread_o.doStop)

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
		
		def on_scan(self):
				self.scanning =True
				self.disableStartButtons()
				self.main.progress.setValue(0)
				self.main.statusBar().showMessage('Scanning..', 2000)

				if not self.progress_thread.isRunning():
					self.progress_thread_o = self.scan_thread(self.hpmsd, self.msparms, logl=self.logl)
					self.progress_thread_o.progress_update.connect(self.updateProgressBar)
					self.progress_thread_o.scan_done.connect(self.showNewScan)
					self.progress_thread_o.scan_status.connect(self.showScanStatus)
					self.progress_thread_o.scan_info.connect(self.showScanInfo)
					self.progress_thread_o.run_stop.connect(self.progress_thread_o.doStop)

					self.progress_thread_o.moveToThread(self.progress_thread)
					#self.progress_thread.started.connect(self.progress_thread_o.doScan)
					self.progress_thread_o.run_scan.connect(self.progress_thread_o.doScan)
					self.progress_thread.start()
					self.progress_thread_o.run_scan.emit()
				else:
					self.progress_thread_o.run_scan.emit()

		def on_run(self):
			if len(self.fname) > 0:
				self.running =True
				self.disableStartButtons()
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
			else:
				self.main.statusBar().showMessage('File Name Not Set', 10000)

		def on_stop(self):
			if self.progress_thread_o:
				self.progress_thread_o.run_stop.emit()

	
		def updateProgressBar(self, maxVal):
			uv = self.main.progress.value() + maxVal
			if maxVal == 0:
				 uv = 0
			if uv > 100:
				 uv = 100
			self.main.progress.setValue(uv)
		
		def showScanStatus(self,ok, emsg):
			if ok:
				self.main.statusBar().showMessage('Scan Done: ' + emsg, 2000)
				self.main.progress.setValue(100)
			else:
				self.main.statusBar().showMessage('Scan Failed: ' + emsg, 10000)
				self.main.progress.setValue(0)
			self.scanning = False
	
		def instStatus(self, hpms, hpgc, hpinj):
			#print(hpms, hpgc, hpinj)
			self.indicators(hpms, hpgc,hpinj)
		def showScanInfo(self, emsg):
			self.main.statusBar().showMessage('Scan Info: ' + emsg, 4000)
		
		def doStatusThread(self):
			if not self.status_thread.isRunning():
				self.status_thread_o = statusThread(self.hpmsd, self.hpgc, self.logl)
				self.status_thread_o.progress_update.connect(self.updateProgressBar)
				self.status_thread_o.ms_status_update.connect(self.onStatusUpdate)
				self.status_thread_o.gc_status_update.connect(self.onStatusUpdateGc)

				self.status_thread_o.moveToThread(self.status_thread)
				self.status_thread_o.run_status.connect(self.status_thread_o.do_st)
				self.status_thread_o.run_stop.connect(self.status_thread_o.doStop)

				self.status_thread.start()
			self.status_timer = QTimer()
			self.status_timer.setSingleShot(False)        
			self.status_timer.timeout.connect(self.doGetStatus)
			self.status_timer.start(5000)
		

		
		def setInitialized(self,ok, emsg):
			if ok:
				self.main.statusBar().showMessage('Init Done: ' + emsg, 2000)
				self.hpmsd = self.init_thread_o.getMsd()
				self.hpgc = self.init_thread_o.getGc()
				self.hpinj = self.init_thread_o.getInj()

				self.main.progress.setValue(100)
				self.enableAllButtons()
				self.init = True
				self.doStatusThread()
			else:
				self.main.statusBar().showMessage('Init Failed: ' + emsg, 2000)
				self.main.progress.setValue(0)
				
		def doGetStatus(self):
			if (not self.running) and (not self.scanning) and (not self.tuning) and self.init:
				self.main.progress.setValue(0)
				self.disableStartButtons()
				self.status_thread_o.run_status.emit(True)

		def onStatusUpdate(self, conf):
			if not self.running and not self.scanning:
				self.enableAllButtons()

			if not 'Error' in conf:
				self.parent.ms_status_area.status_panel(conf)
				#self.parent.paramtabs.status_panel(conf)
				#self.on_draw()

			else:
				self.main.statusBar().showMessage('Status  Error: ' + conf['Error'], 10000)
				self.main.progress.setValue(0)

		def onStatusUpdateGc(self, conf):
			if not self.running:
				self.enableAllButtons()

			if not 'Error' in conf:
				self.parent.gc_status_area.status_panel(conf)
				#self.on_draw()

			else:
				self.main.statusBar().showMessage('Status Error: ' + conf['Error'], 10000)
				self.main.progress.setValue(0)

		def onStatusUpdateInj(self, conf):
			if not 'Error' in conf:
				self.parent.inj_status_area.status_panel(conf)
				#self.on_draw()
			else:
				self.main.statusBar().showMessage('Status Error: ' + conf['Error'], 10000)
				self.main.progress.setValue(0)
#				self.hpmsd = self.init_thread_o.getMsd()
#				self.hpgc = self.init_thread_o.getGc()

		def showRunStatus(self,ok, emsg):
			self.enableStartButtons()
			if ok:
				self.main.statusBar().showMessage('Run Done: ' + emsg, 2000)
				self.main.progress.setValue(100)
			else:
				self.main.statusBar().showMessage('Run Failed: ' + emsg, 10000)
				self.main.progress.setValue(0)
			self.running = False

		def on_tune(self):
			self.tuning =True
			self.disableStartButtons()
			self.main.progress.setValue(0)
			self.main.statusBar().showMessage('Tune..', 2000)
			if not self.tune_thread.isRunning():
				self.tune_thread_o = tuningThread( self.hpmsd, self.msparms, self.logl)
				self.tune_thread_o.progress_update.connect(self.updateProgressBar)
				self.tune_thread_o.tune_spec.connect(self.showTuning)
				self.tune_thread_o.tune_done.connect(self.showTuneStatus)
				self.tune_thread_o.tune_info.connect(self.showTuneInfo)

				self.tune_thread_o.moveToThread(self.tune_thread)
				self.tune_thread_o.run_tune.connect(self.tune_thread_o.doTune)
				self.tune_thread_o.run_stop.connect(self.tune_thread_o.doStop)
				#self.run_stop.connect(self.endRun)

				self.tune_thread.start()
				self.tune_thread_o.run_tune.emit()

			else:
				self.tune_thread_o.run_tune.emit()

		def showTuneStatus(self,ok, emsg, parms):
			self.enableStartButtons()
			if ok:
				self.main.statusBar().showMessage('Tune Done: ' + emsg, 2000)
				self.main.progress.setValue(100)
				self.msparms = parms
				#f = open("tunnew2.json", "w")
				#f.write(json.dumps(parms, indent=4))
				#f.close()
				self.main.upd_tuning(parms)
				self.main.upd_parms()
				#self.main.msparms = parms
			else:
				self.main.statusBar().showMessage('Tune Failed: ' + emsg, 10000)
				self.main.progress.setValue(0)
			self.tuning = False

		def showTuneInfo(self, emsg):
			self.main.statusBar().showMessage('Tune Info: ' + emsg, 4000)



		def updateFname(self,fname):
			self.fname = fname
			if self.progress_thread_o:
				self.progress_thread_o.updateFname(fname)
				
		def updateMethod(self, method, methname):
			self.method = method
			self.methname = methname
			if self.progress_thread_o:
				self.progress_thread_o.updateMethod( method, methname)
			if self.init_thread_o:
				self.init_thread_o.updateMethod( method, methname)

	
		def updateDevs(self, devs):
			self.devs = devs
			if self.init_thread_o:
				self.init_thread_o.updateDevs(devs)

		def updateConn(self, host, port, path):
			self.loadpath = path
			self.rmthost = host
			self.rmtport = port
			if self.init_thread_o:
				self.init_thread_o.updateConn(host, port, path)

		def updateMsParms(self, msparms):
			self.msparms = msparms
			if self.progress_thread_o:
				self.progress_thread_o.updateParms(msparms)
			if self.tune_thread_o:
				self.tune_thread_o.updateParms(msparms)

		def updateParent(self , parent):
			self.parent = parent
		def getMsParms():
			return self.msparms
		def on_close(self):
			self.logl("closing threads")
			if self.status_timer:
				self.status_timer.stop()
			if self.progress_thread_o:
				self.progress_thread_o.run_stop.emit()
				self.progress_thread.terminate()

			if self.init_thread_o:
				self.init_thread_o.run_stop.emit()
				self.init_thread.terminate()

			if self.status_thread_o:
				self.status_thread_o.run_stop.emit()
				self.status_thread.terminate()
	
		
class initThread(QObject):
		init_status = pyqtSignal(bool,str)
		progress_update = pyqtSignal(int)
		inst_status = pyqtSignal(bool, bool, bool)
		run_init = pyqtSignal()
		update_init = pyqtSignal()
		run_stop = pyqtSignal()

		def __init__(self, method, logl, devs=None, forRun=False, host='', path='', port=18812):
				QObject.__init__(self)
				self.reboot = False
				self.method = method
				self.init_msd = False
				self.init_gc = False
				self.init_inj = False
				self.init = False
				self.logl = logl
				self.forRun = forRun
				self.hpmsd = None
				self.hpgc = None
				self.hpinj = None
				self.devs = devs
				self.host = host
				self.lpath = path
				self.port = port
				#self.run_init.connect(self.doInit)

				
		def __del__(self):
				pass
				#self.wait()
				
		def updateMethod(self, m, methname):
			self.method = m
			self.init_gc = False
			self.init_inj = False
			self.init = False
			#self.doInit()
		
		def updateConn(self, host, port, path):
			self.host = host
			self.lpath = path
			self.port = port
			
		def updateDevs(self, devs):
			self.devs = devs

		def doInit(self):
			#init = False
			time.sleep(2)
			stime = 2.0
			while not self.init:
					if self.host and len(self.host) > 0:
						try:
							self.con = rpyc.classic.connect(self.host, self.port)
							self.con._config['sync_request_timeout'] = 60 
							self.rsysm = self.con.modules.sys
							self.rosm = self.con.modules.os
							if len(self.lpath) > 0 and self.lpath not in self.rsysm.path:
								self.rsysm.path.append(self.lpath)
								self.rosm.chdir(self.lpath)
							self.brm = self.con.modules['pygcms.device.busreader']
						except Exception as e:
							self.logl (e)
							self.init_status.emit(False, 'Remote Connection Failed: ' +  str(e))
							time.sleep(stime)
							continue
					else:
						self.brm = busreader
					try:
						self.br = self.brm.BusReader(devs=self.devs,logl=self.logl)
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
							self.hpinj = hp7673.HP7673(self.inj, self.br, self.method['Method']['Injector']['UseInjector'], self.hpgc.addr, self.logl)
							self.logl(self.hpinj.reset())
							self.init_inj = True
							self.inst_status.emit(self.init_msd, self.init_gc, self.init_inj)
						except Exception as e:
							self.logl (e)
							self.logl(traceback.format_exc())
							self.init_status.emit(False, str(e))
							time.sleep(stime)
					if self.init_msd and (self.init_inj or not self.method or not self.forRun) and (self.init_gc or not self.method or not self.forRun):
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
			return self.hpinj
		
		def doStop(self):
			pass


class statusThread(QObject):
		ms_status_update = pyqtSignal(dict)
		gc_status_update = pyqtSignal(dict)

		progress_update = pyqtSignal(int)
		run_status = pyqtSignal(bool)
		run_stop = pyqtSignal()

		def __init__(self, hpmsd, hpgc, logl=print):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				self.hpgc = hpgc
				self.logl = logl
		def __del__(self):
				pass
				#self.wait()

		def updateDevices(self, hpmsd, hpgc):
				self.hpmsd = hpmsd
				self.hpgc = hpgc
				#self.hpinj = hpinj
		

		def do_st(self,gc):
			try:
				ret = self.hpmsd.getConfig(self.progress_update.emit)
				ret2 = self.hpmsd.getRunStat(self.progress_update.emit)
				ret.update(ret2)
				self.ms_status_update.emit(ret)
						
				if self.hpgc:
					ret3 = self.hpgc.statcmds(self.progress_update.emit)
					self.gc_status_update.emit(ret3)
				self.progress_update.emit(100)

			except hp5971.HP5971Exception as e1:
				self.logl('5971 ' + str(e1))
				try:
					errstr = str(self.hpmsd.getErrors())
					self.hpmsd.reset()
				except Exception as e2:
					errstr = str(e)
				finally:
					self.ms_status_update.emit({'Error' : errstr})
			except Exception as e:
				self.logl ('Exc ' + str(e))
				self.logl(traceback.format_exc())
				self.ms_status_update.emit({'Error' : str(e)})
					
		def doStop(self):
			pass


class scanThread(QObject):
		progress_update = pyqtSignal(int)
		scan_done = pyqtSignal(list, list)
		scan_status = pyqtSignal(bool, str)
		scan_info = pyqtSignal(str)

		run_scan = pyqtSignal()
		update_scan = pyqtSignal(hp5971.HP5971)
		run_stop = pyqtSignal()

		def __init__(self, hpmsd, parms, logl=print):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				self.parms = parms
				self.logl = logl
				#self.run_scan.connect(self.doScan)

		def updateDevices(self, hpmsd):
				self.hpmsd = hpmsd
		
		def updateParms(self, parms):
			self.parms = parms	
				
		def __del__(self):
				pass
				#self.wait()


		def doScan(self):
			try:
				#self.scan_status.emit(True, 'Starting Scan')
				self.hpmsd.getAScan(self.parms, self.progress_update.emit)	
				self.scan_done.emit([self.hpmsd.getSpec()], [''])
				self.scan_status.emit(True, 'Complete')

			except hp5971.HP5971Exception as e1:
				self.logl('5971 ' + str(e1))
				try:
					errstr = str(self.hpmsd.getErrors())
					self.hpmsd.reset()

				except Exception as e2:
					errstr = str(e)
				finally:
					self.scan_status.emit(False, errstr)
			except Exception as e:
				self.logl ('Exc ' + str(e))
				self.logl(traceback.format_exc())

				self.scan_status.emit(False, str(e))
		def doStop(self):
			pass


class tripleScanThread(QObject):
		progress_update = pyqtSignal(int)
		scan_done = pyqtSignal(list, list)
		scan_status = pyqtSignal(bool, str)
		scan_info = pyqtSignal(str)
		run_scan = pyqtSignal()
		run_stop = pyqtSignal()

		def __init__(self, hpmsd, parms, logl=print):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				self.parms = parms
				self.logl = logl
				#self.run_scan.connect(self.doScan)

		def updateDevices(self, hpmsd):
				self.hpmsd = hpmsd
	
		def updateParms(self, parms):
			self.parms = parms	
		
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
					pks = [self.hpmsd.tunePeak(self.parms, 1),
								self.hpmsd.tunePeak(self.parms, 2),
								self.hpmsd.tunePeak(self.parms, 3)]
					self.hpmsd.adjScanParms(self.parms['Scan'], pks[0])
					self.hpmsd.getPartialScan(self.parms, self.progress_update.emit, moreScans=True)
					spec1 = self.hpmsd.getSpec()
					#time.sleep(1)
					self.hpmsd.adjScanParms(self.parms['Scan'], pks[1])
					self.hpmsd.getPartialScan(self.parms, self.progress_update.emit, moreScans=True)	
					spec2 = self.hpmsd.getSpec()
					#time.sleep(1)

					self.hpmsd.adjScanParms(self.parms['Scan'], pks[2])
					self.hpmsd.getPartialScan(self.parms, self.progress_update.emit, moreScans=False)	
					spec3 = self.hpmsd.getSpec()

					self.scan_done.emit([spec1, spec2, spec3], pks)
					self.parms['Scan'].update(old_sparms)
					self.scan_status.emit(True, 'Complete')

				except hp5971.HP5971Exception as e1:
					self.logl ('5971 ' + str(e1))
					try:
						errstr = str(self.hpmsd.getErrors())
						self.hpmsd.reset()
					except Exception as e2:
						errstr = str(e)
					finally:
						self.scan_status.emit(False, errstr)
				except Exception as e:
					self.logl ('Exc ' + str(e))
					self.logl(traceback.format_exc())

					self.scan_status.emit(False, str(e))

		def doStop(self):
			pass

class tuningThread(QObject):
		progress_update = pyqtSignal(int)
		tune_spec = pyqtSignal(int, bool, bool, list)
		tune_done = pyqtSignal(bool, str, dict)
		tune_info = pyqtSignal(str)
		run_tune = pyqtSignal()
		run_stop = pyqtSignal()
		
		
		def __init__(self, hpmsd, parms, logl=print):
				QObject.__init__(self)
				self.hpmsd = hpmsd
				self.parms = parms
				self.logl = logl
				#self.run_scan.connect(self.doScan)
				self.tun = tuning.HP5971Tuning(self.hpmsd, self.parms, self.emitScan, self.emitAxis, self.emitRamp, logl=self.logl)

		def updateDevices(self, hpmsd):
				self.hpmsd = hpmsd
			
		def updateParms(self, parms):
			self.parms = parms	
		
		def __del__(self):
				pass
				#self.wait()


		def doTune(self):
				try:
					self.logl(self.hpmsd.getAvc())
					self.logl(self.hpmsd.getCivc())
					wrd = self.hpmsd.getRevisionWord()
					self.logl (hp5971.HP5971.getLogAmpScale(wrd))
					self.logl(self.hpmsd.diagIO())
					self.hpmsd.calValve(1)
					self.hpmsd.readyOn()
					self.tune_info.emit('Waiting for PFTBA to stabilise')

					time.sleep(30)
					self.tune_info.emit('Abundance')

					self.tun.abundance(1e6, 3e6)
					self.tune_info.emit('Width')

					self.tun.width(2)
					self.tune_info.emit('Abundance')
					self.tun.abundance(1e6, 3e6)
					self.tune_info.emit('Mass Axis')

					self.tun.axis(1)
					self.tune_info.emit('Ramp')

					self.tun.rampEnt()
					self.tun.rampEntOfs()
					self.tun.rampXray()
					self.tun.rampRep()
					self.tun.rampIon()

					parms = self.tun.getParms()
					f = open("tunnew.json", "w")
					f.write(json.dumps(parms, indent=4))
					f.close()
					self.tune_done.emit(True, "Tune Done", parms)


				except hp5971.HP5971Exception as e1:
					self.logl ('5971 ' + str(e1))
					try:
						errstr = str(self.hpmsd.getErrors())
						self.hpmsd.reset()
					except Exception as e2:
						errstr = str(e)
					finally:
						self.tune_done.emit(False, errstr, {})
				except Exception as e:
					self.logl ('Exc ' + str(e))
					self.logl(traceback.format_exc())

					self.tune_done.emit(False, str(e), {})

		def doStop(self):
			pass
		
		def emitScan(self, spec, n, pk):
			self.tune_spec.emit(n, False,False, [spec, pk])
		
		def emitAxis(self, spec, n, pk):
			self.tune_spec.emit(n, False,True, [spec, pk])
			
			#spec.plotit(name = ' ' + str(self.tunepk[n]))
		def emitRamp(self, spec, n, pk, parm, ovolt, nvolt):
			self.tune_spec.emit(n, True, False, [spec, parm, ovolt, nvolt, pk])
			#spec.plotrampit(' ' +parm + ' ' + str(self.tunepk[n]), currvolt=ovolt)

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
				
		def updateMethod(self, m, name):
			self.method = m
			self.methname = name
		def updateFname(self, fname):
			self.fname = fname

		def updateParms(self, parms):
			self.method['Method']['MSParms'] = parms	
			
		def datProc(self, m):
				
				self.hpmsd.readData()
				self.stb = self.hpmsd.statusb
				specs = self.hpmsd.getSpecs()
				nspecs = 0
				if specs and len(specs) > 0:
					for sp in specs:
						sp2 = sp.explode()
						if sp2 and len(sp2) > 0:
							for sp3 in sp2:
								rt = sp3.getRetTime()
								self.specs.append((rt, sp3))
								#if (rt - self.last_rt) > 0.1: 
								self.run_spec.emit(sp3)
								#self.last_rt = rt
								nspecs = nspecs +1
						else:
							self.logl("Empty spec")
					return nspecs
				else:
					self.logl("No spec")
					return 0

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
								ns = self.datProc(self.hpmsd)
								idx+=1
								#stb = self.stb
								self.logl('5971 st: ', self.stb, " ns = ", ns)
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
							ns = self.datProc(self.hpmsd)
							idx += 1
							nr -= ns
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
							self.hpmsd.reset()
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


