import struct	
import msfile.readspec as readspec
import pandas
import numpy as	np
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import peakutils
import scipy
import sys
import calc.putil as putil

class ReadMSFile():
	hdr	=	">4p20p62p62p30p30p10p10p20pihhhhiiiihiiiii"
	tic_entry	=	">iii"

	def __init__(self, fname='', spectra=()):
		self.use_computed = False
		self.use_new = False
		self.newtic = None
		self.newspecs =None
		if len(fname) > 0:
			self.theRun = self.readFile(fname)
		if len(spectra) > 0:
			self.theRun = {'Spectra' : spectra}
			self.computeTic(replace=True)

		
	def	readFile(self, fname):
		with open(fname, "rb") as	f:
			self.d	=	f.read()
			#header = self.d [0:512]
			
			sz = struct.calcsize(ReadMSFile.hdr)
			s	=	struct.unpack(ReadMSFile.hdr, self.d[0:sz])
			si = iter(s)
			hr = { 'File_num_Str'	:	next(si),
			 'File_String' : next(si),
			 'Data_name' : next(si),
			 'Misc_info' : next(si),
			 'Operator'	:	next(si),
			 'Date_time' : next(si),
			 'Inst_model'	:	next(si),
			 'Inlet' : next(si),
			 'Method_File' : next(si),
			 'File_type' : next(si),
			 'Seq_index' : next(si),
			 'Als_bottle'	:	next(si),
			 'Replicate' : next(si),
			 'Dir_ent_type'	:	next(si),
			 'Dir_Offset'	:	next(si),
			 'Data_Offset' : next(si),
			 'Run_Tbl_Offset'	:	next(si),
			 'Norm_Offset' : next(si),
			 'Extra_Records' : next(si),
			 'Num_Records' : next(si),
			 'Start_rTime' : next(si),
			 'End_rTime': next(si),
			 'Max_Signal'	:	next(si),
			 'Min_Signal'	:	next(si)}
			dir_ofs	=	hr['Dir_Offset']
			data_ofs = hr['Data_Offset']
			numrec = hr['Num_Records']
			fileType = hr['File_type']
			fileNumStr= hr['File_num_Str']
			if fileType == 2 and fileNumStr == b'2':
				#print(hex(dir_ofs),	numrec,	hex(data_ofs))
				tic_size = struct.calcsize (ReadMSFile.tic_entry)
				tics = []
				specs	=	[]
				itu	=	struct.iter_unpack(ReadMSFile.tic_entry,	self.d[(dir_ofs -1)*2:(dir_ofs	-1)*2	 + tic_size*numrec])
				idx = 0
				for	ofs, rt, totI	in itu:
					 #print('Dir_ofs(c): ', (dir_ofs-1)*2, 'Data Ofs:' , data_ofs, 'ofs: ', ofs, 'Calc Of: ', (ofs-1)*2)
					 rtm = rt/60000
					 tics.append((rtm, totI))
					 #print ('Scan: ' , idx)
					 rs	=	readspec.ReadSpec(self.d, (ofs-1)*2)	
					 specs.append((rtm,	rs))
					 #print ("RetTime:", rtm, rs.getSpectrum()['RetTime'])
					 #print ("TotI: ", totI, rs.getTotIons())
					 idx  += 1 
				t=pandas.DataFrame(np.array(tics), columns=["retention_time",	"abundance"])
				hr.update({'TIC':	t})
				hr.update({'Spectra':	specs})
				return hr
			elif  fileType == 81 and fileNumStr == b'81':
				print ("unsupported FID file")
				srt = hr['Start_rTime']/60000
				ert = hr['End_rTime']/60000
				ofs = (data_ofs -1) * 512
				#f.seek(0x284)
				units = struct.unpack(">3p", self.d[0x244:0x244+3])[0]
				del_ab = struct.unpack('>d', self.d[0x284:0x284+8])[0]
				print(srt, ert, units, del_ab)
				n = 0
				data = []
				while True:
					try:
							inp = struct.unpack('>h', self.d[ofs +n: ofs+n +2])[0]
							n += 2
					except struct.error:
							break

					if inp == 32767:
							inp = struct.unpack('>i', self.d[ofs +n: ofs+n +4])[0]
							n += 4
							inp2 = struct.unpack('>H', self.d[ofs +n: ofs+n +2])[0]
							n+=2
							delt = 0
							data.append(inp * 65534 + inp2)
					else:
							delt += inp
							data.append(data[-1] + delt)
				
				l = len (data)
				
				intvl = (ert -srt)/l
				print (l, intvl)
				tics = zip ( [ srt + (intvl*x) for x in range(l) ], data) 
				#print (*tics)
				
				t=pandas.DataFrame(np.array([*tics]), columns=["retention_time",	"abundance"])
				t["abundance"] = t["abundance"]*del_ab
				hr.update({'TIC':	t})
				return hr
			else:
				print ("unknown file type: ", fileType, hr)
				return hr
			
	def	writeFile(self, fname):
		with open(fname, "wb") as	f:
			self.d	=	[]
			#header = self.d [0:512]
			
			sz = struct.calcsize(ReadMSFile.hdr)
			h = self.theRun
			hdr = struct.pack(ReadMSFile.hdr,
			 h['File_num_Str'],
			 h['File_String'],
			 h['Data_name'],
			 h['Misc_info'],
			 h['Operator'],
			 h['Date_time'],
			 h['Inst_model'],
			 h['Inlet'],
			 h['Method_File'],
			 h['File_type'],
			 h['Seq_index'],
			 h['Als_bottle'],
			 h['Replicate'],
			 h['Dir_ent_type'],
			 h['Dir_Offset'],
			 h['Data_Offset'],
			 h['Run_Tbl_Offset'],
			 h['Norm_Offset'],
			 h['Extra_Records'],
			 h['Num_Records'],
			 h['Start_rTime'],
			 h['End_rTime'],
			 h['Max_Signal'],
			 h['Min_Signal'] )
			f.write(hdr)
			dir_ofs	=	h['Dir_Offset']
			data_ofs = h['Data_Offset']
			numrec = h['Num_Records']
			#print(hex(data_ofs), hex(dir_ofs))
			f.seek((data_ofs-1)*2)
			curOfs = (data_ofs-1)*2
			tics = []
			for rt, s in self.getSpectra():
				#i = s.getSpectrum()['ions']
				rt = int(s.getSpectrum()['RetTime']*60000)
				ti = int(s.getTotIons())
				l = s.getBinaryLen(withHeader=False)
				#print('Dir_ofs: ', dir_ofs, 'Data Ofs:' , data_ofs, 'ofs: ', curOfs, 'Calc: ', (curOfs//2) +1)

				f.write(s.getBinaryData())
				tics.append(((curOfs//2) +1, rt, ti))
				curOfs += l
			#print('Dir_ofs: ', dir_ofs, 'Data Ofs:' , data_ofs, 'ofs: ', curOfs, 'Calc: ', (curOfs//2) +1)
			#print (f.tell(), (f.tell() //2) + 1)
			tic_size = struct.calcsize (ReadMSFile.tic_entry)
			for	ofs, rt, totI	in tics:
				s = struct.pack(ReadMSFile.tic_entry, ofs, rt, totI)
				f.write(s)
			f.close()
			#itu	=	struct.iter_unpack(ReadMSFile.tic_entry,	self.d[(dir_ofs -1)*2:(dir_ofs	-1)*2	 + tic_size*numrec])
			#in itu:
			#	 print('ofs: ', ofs)
			#	 rtm = rt/60000
			#	 tics.append((rtm, totI))
			#	 rs	=	readspec.ReadSpec(self.d, (ofs-1)*2)	
			#	 specs.append((rtm,	rs)) 
			#t=pandas.DataFrame(np.array(tics), columns=["retention_time",	"abundance"])
			
	def	plotit(self):
			i = self.getTic()
			
			base = pandas.DataFrame()
			base['retention_time'] = i['retention_time']
			base['abundance'] = peakutils.baseline(i['abundance'], deg=6)
			
			#i['abundance'] = i['abundance'] - base['abundance']
			mat, mit = putil.PUtil.peaksfr(i, 'abundance', 'retention_time')
			fig, ax	=	plt.subplots()
			ax.plot(i.get('retention_time'),i.get('abundance'))
			#mat = pandas.DataFrame(np.array(maxtab), columns=['retention_time', 'abundance'])
			#mit = pandas.DataFrame(np.array(mintab), columns=['retention_time', 'abundance'])
			ax.scatter(mat['retention_time'], mat['abundance'], color='blue')
			ax.scatter(mit['retention_time'], mit['abundance'], color='green')
			#base = pandas.DataFrame((i['retention_time'], peakutils.baseline(i['abundance'],deg=6)) , columns=['retention_time', 'abundance'])
			
			#print(base)
			#tot = mat.append(mit)
			areas = []
			n = 0
			cls = ['yellow', 'cyan']
			for m in mat['retention_time']:
				
				nearest = putil.PUtil.strad(mit, 'retention_time' ,m)
				strt = nearest['retention_time'].min()
				end = nearest['retention_time'].max()
				#print (m, strt, end)
				istrt =putil.PUtil.nearest(i, 'retention_time', strt).iloc[0].name
				iend = putil.PUtil.nearest(i, 'retention_time', end).iloc[0].name
				#print (istrt, iend)
				#print(i['retention_time'][istrt:iend])
				ax.fill_between(i['retention_time'][istrt:iend],i['abundance'][istrt:iend], color=cls[n%2])
				#print (m, nearest)
				#print (base.index.get_loc(nearest[0].index))
				#nearest.iloc[0]['abundance'] - base.loc[nearest.iloc[0].name]['abundance']
				#nearest.iloc[1]['abundance'] - base.loc[nearest.iloc[1].name]['abundance']
				areas.append(scipy.integrate.trapz(i['abundance'][istrt:iend], i['retention_time'][istrt:iend]))
				n += 1
			aread = pandas.DataFrame(np.array(areas), columns=['area'])
			mat['area'] = aread['area']
			ax.plot(base['retention_time'],  base['abundance'], color='red')
			mat['area'] = mat['area'] / mat['area'].max()
			ax.set(xlabel='time', ylabel='abundance',
						title='Ions')
			for idx, r in mat.iterrows():
				ax.annotate('%.3f' % r['area'], xy=(r['retention_time'] + 0.05, r['abundance'] + 10000))
			ax.grid()
		
			#fig.savefig("test.png")
			plt.show()
			return ax
	
	def plot(self, fig):
		i=self.getTic()
		fig.plot(i.get('retention_time'),i.get('abundance'), linewidth=0.75)
	def axes(fig):
		fig.set(xlabel='Retention Time', ylabel='Abundance',
	       	title='Total Ion')
		fig.grid()
		
	def consolidate (self):
		spectra = self.getSpectra()
		df = pandas.DataFrame()
		for rt, x in spectra:
			i = x.getSpectrum()['ions']
			i['rt'] = rt
			df = df.append(i)
		self.allspectra =df


	def getMinX(self):
		i=self.getTic()
		return i['retention_time'].min()
	def getMaxX(self):
		i=self.getTic()
		return i['retention_time'].max()
	def getMinY(self):
		i=self.getTic()
		return i['abundance'].min()
	def getMaxY(self):
		i=self.getTic()
		return i['abundance'].max()
		
	def computeTic(self, replace=False):
		spectra = self.getSpectra()
		tic = []
		for rt, x in spectra:
			ti = x.getTotIons()
			tic.append((rt, ti))
		tic = pandas.DataFrame(np.array(tic), columns=["retention_time",	"abundance"])
		if replace:
			self.theRun['TIC'] = tic
		else: 
			self.newtic = tic
	def plot3d(self):
		# Make the plot
		fig = plt.figure()
		ax = fig.gca(projection='3d')
		surf = ax.plot_trisurf(self.allspectra['m/z'],self.allspectra['rt'], self.allspectra['abundance'], cmap=plt.cm.viridis, linewidth=0.2)
		fig.colorbar( surf, shrink=0.5, aspect=5)
		plt.show()
	def nearest_tic(self,value):
		i=self.getTic()
		return putil.PUtil.nearest(i, 'retention_time', value)

	def getSpectra(self):
		if self.use_new:
			return self.newspec
		else:
			if 'Spectra' in self.theRun:
				return self.theRun['Spectra']
			return None
	
	def getTic(self):
		if self.use_computed:
			return self.newtic
		else:
			return self.theRun['TIC']
	
	def setComputed(self, comp):
		if (comp or self.newtic is None) and self.getSpectra():
			self.computeTic()
		self.use_computed = comp

	def getRun(self):
		return self.theRun
	
	def setNewSpectra(self, spectra):
		self.newspec = spectra
	
	def setSpectra(self, spectra):
		self.theRun['Spectra'] = spectra
		self.computeTic(replace=True)
	
	def computeHeader(self):
		tic = self.getTic()
		totLen = 0
		for rt,  s in self.getSpectra():
			totLen += s.getBinaryLen(withHeader=False)
		
		
		self.normofs = 257
		self.dataofs = 378
		self.dirofs = (totLen //2) + + self.dataofs
		hdrNew = {
		'File_num_Str': b'2', 
		'File_String': b'GC / MS DATA FILE', 
		'File_type': 2, 
		'Seq_index': 0, 
		'Replicate': 0, 
		'Dir_ent_type': 1, 
		'Dir_Offset': self.dirofs, # 602054, 
		'Data_Offset': self.dataofs, #378,
		'Run_Tbl_Offset': 0, 
		'Norm_Offset': self.normofs, #257, 
		'Extra_Records': 0, 
		'Num_Records': len(self.getSpectra()), 
		'Start_rTime': int(self.getMinX()*60000),
		'End_rTime': int(self.getMaxX()*60000), 
		'Max_Signal': int(self.getMaxY()), 
		'Min_Signal': int(self.getMinY())
		}
		self.theRun.update(hdrNew)

	def setHeader(self, hdr):
		self.theRun.update(hdr)
		self.computeHeader()
	
	def setUseNew(self, comp):
		self.use_new = comp
		
			
if __name__ == "__main__":
	f = ReadMSFile(fname=sys.argv[1])
	print(f.theRun)
	ax = f.plotit()
	
	nearest =f.nearest_tic(5.5)
	print (nearest, nearest.iloc[0]['abundance'])
	print ((f.getTic()['abundance'].max() - f.getTic()['abundance'].min())/100)
	plt.show()
	f.consolidate()
	f.plot3d()
