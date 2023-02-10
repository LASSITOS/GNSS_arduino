# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 12:09:02 2022

Class and function used for handling data files with mixed UBX data from ublox GNSS modules and frm LDS70A Laser altimeter. 

@author: Laktop
"""

import numpy as np
import re
import math
from datetime import datetime
import matplotlib.pyplot as pl
import os,sys
from cmcrameri import cm
from geopy import distance
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import io
from urllib.request import urlopen, Request
from PIL import Image

# %%  data class

class MSG_type:
    
    def __init__(self,MSG):
        self.len=0
        self.MSG=MSG
        
    def addData(self,keys,values):
        self.len=(len(values))
        if len(keys)!=len(values[0]):
            print("Keys and values don't have same length!!")
            print(values[0])
            print(keys)
            
            return
    
        for i,k in enumerate(keys):
            setattr(self,k,np.array([l[i] for l in values]))


    


class INSLASERdata:
    
    MSG_list=['Laser','PINS1','PSTRB']    # NMEA message list to parse
    keyList=[['h','signQ','T','iTOW'],        
             ['iTOW','GPSWeek','insStatus','hdwStatus','roll','pitch','heading','velX', 'velY', 'velZ','lon', 'lat', 'height','OffsetLLA_N','OffsetLLA_E','OffsetLLA_D'],
             ['GPSWeek','iToW','pin','count']]
        
    # extr_list=['PINS1','Laser']
    
    def __init__(self,filepath,name='',Laserrate=10,load=True, 
                 correct_Laser=True,distCenter=0, pitch0=0, roll0=0,laser_time_offset=0,c_pitch=0,c_roll=0):
        """
            Read GNSS and Laser data from .ubx data file. Additional methods are available for plotting and handling data.    
        
            Inputs:
            ---------------------------------------------------    
            path:           file path
            Laserrate:      data reate of Laser in Hz. If  Laserrate=0, do not load Laser data.
           
        """
        if name!='': 
            self.name=name
        else:
             self.name=filepath.split('\\')[-1]   
        
        self.Laserrate=Laserrate
        self.filepath=filepath
        self.ToW=0
        
        if load:
            self.loadData(correct_Laser=correct_Laser)

    
    def loadData(self,correct_Laser=0):
        if not os.path.isfile(self.filepath) :
            print("File not found!!!")
            raise FileNotFoundError()
        
        
        
        print('Reading file: ',self.filepath)
        print('----------------------------')
        file = open(self.filepath, 'rt')
        
        for msg in (self.MSG_list):
            setattr(self,msg+'List',[])
        
        i=0

        self.corrupt=[]
        self.other=[]
        self.dropped=[]
        
        for l in file:
            # print(l)
            # l2=str(l)
            i+=1
            if l[0]=='#':
                continue
            elif l.find('$')!=-1:
                Msg_key,data=parseNMEA(l)
                
                if Msg_key=='PINS1':
                    self.ToW=data[0]

                if Msg_key=='Error':
                    self.corrupt.append(l)
                    # print("Message {:s} not in NMEA message list".format(Msg_key))
                    try: 
                        self.dropped.index(Msg_key)
                    except ValueError: 
                        self.dropped.append(Msg_key)
                    continue
                    
                try:
                  self.MSG_list.index(Msg_key)
                except ValueError:
                    print("Message {:s} not in NMEA message list. Dropping it.".format(Msg_key))
                    continue
                
                getattr(self,Msg_key+'List').append(data)
                
                
                
            elif l.find('D ')!=-1:
                self.LaserList.append(parseLaser(l)+(self.ToW,) )
                
            else:
                self.other.append(l)
                
        
        for msg in (self.MSG_list):
            setattr(self,msg,MSG_type(msg) )
            if len(getattr(self,msg+'List'))>0:
                values=np.array(getattr(self,msg+'List'))
                keys=self.keyList[self.MSG_list.index(msg)]
                getattr(self,msg).addData(keys,values)
            
            # delattr(self,msg+'List')
            
        print("Total lines read: ", i)   
            
        # correct h with angles from INS
        if correct_Laser:
                self.corr_h_laser()
        
    
    def corr_h_laser(self):
        """
        correct height with angles from INS
        """   
        try:
            i=self.PVAT.iTOW.searchsorted( self.Laser.iTOW)
            j=np.array(i)-1
            
            pitch=self.PVAT.vehPitch[j]+(self.PVAT.vehPitch[i]-self.PVAT.vehPitch[j])/(self.PVAT.iTOW[i]-self.PVAT.iTOW[j])*(self.Laser.iTOW-self.PVAT.iTOW[j])
            roll=self.PVAT.vehRoll[j]+(self.PVAT.vehRoll[i]-self.PVAT.vehRoll[j])/(self.PVAT.iTOW[i]-self.PVAT.iTOW[j])*(self.Laser.iTOW-self.PVAT.iTOW[j])
            
            roll-=self.Laser.roll0
            pitch-=self.Laser.pitch0
            roll*=self.Laser.c_roll
            pitch*=self.Laser.c_pitch
            
            self.Laser.pitch=pitch
            self.Laser.roll=roll
            self.Laser.h_corr=self.Laser.h*(np.cos(pitch/180*np.pi)*np.cos(roll/180*np.pi))-self.Laser.distCenter*np.sin(pitch/180*np.pi)
        
        except Exception as e: 
            print(e)
            print('Failed to correct Laser height')
            try:
                self.Laser.h_corr=np.zeros_like(self.Laser.h)
            except AttributeError:
                print('Laser data not found.')
                
                


    def plot_att(self, MSG='ATT',ax=[]):
        plot_att(self,MSG=MSG,ax=ax)
        
    def plot_elevation_time(self, MSG='PVAT',ax=[],title=[]):
        plot_elevation_time(self,MSG=MSG,ax=ax,title=title)

    def plot_longlat(self,MSG='PVAT',z='height',ax=[],cmap= cm.batlow):
        plot_longlat(self,MSG=MSG,z=z,ax=ax,cmap=cmap)
        
    def plot_map(self,MSG='PVAT',z='height',ax=[],cmap= cm.batlow):
        plot_map(self,MSG=MSG,z=z,ax=ax,cmap=cmap)

    def plot_mapOSM(self,MSG='PVAT',z='iTOW',ax=[],cmap= cm.batlow,title=[],extent=[]):
        plot_mapOSM(self,MSG=MSG,z=z,ax=ax,cmap= cmap,title=title,extent=extent)



    # def subset(self, timelim=[],timeformat='ms'):
    #     """
    #     Parameters
    #     ----------
    #     timelim : List, optional
    #         limits in time. The default is [].
    #     timeformat : string, optional
    #         units of time limits. The default is 'ms'.

    #     Returns
    #     -------
    #     data2 : UBX2data object with subset of data into time limits
            

    #     """
    #     for MSG in ['PVAT','PVT']: 
    #         if  getattr(self,  MSG).len>0:
    #              d=getattr(self, MSG)
    #              if timeformat=='ms':
    #                     lim=d.iTOW.searchsorted(timelim)
    #                     iTOW_lim=timelim
    #              if timeformat=='s':
    #                     lim=((d.iTOW -d.iTOW[0])/1000).searchsorted(timelim)
    #                     iTOW_lim=d.iTOW[lim]
    #              break
        
    #     data2=UBX2data(self.file_original,name=self.name,Laserrate=self.Laserrate,load=False)

    #     for attr in (self.MSG_list+['Laser']):
    #         # print(attr)
    #         try:   
    #             msg_data=getattr(self,attr)
    #             lim2=msg_data.iTOW.searchsorted(iTOW_lim)
    #         except   AttributeError:
    #             try:
    #                 msg_data=getattr(self,attr)
    #                 msg_data.extract()
    #                 lim2=msg_data.iTOW[iTOW_lim]
    #             except Exception as e: 
    #                 print(e)
    #                 continue
    #         d2=MSG_type()
            
    #         for a in msg_data.__dict__.keys():
    #             # print('\t',a)
    #             try:
    #                 setattr(d2,a,np.array(getattr(msg_data, a)[lim2[0]:lim2[1]] ))
    #             except TypeError:
    #                 setattr(d2,a,getattr(msg_data, a))
    #         setattr(d2,'len',lim2[1]-lim2[0])
    #         setattr(data2,attr,d2)
    #     return data2
        
# %% #########function definitions #############

def parseNMEA(l):
    """
    l: string with data
    iTOW: time of Week to append to message data
    
    return height, signal quality, temperature 
    
    """
    
    Msg_key=l[l.find('$')+1:l.find(',') ]
    start=l.find('$'+Msg_key)
    end=l.find('*')

    # Check if message is valid
    if (start!=-1 and end!=-1 and start<end and chksum_nmea(l[start:end+3])): 

      try:
          a=np.array(l[start+len(Msg_key)+2:end].split(','),dtype=float)

      except:
          try:
              a=np.array(l[start+len(Msg_key)+2:end].split(','))
          except:
              print('Coud not parse valid NMEA string:', l)  
              return 'Error',l 
    else:
        print('Coud not parse string:', l)    
        return 'Error',l             

    return Msg_key,a

def parseLaser(l):
    """
    l: string with data
    iTOW: time of Week to append to message data
    
    return height, signal quality, temperature 
    
    """
    
    h=[]
    T=[]
    signQ=[]
    iTOW=[]

    i=0
    j=0
    t=0
    length=len(l)
    
    if l[0]=='D': 
    
        a=l.split()
        if len(a)==2:
            signQ= np.nan
            T= np.nan
            try:
                h= float(a[1])
            except:
                h= np.nan
                print('coud not parse string:', l)
        else:
            error=0
            try:
                h= float(a[1])
            except:
                h= np.nan
                error=1
            try:
                signQ= float(a[2])
            except:
                signQ= np.nan
                error=1
            try:
                T= float(a[3]) 
            except:
                T= np.nan 
                error=1
            if error:
                print('coud not parse string:', l)
    else:
        h= np.nan
        signQ= np.nan
        T= np.nan 
        print('coud not parse string:', l)                 


    return h,signQ,T
    
def chksum_nmea(sentence):
    # From: http://doschman.blogspot.com/2013/01/calculating-nmea-sentence-checksums.html
   
    # This is a string, will need to convert it to hex for 
    # proper comparsion below
    end=sentence.find("*")
    cksum = sentence[end+1:end+3]
    
    # String slicing: Grabs all the characters 
    # between '$' and '*' and nukes any lingering
    # newline or CRLF
    chksumdata = re.sub("(\n|\r\n)","", sentence[sentence.find("$")+1:sentence.find("*")])
    
    # Initializing our first XOR value
    csum = 0 
    
    # For each char in chksumdata, XOR against the previous 
    # XOR'd char.  The final XOR of the last char will be our 
    # checksum to verify against the checksum we sliced off 
    # the NMEA sentence
    
    for c in chksumdata:
       # XOR'ing value of csum against the next char in line
       # and storing the new XOR value in csum
       csum ^= ord(c)
    
    # Do we have a validated sentence?
    if hex(csum) == hex(int(cksum, 16)):
       return True

    return False


    
def check_data(data):
    """
    Check data and produce some plots
    
    Input:
    --------------
    data        Member of class UBXdata
    
    """
    
    print('\n\n###############################\n-----------------------------\n',
          data.name,
          '\n----------------------------\n###############################\n')
    
    for attr in data.MSG_list:
        try:   
            d=getattr(data,attr)
            print('\n',attr,'\n----------------------------')
            print('Length:')
            print(len(d.parsed))
            print('Time intervall (s):')
            print((d.iTOW[:5]-d.iTOW[0])/1000)
        except Exception as e: 
                print(e)
            
            
    print('\nOthers: \n----------------------------')   
    for c in data.other[:10]: 
        print(c.identity,', bit length:',c.length) 
    
    print('\nCorrupted: \n----------------------------')   
    for c in data.corrupt[:10]: 
        print(c)      
        
    try:
        if data.PVAT.parsed != []:
            data.plot_att(MSG='PVAT')
        else:
            data.plot_att()
    except AttributeError:
        print('no attitude messages found')
        

    try:
        if len(data.Laser.h)==0:
            raise AttributeError
                
        pl.figure()
        ax=pl.subplot(111)
        ax2=ax.twinx()
        ax.set_ylabel('Laser h (m)')
        ax2.set_ylabel('GNSS Delta_h (m)')
        ax.set_xlabel('time (ms)')
    
        ax.plot(data.Laser.iTOW-data.PVAT.iTOW[0],data.Laser.h,'--xk',label='Laser')
        # ax.plot(data.Laser.iTOW2-data.PVAT.iTOW[0],data.Laser.h,'--ob',label='Laser, time2')
        ax2.plot((data.PVAT.iTOW-data.PVAT.iTOW[0]),data.PVAT.height/1000-(data.PVAT.height[0]/1000-data.Laser.h[0]),'+:r',label='GPS height')
        
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc=0)   
        pl.title(data.name)
    except AttributeError:
        print('No laser data found')






def plot_att(data,ax=[],title='',heading=True):
    if ax==[]:
        fig=pl.figure()
        ax=pl.subplot(111)
    else:
        pl.sca(ax)
    
    d=data.PINS1
    
    if heading:
            ax2=ax.twinx()    
    

    ax.plot((d.iTOW-d.iTOW[0])/1000,np.degrees(d.pitch),'o-r',label='pitch')
    ax.plot((d.iTOW-d.iTOW[0])/1000,np.degrees(d.roll),'x-k',label='roll')
    if heading:
        ax2.plot((d.iTOW-d.iTOW[0])/1000,np.degrees(d.heading),'x-b',label='heading')

    
    
    ax.set_ylabel('pitch/roll (deg)')
    ax.set_xlabel('time (s)')
    if heading:
        ax2.set_ylabel('heading (deg)')
        # ask matplotlib for the plotted objects and their labels
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc=0)   
    else:
        ax.legend(loc=0)
        
    if title=='':
        pl.title(data.name)
    elif title!='none':
        pl.title(title)
    
    
def plot_att_laser(data,ax=[],title='',heading=True):
    if ax==[]:
        fig=pl.figure()
        ax=pl.subplot(111)
    else:
        pl.sca(ax)
        fig=pl.gcf()
    
    d=data.PINS1
    
    if heading:
            ax2=ax.twinx()        
    

    ax.plot((d.iTOW-d.iTOW[0])/1000,np.degrees(d.pitch),'o-r',label='pitch')
    ax.plot((d.iTOW-d.iTOW[0])/1000,np.degrees(d.roll),'x-k',label='roll')
    if heading:
        ax2.plot((d.iTOW-d.iTOW[0])/1000,np.degrees(d.heading),'x-b',label='heading')
    
    
    ax.set_ylabel('pitch/roll (deg)')
    ax.set_xlabel('time (s)')
    if heading:
        ax2.set_ylabel('heading (deg)')
        # ask matplotlib for the plotted objects and their labels
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc=0)   
        ax2.yaxis.label.set_color('b')
        ax2.tick_params(axis='y', colors='b')
    else:
        ax.legend(loc=0)
    
    
    try:
        if len(data.Laser.h)==0:
            raise AttributeError
                
        ax3=ax.twinx()
        fig.subplots_adjust(right=0.75)
        ax3.spines['right'].set_position(("axes", 1.2))
        ax3.yaxis.label.set_color('g')
        ax3.tick_params(axis='y', colors='g')
        ax3.set_ylabel('Laser h (m)')
        ax3.plot((data.Laser.iTOW-d.iTOW[0])/1000,data.Laser.h,':og',label='Laser')
        lines3, labels3 = ax3.get_legend_handles_labels()
    except AttributeError:
        print('No laser data found')
        lines3=[]
        labels3=[]    
    
    
    if title=='':
        pl.title(data.name)
    elif title!='none':
        pl.title(title)
    
def plot_elevation_time(data,MSG='PVT',ax=[],title=[]):
    if ax==[]:
        fig=pl.figure()
        ax=pl.subplot(111)
    else:
        pl.sca(ax)
    
    d=getattr(data,MSG)

    
    ax.plot((d.iTOW-d.iTOW[0])/1000,d.height/1000,'o-r',label='height')
    ax.set_ylabel('elevation (m a.s.l.)')
    ax.set_xlabel('time (s)')
   
    if title:
        pl.title(title)
    pl.tight_layout()
    
    
def plot_longlat(data,MSG='PVT',z='height',ax=[],cmap= cm.batlow):
    if ax==[]:
        fig=pl.figure()
        ax=pl.subplot(111)
    else:
        pl.sca(ax)
    
    d=getattr(data,MSG)
    
    ax2=ax.twinx()    
    c=getattr(d,z)
    if z=='height':
        label='elevation (m a.s.l.)'
        c=c/1000
    elif z=='iTOW':
        label='time (s)'
        c-=c[0]
        c=c/1000
    else:
        label=z
    lat=np.array([distance.distance((d.lat[0],d.lon[0]),(x,d.lon[0])).m for x in d.lat ])
    lon=np.array([distance.distance((d.lat[0],d.lon[0]),(d.lat[0],x)).m for x in d.lon ])
    
    im=ax.scatter(lon,lat,c=c,cmap=cmap,marker='x')
    c=pl.colorbar(im, label=label)
    ax.invert_xaxis()
    ax.set_ylabel('N (m)')
    ax.set_xlabel('W (m)')
    
    pl.title(data.name)
    pl.tight_layout()

        

def plot_summary(data,extent,cmap=cm.batlow,heading=True):
    
    fig=pl.figure(figsize=(8,10))
    spec = fig.add_gridspec(ncols=1, nrows=9)
    cimgt.OSM.get_image = image_spoof # reformat web request for street map spoofing
    osm_img = cimgt.OSM() # spoofed, downloaded street map
    
    ax0 = fig.add_subplot(spec[0:3, 0],projection=osm_img.crs)
    data.plot_mapOSM(MSG='PVAT',z='iTOW',extent=extent,ax=ax0, cmap=cmap  )
    
    ax1 = fig.add_subplot(spec[3:5, 0])
    ax1.plot((data.PVAT.iTOW-data.PVAT.iTOW[0])/1000,
              [distance.distance((data.PVAT.lat[0],data.PVAT.lon[0]),(data.PVAT.lat[0],x)).m for x in data.PVAT.lon ],
              'x:',label='East-West')
    ax1.plot((data.PVAT.iTOW-data.PVAT.iTOW[0])/1000,
              [distance.distance((data.PVAT.lat[0],data.PVAT.lon[0]),(x,data.PVAT.lon[0])).m for x in data.PVAT.lat ],
              '+:',label='North-South')
    ax1.set_ylabel('Distance (m)')
    ax1.legend()
    
    ax2 = fig.add_subplot(spec[5:7, 0],sharex = ax1)
    ax2.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.h, 'x:',label='original')
    ax2.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.h_corr, '+:k',label='corrected')
    ax2.plot((data.PVAT.iTOW-data.PVAT.iTOW[0])/1000,data.PVAT.height/1000-(data.PVAT.height[0]/1000-data.Laser.h[0]),'+:r',label='GPS height')
    ax2.set_ylabel('h_laser (m)')
    ax2.set_xlim(ax1.get_xlim())
    ax2.legend()
    
    ax3 = fig.add_subplot(spec[7:9, 0],sharex = ax1)
    plot_att(data,MSG='PVAT',ax=ax3,title='none',heading=heading)

    return fig



def laser_correction(data,show_corr_angles=0,GPS_h=False,heading=False):
    
    fig, [ax2,ax3] = pl.subplots(2, 1, figsize=(8, 8), sharex=True, sharey=False)

    ax2.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.h, 'x:',label='original')
    ax2.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.h_corr, '+:',label='corrected')
    if GPS_h:
        ax2.plot((data.PVAT.iTOW-data.PVAT.iTOW[0])/1000,data.PVAT.height/1000-(data.PVAT.height[0]/1000-data.Laser.h[0]),'+:r',label='GPS height')
    ax2.set_ylabel('h_laser (m)')
    ax2.legend()

    plot_att(data,MSG='PVAT',ax=ax3,title='none',heading=heading)
    
    if show_corr_angles:
        ax3.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.pitch, 'x:',label='pitch laser')
        ax3.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.roll, 'x:',label='roll laser')
        ax3.legend(loc=0)
    return fig

def laser_correction_superimposed(data,GPS_h=False):
    
    fig, ax2 = pl.subplots(1, 1, figsize=(8, 8))

    ax2.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.h, 'x:',label='original')
    ax2.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.h_corr, '+:',label='corrected')
    if GPS_h:
        ax2.plot((data.PVAT.iTOW-data.PVAT.iTOW[0])/1000,data.PVAT.height/1000-(data.PVAT.height[0]/1000-data.Laser.h[0]),'+:r',label='GPS height')
    ax2.set_ylabel('h_laser (m)')
    ax2.legend(loc=2)

    ax3=ax2.twinx()
    ax3.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.pitch, 'x:k',label='pitch laser')
    ax3.plot((data.Laser.iTOW-data.PVAT.iTOW[0])/1000,data.Laser.roll, '+:r',label='roll laser')
    ax3.legend(loc=1)
    ax3.set_ylabel('Angle (deg)')
    ax2.grid()
    return fig

# %% plot on map
def plot_map(data,MSG='PVT',z='height',ax=[],cmap= cm.batlow,title=[],timelim=[],timeformat='ms'):
    
    if ax==[]:
        fig=pl.figure()
        ax = pl.axes(projection=ccrs.PlateCarree())
    else:
        ax.axes(projection=ccrs.PlateCarree())
    
    
    
    d=getattr(data,MSG)   
    if not timelim==[]:
        if timeformat=='ms':
            lim=d.iTOW.searchsorted(timelim)
        if timeformat=='s':
            lim=((d.iTOW -d.iTOW[0])/1000).searchsorted(timelim)
            
            
            
    c=getattr(d,z)[lim[0]:lim[1]] # get data color plot
    
    if z=='height':
        label='elevation (m a.s.l.)'
        c=c/1000
    elif z=='iTOW':
        label='time (s)'
        c-=c[0]
        c=c/1000
    else:
        label=z
        
    ax.coastlines()
    im=ax.scatter(d.lon[lim[0]:lim[1]],d.lat[lim[0]:lim[1]],c=c,cmap=cmap,marker='x')
    c=pl.colorbar(im, label=label)
    
    lon_formatter = LongitudeFormatter(number_format='0.1f',degree_symbol='',dateline_direction_label=True) # format lons
    lat_formatter = LatitudeFormatter(number_format='0.1f',degree_symbol='') # format lats
    ax.xaxis.set_major_formatter(lon_formatter) # set lons
    ax.yaxis.set_major_formatter(lat_formatter) # set lats
    
    if title:
        pl.title(title)
    pl.tight_layout()  
    


def image_spoof(self, tile): # this function pretends not to be a Python script
        url = self._image_url(tile) # get the url of the street map API
        req = Request(url) # start request
        req.add_header('User-agent','Anaconda 3') # add user agent to request
        fh = urlopen(req) 
        im_data = io.BytesIO(fh.read()) # get image
        fh.close() # close url
        img = Image.open(im_data) # open image with PIL
        img = img.convert(self.desired_tile_form) # set image format
        return img, self.tileextent(tile), 'lower' # reformat for cartopy
    
    
def plot_mapOSM(data,MSG='PVAT',z='height',ax=[],cmap= cm.batlow,title=[], extent=[]):
    """
    Plot data (z) on Open Street Map layer.
    
    Parameters
    ----------
    data : TYPE
        DESCRIPTION.
    MSG : TYPE, optional
        DESCRIPTION. The default is 'PVAT'.
    z : TYPE, optional
        DESCRIPTION. The default is 'height'.
    ax : TYPE, optional
        DESCRIPTION. The default is [].
    cmap : TYPE, optional
        DESCRIPTION. The default is cm.batlow.
    title : TYPE, optional
        DESCRIPTION. The default is [].
    extent:     limits of map. In [[lon,lon,lat,lat]]

    Returns
    -------
    None.

    """
    cimgt.OSM.get_image = image_spoof # reformat web request for street map spoofing
    osm_img = cimgt.OSM() # spoofed, downloaded street map
    
    if ax==[]:
        fig=pl.figure()
        ax = pl.axes(projection=osm_img.crs)
  
    
    # prepare data
    d=getattr(data,MSG)     
    c=np.array( getattr(d,z))
    if z=='height':
        label='elevation (m a.s.l.)'
        c=c/1000
    elif z=='iTOW':
        label='time (s)'
        c-=c[0]
        c=c/1000
    else:
        label=z
    
    if extent==[]:
        dx=(np.max(d.lon)-np.min(d.lon))
        dy=(np.max(d.lat)-np.min(d.lat))
        W=np.max([dx,dy])*3/5
        center=[(np.max(d.lon)+np.min(d.lon))/2, (np.max(d.lat)+np.min(d.lat))/2]
        extent = [center[0]-W,center[0]+W, center[1]-W,center[1]+W] # Contiguous US bounds
        print(extent)
        
    # setup map
    ax.set_extent(extent) # set extents
    ax.set_xticks(np.linspace(extent[0],extent[1],3),crs=ccrs.PlateCarree()) # set longitude indicators
    ax.set_yticks(np.linspace(extent[2],extent[3],4)[1:],crs=ccrs.PlateCarree()) # set latitude indicators
    lon_formatter = LongitudeFormatter(number_format='0.4f',degree_symbol='',dateline_direction_label=True) # format lons
    lat_formatter = LatitudeFormatter(number_format='0.4f',degree_symbol='') # format lats
    ax.xaxis.set_major_formatter(lon_formatter) # set lons
    ax.yaxis.set_major_formatter(lat_formatter) # set lats
    ax.xaxis.set_tick_params()
    ax.yaxis.set_tick_params()
    
    scale = np.ceil(-np.sqrt(2)*np.log(np.divide((extent[1]-extent[0])/2.0,350.0))) # empirical solve for scale based on zoom
    scale = (scale<20) and scale or 19 # scale cannot be larger than 19
    ax.add_image(osm_img, int(scale))

    im=ax.scatter(d.lon,d.lat,c=c,cmap=cmap,marker='x',transform=ccrs.PlateCarree())
    c=pl.colorbar(im, label=label)
    
    if title:
        pl.title(title)
    pl.tight_layout()
