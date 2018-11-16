'''
Module for saving data in the TomoPy_GUI app
'''
import numpy as np
import time
import skimage
import dxchange as dx
from netCDF4 import Dataset
import skimage

__author__ = 'Brandt M. Gibson'
__credits__ = 'Matt Newville, Doga Gursoy'
__all__ = ['import_data']

def import_data(fname, path):
    '''


    Parameters
    -------
    fname : str
            String that has file name.
    path : str
            String that has the working directory of the raw data.

    Returns
    -------

    '''

    if fname.endswith('.nc'): #and beamline == 'APS 13-BM': #this last part will need to be uncommented when incorporated into the multibeamline branch.
        '''
        Reading in .nc files. APS 13BM format.
        Reads in 2 flats (.nc), .setup, and data (.nc).
        '''
        ## Entries 1 and 3 of fname list are flat fields. Dxchange knows how to properly handle this.
        ## Will break if missing a flat or setup file.
        open_data, flat, dark, theta = dx.exchange.read_aps_13bm(fname,format='netcdf4')
        ## nc files don't properly close due to Python still pointing to the files.
        ## Create array and replace contents to allow Python to close original file.
        data = np.zeros(open_data.shape)
        data[:] = open_data
        del open_data
        print('data / data max are ', data.shape, data.max(), data.min())

        ## Let Python know data are unsigned 16 bit integers.
        data = data.astype(np.uint16)
        flat = flat.astype(np.uint16)

        ## Storing the dimensions for updating GUI.
        sx = data.shape[2]
        sy = data.shape[1]
        sz = data.shape[0]
        data_min = data.min()
        data_max = data.max()
        ## Updating the GUI.
        fname = fname[0:-5]
        return path, fname, sx, sy, sz, data_max, data_min, data, flat, dark, theta

        '''
        Everything beneath here has not been implemented in the master branch or cmd branch.
        '''
    if _fname.endswith('.h5') and beamline == 'ALS 8.3.2':
        start = 0
        end = 16
        data, flat, dark, grp_flat = dx.read_als_832h5(fname=_fname, sino=(start,stop))
        theta = tp.angles(data.shape[0], 0, 180)
        ## Fix any wrapped values from oversaturation or file saving.
        flat[np.where(flat < 0)] = (2**16 + flat[np.where(flat < 0)])
        data[np.where(data < 0)] = (2**16 + data[np.where(data < 0)])
        ## Storing the dimensions for updating GUI.
        sx = data.shape[2]
        sy = data.shape[1]
        sz = data.shape[0]
        data_min = data.min()
        data_max = data.max()
        fname = fname[0:-5]
        return path, fname, sx, sy, sz, data_max, data_min, data, flat, dark, theta

    if _fname.endswith('.h5') and beamline == 'APS 2-BM or 32-ID':
        start = 0
        end = 16
        data, flat, dark, theta = dx.read_aps_32id(fname=_fname, sino = (start,end))
        if (theta is None):
            theta = tp.angles(data[0])
        else:
            pass
        ## Fix any wrapped values from oversaturation or file saving.
        flat[np.where(flat < 0)] = (2**16 + flat[np.where(flat < 0)])
        data[np.where(data < 0)] = (2**16 + data[np.where(data < 0)])
        ## Storing the dimensions for updating GUI.
        sx = data.shape[2]
        sy = data.shape[1]
        sz = data.shape[0]
        data_min = data.min()
        data_max = data.max()
        fname = fname[0:-5]
        return path, fname, sx, sy, sz, data_max, data_min, data, flat, dark, theta

    if _fname.endswith('.volume'):
        '''
        Reads in .volume files generated from tomoRecon.
        '''
        data = Dataset(_fname,'r', format = 'NETCDF4')
        data = data.variables['VOLUME'][:]
        data.close()
        # Storing angles.
        theta = tp.angles(data.shape[0])
        ## Fix any wrapped values from oversaturation or file saving.
        flat[np.where(flat < 0)] = (2**16 + flat[np.where(flat < 0)])
        data[np.where(data < 0)] = (2**16 + data[np.where(data < 0)])
        ## Storing the dimensions for updating GUI.
        sx = data.shape[2]
        sy = data.shape[1]
        sz = data.shape[0]
        ## Updating the GUI.
        _fname = _fname[0:-5]
        dark = 'NA'
        data_min = data.min()
        data_max = data.max()
        return
