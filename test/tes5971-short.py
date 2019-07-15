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

import pygcms.msfile.msfileread as msfr

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

msd = load5971()
ms = hp5971.HP5971(msd, br)

ms.reset()
cd = ms.getConfig()
print(cd)

print(ms.getAvc())
print(ms.getCivc())
wrd = ms.getRevisionWord()
print (hp5971.HP5971.getLogAmpScale(wrd))
print(ms.diagIO())



	
