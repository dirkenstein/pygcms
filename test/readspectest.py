import pygcms.msfile.readspec as readspec
import pandas
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pygcms.msfile.msfileread as msfr
import datetime

def test():
	spectra = []
	idx = 0
	while True:
		try:
			fname = 'scans0/scan%i.bin' % idx
			print(fname)
			rs = readspec.FileSpec(fname)
			for nrs in rs.explode():
				idx += 1
				spectra.append((nrs.getRetTime(), nrs))
		except Exception as e:
			print('Exception: ', e)
			break
	print(len(spectra))
	msf = msfr.ReadMSFile(spectra=spectra)
	d = datetime.datetime.now()
	hdr2 = {
		'Data_name': bytes('methanol blank'.rjust(30),'ascii'), 
		'Misc_info': bytes('contaminants'.rjust(25), 'ascii'),
		'Operator': bytes('Dirk'.ljust(9)[0:9], 'ascii'),
		'Date_time': bytes(d.strftime('%d %b %y  %I:%m %p'), 'ascii'),
		'Inst_model': bytes('Dirks 5971'.ljust(9)[0:9], 'ascii'),
		'Inlet': b'GC', 
		'Method_File': bytes('TERPENES'.ljust(19), 'ascii'),
		'Als_bottle': 6, 
	}
	print(hdr2)
	msf.setHeader(hdr2)
	#msf.plotit()
	#x, ions = spectra[0]
	#ions.plotit()
	print(msf.getRun())
	msf.writeFile('test0.MS')
if __name__ == "__main__":
  test()
