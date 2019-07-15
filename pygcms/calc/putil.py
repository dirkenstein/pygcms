import pandas
import numpy as	np
import pygcms.calc.peakdetect as peakdetect

class PUtil():
	def nearest(fr, column, value):
		return fr.iloc[(fr[column]-value).abs().argsort()[:2]]
	def strad(fr, column, value):
		vd = (fr[column]-value)
		#print("vd\n", vd)
		#vll =vd.where (vd < 0).dropna().abs().argsort()[:1]
		#vuu = vd.where (vd < 0).dropna().abs().argsort()[:1]
		vll = vd[vd < 0].abs().sort_values()[:1]
		vuu = vd[vd >= 0].abs().sort_values()[:1]
		#print(vll.name)
		vl =fr.iloc[vll.index]
		vu = fr.iloc[vuu.index]
		#vl = vll
		#vu = vuu
		#if vl.iloc[0].name != vu.iloc[0].name:
		#print ("vll\n", vll,"\n vuu\n", vuu)
		#print ("val,vl,vu: ",value, "\n",  vl, vu)
		nw = vl.append(vu)
		#else:
		#nw = vl
		return nw
	def peaks(fr, column, column2):
		return peakdetect.peakdet(fr[column],(fr[column].max() - fr[column].min())/100, fr[column2])
	def peaksfr(fr, column, column2):
		maxtab, mintab =  peakdetect.peakdet(fr[column],(fr[column].max() - fr[column].min())/100, fr[column2])
		if len(maxtab) > 0:
			mat = pandas.DataFrame(np.array(maxtab), columns=[column2, column])
		else:
			mat = pandas.DataFrame(columns=[column2, column])
		if len(mintab) > 0:
			mit = pandas.DataFrame(np.array(mintab), columns=[column2, column])
		else:
			mit = pandas.DataFrame(columns=[column2, column])
		return mat, mit
