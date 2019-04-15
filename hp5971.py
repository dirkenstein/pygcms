import busreader
import readspec

class HP5971():
	faults = {
		1:'Party fault has occurred.',
		2:'There was an excessive signal level.',
		4:'Difficulty in mass filter electronics.',
		8:'There is no emission current.',
		16:'Excessive source pressure.',
		32:'The diffusion pump is too hot.',
		64:'The foreline pressure has exceeded 300 mTorr.',
		128:'The diffusion pump is too cold.',
		256:'The system is in VENT state.',
		512:'Difficulty with the detector HV supply.',
		8192:'Difficulty with MS internal communication.'
	}
	
	def __init__(self, dev, br, logl=print):
		self.dev = dev
		self.br = br
		self.dev.timeout = 10000
		self.stb = 0
		self.esr = 0
		self.gotConfig = False
		self.addr = busreader.BusReader.getGbpibAddr(dev)
		self.p_step = 4
		self.logl = logl
	
	def reset(self):
		#print ('Reset: ')
		#self.statusb = self.br.statusb(self.dev)
		self.esr = self.br.cmd(self.dev,  r'*SRE 0;:ERR:STR ON;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
	
	def scanSeqInit(self, initial):
		if initial:
			icmd = ":RUN:STOP;RDY OFF;REM:APG:RDY OFF;MASK 4;*CLS;:RUN:STE 0;:MSC:RDY OFF;FLT:RVR 0;:CONFIG:MASS:EXT 0;:AEE 0;:BUF:CLR;:OCW:STR ON;CLR;*RST;:DAT:MODE:ALL;:SCN:TYPE NORM;:SIM:WIDE OFF;:ERR:CLR;*ESR?"
		else:
			icmd = ":RUN:STOP;RDY OFF;REM:APG:RDY OFF;MASK 255;*CLS;:RUN:STE 450;:MSC:RDY OFF;FLT:RVR 1;:CONFIG:MASS:EXT 0;:AEE 88;:BUF:CLR;:OCW:STR ON;CLR;*RST;:REP:DUR:FOR;:ERR:CLR;*ESR?"
		self.esr = self.br.cmd(self.dev ,icmd )
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
	
	def getErrors(self):
		#print ('Errors: ')
		return self.br.cmd(self.dev, r':ERR:ALL?').decode('ascii', errors='replace').strip()
	
	def getAvc(self):
		return self.br.cmd(self.dev, r':MSC:AVC:REV?').decode('ascii', errors='replace').strip()

	def getCivc(self):
		return self.br.cmd(self.dev, r':MSC:CIVC:REV?').decode('ascii', errors='replace').strip()
	
	def getRevisionWord(self):
		return int(self.br.cmd(self.dev, r':MSDC:XFR? 4096,0').decode('ascii', errors='replace').strip())

	def diagIO(self):
		return int(self.br.cmd(self.dev, r':DIAG:MSIO?').decode('ascii', errors='replace').strip())
	
	def getLogAmpScale(word):
		bit1 = (word & 0x1) > 0
		bit8 = (word & 0x100) > 0
		if not bit1 and not bit8:
			return 1.0
		elif not bit1 and bit8:
			return 0.125
		else:
			return -1
			
	def readyOff(self):
		#print ('Ready Off: ')
		self.esr =  self.br.cmd(self.dev, r':MSC:RDY OFF;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
		
	def rvrOff(self):
		#print ('Filter RVR Off: ')
		self.esr = self.br.cmd(self.dev, r':MSC:FLT:RVR OFF;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr

	def rvrOn(self):
		#print ('Filter RVR Off: ')
		self.esr = self.br.cmd(self.dev, r':MSC:FLT:RVR ON;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
				
	def getFaultStat(self):
		#print ('Fault Stat: ')
		return int(self.br.cmd(self.dev, r':MSC:FLT:STAT?').decode('ascii', errors='replace').strip())
		
	def getSourceTemp(self):
		#print ('Source Temperature: ')
		return float(self.br.cmd( self.dev, r':MSC:SENS? SRCTEMP').decode('ascii', errors='replace').strip())

	def getPressure(self):
		#print ('Foreline Pressure')
		return float(self.br.cmd( self.dev, r':MSC:SENS? FORPRES').decode('ascii', errors='replace').strip())

	def isDiffPumpOn(self):
		#print ('Diff Pump:')
		return int(self.br.cmd( self.dev, r':MSC:PARM? DIF').decode('ascii', errors='replace').strip())

	def isPFTBAOn(self):
		#print ('PFTBA: ')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return float(self.br.cmd(self.dev, r':MSC:PARM? CAL').decode('ascii', errors='replace').strip())

	def vent(self):
		#print ('Diff Off')
		self.esr = self.br.cmd(self.dev, r':MSC:PARM DIF, 0;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr

	def massParms(self, parms):
		#print ('Mass Params: ')
		massParm = ':MSC:PARM MASG,%i;PARM MASO,%i;*ESR?' % (parms['MassGain']['value'], parms['MassOffs']['value'])
		self.logl("Mass: ", massParm)
		self.esr =  self.br.cmd(self.dev,massParm)
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		
		return self.esr

	def tuningParms(self, parms, nxt):
		#print ('Tuning Params: ')
		if nxt:
			tune = ':MSC:PARM:NEXT AMUG,%1.6f;NEXT AMUO,%1.6f;NEXT ECUR,%1.6f;NEXT REP,%1.6f;NEXT IFOC,%1.6f;NEXT ENT,%1.6f;NEXT XRAY,%1.6f;NEXT EMUL,%1.6f;NEXT DCP,%1.6f;NEXT FSEL,%1.6f;NEXT TTI,%1.6f;NEXT MMW,%1.6f;NEXT ENTO,%1.6f;*ESR?'
		else:
			tune = ':MSC:PARM AMUG,%1.6f;PARM AMUO,%1.6f;PARM ECUR,%1.6f;PARM REP,%1.6f;PARM IFOC,%1.6f;PARM ENT,%1.6f;PARM XRAY,%1.6f;PARM EMUL,%1.6f;PARM DCP,%1.6f;PARM FSEL,%1.6f;PARM TTI,%1.6f;PARM MMW,%1.6f;PARM ENTO,%1.6f;*ESR?'
		t = tune % (parms['AmuGain']['value'], parms['AmuOffs']['value'], parms['Emission']['value'], parms['Repeller']['value'], parms['IonFocus']['value'],parms['EntLens']['value'], parms['Xray']['value'], parms['EMVolts']['value'], parms['DC Pol']['value'],parms['Filament']['value'], parms['TTI']['value'], parms['Wid219']['value'], parms['EntOffs']['value'])
		self.logl("Tune: ",t)
		self.esr = self.br.cmd(self.dev, t)
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr

	def filtSetupStd(self):
		#print ('Filter Setup: ')
		self.esr = self.br.cmd(self.dev,':FLTR:MASS:CALC ISTD;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
	
	def filtSetupStdCoeff(self, i):
		self.esr = self.br.cmd(self.dev, ":FLTR:MASS:CALC ISTD;:FLTR:TIME:COEF %i;*ESR?" % i)
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
	

	def qualSetupMaxOf3(self):
		#print ('Qualifier Setup: ') 
		self.esr = self.br.cmd(self.dev,':SCN:PEAK:QUAL MAXOF3;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr

	def calValve(self,i):
		#print ('Calibration Relay: ')
		self.esr = self.br.cmd(self.dev,':MSC:PARM CAL,%i;*ESR?' % i)
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
		
	def isReady(self):
		rdy = self.br.cmd(self.dev,'MSC:RDY?')
		return rdy == 1
		 
	def readyOn(self):
		#print ('Ready On: ')
		self.esr = self.br.cmd(self.dev,':MSC:RDY ON;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
		
	def clearBuf(self):
		self.logl ('Clear Buffer: ')
		self.esr = self.br.cmd(self.dev,':BUF:CLR;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
	
	def scanSetup(self, parms, partial=False):
		self.logl ('Scan Setup:')
		if partial:
			scan = ':DIAG:STM %1.6f;:PSCN:NAVG %i;NSAM %i;MASS:STEP %1.6f;RANG %1.6f,%1.6f;*ESR?' % (parms['RangeFrom']['value'],  parms['Avg']['value'], parms['Samples']['value'], parms['Step']['value'], parms['RangeFrom']['value'],  parms['RangeTo']['value'])
		else:
			scan = ':SCN:GRP:EDT %i;:SCN:TYPE NORM;THR %i;NAVG %i;NSAM %i;MASS:STEP %1.6f;RANG %1.6f,%1.6f;*ESR?' % (parms['EDT']['value'], parms['Threshold']['value'],  parms['Avg']['value'], parms['Samples']['value'], parms['Step']['value'], parms['RangeFrom']['value'],  parms['RangeTo']['value'])
		self.logl("Scan: ", scan)
		self.esr =  self.br.cmd(self.dev,scan)
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
			
		return self.esr
	def getScanType(self):
		return self.br.cmd(self.dev,':SCN:TYPE?')
		
	def scanStart(self, partial=False):
		self.logl ('Scan start')
		if partial:
			self.esr = self.br.cmd(self.dev,':PSCN:STRT;*ESR?')
		else:
			self.esr = self.br.cmd(self.dev,':SCN:STRT;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
			
	def clearLensTable(self):
		self.esr = self.br.cmd(self.dev,':LENS:TBL:CLR;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
		
	def dataMode(self, n):
		#print ('Data Mode: ')
		self.esr= self.br.cmd(self.dev,':DAT:MODE:BRECP %i, 4086;*ESR?'% n)
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
	
	def readData(self):
		data = self.br.cmd(self.dev,':DAT:READ?', raw=True)
		#print (data)
		self.statusb = self.br.statusb(self.dev)
		#print('RPost REad Status ', self.br.getStb())
		##while stb == last_stb:
		##        stb = self.dev.read_stb()
		##        print (stb)
		self.rs = readspec.MachineSpec(data, self.logl)
		
	def getConfig(self, progress=None):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = self.p_step
		self.faultstat = self.getFaultStat()
		progress(p)
		self.sourceTemp = self.getSourceTemp()
		progress(p)
		self.pressure = self.getPressure()
		progress(p)
		self.diffPump = self.isDiffPumpOn()
		progress(p)
		self.pftba = self.isPFTBAOn()
		progress(p)
		self.gotConfig = True
		return self.getStoredConfig()
	
	def scanSeq(self, parms, progress=None, partial=False):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = self.p_step
		self.clearBuf()
		progress(p)
		self.scanSetup(parms, partial=partial)
		progress(p)
		self.scanStart(partial=partial)
		progress(p)
		self.dataMode(1)
		progress(p)
		self.readData()
		progress(40)
		
	def scanDone(self, progress=None, moreScans=False):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = self.p_step
		self.clearBuf()
		progress(p)
		if not moreScans:
			self.readyOff()
			progress(p)
		
	def emit_dummy(a):
		pass
		
	def msdInit(self, progress=None):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = 4
		self.reset()
		progress(p)
		self.ErrStr = self.getErrors()
		progress(p)
		self.readyOff()
		progress(p)
		self.rvrOff()
		progress(p)
		gotConfig= False
		
	def scanInit(self, mparms, tparms, progress=None):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = self.p_step
		self.logl("Mass")
		self.massParms(mparms)
		progress(p)
		self.logl("Tuning")

		self.tuningParms( tparms, True)

		progress(p)
		self.logl("Filt")
		self.filtSetupStd()
		progress(p)
		self.qualSetupMaxOf3()
		progress(p)
		self.calValve(tparms['PFTBA']['value'])
		progress(p)
		self.logl("ReadyOn")
		self.readyOn()
		progress(p)
		self.logl("RvrOff")

		self.rvrOff()
		progress(p)
		self.faultstat = self.getFaultStat()
		self.logl("Fault: ", self.faultstat)
		progress(p)
		
	def getAScan(self, parms, progress=None):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = self.p_step
		if not self.gotConfig:
			self.getConfig(progress)
		self.logl("ScanInit")
		self.scanInit(parms['Mass'], parms['Tuning'], progress)
		self.logl("ScanSeq")
		self.scanSeq(parms['Scan'], progress)
		self.logl("ScanDone")
		self.scanDone(progress)
		
	def getPartialScan(self, parms, progress=None, moreScans=False):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = self.p_step
		if not self.gotConfig:
			self.getConfig(progress)
		self.logl("ScanInit")
		self.scanInit(parms['Mass'], parms['Tuning'], progress)
		self.logl("ScanSeq")
		self.scanSeq(parms['Scan'], progress, partial=True)
		self.logl("ScanDone")
		self.scanDone(progress, moreScans=moreScans)
	
	def getSpec(self):
		#return self.rs.getSpectrum()
		return self.rs
	def getStoredConfig(self):
		return {'Fault' : self.faultstat,
		'SourceTemp':self.sourceTemp ,
		'Pressure': self.pressure ,
		'DiffPump': self.diffPump,
		'PFTBA': self.pftba}

	def runStat(self):
		self.runstat = int(self.br.cmd(self.dev ,":RUN:STAT?").decode('ascii', errors='replace').strip())
		return self.runstat
	
	def getAer(self):
		self.aer = int(self.br.cmd(self.dev ,":AER?").decode('ascii', errors='replace').strip())
		return self.aer
		
	def getRunTime(self):
		self.runtime = float(self.br.cmd(self.dev ,":RUN:TIME?").decode('ascii', errors='replace').strip())
		return self.runtime
		
	def setRunDuration(self, t):
		self.esr = self.br.cmd(self.dev, ":RUN:DUR %.6f;*ESR?" % t)
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
		
	def setSrcEs(self, es):
		self.esr = self.br.cmd(self.dev, ":CONFIG:SRC:ES %i;*ESR?" % es)
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr

	def runReady(self):
		self.esr = self.br.cmd(self.dev ,":RUN:REM:APG ON;:RUN:RDY ON;*ESR?")
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr

	def createRunTable(self, solventDelay):
		self.esr = self.br.cmd(self.dev ,":RUN:TBL:CLR;DEF 0, #214:SCN:GRP:ACT 0;DEF %i, #211:MSC:RDY ON;DEF %i, #221:REP:PROG #18SCN:STRT;*ESR?" % (solventDelay, solventDelay))
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr
			
	def runTableOverride():
		self.esr = self.br.cmd(self.dev ,":REP:PROG #18SCN:STRT;*ESR?")
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))
		return self.esr

	def override(self):
		self.readyOn()
		self.runTableOverride()
	
	def scanStrtSeqInt(self, sparms, mparms, tparms, rparms, progress=None):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = self.p_step
		self.scanSeqInit(False)
		progress(p)
		self.dataMode(10)
		progress(p)
		self.scanSetup(sparms, False)
		progress(p)
		self.filtSetupStdCoeff(1)
		progress(p)
		self.setRunDuration(39000.0)
		progress(p)
		self.calValve(0)
		progress(p)
		self.setSrcEs(0)
		progress(p)
		self.tuningParms(tparms, False)
		progress(p)
		self.clearLensTable()
		progress(p)
		self.filtSetupStd()
		progress(p)
		self.qualSetupMaxOf3()
		progress(p)
		self.massParms(mparms)
		progress(p)
		self.createRunTable(rparms['SolventDelay']['value'])
		progress(p)

	def tunePeak(self, parms, n):
		comp = parms['Tuning']['Compound']
		name = 'Peak%i' % n
		return comp[name]['value']
	
	def adjScanParms(self, sparms, peak, span=10.0, avg=1, samples=16, step=0.10):
		sparms['RangeFrom']['value'] = peak - (span/2.0)
		sparms['RangeTo']['value'] = peak + (span/2.0)
		sparms['Avg']['value'] = avg
		sparms['Samples']['value'] = samples
		sparms['Step']['value'] = step
	
	def scanStartSeq(self, parms, progress=None):
		self.scanStrtSeqInt(parms['Scan'], parms['Mass'], parms['Tuning'], parms['Run'], progress)
		
	def getRunStat(self,progress=None):
		return { 'RunStat': self.runStat(),	
							'AER' : self.getAer(), 
							'RunTime': self.getRunTime()}
		
	def getNrec(self):
		self.nrec = int(self.br.cmd(self.dev ,":BUF:NREC?").decode('ascii', errors='replace').strip())
		return self.nrec
	
	def runStop(self):
		self.logl ('Run Stop: ')
		self.esr =  self.br.cmd(self.dev,':RUN:STOP;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))

	def endRun(self, progress=None):
		if progress is None:
			progress=HP5971.emit_dummy 
		p = self.p_step
		self.runStop()
		progress(p)
		self.readyOff()
		progress(p)
		nr = int(self.getNrec())
		return nr
	
	def runReadyOff(self):
		self.esr =  self.br.cmd(self.dev,':RUN:REM:APG:RDY OFF;MASK 4;*ESR?')
		if int(self.esr) != 0:
			raise HP5971Exception('Bad status register: ' + str(self.esr))

	def faultmsgs(f):
		fm = f & 16383
		fd = 8192
		fmsgs = []
		while fd > 0:
			fi = fm & fd
			if  fi > 0:
				if fi in HP5971.faults:
					fmsgs.append(HP5971.faults [fi])
				else:
					fmsgs.append(str(fi))
			fd = fd >> 1
		return fmsgs
	
	def status(self):
		return self.br.statusb(self.dev)
		
class HP5971Exception(Exception):
	pass
