import visa
import re
import json
import struct
import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pygcms.msfile.readspec as readspec
import pygcms.device.busreader as busreader
import pygcms.device.hp5971 as hp5971
import pygcms.device.hp7673 as hp7673
import pygcms.device.hp5890 as hp5890
import time
import datetime
import pygcms.msfile.msfileread as msfr
import argparse 

method = sys.argv[1]
if len(sys.argv) > 2 and sys.argv[2] == '--run':
	msfile = sys.argv[3]
	doRun = True
else:
	doRun = False
	
f = open(method + ".json", "r")
mtparms = f.read()
mparms = json.loads(mtparms)
f.close()

br = busreader.BusReader()

def load5971():
		msd = br.deviceByName('5971')
		if br.isSmartCardDevice(msd) and br.needsLoading(msd):
				br.loadSmartCard(msd)
		return msd
		
def test5971_alone():
		m = hp5971.HP5971(msd, br)
		m.getAScan(parms)
		m.rs.plotit()

def test5971_seq(msd, m):
		m.scanStartSeq(mparms['Method']['MSParms'])
		m.getRunStat()
		
def init7673(gc, injector):
		inj = br.deviceByName('7673')
		i = hp7673.HP7673(inj, br, injector, gc.addr)
		print(i.reset())
		return i

def movel(i, n, vial):
		if n == 1:
			print(i.status())
			st = i.moveStart(vial, "RR")
		elif n == 2:
			st = i.moveStart("RR", "I%i" % i.injnum)
		elif n == 4:
			st = i.moveStart("I%i" % i.injnum, vial)
		else:
			st = False
		return st
		

def test5890():
		gasc = br.deviceByName('5890')
		gc= hp5890.HP5890(gasc, br, mparms['Method']['GCParms'])
		gc.upload()
		return gc

def datProcFile(m, idx):
		m.readData()
		f = open("scan%i.bin" % idx, "wb")
		m.rs.saveRaw(f)
		f.close()

def datProc(m, idx):
		m.readData()
		specs.append((m.rs.spectrum['RetTime'], m.rs))

specs = []
msd = load5971()
ms = hp5971.HP5971(msd, br)
ms.scanSeqInit(True)
cd = ms.getConfig()
print(cd)
if cd ['Fault'] == 33:
	br.loadSmartCard(msd, reboot=True)
	
gc = test5890()
i = init7673(gc, mparms['Method']['Injector']['UseInjector'])
test5971_seq(msd, ms)
cd = ms.getConfig()
print(cd)
if doRun:
	idx = 0
	doData = False
	injecting = False
	injected = False
	moving = False
	movpos = 1
	while True:
		if not injected and not moving and not injecting:
			moving = movel(i, movpos, mparms['Method']['Header']['Vial'])
			movpos += 1
		if moving:
			moving = not i.injDone()
			if not moving:
				if not injecting:
					mvst = i.moveFinish()
					print (movpos, mvst)
				else:
					ijst = i.injectFinish()
					print (movpos, ijst)
				if movpos == 2:
					print("Reader: ", i.read())
				elif movpos == 3:
					ms.runReady()
					parms = mparms['Method']['Injector']
					i.injectStart( prewash=parms['Prewash'], visc=parms['Viscosity'], pumps = parms['Pumps'], 
						quant=parms['Quantity'], solvwasha=parms['SolvWashA'], solvwashb=parms['SolvWashB'])
					injecting = True
					moving = True
					movpos += 1
				elif movpos == 4:
					print(i.status(dosi=True))
					injecting = False
				elif movpos == 5:
					injected = True
		if doData:
			stb = br.statusb(msd)
			print ('5971 Data st: ', stb)
			while stb == 8:
				datProc(ms, idx)
				idx+=1
				stb = br.statusb(msd)
				print('5971 st: ', stb)
			if not gc.isRunning():
				gc.endRun()
				nr = ms.endRun()
				while nr > 0:
					stb = br.statusb(msd)
					print(stb)
					datProc(ms, idx)
					idx += 1
					nr -= 1
				ms.runReadyOff()
				break
		runstat =  ms.getRunStat()
		print(runstat)
		stb = br.statusb(msd)
		print ('5971 Run st: ', stb)
		if stb != 8: 
			gcst = gc.statcmds()
			print(gcst)
		if not doData:
			msst = ms.getConfig()
			print(msst)
			flt = msst['Fault']
		else :
			if stb != 8:
				flt = ms.getFaultStat()
				stb = br.statusb(msd)
				print ('5971 Fault st: ', stb, flt)
			else:
				flt = 0
		if flt != 0:
			print ('Fault %i. Terminating.' % flt)
			print(hp5971.HP5971.faultmsgs(flt))
			gc.endRun()
			ms.endRun()
			ms.runReadyOff()
			break
		if float(ms.runtime) > 180.0:
			if runstat['RunStat'] == 2 and runstat['AER'] == 64:
				doData=True
	d = datetime.datetime.now()
	hdr = {
			'Data_name': bytes(mparms['Method']['Header']['SampleName'].rjust(30),'ascii'), 
			'Misc_info': bytes(mparms['Method']['Header']['Info'].rjust(25), 'ascii'),
			'Operator': bytes(mparms['Method']['Header']['Operator'].ljust(9)[0:9], 'ascii'),
			'Date_time': bytes(d.strftime('%d %b %y  %I:%m %p'), 'ascii'),
			'Inst_model': bytes(mparms['Method']['Header']['Inst'].ljust(9)[0:9], 'ascii'),
			'Inlet': b'GC', 
			'Method_File': bytes(method.ljust(19), 'ascii'),
			'Als_bottle': mparms['Method']['Header']['Vial'], 
	}
	print(hdr)
	print(len(specs))
	msf = msfr.ReadMSFile(spectra=specs)
	msf.setHeader(hdr)
	#msf.plotit()
	#x, ions = spectra[0]
	#ions.plotit()
	print(msf.theRun)
	msf.writeFile(msfile + '.MS')
