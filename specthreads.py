
from PyQt5.QtCore import *
import readspec
import busreader
import hp5971
import visa
import hp5971
import hp7673
import hp5890
import copy
import time
import datetime
import traceback


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


