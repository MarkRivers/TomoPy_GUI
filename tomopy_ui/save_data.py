'''
Module for saving data in the TomoPy_GUI appself.
'''
import numpy as np
import time
import skimage
import dxchange as dx
from netCDF4 import Dataset

__author__ = 'Brandt M. Gibson'
__credits__ = 'Matt Newville, Doga Gursoy'
__all__ = ['save_recon']

def save_recon(data_type, save_dtype, npad, data, fname):
    '''
    Method for saving. Data are converted based on user specified options,
    then exported as tif stack or netcdf3 .volume file. Format conversions
    are very slow. Raw data usually saves quickly, but data that has been
    changed to float format is slow.

    Parameters
    -------
    data_type : str
            String of current data format.
    save_dtype : str
            String of what the save format will be.
    npad : int, optional
            Sizing of the padding done to the dataset.
    data : ndarray
            Array of data to be saved.
    _fname : str
            String of what the dataset is called and file save will be named.

    Returns
    -------
    Nothing
    '''

    ## Setup copy of data to allow user to scale and save at different file
    ## types (e.g. 8 bit, 16 bit, etc.). Must check to see if data are padded.
    if npad == 0:
        save_data = data[:]
    ## Exporting data without padding.
    if npad != 0: #was padded.
        if data.shape [1] == data.shape[2]: #padded and reconstructed.
            save_data = data[:,npad:data.shape[1]-npad,npad:data.shape[2]-npad]
        if data.shape[1] != data.shape[2]: #padded and NOT reconstructed.
            save_data = data[:,:,npad:data.shape[2]-npad]
    ## Scales the data appropriately.
    ## This is extremely slow from float32 to other formats.
    a = float(save_data.min())
    b = float(save_data.max()) - a
    if save_dtype == 'u1':
        save_data = ((save_data - a) / b) * 255.
        save_data = save_data.astype(np.uint8)
    if save_dtype == 'u2':
        save_data = ((save_data - a) / b) * 65535.
        save_data = save_data.astype(np.uint16)
    ## This allows processed data (float 32) be saved as signed integer (16 signed int) which is same as raw data.
    if save_dtype =='u2' and data.dtype=='float32':
        save_data = ((save_data - a) / b)
        for i in range(save_data.shape[0]):
            save_data[i,:,:] = skimage.img_as_int(save_data[i,:,:])
    '''
    Data exporting.
    '''
    ## Create tif stack within a temp folder in the current working directory.
    if data_type == '.tif':
        dx.write_tiff_stack(save_data, fname = fname, dtype = save_dtype, overwrite=True)
    ## Create a .volume netCDF3 file.
    ## netndf3 does not support unsigned integers.
    if data_type == '.vol':
        ## Creates the empty file, and adds metadata.
        ncfile = Dataset(fname+'_tomopy_recon.volume', 'w', format = 'NETCDF3_64BIT', clobber = True) # Will overwrite if pre-existing file is found.
        ncfile.description = 'Tomography dataset'
        ncfile.source = 'APS GSECARS 13BM'
        ncfile.history = "Created "+time.ctime(time.time())
        ## Creates the correct dimensions for the file.
        NX = ncfile.createDimension('NX', save_data.shape[2])
        NY = ncfile.createDimension('NY', save_data.shape[1])
        NZ = ncfile.createDimension('NZ', save_data.shape[0])
        print('save_dtype is ', save_dtype)
        ## Creates variable for data based on previously constructed dimensions.
        volume = ncfile.createVariable('VOLUME',  save_dtype, ('NZ','NY','NX',))
        ## Copies data into empty file array.
        volume[:] = save_data
        print('volume ', volume.shape, type(volume), volume.dtype)
        ncfile.close()
    del save_data
