# -*- coding: utf-8 -*-

class Node(object):

		def __init__(self, name, parent=None):
				self._name = name
				self._parent = parent
				self._children = []
				self._value = None
				self._type = None
				self._range = []
				self._step = -1
				self._floc = -1
				self._ftype = None
				self._table = None
				self._tdefn = None

				if parent is not None:
						parent.addChild(self)

		def typeInfo(self):
				return 'NODE'

		def addChild(self, child):
				self._children.append(child)

		def insertChild(self, position, child):
				if position < 0 or position > len(self._children):
						return False

				self._children.insert(position, child)
				child._parent = self
				return True

		def removeChild(self, position):
				if position < 0 or position > len(self._children):
						return False

				self._children.pop(position)
				child._parent = None
				return True

		def attrs(self):
				classes = self.__class__.__mro__
				keyvalued = {}
				for cls in classes:
						for key, value in cls.__dict__.iteritems():
								if isinstance(value, property):
										keyvalued[key] = value.fget(self)
				return keyvalued

		def to_list(self):
				output = []
				if self._children:
						for child in self._children:
								output += [self.name, child.to_list()]
				else:
						output += [self.name, self.value]
				return output

		def to_dict(self, d={}):
				for child in self._children:
						child._recurse_dict(d)
				return d

		def _recurse_dict(self, d):
				if self._children:
						d[self.name] = {}
						for child in self._children:
								child._recurse_dict(d[self.name])
				else:
						if self.vtype:
							d[self.name] = {"value" : self.value}  
							d[self.name].update({"type" : self.vtype })
							if len(self.vrange) > 0:
								d[self.name].update({"range" : self.vrange})
							if self.step > 0:
								d[self.name].update({"step" : self.step})
							if self.floc > 0:
								d[self.name].update({"floc" : self.floc, "ftype" : self.ftype})
						else:
							d[self.name] = self.value
		def name():
				def fget(self):
						return self._name
				def fset(self, value):
						self._name = value
				return locals()
		name = property(**name())

		def value():
				def fget(self):
						return self._value
				def fset(self, value):
						self._value = value
				return locals()
		value = property(**value())

		def vtype():
				def fget(self):
						return self._type
				def fset(self, t):
						self._type = t
				return locals()
		vtype = property(**vtype())

		def vrange():
				def fget(self):
						return self._range
				def fset(self, r):
						self._range = r
				return locals()
		vrange = property(**vrange())

		def step():
				def fget(self):
						return self._step
				def fset(self, s):
						self._step = s
				return locals()
		step = property(**step())
 
		def ftype():
				def fget(self):
						return self._ftype
				def fset(self, ftype):
						self._ftype = ftype
				return locals()
		ftype = property(**ftype())

		def floc():
				def fget(self):
						return self._floc
				def fset(self, floc):
						self._floc = floc
				return locals()
		floc = property(**floc())
		def table():
				def fget(self):
						return self._table
				def fset(self, table):
						self._table = table
				return locals()
		table = property(**table())
		def tdefn():
				def fget(self):
						return self._tdefn
				def fset(self, tdefn):
						self._tdefn = tdefn
				return locals()
		tdefn = property(**tdefn())
		
		def child(self, row):
				return self._children[row]

		def childCount(self):
				return len(self._children)

		def parent(self):
				return self._parent

		def row(self):
				if self._parent is not None:
						return self._parent._children.index(self)

		def log(self, tabLevel=-1):
				output = ''
				tabLevel += 1

				for i in range(tabLevel):
						output += '    '

				output += ''.join(('|----', self._name,' = ', '\n'))

				for child in self._children:
						output += child.log(tabLevel)

				tabLevel -= 1
				output += '\n'
				return output

		def __repr__(self):
				return self.log()

		def data(self, column):
				if   column is 0:
						return self.name
				elif column is 1:
						return self.value

		def setData(self, column, value):
				if column is 0:
						self.name = value
				if column is 1:
						if not self.vtype:
							self.value = value
						elif self.vtype == "f":
							try:
								f= float(value)
							except Exception as e:
								f = 0
							if self.vrange and self.vrange[0] <= f and self.vrange[1] >= f:
								self.value = f
							else:
								print ("value " +str(f) + " out of range")
						elif self.vtype == "i":
							try:
								i= int(value)
							except Exception as e:
								i = 0
							if  self.vrange and self.vrange[0] <= i and self.vrange[1] >= i:
								self.value = i
							else:
								print ("value " +str(i)  + " out of range")
						elif self.vtype == "b":
							try:
								b  = bool(value)
							except Exception as e:
								b = False
							self.value = b
						else:
							print ("invalid value " + str(value))

		def resource(self):
				return None