'''
Module for saving data in the TomoPy_GUI app
'''
import numpy as np
import time
import skimage
import dxchange as dx
from netCDF4 import Dataset

__author__ = 'Brandt M. Gibson'
__credits__ = 'Matt Newville, Doga Gursoy'
__all__ = ['normalize_data']

def normalize_data(data, flat, dark, ncore, cb, pad_size):
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
    ## Normalize via flats and darks.
    ## First normalization using flats and dark current.
    tp.normalize(data,
                 flat=flat,
                 dark=dark,
                 ncore = ncore,
                 out = data)

    ## Additional normalization using the 10 outter most air pixels.
    ## Should eventually add an option for specifying how many air pixels.
    if cb == True:
        data = tp.normalize_bg(data,
        air = 10)

    ## Padding options.
    if pad_size != 0:
        npad = 0
        ## Need to figure a way to send this back to the UI script.
        if int(pad_size) < data.shape[2]:
            status_ID.SetLabel('Pad Size too small for dataset. Normalized but no padding.')
            return
        else:
            npad = int( (int(pad_size) - data.shape[2] ) / 2)
            data = tp.misc.morph.pad(data,
                                          axis = 2,
                                          npad =npad,
                                          mode = 'edge')

        del dark
        ## Scale data for I0 should be 0. This is done to not take minus_log of 0.
        data[np.where(data < 0)] = 1**-6
        print('just before minus_logged data are ', data.shape, data.max(), data.min())
        tp.minus_log(data, out = data)
        print('minus_logged data are ', data.shape, data.max(), data.min())
        data = tp.remove_nan(data,
                            val = 0.,
                            ncore = ncore)
        return data, npad, status_ID
