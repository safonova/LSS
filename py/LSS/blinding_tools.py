#tools to help apply blinding routines to LSS catalogs
#requires cosmology calculations from cosmoprimo

import fitsio
from astropy.table import Table
import numpy as np

from LSS.common_tools import write_LSS



def apply_zshift_DE(data,out_file,w0=-1,wa=0,zcol='Z'):
    #data is table of LSS catalog info
    #out_file is the full path for where to write the output
    #w0 is the equation of state today to use to shift the redshifts
    #wa is the change in w0 w.r.t. the scale factor
    #zcol is the column name
    #data = Table(fitsio.read(in_file))
    from cosmoprimo.fiducial import DESI
    from cosmoprimo.utils import DistanceToRedshift
    from cosmoprimo import Cosmology

    #fiducial cosmo
    cosmo_fid = DESI()
    dis_fid = cosmo_fid.comoving_radial_distance

    #give distances assuming different cosmo
    cosmo_d = cosmo_fid.clone(w0_fld=w0,wa_fld=wa)#Cosmology(h=cosmo_fid['h'],Omega_m=cosmo_fid['Omega_m'],w0_fld=w0,wa_fld=wa,engine='class')
    dis_d = cosmo_d.comoving_radial_distance
    dis_val = dis_d(data[zcol]) 
    
    #put back to z assuming fiducial cosmo
    d2z = DistanceToRedshift(dis_fid) 
    z_shift = d2z(dis_val)
    data['Z'] = z_shift
    write_LSS(data,out_file,comments=None)

def swap_z(data,out_file,frac=0.01,zcols=['Z']):
    #swap some fraction of the redshifts
    #data is table of LSS catalog info
    #out_file is the full path for where to write the output
    #frac is the fraction to swap (twice this fraction get swapped)
    #zcols is the list of columns associated with the redshift column that should be swapped around
    sel1 = np.random.binomial(1, frac,len(data))
    sel2 = np.random.binomial(1, frac,len(data))
    print(len(data[sel1]))
    print(len(data[sel2]))
    for col in zcols:
        print(col)
        d1 = data[col][sel1]
        d2 = data[col][sel2]
        data[col][sel1] = d2
        data[col][sel2] = d1
    write_LSS(data,out_file,comments=None)