import json
import sys 
import struct 

def updatefromTuning(t, parms):
	for parm in parms:
		prm = parms[parm]
		if 'floc' in prm and 'ftype' in prm:
			flc = parms[parm]['floc']
			ft = parms[parm]['ftype']
			if ft == 'h':
				l = 2
			elif ft == 'd':
				l = 8
			elif ft == 'b':
				l = 1
			else:
				l = 0
			i1 =  struct.unpack("<" + ft, t[flc : flc + l])[0]
			parms[parm]['value'] = i1
			print(parm, i1)
		elif 'value' in prm:
			print(parm, "Not in tune file")
		else:
			updatefromTuning(t, prm)


if __name__ == "__main__":
		f = f = open(sys.argv[1], 'r')
		m = f.read()
		f.close()

		
		f = open(sys.argv[2], 'rb')
		t = f.read()
		f.close()
		
		meparms = json.loads(m)
		
		tparms = meparms['Method']['MSParms']['Tuning']
		mparms = meparms['Method']['MSParms']['Mass']
		sparms = meparms['Method']['MSParms']['Scan']
		
		
		updatefromTuning(t, mparms)
		
		updatefromTuning(t, tparms)
		updatefromTuning(t, sparms)
		
		if len(sys.argv) == 4:
			f = open(sys.argv[3], 'w')
			f.write(json.dumps(meparms, indent=4))
			f.close()


	
	
