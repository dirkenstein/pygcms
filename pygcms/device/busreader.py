import re
import os
import time

try:
    import visa_test as visa
except ImportError: 
    import visa

class BusReader():
	def __init__(self, logl=print, devs=None):
		self.logl = logl
		self.insts = {}
		self.instidx = {}
		#self.con = rpyc.classic.connect("192.168.29.102")
		#self.v = self.con.modules.visa
		self.v = visa
		self.stb = 0
		self.last_stb = 0
		self.getdevices(rsrcs=devs)

	def getGbpibAddr(dev):
		#d = str(dev).split('::')
		#a = d[1]
		return dev.primary_address
	
	def statusb(self, dev):
		self.stb = dev.read_stb()
		return self.stb
	
	def getStb(self):
		return self.stb
		
	def loadSmartCard(self,device, reboot=False, progress=None):
		#stb = device.read_stb()
		#self.logl ("St: ",stb)
		#if stb != 0:
		#	reboot = True
		device.timeout=10000

		if reboot:
			stb = device.read_stb()
			self.logl ("St: ",stb)
			device.write(':BOOT')
			stb = device.read_stb()
			self.logl ("St: ",stb)
			stb = device.read_stb()
			self.logl ("St: ",stb)
			time.sleep(3)
			try:
				instname=device.query('*IDN?')
			except visa.VisaIOError:
				device.clear()
				instname=device.query('*IDN?')
			if re.match (".*05990-60410.*", instname):
				self.insts['5971'] = (device, instname)
				
		device.write('POC')
		device.write('FFAA00,5,5971A')
		device.write('DWN')
		stb = device.read_stb()
		self.logl ("St: ", stb)
		device.timeout=10000
		device.send_end=False
		nulhdr = bytes(25)
		fname = "59XXII.BIN"
		bsize = os.path.getsize(fname)
		bperc =  100.0* (4096.0 / bsize)
		with open(fname, "rb") as binary_file:
			device.write_raw(nulhdr)
			self.logl('written 25')
			data = binary_file.read(4096)
			while len(data) > 0:
				if len(data) < 4096:
					device.send_end=True
					data += bytes([0])
				device.write_raw(data)
				self.logl('written ', len(data) )
				data = binary_file.read(4096)
				if progress is not None:
					progress(bperc)

	def	cmd(self, dev, cmds, raw=False, waitstb=False):
		self.stb	=	dev.read_stb()
		self.last_stb = self.stb
		dev.write(cmds)
		idx = 0
		while	waitstb and self.stb	== self.last_stb and idx < dev.timeout//20:
			self.last_stb = self.stb
			self.stb = dev.read_stb()
			time.sleep(0.01)
			idx += 1
		##								print	(stb)
		if raw:
						dev.read_termination = ''
		else:
						dev.read_termination = '\n'
		d	=	dev.read_raw()
		self.stb	=	dev.read_stb()
		self.last_stb = self.stb
		##				while	stb	== last_stb:
		##								stb	=	dev.read_stb()
		##								print	(stb)
		return d

	def getdevices(self, rsrcs=None):
		#self.rm = visa.ResourceManager()
		self.rm = self.v.ResourceManager()
		if not rsrcs:
			rsrcs = self.rm.list_resources()
		self.insts = {}
		instname=""
		instrec={}
		inst = None
		for r in rsrcs:
			self.logl("Trying: ", r)
			inst = self.rm.open_resource(r, write_termination='\n', read_termination='\n', timeout=5000)
			try:
				stb=inst.read_stb()
				self.logl ("St:", stb)
				instname=inst.query('*IDN?')
				stb=inst.read_stb()
				self.logl ("Stp:", stb)
##			if stb != 0:
##				inst.clear()
##				stb=inst.read_stb()
##				self.logl ("Stp2:", stb)
##				instname=inst.query('*IDN?')
			except visa.VisaIOError:
				try:
					inst.clear()
					stb=inst.read_stb()
					self.logl ("DCL St",stb)
					instname=inst.query('*IDN?')
				except visa.VisaIOError:
					try:
						instname=inst.query('SYID')
					except visa.VisaIOError:   
						try:
							instname=inst.query('ID')
						except visa.VisaIOError:
							self.logl ("Can't query ", r)
							inst.clear()
			#print (instname)
			if re.match (".*05990-60410.*|.*5971Ax.*", instname):
				instrec = {'5971' :(inst, instname)}
			elif re.match (".*7673A.*", instname):
				instrec = {'7673' :(inst, instname)}
			elif re.match(".*HP19257A.*", instname):
				instrec = {'5890' :(inst, instname)}
		
			instid = { inst: instrec}
			self.insts.update(instrec)
			self.instidx.update(instid)

	def controller(self):
            self.ctlr = self.rm.open_resource('GPIB0::INTFC')
            return self.ctlr
        
	def deviceByName(self, devname):
		return self.insts[devname][0]
		
	def isSmartCardDevice(self, devc):
		instn = [*self.instidx[devc].keys()][0]
		return instn == '5971'
	
	def needsLoading(self, dev):
		inst, iname = [*self.instidx[dev].values()][0]
		if not re.match(r'.*5971Ax.*', iname):
			return True
		return False
	
		
