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
		self.spectrum = []
		self.blist =[]
		self.nrec = 0
		self.hhlen = 0
		self.read_hp_bindata(usehdr=False, onerec=True)

	def hpfloat(theword):
		mask=(2<<13) -1
		mantissa=theword&mask
		scale = theword >> 14
		#print (mantissa, scale, 8** scale)
		return mantissa * (8 ** scale)
	
	def hpmz(rawval):
		return rawval/20.0
	
	def read_hp_bindata(self, usehdr=True, onerec=True):
		if usehdr:
			hdr=chr(self.b[0])
			hlen=int(chr((self.b[1])))
			self.hhlen=hlen+2
			#print (hdr, hlen)
			if hdr == '#':
				self.flen=int(self.b[2:2+hlen])
			else:
				self.logl('No machine header')
				return
		else:
			self.flen = len(self.b)
			self.hhlen = 0
		#print(self.flen)
		if self.flen > 18:
			#Dataype 3 (SIM?/ramp records) has all NULs 
			#replaced with spaces
			#Yuk
			if ord(self.b[self.hhlen:self.hhlen+1]) == 32:
				self.b = bytearray(self.b)
				for idx in range(self.hhlen, len(self.b)):
					if self.b[idx] == 32:
						self.b[idx] = 0	
			cofs = self.hhlen 
			self.nrec = 0
			while cofs < self.flen:
				ofs, spec = self.read_hp_bindata_hdr(cofs)
				self.read_hp_bindata_ions(spec, cofs, ofs)
				self.spectrum.append(spec)
				
				if 'BinLen' in spec:
					l = spec['BinLen']*2
					self.blist.append(self.b[cofs:cofs+l])
					cofs += l
					self.nrec = self.nrec + 1
					if onerec:
						self.flen = l
						break
				else:
					self.logl("Spectrum length invalid")
					break
		else:
			self.logl ("Ion sequence too short: ", self.flen)
	

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
		}
		#print ('BinLen: ', ws['BinLen'], ws['BinLen']*2, self.flen)
		DataType=ws['DataType']
		if DataType == 1 or DataType == 2 or DataType==3:
			ws.update( {
			'Status':b[4],
			'NumPks':b[5]
			})
		if DataType == 1:
			ws.update( {
			'BasePk':b[6],
			'BaseAb':ReadSpec.hpfloat(b[7]),
			})
		elif DataType == 2:
			ws.update( { 
			'RStart': ReadSpec.hpmz(b[6]),
			'REnd': ReadSpec.hpmz(b[7])})
			ub = struct.unpack('>' + 'HHHIH',self.b[nofs:nofs+12])
			ws.update( { 
			'NSamp': ub[0],
			'CStart':ReadSpec.hpmz(ub[2]),
			'CEnd': ReadSpec.hpmz(ub[4]),
			'Unk1':ub[1],
			#'Unk2':ub[3],
			#'Unk3':ub[4]})
			'PeakIon':ub[3]})
			nofs= nofs+12
			#un = 1
			#for u in ub:
			#	us={'Unk'+str(un): u }
			#	print us
			#	un += 1
		elif DataType == 3:
			ws.update( {
			'Ion':ReadSpec.hpmz(b[6]),
			'Abundance':ReadSpec.hpfloat(b[7])
			})
		else:
			self.logl('Unknown dataType: %i' % DataType)
		#print(ws)
		return  nofs, ws
		
	def read_hp_bindata_ions(self, spec, oofs, ofs):
		ws = spec
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
			if DataType == 1 or DataType == 3:
				ions.append ((ReadSpec.hpmz(x), ReadSpec.hpfloat(y)))
			elif DataType== 2:
				#if x != 0:
				#	self.logl("weird value: ", x)
				#ions.append ( (rstart + ioninc *n ,ReadSpec.hpfloat(y)))
				ions.append ( (rstart + ioninc *n , (x*65536) + y))
				
			else:
				self.logl("Unknown datatype: ", DataType)
			n += 1
		#print(ions)
		if len(ions) > 0:
			i=pandas.DataFrame(np.array(ions), columns=["m/z", "abundance"])
			ws.update({'ions':i})
		else:
			self.logl("Short ion sequence")
		#print len(ions)
		#print (ofs, NumPks*4,oofs+blen)
		brem = self.b[ofs+ NumPks*4:oofs+blen]
		
		#print (brem)
		#s = str(len(brem)/2)
		#print(s)
		l = int(len(brem)/2)
		if l > 0:
			remw = struct.unpack('>' + str(l)+'H', brem[:l*2])
			self.logl (l, remw[-l:])

		#Total Abundance is the last field in the frame
		#This only works for dataypes 1 and 3 
		#DataType 2 has 1 extra 32bit abundance value 
		#i.e if NumPks is 101 there are actually 102 records
		if l >= 5:
			lastl = struct.unpack('>I', brem[6:10])[0]
			ws.update({'TotalIon':lastl})
		#brem = brem[l*2:]
		#self.logl (l, remw[-l:])
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

	def plotit(self, n=0):
		i=self.spectrum[n]['ions']
		DataType = self.spectrum[n]['DataType']
		fig, ax = plt.subplots()

		if DataType == 1 or DataType == 3:
			markerlines,stemlines, baselines  = ax.stem(i.get('m/z'),i.get('abundance'), linefmt='k-', markerfmt=' ')
			plt.setp(stemlines, 'linewidth', 1.0)
		else:
			ax.plot(i.get('m/z'),i.get('abundance'), linewidth=0.75)
			
		ax.set(xlabel='M/z', ylabel='abundance',
	       	title='Ions')
		ax.grid()
	
		#fig.savefig("test.png")
		plt.show()
	
	def plotramp(self):
		i=self.ramp
		fig, ax = plt.subplots()

		ax.plot(i.get('voltage'),i.get('abundance'), linewidth=0.75)
			
		ax.set(xlabel='voltage', ylabel='abundance',
	       	title='Ramp')
		ax.grid()
		plt.show()

	def plotint(fig, i, DataType):
			#x, y = zip(*i)
		if DataType == 1 or DataType == 3:
			markerlines,stemlines, baselines = fig.stem(i.get('m/z'),i.get('abundance'), linefmt='k-', markerfmt=' ')
			plt.setp(stemlines, 'linewidth', 1.0)
		else:
			fig.plot(i.get('m/z'),i.get('abundance'),  linewidth=0.75)

	def plot(self, fig, n=0):
		i=self.spectrum[n]['ions']
		
		DataType = self.spectrum[n]['DataType']
		ReadSpec.plotint(fig, i, DataType)
		
		
	def smooth(self, n=0):
		window=5
		poly=3
		i=self.spectrum[n]['ions']
		DataType = self.spectrum[n]['DataType']
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

	def getMinX(self, n = 0):
		i=self.spectrum[n]['ions']
		return i['m/z'].min()
	
	def axes(fig):
		fig.set(xlabel='M/z', ylabel='Abundance',
	       	title='Ions')
		fig.grid()
		
	def getSpectrum(self,n=0):
		return self.spectrum[n]

	def getSpectra(self):
		return self.spectrum

	def getRetTime(self, n=0):
		return self.spectrum[n]['RetTime']
		
	def setSpectrumIons(self, ions, n=0):
		self.spectrum[n]['ions'] = ions
		self.spectrum[n]['NumPks'] = len(ions)
	
	def getSpectrumX(self, n=0):
		#x, y = zip(*i)
		return self.spectrum[n]['ions'].get('m/z') 

	def getSpectrumY(self, n=0):
		#x, y = zip(*i)
		return self.spectrum[n]['ions'].get('abundance') 
	
	def getData(self):
		return self.b
			
	def saveMsp(self, f, rt, name, n=0):
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
		f.write("NUM PEAKS: %i\n" % self.spectrum[n]['NumPks'])
		i = self.spectrum[n]['ions']
		for idx, s in i.iterrows():
			#print (idx, s)
			f.write("%.1f %i;\n" % (s['m/z'], s['abundance']))
		f.write("\n")
	
	def saveRaw(self, f):
		f.write(self.b)
		
	def getTotIons(self, n=0):
		if "TotalIon" in self.spectrum[n]:
			return self.spectrum[n]['TotalIon']
		else:
			return self.spectrum[n]['ions']['abundance'].sum()

	def rampBuild(self, start, incr):
		ramp = []
		n = start
		for spec in self.spectrum:
			ab = spec['ions']['abundance'].tolist()[0]
			r = n 
			n = n+ incr
			ramp.append((r, ab))		
			
		self.ramp=pandas.DataFrame(np.array(ramp), columns=["voltage", "abundance"])
	
	def getReadRecords(self):
		return self.nrec	
	
	def merge(self, spect):
		self.spectrum.extend(spect.spectrum)
		self.nrec += spect.nrec
		b1 = bytearray(self.b[self.hhlen:])
		b2 = bytearray(spect.b[spect.hhlen:])
		b1.extend(b2)
		newb =  b1
		#print (len(newb))
		l1 = self.flen
		l2 = spect.flen
		newl = l1 + l2
		bl1 = self.blist
		bl2 = spect.blist
		bl1.extend(bl2)
		newbl = bl1
		self.blist = newbl
		if self.hhlen > 0:
				hdr1 = '%i' % newl
				lhd = len(hdr1)
				hdr2 = bytearray('#%i%s' % (lhd, hdr1), 'ASCII')
				hl = len(hdr2)
				hdr2.extend(newb)
				self.b = hdr2
				self.flen = newl +hl
		else:
			self.b = newb
			self.flen = newl
				
	def explode(self):
		speclist = []
		n = 0
		for s in self.spectrum:
			speclist.append(ExplodeSpec(self.blist[n], s, self.logl))
			n += 1
		return speclist
		
class MachineSpec(ReadSpec):
	def __init__(self, data, logl=print):
		self.b = data
		self.logl = logl
		self.spectrum = []
		self.blist = []

		self.read_hp_bindata(usehdr=True, onerec=False)


class ExplodeSpec(ReadSpec):
	def __init__(self, data, spec, logl=print):
		self.b = data
		self.logl = logl
		self.spectrum = [spec]
		self.nrec = 1
		self.hhlen = 0
		self.flen = len(data)
		
class SpecHeader(ReadSpec):
	def __init__(self, data, ofs, logl=print, n=0):
		self.b = data
		self.hhlen = 0
		self.logl = logl
		self.spectrum = []
		self.blist = []

		spec, ofs = self.read_hp_bindata_hdr(ofs)
		if 'BinLen' in spec:
			self.flen= spec['BinLen']*2
			self.nrec = 1
			self.blist.append(self.b[ofs:])
		else:
			self.flen = 0
			self.nrec = 0
		self.spectrum.append(spec)
		
		
class FileSpec(MachineSpec):
	def __init__(self, fname, noHeader=False, logl=print):
		self.fname = fname
		self.logl = logl
		self.spectrum = []
		self.blist = []
		self.b = self.read_from_file()
		if noHeader:
			self.read_hp_bindata(usehdr=False, onerec=False)
		else:
			self.read_hp_bindata(usehdr=True, onerec=False)
		
	def read_from_file(self):
		bytes_read = open(self.fname, "rb").read()
		return bytes_read
		
if __name__ == "__main__":
	#fname = 'scan%i.bin' % 0
	#print(fname)
	fname = sys.argv[1]
	if len(sys.argv) > 2:
		nohdr = not sys.argv[2] == "-h" 
	else: nohdr = True
	rs = FileSpec(fname, nohdr)
	#rs2 = FileSpec(fname, nohdr)
	print(rs.spectrum)
	print (rs.getTotIons())
	#rs.merge(rs2)
	#print(rs.b)
	if rs.getSpectrum()['DataType'] == 3:
		rs.rampBuild(0, 4.275)
		print (rs.ramp)
		rs.plotramp()
		#print(rs.explode())
	else:
		rs.plotit()
