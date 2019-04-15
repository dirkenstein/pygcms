import struct
import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pandas
import scipy.signal

#import crc16
import sys

class ReadSpec():
	
	def __init__(self, data,ofs, logl=print):
		self.logl = logl
		self.b = data[ofs:]
		ofs = self.read_hp_bindata_hdr(0)
		self.read_hp_bindata_ions(ofs)
				
	def hpfloat(theword):
		mask=(2<<13) -1
		mantissa=theword&mask
		scale = theword >> 14
		#print (mantissa, scale, 8** scale)
		return mantissa * (8 ** scale)
	
	def hpmz(rawval):
		return rawval/20.0
	
	def read_hp_bindata(self):
		hdr=chr(self.b[0])
		hlen=int(chr((self.b[1])))
		self.hhlen=hlen+2
		#print (hdr, hlen)
		if hdr == '#':
			self.flen=int(self.b[2:2+hlen])
		#print(self.flen)
			if self.flen > 18:
				ofs = self.read_hp_bindata_hdr(self.hhlen)
				self.read_hp_bindata_ions(ofs)
			else:
				self.logl ("Ion sequence too short: ", self.flen)
		else:
			self.logl('Not an ion sequence')

	def cksum(self):
		sum8 = 0
		sum16 =0
		sum32=0
		sumspc = self.b
		#for b in sumspc:
		#	sum8 = (sum8 +b) %256
		#for b in sumspc:
		#	sum  = (sum +b) %65536
		for c in range(0, len(sumspc),2):
			sum16 = (sum16+ (sumspc[c]*256) + sumspc[c+1]) % 65536
		#for c in range(0, len(sumspc),4):
		#	sum32 += sumspc[c])*16777216 + 65536*sumspc[c+1]+ 256*sumspc[c+2] + sumspc[c+3]
		#crc32 = zlib.crc32(sumspc)
		#crc = crc16.crc16xmodem(sumspc)
		crc=0
		return sum16, crc

	def read_hp_bindata_hdr(self, ofs):
		reclen=18
		nofs=ofs+reclen
		b = struct.unpack('>hIhhhhHH',self.b[ofs:ofs+reclen])
		#print (b)
		ws = {
			'BinLen':b[0],
			'RetTime': b[1]/60000.0,
			'WdsLess3': b[2],
			'DataType':b[3],
			'Status':b[4],
			'NumPks':b[5],
		}
		#print ('BinLen: ', ws['BinLen'], ws['BinLen']*2, self.flen)
		DataType=ws['DataType']
		if DataType == 1:
			ws.update( {
			'BasePk':b[6],
			'BaseAb':ReadSpec.hpfloat(b[7]),
			})
		elif DataType == 2:
			ws.update( { 
			'RStart': ReadSpec.hpmz(b[6]),
			'REnd': ReadSpec.hpmz(b[7])})
			ub = struct.unpack('>' + 6*'H',self.b[nofs:nofs+12])
			ws.update( { 
			'NSamp': ub[0],
			'CStart':ReadSpec.hpmz(ub[2]),
			'CEnd': ReadSpec.hpmz(ub[5]),
			'Unk1':ub[1],
			'Unk2':ub[3],
			'Unk3':ub[4]})
			nofs= nofs+12
			#un = 1
			#for u in ub:
			#	us={'Unk'+str(un): u }
			#	print us
			#	un += 1
		else:
			self.logl('Unknown dataType: %i' % DataType)
		#print(ws)
		self.spectrum = ws
		return  nofs
		
	def read_hp_bindata_ions(self, ofs):
		ws = self.spectrum
		DataType = ws['DataType']
		NumPks = ws['NumPks']
		blen = ws['BinLen']*2
		if DataType == 2:
			rstart =  ws['RStart']
			rspan = ws['REnd'] - rstart
			ioninc = rspan / NumPks
	
		ions = []
		iop = struct.unpack('>' + str(NumPks*2)+'H', self.b[ofs:ofs+(NumPks*4)])
		it = iter(iop)
		ent = zip(it, it)
		n = 0	
		#snio = map (lambda x : (hpmz(x[0]), hpfloat(x[1])), ent)
		for (x, y) in ent:
			if DataType == 1:
				ions.append ((ReadSpec.hpmz(x), ReadSpec.hpfloat(y)))
			elif DataType== 2:
				ions.append ( (rstart + ioninc *n ,ReadSpec.hpfloat(y)))
			else:
				self.logl("Unknown datatype: ", DataType)
			n += 1
		#print(ions)
		if len(ions) > 0:
			i=pandas.DataFrame(np.array(ions), columns=["m/z", "abundance"])
			self.spectrum.update({'ions':i})
		else:
			self.logl("Short ion sequence")
		#print (ws)
		#print (ws['Unk3'] / 20.0, hpfloat(ws['Unk3']))
		#print len(ions)
		brem = self.b[ofs+ NumPks*4:blen]
		#s = str(len(brem)/2)
		#print(s)
		l = int(len(brem)/2)
		remw = struct.unpack('>' + str(l)+'H', brem[:l*2])
		brem = brem[l*2:]
		self.logl (l, remw[-5:])
		#rb = []
		#for b in brem:
		#	rb.append(b)
		#print(DataType, remw, rb, self.cksum())
		
		#print ord(brem[-1]), sum8
		#print hex(sum8),hex(sum), hex(sum16), hex(crc32)
	
	def getBinaryLen(self, withHeader=True):
		if withHeader:
			l = self.hhlen + self.flen
		else:
			l = self.flen
			#print(l)
		return l

	def getBinaryData(self):
		sb = self.b[self.hhlen:self.flen+self.hhlen]
		sbl = len(sb)
		#print ('HHLen: ', self.hhlen, 'Flen: ', self.flen, 'Len: ', sbl, 'Last ', sb [-1:])
		return sb

	def plotit(self):
		i=self.spectrum['ions']
		DataType = self.spectrum['DataType']
		fig, ax = plt.subplots()

		if DataType == 1:
			markerlines,stemlines, baselines  = ax.stem(i.get('m/z'),i.get('abundance'), linefmt='k-', markerfmt=' ')
			plt.setp(stemlines, 'linewidth', 1.0)
		else:
			ax.plot(i.get('m/z'),i.get('abundance'), linewidth=0.75)
			
		ax.set(xlabel='M/z', ylabel='abundance',
	       	title='Ions')
		ax.grid()
	
		#fig.savefig("test.png")
		plt.show()
	
	def plotint(fig, i, DataType):
			#x, y = zip(*i)
		if DataType == 1:
			markerlines,stemlines, baselines = fig.stem(i.get('m/z'),i.get('abundance'), linefmt='k-', markerfmt=' ')
			plt.setp(stemlines, 'linewidth', 1.0)
		else:
			fig.plot(i.get('m/z'),i.get('abundance'),  linewidth=0.75)

	def plot(self, fig):
		i=self.spectrum['ions']
		
		DataType = self.spectrum['DataType']
		ReadSpec.plotint(fig, i, DataType)
		
		
	def smooth(self):
		window=5
		poly=3
		i=self.spectrum['ions']
		DataType = self.spectrum['DataType']
		if DataType == 2:
			ab = i.get('abundance')
			l = len(ab)
			#print (l, l //5, )
			window = 1 + ((l//5) // 2)
			#b, a = scipy.signal.butter(3, 0.25)
			#zi = scipy.signal.lfilter_zi(b, a)
			#z, _ = scipy.signal.lfilter(b, a, ab, zi=zi*ab[0])
			#i['abundance'] = z
			#i['abundance'] = scipy.signal.savgol_filter(ab, window, poly, deriv=0, delta=1.0)
			i['abundance'] = scipy.ndimage.gaussian_filter1d(ab, 4)
			#print (i['abundance'])
			#print (ab)

	def getMinX(self):
		i=self.spectrum['ions']
		return i['m/z'].min()
	def axes(fig):
		fig.set(xlabel='M/z', ylabel='Abundance',
	       	title='Ions')
		fig.grid()
		
	def getSpectrum(self):
		return self.spectrum

	def setSpectrumIons(self, ions):
		self.spectrum['ions'] = ions
		self.spectrum['NumPks'] = len(ions)
	
	def getSpectrumX(self):
		#x, y = zip(*i)
		return self.spectrum['ions'].get('m/z') 

	def getSpectrumY(self):
		#x, y = zip(*i)
		return self.spectrum['ions'].get('abundance') 
	def getData(self):
		return self.b
			
	def saveMsp(self, f, rt, name):
		f.write("NAME: %s\n" % name)
		f.write("COMMENTS: \n")
		f.write("RT: %f\n" % rt)
		f.write("RRT: 0\n")
		f.write("RI: 0\n")
		f.write("FORMULA: \n")
		f.write("MW: 0.0\n")
		f.write("CASNO: \n")
		f.write("SMILES: \n")
		f.write("DB: \n")
		f.write("REFID: \n")
		f.write("NUM PEAKS: %i\n" % self.spectrum['NumPks'])
		i = self.spectrum['ions']
		for idx, s in i.iterrows():
			#print (idx, s)
			f.write("%.1f %i;\n" % (s['m/z'], s['abundance']))
		f.write("\n")
	
	def saveRaw(self, f):
		f.write(self.b)
		
	def getTotIons(self):
		return self.spectrum['ions']['abundance'].sum()
		
class MachineSpec(ReadSpec):
	def __init__(self, data, logl=print):
		self.b = data
		self.logl = logl
		self.spectrum = None
		self.read_hp_bindata()

		
class SpecHeader(ReadSpec):
	def __init__(self, data, ofs, logl=print):
		self.b = data
		self.hhlen = 0
		self.logl = logl
		self.spectrum = None

		self.read_hp_bindata_hdr(ofs)
		if 'BinLen' in self.spectrum:
			self.flen= self.spectrum['BinLen']*2
		else:
			self.flen = 0
		
class FileSpec(MachineSpec):
	def __init__(self, fname, noHeader=False, logl=print):
		self.fname = fname
		self.logl = logl
		self.spectrum = None
		self.b = self.read_from_file()
		if noHeader:
			self.hhlen = 0
			ofs = self.read_hp_bindata_hdr(0)
			self.read_hp_bindata_ions(ofs)
			if 'BinLen' in self.spectrum:
				self.flen= self.spectrum['BinLen']*2
			else:
				self.flen = 0
		else:
			self.read_hp_bindata()
		
	def read_from_file(self):
		bytes_read = open(self.fname, "rb").read()
		return bytes_read
		
if __name__ == "__main__":
	#fname = 'scan%i.bin' % 0
	#print(fname)
	fname = sys.argv[1]
	rs = FileSpec(fname, True)
	print(rs.spectrum)
	print (rs.getTotIons())
	rs.plotit()
