from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


def deleteItems(layout): 
		if layout is not None: 
			while layout.count(): 
				item = layout.takeAt(0) 
				widget = item.widget() 
				if widget is not None: 
					widget.deleteLater() 
				else: 
					deleteItems(item.layout()) 

class QParamArea(QWidget):
		def __init__(self, parent = None, params=None, heading=None):
			super().__init__(parent)
			self.params = params
			self.tl, self.paramboxes, mtboxes = self.create_tab_panel(self.params, heading)
			self.heading = heading
			if len(mtboxes) > 0:
				self.cparambox = mtboxes[0]
				print(self.cparambox)
				self.cparamgrid = QGridLayout()
				self.cparambox.setLayout(self.cparamgrid)
			else:
				print("No empty boxes")
			hbox = QHBoxLayout()
			hbox.addWidget(self.tl)
			self.setLayout(hbox)
			
		def on_parm_update(self):
			self.pupdate (self.paramboxes, self.params)
		
		def pupdate(self, pb, pu):
				for p in pb:
					b = pb[p]
					if p == self.heading:
						ub = pu
					else:
						ub = pu[p]
					if isinstance(b, QLineEdit):
						#print (p, q, wtb.text())
						#print (self.params)
						v = b.text()
					elif isinstance(b, QCheckBox):
						v = b.isChecked()
					elif isinstance(b, QSpinBox) or isinstance(b, QDoubleSpinBox) :
							v = b.value()
					elif isinstance(b, dict):
						self.pupdate(b, ub)
						continue
					else:
						print ("bad type: ", p, b)
					
					if isinstance(ub, dict):
						if 'value' in ub:
							ub['value'] = v
						else:
							print ("not a value: ", ub)
					else:
						if p == self.heading:
							print ("can't update ", p, pu)
						else:
						  pu[p] = v
						#print (p, q, wtb.text())
			
		def pboxupdate(self, pb, pu):
				for p in pb:
					b = pb[p]
					if p == self.heading:
						ub = pu
					else:
						ub = pu[p]
						
					if isinstance(ub, dict):
						if 'value' in ub:
							v = ub['value']
						else:
							self.pboxupdate(b, ub)
							continue
					else:
						v = pu[p]
					if isinstance(b, QLineEdit):
						#print (p, q, wtb.text())
						#print (self.params)
						b.setText(v)
					elif isinstance(b, QCheckBox):
						b.setChecked(v)
					elif isinstance(b, QSpinBox) or isinstance(b, QDoubleSpinBox) :
						b.setValue(v)
					elif isinstance(b, dict):
						print ("not a valid typ: ", p, b)
					else:
						print ("bad type: ", p, b)
					
					
						#print (p, q, wtb.text())
		def updatepboxes(self):
			self.pboxupdate(self.paramboxes, self.params)
		
		def config_panel(self, conf):
			self.cparambox.setTitle("Config")
			n = 0 
			deleteItems(self.cparamgrid)	
			for c in conf:
				tbl = QLabel(c)
				tb = QLineEdit(str(conf[c]))    
				tb.setReadOnly(True)
				self.cparamgrid.addWidget(tbl, n,0)
				self.cparamgrid.addWidget(tb, n,1)
				n += 1
			self.cparambox.update()
			
		def basetype(self, lbl, bt, layout, n):
			#print (bt)
			if isinstance(bt, dict):
				if not 'type' in bt:
					#print(bt, " does not contain a type")
					#return (None, None, None)
					tl, paramboxes, mtboxes = self.create_tab_panel( bt, lbl)
					tbl = QLabel('')
					layout.addWidget(tbl, n, 0)
					layout.addWidget (tl, n, 1)
					layout.setAlignment(tl, Qt.AlignRight)
					#return (lbl, tbl, tl)
					r= paramboxes
					#print("EEP:  ", r)
					return r, mtboxes
				else:
					t = bt['type']
					v = bt['value']
					if t in ['f', 'i']:
						r0= bt['range'][0]
						r1 = bt['range'][1]
					if t == 'f':
						st = bt['step']
			elif isinstance(bt, int):
				t = "i"
				v = bt
				r0 = 0
				r1 = 100
			elif isinstance(bt, float):
				t = "f"
				v = bt
				r0 = -1.0e6
				r1 = 1.0e6
				st = 1.0
			elif isinstance(bt, str):
				t = "s"
				v = bt
			else:
				print ("Unknown type: ", bt)
				return None, []
				#return (None, None, None)
			
			if t == "f":
				tb = QDoubleSpinBox()
				tb.setMinimum(r0)
				tb.setMaximum(r1)
				tb.setSingleStep(st)
				tb.setValue(v)
			elif t == "i":
				tb = QSpinBox()
				tb.setMinimum(r0)
				tb.setMaximum(r1)
				tb.setValue(v)
			elif t == "s":
				tb = QLineEdit()
				tb.setText(v)
			elif t == "b":
				tb = QCheckBox()
				tb.setChecked(v)
			tb.setMinimumWidth(18)
			if t == 'b': 
				tb.stateChanged.connect(self.on_parm_update)
			else:
				tb.editingFinished.connect(self.on_parm_update)
			tbl = QLabel(lbl)
			layout.addWidget(tbl, n, 0)
			layout.addWidget (tb, n, 1)
			layout.setAlignment(tb, Qt.AlignRight)
			return {lbl: tb}, []

		def create_tab_panel(self, params, heading):
				mtboxes = [] 
				#gmtboxes = [] 

				# Initialize tab screen
				tabs = QTabWidget()
				pparmar = {}
				pparmar2 = {}

				#gparmar = []
				#gpparmar = []
				n = 0
				ggl = QGridLayout()
				ggb = QGroupBox(heading)
				gotTl = False
				parmar2 = {}
				for p in params:
					pg = params[p]
					if isinstance(pg, dict) and not 'type' in pg:
						gl = QGridLayout()
						gb = QGroupBox(p)
						parmar = {}
						n2 = 0
						for q in pg:
							l, mtb  = self.basetype(q,pg[q], gl, n2)
							mtboxes.extend(mtb)
							parmar.update(l)
							n2 += 1
						gb.setLayout(gl)
						pvbox = QVBoxLayout()
						pvbox.addWidget(gb)
						gb2 = QGroupBox()
						gb2.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
						mtboxes.append(gb2)
						pvbox.addWidget(gb2)
						qv = QWidget()
						qv.setLayout(pvbox)
						tabs.addTab(qv,p)
						pparmar.update( {p : parmar } )
						#isTl = False
					else:
						l, mtb = self.basetype(p,pg, ggl, n)
						mtboxes.extend(mtb)
						parmar2.update(l)
						n += 1
						gotTl = True
						#isTl = True
				if gotTl:
					parmar2.update(pparmar)
					pparmar2.update( {heading : parmar2 } )
					ggb.setLayout(ggl)
					ggb2 = QGroupBox()
					ggb2.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
					gpvbox = QVBoxLayout()
					gpvbox.addWidget(ggb)
					gpvbox.addWidget(ggb2)
					mtboxes.append(ggb2)
					gqv = QWidget()
					gqv.setLayout(gpvbox)
					if len(tabs) > 0:
						tabs.addTab(gqv,heading)
					else:
						tabs = gqv
				else:
					pparmar2.update({heading : pparmar})
				#tabs.addTab(gqv,p)
				#	return gqv, gpparmar, gmtboxes
				#else:	
				return tabs, pparmar2, mtboxes



class QStatusArea(QWidget):
		def __init__(self, parent = None, main=None, heading=None, labels={}):
			super().__init__(parent)
			self.vbox = QVBoxLayout()
			self.cparambox = QGroupBox(heading)
			self.cparamgrid = QGridLayout()
			self.cparambox.setLayout(self.cparamgrid)
			self.vbox.addWidget(self.cparambox)
			#self.dummybox = QGroupBox()
			#self.vbox.addWidget(self.dummybox)
			self.setLayout(self.vbox)
			self.labels = labels
			
			
		def status_panel(self, stv):
			n = 0 
			deleteItems(self.cparamgrid)	
			for c in stv:
				tbl = QLabel(c)
				val = stv[c]
				if isinstance(val, tuple) or isinstance(val, list):
					tbg = QGridLayout()
					n2 = 0
					self.cparamgrid.addWidget(tbl, n,0)
					val2 = []
					for v in val:
						if isinstance (v, str):
							vss = v.strip().split(',')
							vss2 = [ vx.strip() for vx in vss ]
							val2.extend(vss2)
						else:
							val2.append(v)
					for v in val2:
						strv = str(v).strip()
						
						if len(strv) > 0:
							if c in self.labels:
								ltbl = self.labels[c] 
								row = 1
								tbll = QLabel(ltbl[n2])
								tbg.addWidget(tbll, 0, n2)
							else:
								row = 0
								
							tbv = QLineEdit(strv)
							tbv.setReadOnly(True)
							tbg.addWidget(tbv, row, n2)
							n2 += 1
	 
					self.cparamgrid.addLayout(tbg, n,1)
				else:
					if isinstance(val, float):
						strv = "%.3f" % val
					else:
						strv = str(val).strip()
					tb = QLineEdit(strv)    
					tb.setReadOnly(True)
					self.cparamgrid.addWidget(tbl, n,0)
					self.cparamgrid.addWidget(tb, n,1)
				n += 1
			self.cparambox.update()

