import busreader
import time
class HP7673():
	def __init__(self, dev, br, inj, gcaddr, logl=print):
		self.dev = dev
		self.br = br
		self.dev.timeout = 20000
		self.stb = 0
		self.esr = 0
		self.gotConfig = False
		self.injnum = inj
		self.gcaddr = gcaddr
		self.addr = busreader.BusReader.getGbpibAddr(dev)
		self.logl = logl
		#self.ctlraddr = ctlraddr
		
		
	def reset(self):
		self.logl ('Reset: ')
		self.stst = self.br.cmd(self.dev, "ST").decode('ascii', errors='replace').strip()
		self.st = self.br.cmd(self.dev, "I%i P0000" % self.injnum).decode('ascii', errors='replace').strip()
		self.st = self.br.cmd(self.dev, "I%i X0046" % self.injnum).decode('ascii', errors='replace').strip()
		self.rrconf = self.br.cmd(self.dev, "RR CONF", raw=True).decode('ascii', errors='replace').strip() #RR CONF00
		self.rrom = self.br.cmd(self.dev, "RR RSETFF", raw=True).decode('ascii', errors='replace').strip() #RR RSETFF
		self.st = self.br.cmd(self.dev, "AB TR").decode('ascii', errors='replace').strip()
		self.st = self.br.cmd(self.dev, "AB I%i"	%	self.injnum).decode('ascii', errors='replace').strip()
		return { 'ST': self.st,
		 'IST': self.stst, 
		 	'RRCONF': self.rrconf,
		 	'RROM':  self.rrom}
		
	def	status(self, dosi=False):
		MTA = 0x40
		MLA = 0x20
		self.lsst = self.br.cmd(self.dev, "LS").decode('ascii', errors='replace').strip()
		ctlr = self.br.controller()
		self.ctlraddr = busreader.BusReader.getGbpibAddr(ctlr)
		#self.sist = self.br.cmd(self.dev,	"SI")
		if dosi:
			self.dev.write("SI")
			ctlr.send_command(bytes([MTA+ self.addr, MLA + self.gcaddr, MLA + self.ctlraddr]))
			#self.sist = self.dev.read_raw()
			sires, st = ctlr.visalib.buffer_read(ctlr.session, 3)
			self.sist = sires.decode('ascii', errors='replace').strip()
			#self.gc.dev.write("SR")
		else:
			self.sist =""
		self.stst = self.br.cmd(self.dev, "ST").decode('ascii', errors='replace').strip()
		return { 
			'LSST':  self.lsst,
			'SIST': self.sist,
			'IST' :  self.stst, 
			}
		
	def	apStart(self, dosi=False):
		self.dev.write("AP")
		return True
	
	def apFinish(self):		
		self.apst = self.dev.read_raw().decode('ascii', errors='replace').strip()
		return { 'APST' : self.apst }

	def read(self):
		return self.br.cmd(self.dev, "RR READ", raw=True).decode('ascii', errors='replace').strip()

	def	moveStart(self, srcv, trgv):
		specials = ["RR",	"I1",	"I2"]
		if isinstance(srcv,	int):
			 src = str(srcv)
		else:
			src	=	srcv
		if isinstance(trgv,	int):
			trg	=	str(trgv)
		else:
			trg	=	trgv
		if src in	specials or	src.isnumeric():
			if trg in	specials or	trg.isnumeric():
				self.dev.write("MV %s %s" % (trg, src))
				self.stb = self.br.statusb(self.dev)
				#print (stb)
				self.last_stb = self.stb
				return True
		return False
	
	def injDone(self):
		self.stb = self.br.statusb(self.dev)
		if (self.last_stb == self.stb):
			self.last_stb = self.stb
			return False
		return True
	
	def moveFinish(self):
		self.mst	=	self.dev.read_raw().decode('ascii', errors='replace').strip()
		if int(self.mst) != 0:
			raise HP7673Exception('Bad move status: ' + str(self.mst))
		return { 'MST' : self.mst}

	def	move(self, srcv, trgv):
		if self.moveStart(srcv, trgv):
				while not self.moveDone():
					time.sleep(1)
				self.logl ("St: ", self.stb)
				self.moveFinish()


	def	injectStart(self, prewash=0, visc=0, pumps = 6, quant=1, solvwasha=2, solvwashb=2):
		self.logl("inject Start")
		self.spst = self.br.cmd(self.dev, "SP %i 0 %i %i %i %i %i %i" % (self.injnum, prewash, visc, pumps, quant, solvwasha, solvwashb)).decode('ascii', errors='replace').strip()
		#											"SP 2 0 0 0 6 1 2 2") #no prewash, 6 pumps, 1ul, 2 solvent a 2 solvent b 
		#											"SP 2 0 1 0 6 2 2 2" #1 prewash, 6 pumps 2ul, 2 solvent a, 2 solvent b
		#											"SP 2 0 0 1 6 1 2 2" ##no prewash, 1s vicosity, 6 pumps, 1ul, 2 solvent a 2 solvent b 
		self.logl("inject SP")
		self.cist = self.br.cmd(self.dev, "CI %i 1 0" % self.injnum) .decode('ascii', errors='replace').strip()
		self.logl("inject CI")
		self.wpst = self.dev.write("WP %i 0" % self.injnum)
		self.logl("inject WP Start")
		
	def injectFinish(self):
		self.wpst	=	self.dev.read_raw().decode('ascii', errors='replace').strip()
		return { 'SPST' : self.spst, 'CIST' : self.cist, 'WPST' : self.wpst}

class	HP7673Exception(Exception):
	pass
