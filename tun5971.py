import visa
import re
import json
import struct
import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import readspec
import busreader
import hp5971
import tuning
import time

import msfileread as msfr

def load5971(br):
		msd = br.deviceByName('5971')
		if br.isSmartCardDevice(msd) and br.needsLoading(msd):
				br.loadSmartCard(msd)
		return msd
		
def test5971_alone():
		m = hp5971.HP5971(msd, br)
		m.getAScan(parms)
		m.rs.plotit()


def main():
	method = sys.argv[1]
	
	f = open(method + ".json", "r")
	mtparms = f.read()
	mparms = json.loads(mtparms)
	f.close()
	
	parms = mparms['Method']['MSParms']
	br = busreader.BusReader()
	
	msd = load5971(br)
	ms = hp5971.HP5971(msd, br)
	
	ms.reset()
	cd = ms.getConfig()
	print(cd)
	if cd ['Fault'] == 33:
		br.loadSmartCard(msd, reboot=True)
	
	print(ms.getAvc())
	print(ms.getCivc())
	wrd = ms.getRevisionWord()
	print (hp5971.HP5971.getLogAmpScale(wrd))
	print(ms.diagIO())
	ms.calValve(1)
	ms.readyOn()
	time.sleep(30)
	tun = tuning.HP5971Tuning(ms, parms)
	tun.abundance(1e6, 3e6)
	tun.width(2)
	tun.abundance(1e6, 3e6)
	tun.axis(1)
	tun.rampEnt()
	tun.rampEntOfs()
	tun.rampXray()
	tun.rampRep()
	tun.rampIon()

	parms = tun.getParms()
	f = open("tunnew.json", "w")
	f.write(json.dumps(parms, indent=4))
	f.close()
	
	
main()