import pygcms.msfile.msfileread as msfileread
import sys

rs = msfileread.ReadMSFile(sys.argv[1])
ort = 0.0
for rt, s in rs.getSpectra():
	print ((rt - ort) * 60.0)
	ort = rt
