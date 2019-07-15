class ResourceManager():
	def list_resources(self):
		return ['INST::20::GPIB']
	def open_resource(self, name,read_termination='\n', write_termination='\n', timeout=5000):
		print (name) 
		return VisaResource()

class VisaResource():
	def __init__(self):
		self.calls = 0
		f = open("scan0.bin", "rb")
		bytes_read = f.read()
		self.callar = [b'abc05990-60410def', 
		b'0', b'No Errors', b'0', b'0', b'0', 
		b'0', b'22.9', b'29.4', b'0', b'0',
		b'0', b'22.9', b'29.4', b'0', b'0',
		b'0', b'0', b'0',
		b'0', b'22.9', b'29.4', b'0', b'0',
		b'0', b'0', b'0',
		b'0', b'22.9', b'29.4', b'0', b'0',
		b'0', b'0', b'0',
		b'0', b'22.9', b'29.4', b'0', b'0',
		b'0', b'0', b'0',
		b'0', b'22.9', b'29.4', b'0', b'0', 
		b'0', b'0', b'0', 
		b'0', b'0', b'0', b'0', b'0', b'0', b'0', b'0', b'0', b'0', b'0', b'0',
		bytes_read, b'0', b'0']
	def read_stb(self):
		return 0
	def read_raw(self):
		c = self.callar[self.calls]
		self.calls += 1
		print ('ret ' + str(c))
		return c
	def read(self):
		return str(self.read_raw())
	def write(self, b):
		self.write_raw(bytes(b, 'utf8'))
	def write_raw(self, b):
		print (str(b))
	def query(self, b):
		print (b)
		c = self.callar[self.calls]
		self.calls += 1
		print ('ret ' + str(c))
		return str(c)
	def clear(self):
		pass
	def __str__(self):
		return 'INST::20::GPIB'
	primary_address = 20
		
class VisaIOError(Exception):
	pass
