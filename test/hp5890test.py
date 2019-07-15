import pygcms.device.hp5890
import hp5890parms
import expandkeys
import json

class CMDTest:
	def cmd(self, dev, str):
		print (expandkeys.expandkeys(str))
		return 'RKEN'
	def write(self, str):
		print(str)

f = open("gcparms.json", "w")
f.write(json.dumps(hp5890parms.parms, indent=4))
f.close()
gc = hp5890.HP5890(CMDTest(), CMDTest(), hp5890parms.parms)
gc.test()
