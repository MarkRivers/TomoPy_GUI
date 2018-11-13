# TomoPy_GUI
Written by B.M.Gibson with significant help from Matt Newville and Doga Gursoy.  
TomoPy_GUI is a simple interface for reconstructing synchrotron tomography datasets using TomoPy.  
Currently, this UI is optimized for APS 13-BM netcdf datasets, but future interations will expand to accommodate data formats.  
More information about TomoPy can be found at https://github.com/tomopy/tomopy.  

# Installing
Download and extract the TomoPy_GUI directory.  
Via command line (ex. Anaconda) navigate to the downloaded directory.  
run "python setup.py install"  
An icon should appear on the desktop. To view command line print statements, navigate to the Scripts folder of your python path via cmd line, and run 
"tomopy_13bmapp-script.pyw".

# Dependencies
Users will need to install the following packages.
- conda install -c dgursoy tomopy
- conda install -c gsecars wxmplot
- conda install -c conda-forge wx
- conda install -c conda-forge os
- conda install -c conda-forge glob
- conda install -c conda-forge time
- conda install -c conda-forge gc
- conda install -c conda-forge scipy
- conda install -c conda-forge skimage
- conda install -c conda-forge netCDF4
- conda install -c conda-forge dxchange
- conda install -c conda-forge numpy

# Known issues include: 
- Converting from int16 to uint16
- Some features slower than desired (movie, data conversion, TomoPy algorithms other than gridrec).
- Can get inf values during normalization. This is particularly prevalent when using the background (air) normalization procedure.

