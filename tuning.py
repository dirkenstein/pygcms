import hp5971 
import copy
import numpy as np
import scipy
import pandas 
import math
import putil 

class HP5971Tuning():
	def __init__(self,msd, parms, logl=print):
		self.hpmsd = msd
		self.parms = copy.deepcopy(parms)
		self.logl = logl
		self.defaultMassParms = parms['Mass']
		self.defaultTuningParms = parms['Tuning']
		sparms = parms['Scan']
		self.mass = [{},{}, {}]
		self.tunepk = [0, 0, 0]
		for x in range(3):
			self.tunepk[x]=  self.hpmsd.tunePeak(self.parms, x+1)
			self.mass[x] = copy.deepcopy(sparms)
			self.hpmsd.adjScanParms(self.mass[x],self.tunepk[x])
		wrd = self.hpmsd.getRevisionWord()
		self.logampf = hp5971.HP5971.getLogAmpScale(wrd)
	
	def getParms(self):
		self.parms.update({'Mass': self.defaultMassParms})
		self.parms.update({'Tuning': self.defaultTuningParms})
		return self.parms

	def readAScanAb(self, n=0):
		 self.hpmsd.scanStart(partial=True)
		 self.hpmsd.dataMode(1)
		 self.hpmsd.readData()
		 self.abPw50()
		 self.emitScan(n)
		 
	def stdSetupAb(self):
		self.hpmsd.filtSetupStd()
		self.hpmsd.qualSetupMaxOf3()
		self.hpmsd.readyOn()
		self.hpmsd.rvrOff()
		self.fault = self.hpmsd.getFaultStat()
	def defMassParmsAb(self):
		self.fault = self.hpmsd.getFaultStat()
		self.hpmsd.rvrOn()
		self.hpmsd.massParms(self.defaultMassParms)
	def setupMass1Ab(self):
		self.hpmsd.scanSetup(self.mass[0], partial=True)
		self.hpmsd.clearBuf()
	def initAbundance(self):
		self.hpmsd.rvrOff()
		self.fault = self.hpmsd.getFaultStat()
		self.hpmsd.massParms(self.defaultMassParms)
		self.hpmsd.tuningParms(self.defaultTuningParms, nxt=True)

	def start(self, tparms, value):
			return tparms['Ramp'][value]['Start']['value']
	def stop(self, tparms, value):
			return tparms['Ramp'][value]['Stop']['value']

	def step(self, tparms, value):
		return tparms['Ramp'][value]['Step']['value']

	def ramp(self,tparms, value,n):
		nparms = copy.deepcopy(tparms)
		nparms[value]['value'] = nparms[value]['value'] + (self.step(tparms, value)*n)
		return nparms
	
	def ratio(self,tparms, value,n):
		nparms = copy.deepcopy(tparms)
		nparms[value]['value'] = nparms[value]['value']*n
		return nparms
	
	def ov(self,tparms, value):
		return tparms[value]['value']
		
	def nv(self,tparms, value, n):
		nparms = copy.deepcopy(tparms)
		nparms[value]['value'] = n
		return nparms
		
	def rampEmv(self,tparms, n):
		return self.ramp(tparms, 'EMVolts', n)
	
	def rampAmuOfs(self,tparms, n):
		return self.ramp(tparms, 'AmuOffs', n)
	
	def rampAmuGain(self,tparms, n):
		return self.ramp(tparms, 'AmuGain', n)
	def ratioAmuOfs(self,tparms, n):
		return self.ratio(tparms, 'AmuOffs', n)
	
	def ratioAmuGain(self,tparms, n):
		return self.ratio(tparms, 'AmuGain', n)
	def abPw50(self):
		i = self.hpmsd.getSpecs()[0].getSpectrum()['ions']
		self.maxab =i['abundance'].max()
		self.maxima, self.minima = putil.PUtil.peaksfr(i, 'abundance', 'm/z')
		#		#sels= []
				#for idx, r in self.maxima.iterrows():
					#sels.append((False, None, None))
				#self.sels = sels
				#from scipy.interpolate import UnivariateSpline
		self.spline = scipy.interpolate.UnivariateSpline(i['m/z'],i['abundance'] - i['abundance'].max()/2,s=0)
		self.fwhm = abs(self.spline.roots()[1]-self.spline.roots()[0])
		return self.maxab, self.fwhm
		
	def abundance(self, ab1, ab2):
		
		adjAb1 = ab1 * self.logampf
		adjAb2 = ab2 * self.logampf
		self.maxabs = [0,0,0]
		self.pws = [0,0,0]
		self.initAbundance()
		
		self.stdSetupAb()
		self.setupMass1Ab()
		self.readAScanAb(0)
		self.maxabs[0] = self.maxab
		self.logl("mass1 ab ",self.maxabs[0] )

		self.hpmsd.scanSetup(self.mass[1], partial=True)
		self.readAScanAb(1)
		self.maxabs[1] = self.maxab
		
		self.logl("mass2 ab ",self.maxabs[1] )
		self.hpmsd.scanSetup(self.mass[2], partial=True)
		self.readAScanAb(2)
		self.maxabs[2] = self.maxab
		self.logl("mass3 ab ",self.maxabs[2] )

		print ("initial ratio 1:" , self.maxabs[1]/self.maxabs[0], ":", self.maxabs[2]/self.maxabs[0])  

		step = 1
		emv = 0
		while step != 0:
			if self.maxabs[0] > adjAb2:
				step = -1 
			elif self.maxabs[0] < adjAb1:
				step = 1 
			else:
				step = 0
			if step != 0:
				self.logl("ramp EMV ", step, ":", emv)
				emv += step
				self.hpmsd.massParms(self.defaultMassParms)
				self.hpmsd.tuningParms(self.rampEmv(self.defaultTuningParms, emv), nxt=True)
							
				self.stdSetupAb()
				self.setupMass1Ab()
				self.readAScanAb(0)
				self.maxabs[0] = self.maxab
					
				self.logl("mass1 ab ",self.maxabs[0] )
			
				self.hpmsd.scanSetup(self.mass[1], partial=True)
				self.readAScanAb(1)
				self.maxabs[1] = self.maxab
				self.logl("mass2 ab ", self.maxabs[1])

				self.hpmsd.scanSetup(self.mass[2], partial=True)
				self.readAScanAb(2)
				self.maxabs[2] = self.maxab
				self.logl("mass3 ab ", self.maxabs[2])
		
		print ("final emv adj ", emv, " ratio 1:" , self.maxabs[1]/self.maxabs[0], ":", self.maxabs[2]/self.maxabs[0])  
		newemv = emv
		self.defaultTuningParms = self.rampEmv(self.defaultTuningParms, newemv)
	
	def width(self, secondpeak):
		#amuG = [538.124266, 539.348550, 541.378532, 542.360946 , 542.000000]
		#amuO = [87.452978, 86.917336, 85.903778, 85.376510, 85.000000]
		
		self.defMassParmsAb()
		self.hpmsd.tuningParms(self.defaultTuningParms, nxt=True)
		self.stdSetupAb()		
		self.hpmsd.massParms(self.defaultMassParms)
		self.hpmsd.tuningParms(self.defaultTuningParms, nxt=True)

		self.stdSetupAb()
		self.setupMass1Ab()
		self.readAScanAb(0)
		self.pws[0] = self.fwhm
		self.logl("mass1 pw ", self.pws[0])

		self.hpmsd.massParms(self.defaultMassParms)
		self.hpmsd.tuningParms(self.defaultTuningParms, nxt=True)
		self.stdSetupAb()
		self.hpmsd.scanSetup(self.mass[secondpeak], partial=True)
		self.readAScanAb(secondpeak)
		self.pws[secondpeak] = self.fwhm
		self.logl("massx pw ", self.pws[secondpeak])
		ideal = 0.5
		pwr =  self.pws[secondpeak]/self.pws[0]
		pwo = self.pws[0] - ideal 
		pwos = self.pws[secondpeak] - ideal
		pwors = self.pws[secondpeak]/ideal
		print ("pw ratio 1: ", pwr)
		print ("ideal diff: 1: ", pwo , "3: " , pwos)
		#ganr = (1.0/pwr + 1.0/pwor2)/2
		#gano = -(pwo + pwos)/2
		limit = 0.075
		limit2 = 1.0
		opwo =  pwo
		opwos = pwos
		self.updatedTuningParms = copy.deepcopy(self.defaultTuningParms)
		gainstep = self.step(self.updatedTuningParms, 'AmuGain')
		ofsstep = self.step(self.updatedTuningParms, 'AmuOffs')
		while abs(pwo) > limit or abs(pwos) > limit or abs(1-pwr) > limit:
			ogain = self.ov(self.updatedTuningParms, 'AmuGain')
			oofs = self.ov(self.updatedTuningParms, 'AmuOffs')
			if abs(pwo) > limit2 or abs(pwos) > limit2 or abs(1-pwr) > limit2:
				self.logl("step width adj")
				if pwos > 0:
					ngain = ogain + gainstep
				else:
					ngain = ogain - gainstep
				if pwo > 0:
					nofs = oofs + ofsstep
				else:
					nofs = oofs - ofsstep
				if abs(opwo) > abs(pwo):
					offstep = offstep /2
				if abs(opwos) > abs(pwos):
					gainstep = gainstep /2
			else:
			#self.updatedTuningParms = self.rampAmuOfs(self.ratioAmuGain(self.updatedTuningParms, ganr), gano)
				self.logl("small width adj")
				ngain = ogain + (pwos + self.tunepk[0]/self.tunepk[secondpeak]*pwo)/2
				nofs = oofs + (pwo + pwos)/4

			self.logl("new gain: ", ngain, "new ofs: ", nofs)
			self.updatedTuningParms = self.nv(self.nv(self.updatedTuningParms, 'AmuGain', ngain), 'AmuOffs', nofs)

			self.hpmsd.massParms(self.defaultMassParms)
			self.hpmsd.tuningParms(self.updatedTuningParms, nxt=True)
			self.stdSetupAb()
			self.setupMass1Ab()
			self.readAScanAb(0)
			self.pws[0] = self.fwhm
			self.logl("mass1 pw ", self.pws[0])

			
			self.hpmsd.massParms(self.defaultMassParms)
			self.hpmsd.tuningParms(self.updatedTuningParms, nxt=True)
			self.stdSetupAb()
			self.hpmsd.scanSetup(self.mass[2], partial=True)
			self.readAScanAb(2)
			self.pws[secondpeak] = self.fwhm
			self.logl("mass%i pw " % (secondpeak+1), self.pws[2])
			opwo =  pwo
			opwos = pwos
			pwr =  self.pws[secondpeak]/self.pws[0]
			pwo = self.pws[0] - ideal 
			pwos = self.pws[secondpeak] - ideal
			pwors = self.pws[secondpeak]/ideal

			self.logl ("pw ratio 1: ", pwr)
			self.logl ("ideal diff: 1: ", pwo, "%i: "% (secondpeak+1) , pwos)
			#ganr = (1.0/pwr + 1.0/pwor2)/2
			#gano = -(pwo + pwos)/2
		gain = self.ov(self.updatedTuningParms, 'AmuGain')
		ofs = self.ov(self.updatedTuningParms, 'AmuOffs')
		self.updatedTuningParms = self.nv(self.nv(self.updatedTuningParms, 'AmuGain', math.trunc(gain)), 'AmuOffs', math.trunc(ofs))

		
		self.defMassParmsAb()
		self.hpmsd.tuningParms(self.updatedTuningParms, nxt=True)
		self.stdSetupAb()
		
		self.hpmsd.massParms(self.defaultMassParms)
		self.hpmsd.tuningParms(self.updatedTuningParms, nxt=True)
		self.stdSetupAb()
		self.setupMass1Ab()
		self.readAScanAb(0)
		self.logl("mass1 ab: ", self.maxab, " pw ", self.fwhm)


		self.hpmsd.scanSetup(self.mass[1], partial=True)
		self.readAScanAb(1)
		self.logl("mass2 ab: ", self.maxab, " pw ", self.fwhm)


		self.hpmsd.scanSetup(self.mass[2], partial=True)
		self.readAScanAb(2)
		self.logl("mass3 ab: ", self.maxab, " pw ", self.fwhm)
		self.defaultTuningParms = self.updatedTuningParms

	def scanRepMx(self, n):
		summz = 0
		sumab = 0
		for x in range(5):
			self.readAScanMx(n)
			summz += self.mzofmax
			sumab += self.maxab
		self.avgmz = summz / 5
		self.avgab = sumab / 5
		self.logl ("avg m/z: ", self.avgmz, " avg ab: ", self.avgab)
		
	def setupMass1Mx(self):
		self.hpmsd.massRange(self.mass[0], 0)
		self.hpmsd.clearBuf()
		self.hpmsd.scanSetup(self.mass[0], partial=False)
	def readAScanMx(self, n):
		self.hpmsd.scanStart(partial=False)
		self.hpmsd.dataMode(1)
		self.hpmsd.readData()
		self.mzaxis()
		self.emitScan(n)
	def stdSetupMx(self):
		self.fault = self.hpmsd.getFaultStat()
		self.hpmsd.rvrOn()
		self.hpmsd.massParms(self.defaultMassParms)
		self.hpmsd.tuningParms(self.defaultTuningParms, nxt=True)
		self.hpmsd.filtSetupStd()
		self.hpmsd.qualSetupMaxOf3()
		self.hpmsd.readyOn()
		self.hpmsd.rvrOff()
		self.fault = self.hpmsd.getFaultStat()

	def mzaxis(self):
			i = self.hpmsd.getSpecs()[0].getSpectrum()['ions']
			self.maxab =i['abundance'].max()
			idx = i['abundance'].idxmax()
			#self.mzofmax = i['m/z'].iloc(idx)
			self.mzofmax = i.iloc[idx]['m/z']
			self.logl ("maxab: ", self.maxab, " idx:" , idx, " m/z: ", self.mzofmax)
			
	def axis(self, secondpeak):
		self.stdSetupMx()
		self.hpmsd.massParms( self.defaultMassParms)
		self.setupMass1Mx()
		self.scanRepMx(0)
		mz1 = self.avgmz 
		ab1 = self.avgab
		self.hpmsd.massRange(self.mass[0], 0.05)
		self.scanRepMx(0)
		mz1o = self.avgmz
		ab1o = self.avgab
		self.hpmsd.massRange(self.mass[secondpeak], 0)
		self.scanRepMx(secondpeak)
		mz2 = self.avgmz
		ab2 = self.avgab
		self.hpmsd.massRange(self.mass[secondpeak], 0.05)
		self.scanRepMx(secondpeak)
		mz2o = self.avgmz
		ab2o = self.avgab
		
		if ab1o > ab1:
			ab1u = ab1o
			mz1u = mz1o 
			mz1u += 0.05
		else:
			ab1u = ab1
			mz1u = mz1
		
		if ab2o > ab2:
			ab2u = ab2o
			mz2u = mz2o 
			mz2u += 0.05
		else:
			ab2u = ab2
			mz2u = mz2
			
		d1 = mz1o - mz1
		d2 = mz2o - mz2
		
		mz1d =  mz1u - self.tunepk[0]
		mz2d = mz2u - self.tunepk[secondpeak]
		spanref = self.tunepk[secondpeak] -  self.tunepk[0]
		spanreal = mz2u - mz1u
		
		self.logl("diff1 ", d1," diff2 ", d2)
		self.logl ("diff base " ,mz1d)
		self.logl ("diff second ", mz2d)
		self.logl ("span ref ", spanref)
		self.logl ("span real ", spanreal)
		self.logl("span diff: ", spanref - spanreal)
		self.logl ("ab1 ", ab1, ab1o)
		self.logl ("ab2 ", ab2, ab2o)
		omasg = self.ov(self.defaultMassParms, 'MassGain')
		omaso = self.ov(self.defaultMassParms, 'MassOffs')
		#self.logl("new gain: ", omasg*spanreal/spanref)
		nmasg =  round(omasg + ((spanref - spanreal)*mz2u))
		nmaso = round(omaso - ((spanref - spanreal)*mz1u))
		self.logl ("old gain : ", omasg, " old ofs ", omaso)
		self.logl ("new gain : ", nmasg, " new ofs ", nmaso)
		self.correctedMassParms = self.nv(self.nv(self.defaultMassParms, 'MassGain', nmasg), 'MassOffs', nmaso)
		self.hpmsd.massParms(self.correctedMassParms)
		self.setupMass1Mx()
		self.scanRepMx(0)
		mz1 = self.avgmz 
		ab1 = self.avgab
		
		self.hpmsd.massRange(self.mass[0], 0.05)
		self.scanRepMx(0)
		mz1o = self.avgmz 
		ab1o = self.avgab

		self.hpmsd.massRange(self.mass[2], 0)
		self.scanRepMx(1)
		mz3 = self.avgmz
		ab3 = self.avgab

		self.hpmsd.massRange(self.mass[2], 0.05)
		self.scanRepMx(2)
		mz3o = self.avgmz
		ab3o = self.avgab

		
		if ab1o > ab1:
			ab1u = ab1o
			mz1u = mz1o 
			mz1u += 0.05
		else:
			ab1u = ab1
			mz1u = mz1
		
		if ab3o > ab3:
			ab3u = ab3o
			mz3u = mz3o 
			mz3u += 0.05
		else:
			ab3u = ab3
			mz3u = mz3
			

		d1 = mz1o - mz1
		d3 = mz3o - mz3
		mz1d =  mz1u - self.tunepk[0]
		mz3d =  mz3u - self.tunepk[2]
		spanref =  self.tunepk[2] -self.tunepk[0]
		spanreal = mz3u - mz1u
	
		self.logl("diff1 ", d1," diff3 ", d3)
		self.logl ("diff base " , mz1d)
		self.logl ("diff third ", mz3d)
		self.logl ("span ref ", spanref)
		self.logl ("span real ", spanreal)
		self.logl("span diff: ", spanref - spanreal)
		self.logl ("ab1 ", ab1, ab1o)
		self.logl ("ab2 ", ab3, ab3o)
		omasg = self.ov(self.correctedMassParms, 'MassGain')
		omaso = self.ov(self.correctedMassParms, 'MassOffs')
		#self.logl("new gain: ", omasg*spanreal/spanref)

		nmasg =  round(omasg + ((spanref - spanreal)*mz3u))
		nmaso = round(omaso - ((spanref - spanreal)*mz1u))
		self.logl ("old gain : ", omasg, " old ofs ", omaso)
		self.logl ("new gain : ", nmasg, " new ofs ", nmaso)
		self.correctedMassParms = self.nv(self.nv(self.defaultMassParms, 'MassGain', nmasg), 'MassOffs', nmaso)
		self.defaultMassParms = self.correctedMassParms 
	
	def rampInit(self):
		self.fault = self.hpmsd.getFaultStat()
		self.hpmsd.rvrOn()
	
	def rampPrep(self):
		self.hpmsd.massParms(self.defaultMassParms)
		self.hpmsd.tuningParms(self.defaultTuningParms, nxt=True)
		self.hpmsd.filtSetupStd()
		self.hpmsd.qualSetupMaxOf3()
		self.hpmsd.readyOn()
		self.hpmsd.rvrOff()
	
	def rampMax(self):
		i = self.hpmsd.getSpecs()[0].ramp
		self.maxramp =i['abundance'].max()
		maxidx = i['abundance'].idxmax()
		maxvidx = i['voltage'].idxmax()
		self.voltofmax = i.iloc[maxidx]['voltage']
		self.rampmaxima, self.rampminima = putil.PUtil.peaksfr(i,'abundance','voltage')
		if not self.rampmaxima.empty:
			# = pandas.DataFrame(np.array(maxtab), columns=['voltage', 'abundance'])
			idxm = self.rampmaxima['abundance'].idxmax()
			self.voltofmax = self.rampmaxima.iloc[idxm]['voltage']
			
		#if len(mintab) > 0:
		#	self.rampminima = pandas.DataFrame(np.array(mintab), columns=['voltage', 'abundance'])
		self.avgvol = i['voltage'].mean()
		self.avgab = i['abundance'].mean()
		nearest = putil.PUtil.nearest(i, 'abundance', self.avgab)
		self.voltofavg =  nearest.iloc[0]['voltage']
		if maxidx == maxvidx:
			self.chosenvoltage = self.voltofavg
		else:
			self.chosenvoltage = self.voltofmax
		
	def readRampRecs(self, parm, n=0):
		nrec = self.hpmsd.getNrec()
		self.hpmsd.dataMode(nrec)
		self.hpmsd.readData()
		self.hpmsd.merge()
		self.hpmsd.getSpecs()[0].rampBuild( self.start(self.defaultTuningParms, parm), self.step(self.defaultTuningParms, parm))
		self.rampMax()
		ovolt = self.ov(self.defaultTuningParms , parm)
		self.emitRamp(n, parm, ovolt)
		
	def rampIt(self, mass, nam, parm, dwell=35):
		self.rampInit()
		self.rampPrep()
		self.hpmsd.simSetup(mass, 100/1000)
		self.hpmsd.simAct()
		self.hpmsd.simRamp(mass, dwell/1000, nam, self.start(self.defaultTuningParms, parm), self.stop(self.defaultTuningParms, parm), self.step(self.defaultTuningParms, parm))
	
	def rampRep(self):
		self.doRamp( "REP", "Repeller", 35)
	
	def rampIon(self):
		self.doRamp( "IFOC", "IonFocus", 35)
	
	
	def rampEnt(self):
		self.doRamp("ENT", "EntLens", 35)

	def rampEntOfs(self):
		self.doRamp("ENTO", "EntOffs", 35)
	
	def rampXray(self):
		self.doRamp("XRAY", "Xray", 35)
	
	def doRamp(self, nam, parm, dwell):
		self.rampv = [0, 0, 0]
		self.rampInit()
		self.rampPrep()
		self.rampIt(self.tunepk[0], nam, parm, dwell)
		self.readRampRecs(parm, 0)
		self.rampv[0] = self.chosenvoltage
		self.rampPrep()
		self.rampIt(self.tunepk[1], nam, parm, dwell)
		self.readRampRecs(parm, 1)
		self.rampv[1] = self.chosenvoltage
		self.rampPrep()
		self.rampIt(self.tunepk[2], nam, parm, dwell)
		self.readRampRecs(parm, 2)
		self.rampv[2] = self.chosenvoltage
		newv = math.fsum(self.rampv)/len(self.rampv)
		print ("New voltage: ", newv)
		self.defaultTuningParms = self.nv (self.defaultTuningParms, parm, newv)
		
	def emitScan(self, n):
		self.hpmsd.getSpecs()[0].plotit(name = ' ' + str(self.tunepk[n]))
	def emitRamp(self, n, parm, ovolt):
		self.hpmsd.getSpecs()[0].plotrampit(' ' +parm + ' ' + str(self.tunepk[n]), currvolt=ovolt)
