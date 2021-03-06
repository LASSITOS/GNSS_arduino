# -*- coding: utf-8 -*-
"""
Created on Wed Mar  9 10:43:39 2022

@author: Ac. Capelli
"""



import numpy as np
from datetime import datetime
import matplotlib.pyplot as pl
import os,sys
from pyubx2 import UBXReader
import geopy 


sys.path.append(r'C:\Users\Laktop\GNSS_arduino')
sys.path.append(r'C:\Users\AcCap\GNSS_arduino')
from UBX2data import *




# %% check test data with mixed Laser and GNSS

filepath=r'C:\Users\AcCap\GNSS_arduino\data_examples\GNSS_laser'
filepath=r'C:\Users\Laktop\GNSS_arduino\data_examples\GNSS_laser'

#rate=1
rate1=UBX2data(filepath+r'\a000101_1259.ubx',name='rate=1Hz')
rate5=UBX2data(filepath+r'\a000101_2153.ubx',name='rate=5Hz')
rate10=UBX2data(filepath+r'\a000101_1240.ubx',name='rate=10Hz')
# rate15=UBX2data(filepath+r'\a000101_1111.ubx',name='rate=15Hz')
rate20=UBX2data(filepath+r'\a000101_0852.ubx',name='rate=20Hz')


check_data(rate1)
check_data(rate5)
check_data(rate10)
check_data(rate20)


# %% test cleaning laser
filepath=r'C:\Users\Laktop\GNSS_arduino\data_examples\GNSS_laser'
clean_manual=UBX2data(filepath+r'\a000101_2153_mclean.ubx',name='manual')
clean_machine=UBX2data(filepath+r'\a000101_2153_GNSS.ubx',name='machine')
original=UBX2data(filepath+r'\a000101_2153.ubx',name='original')
check_data(clean_manual)
check_data(clean_machine)
check_data(original)

pl.figure() 
pl.plot( clean_manual.PVAT.iTOW,clean_manual.PVAT.vehPitch,'b+:')
pl.plot( original.PVAT.iTOW,original.PVAT.vehPitch,'xr:')
pl.plot( clean_machine.PVAT.iTOW,clean_machine.PVAT.vehPitch,marker='o',mec='g',mfc='none')


# %% 
rate5=UBX2data(filepath+r'\a220315_0446.ubx')
check_data(rate5)

# %%  check readFiles.py and missing laser data
data=UBX2data(filepath+r'\a000101_0457.ubx')
check_data(data)

for i in range(0, len(data.Laser.iTOW)-1):
    if (data.Laser.iTOW[i+1]-data.Laser.iTOW[i]) > 300:
        print(i,', ',data.Laser.iTOW[i+1]-data.Laser.iTOW[i])

"""
data Download worked fine. Laser data is missing
"""