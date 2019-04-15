import busreader
import struct 

class HP5890():
	def __init__(self, dev, br, params, logl=print):
		self.dev = dev
		self.br = br
		self.dev.timeout = 10000
		self.parms = params
		self.addr = busreader.BusReader.getGbpibAddr(dev)
		self.p_step = 4
		self.logl = logl
		self.sv = [(0,0), (0,0)]
	def eds(b):
		return 'E' if b else 'F'
	def emit_dummy(a):
		pass
		
	def upload(self, progress=None):
		self.startup_part1(progress)
		self.logl(self.statcmds(progress))
		self.startup_part2(progress)
		self.init(progress)
		self.startup_part3(progress)
			
	def startup_part1(self, progress=None):
		if progress is None:
			progress=HP5890.emit_dummy 
		pr = self.logl
		p = self.p_step
		self.dev.write('CC BOTH,NODE,09,[10]')
		progress(p)
		self.dev.write('NTAB')
		progress(p)
		self.dev.write('NDAB')
		progress(p)
		self.dev.write('HB 512')
		progress(p)
		pr (self.br.cmd(self.dev, "LC"))
		progress(p)
		pr (self.br.cmd(self.dev, "EV"))
		progress(p)

		self.dev.write("DB NONE,NONE,NONE")
		self.dev.write( "CD 4  ,IMMEDIATE,ON_FULL,4  ,IMMEDIATE,ON_FULL,BINARY     ,ON ,10  ")
		pr (self.br.cmd(self.dev, "RK:?.3@E?"))
		#RKEN  SYSTEM NOT READY  

		pr (self.br.cmd(self.dev, "NC 1; AQ"))

		pr (self.br.cmd(self.dev, "NC 1; SK"))
		pr (self.br.cmd(self.dev, "RK:Q%i@" % 700))
		#RKABOVEN LIMIT = 450    
		self.icst = self.br.cmd(self.dev, "IC")[4:]
		pr (self.br.cmd(self.dev, "LC"))

		pr (self.br.cmd(self.dev, "AM MANUAL"))
		pr (self.br.cmd(self.dev, "NC 1; AB"))
		
		pr (self.br.cmd(self.dev, "LC"))
		


	def startup_part2(self, progress=None):
		pr = self.logl
		if progress is None:
			progress=HP5890.emit_dummy 
		p = self.p_step
		pr (self.br.cmd(self.dev, "NC 1; IL"))
		progress(p)
		pr (self.br.cmd(self.dev, "NC 1; AQ"))
		progress(p)
		pr (self.br.cmd(self.dev, "PMRQ?"))
		progress(p)
		
	def startup_part3(self,progress=None):
		pr = self.logl
		if progress is None:
			progress=HP5890.emit_dummy 
		p = self.p_step		
		self.dev.write("DB NONE,NONE,NONE")
		progress(p)
		self.dev.write( "CD 4  ,IMMEDIATE,ON_FULL,4  ,IMMEDIATE,ON_FULL,BINARY     ,ON ,10  ")
		progress(p)
		self.dev.write( "SD")
		progress(p)
		pr (self.br.cmd(self.dev, "NC 1; IL"))
		progress(p)
		pr (self.br.cmd(self.dev, "OTDOWNLOAD COMPLETE"))
		progress(p)
		pr (self.br.cmd(self.dev, "NC 1; SU"))
		progress(p)


	def statcmds(self, progress=None):
		pr = self.logl
		statd = {}
		if progress is None:
			progress=HP5890.emit_dummy 
		p = self.p_step	
		statd.update(self.statRI())
		progress(p)
		statd.update(self.statTemps())
		progress(p)
		statd.update(self.statCV())
		progress(p)
		statd.update(self.statDS())
		self.statEndSearch()
		progress(p)
		statd.update(self.statRL())
		progress(p)
		statd.update(self.statSig(0))
		progress(p)
		statd.update(self.statSig(1))
		progress(p)
		return statd
		
	def statRI(self):
		self.rires = self.br.cmd(self.dev, "RI")[4:].decode('ascii', errors='replace').strip().split(' ')
		return { 'RI' : self.rires }

	def statTemps(self):	
		self.temps = [x.strip() for x in self.br.cmd(self.dev, "AT")[4:].decode('ascii', errors='replace').strip().split(',')]
		return { 'Temps' : self.temps }
		
	def statCV(self):
		self.cvs = [x.strip() for x in self.br.cmd(self.dev, "CV")[4:].decode('ascii', errors='replace').strip().split(',')]
		return { 'CV': self.cvs }
		
	def statDS(self):
		self.dss= [x.strip() for x in self.br.cmd(self.dev, "DS")[4:].decode('ascii', errors='replace').strip().split(';')]
		return { 'DS': self.dss }

	def statEndSearch(self):
		self.dev.write("LO GC END SEARCH")
		return {}

	def statRL(self):
		self.rls = [x.strip() for x in self.br.cmd(self.dev, "RL")[4:].decode('ascii', errors='replace').strip().split(';')]
		return { 'RL': self.rls }

	def statSig(self, i):
		s = self.br.cmd(self.dev, "S%i" % i, raw=True)[4:-1] #40 bytes
		sl = len(s) 
		ss = s.strip()
		if len(ss) == 0: 
			sl = 0
		if sl % 4 != 0:
			pr ("S%i Mismatch" % i, sl, sl % 4, s)
		self.sv[i] = struct.unpack('>' + str(sl//4) +'I', s[:(sl//4)*4])
		return { 'S%i' % i: self.sv[i] }

		
	def init_short(self,progress=None):
		pr = self.logl
		if progress is None:
			progress=HP5890.emit_dummy 
		ps = self.p_step		
		p = self.parms
		
		pr (self.br.cmd(self.dev,"RK:Q%i@:G%s@:Q%i@"%(p['OvenMax_Init']['value'], HP5890.eds(p['OvenOn']['value']), p['OvenMax']['value'])))
		progress(ps)
		#RKENOVEN MAXIMUM     325
		pr (self.br.cmd(self.dev, "RK:>A%s:/1@%i@:/SA%s@" %( HP5890.eds(p['DetA']['On']['value']), p['PressureUnits']['value'], HP5890.eds(p['InlA']['ConstantFlowOn']['value']))))
		progress(ps)
		#RKENEPP A CONST FLOW OFF
		pr (self.br.cmd(self.dev, "RK:/1@%i@:/SB%s@"%(p['PressureUnits']['value'], HP5890.eds(p['InlB']['ConstantFlowOn']['value']))))
		progress(ps)
		# RKENEPP B CONST FLOW ON 
		pr (self.br.cmd(self.dev, "RK:/SASSSS%.2f@" % p['ColumnA']['Length']['value']))
		progress(ps)
		#RKENA: Column Len 30.00M
		pr (self.br.cmd(self.dev, "RK:/SASSS%i@" % p['ColumnA']['Dia']['value']))
		progress(ps)
		#RKENA: Column Dia .530mm
		pr (self.br.cmd(self.dev, "RK:/SAS%i@" % p['ColumnA']['Gas']['value']))
		progress(ps)
		#RKENEPP A    N2   [2]   
		pr (self.br.cmd(self.dev, "RK:/SASSSSS%i@" % p['ColumnA']['Flow']['value']))
		progress(ps)
		#RKENA: Split    0 Ml/Min
		pr (self.br.cmd(self.dev, "RK:/SBSSSS%.2f@" % p['ColumnB']['Length']['value']))
		progress(ps)
		#RKENB: Column Len 23.00M
		pr (self.br.cmd(self.dev, "RK:/SBSSS%i@" % p['ColumnB']['Dia']['value']))
		progress(ps)
		#RKENB: Column Dia .250mm
		pr (self.br.cmd(self.dev, "RK:/SBS%i@" % p['ColumnB']['Gas']['value']))
		progress(ps)
		#RKENEPP B    H2   [3]   
		pr (self.br.cmd(self.dev, "RK:/SBSSSSS%i@:UA%s"%(p['ColumnB']['Flow']['value'], HP5890.eds(p['InlA']['Purge']['On']['value']))))
		progress(ps)
		# RKENINL PURGE A  OFF    
		pr (self.br.cmd(self.dev, "RK:UB%s:U1%s:U2%s"%(HP5890.eds(p['InlB']['Purge']['On']['value']), HP5890.eds(p['Valve1']['value']), HP5890.eds(p['Valve2']['value']))))
		progress(ps)
		#RKEN    VALVE 2  OFF

	def pressureProg(self, a, prog, progress=None):
		pr = self.logl
		if progress is None:
			progress=HP5890.emit_dummy 
		ps = self.p_step	
		p = prog ['InlA' if a else 'InlB']['PressureProg']
		key = 'M' if a else 'N'
		pr (self.br.cmd(self.dev,"RK:/%sH%.1f@" % (key, p['InitPressure']['value'])))
		progress(ps)
		# RKENA:INIT PRES      0.0
		pr (self.br.cmd(self.dev,"RK:/%sI%.2f@" % (key, p['InitTime']['value'])))
		progress(ps)
		# RKENA:INIT TIME  650.00 
		pr (self.br.cmd(self.dev,"RK:/%sJ%.2f@:/MK%.1f@" % (key, p['Rate']['value'], p['FinalPressure']['value'])))
		progress(ps)
		# RKENA:FINAL PRES     0.0
		pr (self.br.cmd(self.dev,"RK:/%sL%.2f@"% (key,p['FinalTime']['value'])))
		progress(ps)
		# RKENA:FINAL TIME    0.00
		pr (self.br.cmd(self.dev,"RK:/%sJA%.2f@" %(key,p['A']['Rate']['value'])))
		progress(ps)
		# RKENA:RATE A  0.00 PSI/M
		pr (self.br.cmd(self.dev,"RK:/%sKA%.1f@" % (key,p['A']['Pressure']['value'])))
		progress(ps)
		# RKENA:FINAL PRES  A  0.0
		pr (self.br.cmd(self.dev,"RK:/%sLA%.2f@" % (key,p['A']['Time']['value'])))
		progress(ps)
		# RKENA:FINAL TIME A  0.00
		pr (self.br.cmd(self.dev,"RK:/%sB%.2f@" % (key, p['B']['Rate']['value'])))
		progress(ps)
		# RKENA:RATE B  0.00 PSI/M
		pr (self.br.cmd(self.dev,"RK:/%sKB%.1f@" % (key, p['B']['Pressure']['value'])))
		progress(ps)
		# RKENA:FINAL PRES  B  0.0
		pr (self.br.cmd(self.dev,"RK:/%sLB%.2f@" % (key, p['B']['Time']['value'])))
		progress(ps)
		# RKENINJ B TEMP  250  250
		
	def init(self,progress=None):
		pr = self.logl
		if progress is None:
			progress=HP5890.emit_dummy 
		ps = self.p_step		
		p = self.parms
		pr (self.br.cmd(self.dev,"RK:/HJ@"))
		progress(ps)
		# RKENTIME TABLE IS EMPTY 
		pr (self.br.cmd(self.dev,"RK:Q%i@:G%s@:H%i@" % (p['OvenMax_Init']['value'], HP5890.eds(p['Oven']['On']['value']), p['Oven']['Init']['Temp']['value'])))
		progress(ps)
		# RKENINITIAL TEMP      70
		pr (self.br.cmd(self.dev,"RK:I%.2f@:J%.1f@"%(p['Oven']['Init']['Time']['value'], p['Oven']['Final']['Rate']['value'])))
		progress(ps)
		# RKENRATE    20.0 DEG/MIN
		pr (self.br.cmd(self.dev,"RK:L%.2f@:K%i@"%(p['Oven']['Final']['Time']['value'], p['Oven']['Final']['Temp']['value'])))
		progress(ps)
		# RKENFINAL TEMP       210
		pr (self.br.cmd(self.dev,"RK:JA%.1f@:LA0%.2f@"%(p['Oven']['ProgA']['Rate']['value'], p['Oven']['ProgA']['Time']['value'])))
		progress(ps)
		# RKENFINAL TIME A    0.00
		pr (self.br.cmd(self.dev,"RK:KA%i@:JB%.1f@"%(p['Oven']['ProgA']['Temp']['value'], p['Oven']['ProgB']['Rate']['value'])))
		progress(ps)
		# RKENRATE B   0.0 DEG/MIN
		pr (self.br.cmd(self.dev,"RK:LB%.2f@:KB%i@"%(p['Oven']['ProgB']['Time']['value'], p['Oven']['ProgB']['Temp']['value'])))
		progress(ps)
		# RKENFINAL TEMP  B     50
		pr (self.br.cmd(self.dev,"RK:Q%i@:R%.2f@:V%i@"%(p['Oven']['Max']['value'],p['EquibTime']['value'],p['Sig1']['value'] )))
		progress(ps)
		# RKENSIGNAL 1  TEST PLOT 
		pr (self.br.cmd(self.dev,"RK:W%i@:>A%s:O%i@:O%s@"%(p['Sig2']['value'], HP5890.eds(p['DetA']['On']['value']), p['DetA']['Temp']['value'], HP5890.eds(p['DetA']['HtrOn']['value']))))
		progress(ps)
		# RKENDET A TEMP   55  OFF
		pr (self.br.cmd(self.dev,"RK:P%i@:P%s@:M%i@"%(p['DetB']['Temp']['value'], HP5890.eds(p['DetB']['HtrOn']['value']), p['InlA']['Temp']['value'] )))
		progress(ps)
		# RKENINJ A TEMP   44   50
		pr (self.br.cmd(self.dev,"RK:M%s@:/1@%i@:/SA%s@"%(HP5890.eds(p['InlA']['HtrOn']['value']), p['PressureUnits']['value'], HP5890.eds(p['InlA']['ConstantFlowOn']['value']))))
		progress(ps)
		# RKENEPP A CONST FLOW OFF≈
		if p['InlA']['ConstantFlowOn']['value']:
			pr (self.br.cmd(self.dev,"RK:/M[%i@%.1f@"%(p['InlA']['ConstFlowTemp']['value'], p['InlA']['Pressure']['value'])))
			progress(ps)
		if 'PressureProg' in p['InlA']:
			self.pressureProg(True, p, progress)
			progress(ps)
		pr (self.br.cmd(self.dev,"RK:N%i@" % p['InlB']['Temp']['value']))
		progress(ps)
		# RKENINJ B TEMP  250  250
		pr (self.br.cmd(self.dev,"RK:N%s@:/1@%i@:/SB%s@"%(HP5890.eds(p['InlB']['HtrOn']['value']), p['PressureUnits']['value'], HP5890.eds(p['InlB']['ConstantFlowOn']['value']))))
		progress(ps)
		# RKENEPP B CONST FLOW ON 
		if p['InlB']['ConstantFlowOn']['value']:
			pr (self.br.cmd(self.dev,"RK:/N[%i@%.1f@"%(p['InlB']['ConstFlowTemp']['value'], p['InlB']['Pressure']['value'])))
			progress(ps)
		# RKENEPP B CF:  70,   0.8
		if 'PressureProg' in p['InlB']:
			self.pressureProg(False, p, progress)
		pr (self.br.cmd(self.dev,"RK:/SASSSS%.2f@"% p['ColumnA']['Length']['value']))
		progress(ps)
		# RKENA: Column Len 30.00M
		pr (self.br.cmd(self.dev,"RK:/SASSS%i@"% p['ColumnA']['Dia']['value']))
		progress(ps)
		# RKENA: Column Dia .530mm
		pr (self.br.cmd(self.dev,"RK:/SAS%i@:/SASS%s@"% (p['ColumnA']['Gas']['value'], HP5890.eds(p['ColumnA']['VacComp']['value']))))
		progress(ps)
		# RKENEPP A  VAC COMP  OFF
		pr (self.br.cmd(self.dev,"RK:/SASSSSS%i"%p['ColumnA']['Flow']['value']))
		progress(ps)
		# RKENA: Split    0 Ml/Min
		pr (self.br.cmd(self.dev,"RK:/SBSSSS%.2f@"% p['ColumnB']['Length']['value']))
		progress(ps)
		# RKENB: Column Len 23.00
		pr (self.br.cmd(self.dev,"RK:/SBSSS%i@"% p['ColumnB']['Dia']['value']))
		progress(ps)
		# RKENB: Column Dia .250mm
		pr (self.br.cmd(self.dev,"RK:/SBS%i@:/SBSS%s@"%(p['ColumnB']['Gas']['value'], HP5890.eds(p['ColumnB']['VacComp']['value']))))
		progress(ps)
		# RKENEPP B  VAC COMP  ON 
		pr (self.br.cmd(self.dev,"RK:/SBSSSSS%i@:UA%s"%(p['ColumnB']['Flow']['value'], HP5890.eds(p['InlA']['Purge']['On']['value']))))
		progress(ps)
		# RKENINL PURGE A  OFF    
		pr (self.br.cmd(self.dev,"RK:UB%s:UAT%s%.2f@"%(HP5890.eds(p['InlB']['Purge']['On']['value']), HP5890.eds(p['InlA']['Purge']['TimeOn']['value']), p['InlA']['Purge']['Time']['value'])))
		progress(ps)
		# RKENPURGE A  ON     0.00
		pr (self.br.cmd(self.dev,"RK:UAT%s%.2f@"%(HP5890.eds(p['InlA']['Purge']['TimeOn']['value']), p['InlA']['Purge']['Time']['value'])))
		progress(ps)
		# RKENPURGE A  OFF    0.00
		pr (self.br.cmd(self.dev,"RK:UBT%s%.2f@"%(HP5890.eds(p['InlB']['Purge']['TimeOn']['value']), p['InlB']['Purge']['Time']['value'])))
		progress(ps)
		# RKENPURGE B  ON     1.00
		pr (self.br.cmd(self.dev,"RK:UBT%s%.2f@:U1%s"%(HP5890.eds(p['InlB']['Purge']['TimeOn']['value']), p['InlB']['Purge']['Time']['value'], HP5890.eds(p['Valve1']['value']))))
		progress(ps)
		# RKEN    VALVE 1  OFF      
		pr (self.br.cmd(self.dev,"RK:U2%s:/UFUFU25@:"% HP5890.eds(p['Valve2']['value'])))
		progress(ps)
		# RKENSTART/STOP DISABLED 
		
	def endRun(self,progress=None):
		pr = self.logl
		if progress is None:
			progress=HP5890.emit_dummy 
		ps = self.p_step		
		pr (self.br.cmd(self.dev,"NC 1; SK"))
		progress(ps)
		pr (self.br.cmd(self.dev,"AM MANUAL"))
		progress(ps)

	def isRunning(self):
		 return self.dss[0] != 'IDLE'
