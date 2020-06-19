'''
python functions to do various useful date processing/manipulation
'''
import numpy as np
import fitsio
import glob
import astropy.io.fits as fits
from astropy.table import Table,join,unique,vstack
from matplotlib import pyplot as plt
import desimodel.footprint
import desimodel.focalplane


def combspecdata(tile,night):
    #put data from different spectrographs together, one table for fibermap, other for z
    specs = []
    #find out which spectrograph have data
    for si in range(0,10):
        try:
            fitsio.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(si)+'-'+str(tile)+'-'+night+'.fits')
            specs.append(si)
    except:
        print('no spectrograph '+str(si)+ ' on night '+night)
    print('spectrographs with data:')
    print(specs)			
    tspec = Table.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(specs[0])+'-'+str(tile)+'-'+night+'.fits',hdu='ZBEST')
    tf = Table.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(specs[0])+'-'+str(tile)+'-'+night+'.fits',hdu='FIBERMAP')
    for i in range(1,len(specs)):
        tn = Table.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(specs[i])+'-'+str(tile)+'-'+night+'.fits',hdu='ZBEST')
        tnf = Table.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(specs[i])+'-'+str(tile)+'-'+night+'.fits',hdu='FIBERMAP')
        tspec = vstack([tspec,tn])
        tf = vstack([tf,tnf])
    return tspec,tf

def goodlocdict(tf):
    '''
    Make a dictionary to map between location and priority
    '''
    wloc = tf['FIBERSTATUS'] == 0
    print(str(len(tf[wloc])) + ' locations with FIBERSTATUS 0')
    goodloc = tf[wloc]['LOCATION']
    pdict = dict(zip(tf['LOCATION'], tf['PRIORITY'])) #to be used later for randoms
    return pdict

def gettarinfo_type(fadir,tile,goodloc,mtlf,tarbit,tp='CMX_TARGET'):
    #get target info
    tfa = Table.read(fadir+'fiberassign-0'+str(tile)+'.fits',hdu='POTENTIAL_ASSIGNMENTS')
    tft = unique(tfa,keys=['TARGETID'])
    wgt = (np.isin(tfa['LOCATION'],goodloc)) 
    print(str(len(np.unique(tfa[wgt]['LOCATION']))) + ' good locations')
    print('comparison of number targets, number of targets with good locations')
    print(len(tfa),len(tfa[wgt]))
    tfa = unique(tfa[wgt],keys=['TARGETID'])
    tt = Table.read(mtlf)
    wtype = ((tt[tp] & 2**bit) > 0)
    tt = tt[wtype]
    tfa = join(tfa,tt,keys=['TARGETID'])
    tft = join(tft,tt,keys=['TARGETID'])
    print(str(len(tfa)) +' unique '+type+' targets with good locations and  at '+str(len(np.unique(tfa['LOCATION'])))+' unique locations and '+str(len(tft))+ ' total unique '+type +' targets at '+str(len(np.unique(tft['LOCATION']))) +' unique locations ')

    #Mark targets that actually got assigned fibers
    tfall = Table.read(fadir+'fiberassign-0'+str(tile)+'.fits',hdu='FIBERASSIGN')
    wgl = np.isin(tfall['LOCATION'],goodloc)
    wtype = ((tfall[tp] & 2**bit) > 0)
    wtfa = wgl & wtype
    print('number of assigned ' +type +' fibers at good locations '+str(len(tfall[wtfa])))
    tfall.keep_columns(['TARGETID','LOCATION'])
    tfa = join(tfa,tfall,keys=['TARGETID'],join_type='left',table_names = ['', '_ASSIGNED'], uniq_col_name='{col_name}{table_name}')
    wal = tfa['LOCATION_ASSIGNED']*0 == 0
    print('number of assigned fibers '+str(len(tfa[wal])))
    tfa['LOCATION_ASSIGNED'] = np.zeros(len(tfa),dtype=int)
    tfa['LOCATION_ASSIGNED'][wal] = 1
    wal = tfa['LOCATION_ASSIGNED'] == 1
    print('number of assigned fibers '+str(len(tfa[wal])))

    return tfa

print(str(len(tfa)) +' unique targets with good locations out of '+str(len(tft))+ ' unique targets occupying ' +str(len(np.unique(tft['LOCATION']))) + ' unique locations ')


def cutphotmask(aa,bits):
    keep = (aa['NOBS_G']>0) & (aa['NOBS_R']>0) & (aa['NOBS_Z']>0)
    for biti in bits:
        keep &= ((aa['MASKBITS'] & 2**biti)==0)
        aa = aa[keep]
    print(str(len(aa)) +' after imaging veto' )
    return aa

def countloc(aa):
    locs = aa['LOCATION']
    la = np.max(locs)+1
    nl = np.zeros(la)
    for i in range(0,len(aa)):
        nl[locs[i]] += 1
    return nl

def assignweights(aa,nl):
    wts = np.ones(len(aa))
    for i in range(0,len(aa)):
        loc = aa[i]['LOCATION']
        wts[i] = nl[loc]
    return wts	


def mkran4fa(N=2e8,fout='random_mtl.fits',dirout=minisvdir+'random/'):
	'''
	cut imaging random file to first N entries and add columns necessary for fiberassignment routines
	'''
	rall = fitsio.read('/project/projectdirs/desi/target/catalogs/dr8/0.31.0/randomsall/randoms-inside-dr8-0.31.0-all.fits',rows=np.arange(N))
	rmtl = Table()
	for name in rall.dtype.names:
		rmtl[name] = rall[name]
	rmtl['TARGETID'] = np.arange(len(rall))
	rmtl['DESI_TARGET'] = np.ones(len(rall),dtype=int)*2
	rmtl['SV1_DESI_TARGET'] = np.ones(len(rall),dtype=int)*2
	rmtl['NUMOBS_INIT'] = np.zeros(len(rall),dtype=int)
	rmtl['NUMOBS_MORE'] = np.ones(len(rall),dtype=int)
	rmtl['PRIORITY'] = np.ones(len(rall),dtype=int)*3400
	rmtl['OBSCONDITIONS'] = np.ones(len(rall),dtype=int)
	rmtl['SUBPRIORITY'] = np.random.random(len(rall))
	rmtl.write(dirout+fout,format='fits', overwrite=True)

def randomtiles(tilef = minisvdir+'msvtiles.fits'):
	tiles = fitsio.read(tilef)
	rt = fitsio.read(minisvdir+'random/random_mtl.fits')
	print('loaded random file')
	indsa = desimodel.footprint.find_points_in_tiles(tiles,rt['RA'], rt['DEC'])
	print('got indexes')
	for i in range(0,len(indsa)):
		tile = tiles['TILEID']
		fname = minisvdir+'random/tilenofa-'+str(tile)+'.fits'
		inds = indsa[i]
		fitsio.write(fname,rt[inds],clobber=True)
		print('wrote tile '+str(tile))

def randomtilesi(tilef = minisvdir+'msvtiles.fits'):
	tiles = fitsio.read(tilef)
	trad = desimodel.focalplane.get_tile_radius_deg()*1.1 #make 10% greater just in case
	print(trad)
	rt = fitsio.read(minisvdir+'random/random_mtl.fits')
	print('loaded random file')	
	
	for i in range(0,len(tiles)):
		tile = tiles['TILEID'][i]
		fname = minisvdir+'random/tilenofa-'+str(tile)+'.fits'
		tdec = tiles['DEC'][i]
		decmin = tdec - trad
		decmax = tdec + trad
		wdec = (rt['DEC'] > decmin) & (rt['DEC'] < decmax)
		print(len(rt[wdec]))
		inds = desimodel.footprint.find_points_radec(tiles['RA'][i], tdec,rt[wdec]['RA'], rt[wdec]['DEC'])
		print('got indexes')
		fitsio.write(fname,rt[wdec][inds],clobber=True)
		print('wrote tile '+str(tile))

def ELGtilesi(tilef = minisvdir+'msv0tiles.fits'):
	tiles = fitsio.read(tilef)
	trad = desimodel.focalplane.get_tile_radius_deg()*1.1 #make 10% greater just in case
	print(trad)
	rt = fitsio.read(minisvdir+'targets/MTL_all_SV0_ELG_tiles_0.37.0.fits')
	print('loaded random file')	
	
	for i in range(3,len(tiles)):
		tile = tiles['TILEID'][i]
		fname = minisvdir+'targets/MTL_TILE_ELG_'+str(tile)+'_0.37.0.fits'
		tdec = tiles['DEC'][i]
		decmin = tdec - trad
		decmax = tdec + trad
		wdec = (rt['DEC'] > decmin) & (rt['DEC'] < decmax)
		print(len(rt[wdec]))
		inds = desimodel.footprint.find_points_radec(tiles['RA'][i], tdec,rt[wdec]['RA'], rt[wdec]['DEC'])
		print('got indexes')
		fitsio.write(fname,rt[wdec][inds],clobber=True)
		print('wrote tile '+str(tile))


def targtilesi(type,tilef = minisvdir+'msvtiles.fits'):
	tiles = fitsio.read(tilef)
	trad = desimodel.focalplane.get_tile_radius_deg()*1.1 #make 10% greater just in case
	print(trad)
	rt = fitsio.read(tardir+type+'allDR8targinfo.fits')
	print('loaded random file')	
	
	for i in range(0,len(tiles)):
		tile = tiles['TILEID'][i]
		fname = tardir+type+str(tile)+'.fits'
		tdec = tiles['DEC'][i]
		decmin = tdec - trad
		decmax = tdec + trad
		wdec = (rt['DEC'] > decmin) & (rt['DEC'] < decmax)
		print(len(rt[wdec]))
		inds = desimodel.footprint.find_points_radec(tiles['RA'][i], tdec,rt[wdec]['RA'], rt[wdec]['DEC'])
		print('got indexes')
		fitsio.write(fname,rt[wdec][inds],clobber=True)
		print('wrote tile '+str(tile))


	
def mkminisvtilef(dirout=minisvdir,fout='msvtiles.fits'):
	'''
	manually make tile fits file for sv tiles
	'''
	msvtiles = Table()
	msvtiles['TILEID'] = np.array([70000,70001,70002,70003,70004,70005,70006],dtype=int)
	msvtiles['RA'] = np.array([119.,133.,168.,214.75,116.,158.,214.75])
	msvtiles['DEC'] = np.array([50.,26.5,27.6,53.4,20.7,25.,53.4])
	msvtiles['PASS'] = np.zeros(7,dtype=int)
	msvtiles['IN_DESI'] = np.ones(7,dtype=int)
	msvtiles['OBSCONDITIONS'] = np.ones(7,dtype=int)*65535
	pa = []
	for i in range(0,7):
		pa.append(b'DARK')
	msvtiles['PROGRAM'] = np.array(pa,dtype='|S6')
	msvtiles.write(dirout+fout,format='fits', overwrite=True)

def mkminisvtilef_SV0(dirout=minisvdir,fout='msv0tiles.fits'):
	'''
	manually make tile fits file for minisv0 tiles
	'''
	msvtiles = Table()
	msvtiles['TILEID'] = np.array([68000,68001,68002,67142,67230],dtype=int)
	msvtiles['RA'] = np.array([214.75,214.76384,202.,204.136476102484,138.997356099811])
	msvtiles['DEC'] = np.array([53.4,53.408,8.25,5.90422737037591,0.574227370375913])
	msvtiles['PASS'] = np.zeros(5,dtype=int)
	msvtiles['IN_DESI'] = np.ones(5,dtype=int)
	msvtiles['OBSCONDITIONS'] = np.ones(5,dtype=int)*65535
	pa = []
	for i in range(0,5):
		pa.append(b'DARK')
	msvtiles['PROGRAM'] = np.array(pa,dtype='|S6')
	msvtiles.write(dirout+fout,format='fits', overwrite=True)

	
def plotdatran(type,tile,night):
	df = fitsio.read(dircat+type +str(tile)+'_'+night+'_clustering.dat.fits')
	rf = fitsio.read(dircat+type +str(tile)+'_'+night+'_clustering.ran.fits')
	plt.plot(rf['RA'],rf['DEC'],'k,')		     
	if type == 'LRG':
		pc = 'r'
		pt = 'o'
	if type == 'ELG':
		pc = 'b'
		pt = '*'
	plt.scatter(df['RA'],df['DEC'],s=df['WEIGHT']*3,c=pc,marker=pt)
	plt.xlabel('RA')
	plt.ylabel('DEC')
	plt.title(type + ' '+tile+' '+night)
	plt.savefig('dataran'+type+tile+night+'.png')
	plt.show()
		

def gathertargets(type):
	fns      = glob.glob(targroot+'*.fits')
	keys = ['RA', 'DEC', 'BRICKNAME','MORPHTYPE','DCHISQ','FLUX_G', 'FLUX_R', 'FLUX_Z','MW_TRANSMISSION_G', 'MW_TRANSMISSION_R', 'MW_TRANSMISSION_Z','NOBS_G', 'NOBS_R', 'NOBS_Z','PSFDEPTH_G', 'PSFDEPTH_R', 'PSFDEPTH_Z', 'GALDEPTH_G', 'GALDEPTH_R',\
        'GALDEPTH_Z','FIBERFLUX_G', 'FIBERFLUX_R', 'FIBERFLUX_Z', 'FIBERTOTFLUX_G', 'FIBERTOTFLUX_R', 'FIBERTOTFLUX_Z',\
        'MASKBITS', 'EBV', 'PHOTSYS','TARGETID','DESI_TARGET']
	#put information together, takes a couple of minutes
	ncat     = len(fns)
	mydict   = {}
	for key in keys:
		mydict[key] = []
	if type == 'ELG':
		bit = 1 #target bit for ELGs
	if type == 'LRG':
		bit = 0
	if type == 'QSO':
		bit = 2
	for i in range(0,ncat):
		data = fitsio.read(fns[i],columns=keys)
		data = data[(data['DESI_TARGET'] & 2**bit)>0]
		for key in keys:
			mydict[key] += data[key].tolist()
		print(i)	
	outf = tardir+type+'allDR8targinfo.fits'
	collist = []
	for key in keys:
		fmt = fits.open(fns[0])[1].columns[key].format
		collist.append(fits.Column(name=key,format=fmt,array=mydict[key]))
		print(key)
	hdu  = fits.BinTableHDU.from_columns(fits.ColDefs(collist))
	hdu.writeto(outf,overwrite=True)
	print('wrote to '+outf)