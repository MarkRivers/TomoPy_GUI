'''
TomoPy GUI designed for APS 13BM.
Code written by B.M. Gibson.
Version 1.0 (October 9, 2018)

Updates:
    Version 1.0.1 (October 9, 2018) B.M.Gibson
        - Updated title and commented code.
    Version 1.0.2 (Date) Contributor
        - Modifications

'''
## Importing packages.
import wx
import os
import glob
import gc
import time
import scipy

from netCDF4 import Dataset

import dxchange as dx
import tomopy as tp
import numpy as np

is_wxPhoenix = 'phoenix' in wx.PlatformInfo
if is_wxPhoenix:
    PyDeadObjectError = RuntimeError
else:
    from wx._core import PyDeadObjectError
from wxmplot.imageframe import ImageFrame


class APS_13BM(wx.Frame):
    '''
    Setting up the GUI frame.
    '''
    def __init__(self, parent=None, *args,**kwds):

        kwds["style"] = wx.DEFAULT_FRAME_STYLE|wx.RESIZE_BORDER|wx.TAB_TRAVERSAL

        wx.Frame.__init__(self, parent, wx.NewId(), '',
                         wx.DefaultPosition, wx.Size(-1,-1), **kwds)
        self.SetTitle(" TomoPy ")
        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)
        self.image_frame = None
        '''
        Making the menu
        '''
        menuBar = wx.MenuBar()
        menu = wx.Menu()
        ## Making menu buttons.
        menu_open = menu.Append(wx.NewId(), "Import Data", "Read in data files")
        menu_chdr = menu.Append(wx.NewId(), 'Change Directory', 'Change the Saving and Working Directory')
        menu_free = menu.Append(wx.NewId(), "Free Memory", "Release data from RAM")        
        menu_exit = menu.Append(wx.NewId(),"Exit", "Terminate the program")
        ## Adding buttons to the File menu button of the bar.
        menuBar.Append(menu, "File");
        self.SetMenuBar(menuBar)
        ## Binding the menu commands to respective buttons.
        self.Bind(wx.EVT_MENU, self.client_read_nc, menu_open)
        self.Bind(wx.EVT_MENU, self.change_dir, menu_chdr)
        self.Bind(wx.EVT_MENU, self.client_free_mem, menu_free)
        self.Bind(wx.EVT_MENU, self.OnExit, menu_exit)
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        self.panel = wx.Panel(self)        
        title_label = wx.StaticText(self.panel, 1, label = 'TomoPy (optimized for APS 13-BM)')             
        
        '''
        Info Panel (File) - Top Left
        '''
        ## Making the buttons.
        file_label = wx.StaticText(self.panel, -1, label = 'File: ', size = (-1,-1))
        self.file_ID = wx.StaticText(self.panel, 1, label = '')
        path_label = wx.StaticText(self.panel, -1, label = 'Path: ', size = (-1,-1))
        self.path_ID = wx.StaticText(self.panel, 1, label = '')
        status_label = wx.StaticText(self.panel, -1, label = 'Status: ')
        self.status_ID = wx.StaticText(self.panel, -1, label = '')
        
        '''
        Preprocessing Panel
        '''
        ## Making the buttons
        preprocess_label = wx.StaticText(self.panel, -1, label = 'Preprocessing', size = (-1,-1))
        dark_label = wx.StaticText(self.panel, -1, label = 'Dark Current:', size = (-1,-1))
        self.dark_ID = wx.TextCtrl(self.panel, -1, value ='', size = (-1,-1))
        preprocess_button = wx.Button(self.panel, -1, label ='Preprocess', size = (-1,-1))  # this is normalizing step.
        preprocess_button.Bind(wx.EVT_BUTTON, self.normalization)
        pad_size_opt = [
                'No Padding',
                '1024',
                '2048',
                '4096']
        ## Setting default pad size to 2048 because 13BM NX is 1920 and typically uses gridrec.
        self.pad_size = 2048
        ## Setting default npad to 0 allows the user to save without processing. This immediately gets changed
        ## during normalization or when pad size is changed on the GUI.
        self.npad = 0
        self.pad_size_combo = wx.ComboBox(self.panel, value = 'Auto Pad', choices = pad_size_opt)
        self.pad_size_combo.Bind(wx.EVT_COMBOBOX, self.pad_size_combo_recall)
        zinger_button = wx.Button(self.panel, -1, label = 'Remove Zingers', size = (-1,-1))
        zinger_button.Bind(wx.EVT_BUTTON, self.zinger_removal)
        
        '''
        Centering Panel
        '''
        ## Initialization of labels, blanks, and buttons for single slice reconstruction. 
        centering_label = wx.StaticText(self.panel, -1, label = 'Centering Parameters', size = (-1,-1))
        upper_slice_label = wx.StaticText(self.panel, -1, label = 'Upper slice:', size = (-1,-1))
        self.upper_rot_slice_blank = wx.TextCtrl(self.panel, value = '300')
        self.upper_rot_center_blank = wx.TextCtrl(self.panel, value = '960.00')
        upper_slice_recon_button = wx.Button(self.panel, -1, label = 'Reconstruct Slice', size = (-1,-1))
        upper_slice_recon_button.Bind(wx.EVT_BUTTON, self.up_recon_slice)
        lower_slice_label = wx.StaticText(self.panel, -1, label = 'Lower Slice:', size = (-1,-1))
        self.lower_rot_slice_blank = wx.TextCtrl(self.panel, value = '800')
        self.lower_rot_center_blank = wx.TextCtrl(self.panel, value = '960.00')
        lower_slice_recon_button = wx.Button(self.panel, -1, label = 'Reconstruct Slice', size = (-1,-1))
        lower_slice_recon_button.Bind(wx.EVT_BUTTON, self.lower_recon_slice)
        
        ## Initialization of centering parameters. 
        rot_center_title = wx.StaticText(self.panel, -1, label = ' Rotation Center:', size = (-1,-1))
        center_method_title = wx.StaticText(self.panel, -1, label = 'Centering Method:', size = (-1,-1))
        self.est_rot_center_blank = wx.TextCtrl(self.panel, value = '960.00')   
        self.find_center_type = 'Vghia Vo'
        find_center_list = [
                'Entropy',
				'Vghia Vo',
                '0-180']
        self.find_center_menu = wx.ComboBox(self.panel, value = 'Vghia Vo', choices = find_center_list)
        self.find_center_menu.Bind(wx.EVT_COMBOBOX, self.find_center_algo_type)
        tol_title = wx.StaticText(self.panel, -1, label = '         Tolerance: ' )
        self.tol_blank = wx.TextCtrl(self.panel, value = '0.25')
        rot_center_button = wx.Button(self.panel, -1, label = 'Optimize Center', size = (-1,-1))
        rot_center_button.Bind(wx.EVT_BUTTON, self.find_rot_center)
        
        '''
        Reconstruction Panel
        '''
        recon_algo_title = wx.StaticText(self.panel, -1, label = 'Reconstruction')
                
        ## Drop down for reconstruction algorithm choices. Defaults to Gridrec (fastest).
        recon_type_label = wx.StaticText(self.panel, -1, label = "Algorithm: ", size = (-1,-1))
        self.recon_type = 'gridrec'
        recon_type_list = [
                'Algebraic',
                'Block Algebraic', 
                'Filtered Back-projection', 
                'Gridrec',
                'Max-likelihood Expectation',
                'Ordered-subset Expectation',
                'ospml_hybrid',
                'ospml_quad',
                'pml_hybrid',
                'pml_quad',
                'Simultaneous Algebraic',
                'Total Variation',
                'Gradient Descent'
                ]
        self.recon_menu = wx.ComboBox(self.panel, value = 'gridrec', choices = recon_type_list)
        self.recon_menu.Bind(wx.EVT_COMBOBOX, self.OnReconCombo)
        
        ## Filtering choice for during reconstruction.
        self.filter_type = 'hann'
        filter_label = wx.StaticText(self.panel, -1, label = '   Filter:   ', size = (-1,-1))
        filter_list = [
                'none',
                'shepp',
                'cosine',
                'hann',
                'hamming',
                'ramlak',
                'parzen',
                'butterworth'
                ]
        self.filter_menu = wx.ComboBox(self.panel, value = 'hann', choices = filter_list)
        self.filter_menu.Bind(wx.EVT_COMBOBOX, self.OnFilterCombo)
        
        ## Buttons for tilting and reconstructing 
        tilt_button = wx.Button(self.panel, -1, label = "Tilt Correction", size = (-1,-1))
        tilt_button.Bind(wx.EVT_BUTTON, self.tilt_correction)
        recon_button = wx.Button(self.panel, -1, label = "Reconstruct", size = (-1,-1))
        recon_button.Bind(wx.EVT_BUTTON, self.reconstruct)
        ring_remove_button = wx.Button(self.panel, -1, label = ' Remove Ring ', size = (-1,-1))
        ring_remove_button.Bind(wx.EVT_BUTTON, self.remove_ring)
       
        
        '''
        Top Right (Visualize) Panel
        '''
        ## Initializes display for dimensions of dataset.
        dim_label = wx.StaticText(self.panel, label = "Data Dimensions ")  
        sx_label = wx.StaticText(self.panel, label = 'NX: ')
        sy_label = wx.StaticText(self.panel, label = 'NY: ')
        sz_label = wx.StaticText(self.panel, label = 'NZ: ')
        self.sx_ID = wx.StaticText(self.panel, label ='')
        self.sy_ID = wx.StaticText(self.panel, label ='')
        self.sz_ID = wx.StaticText(self.panel, label ='')
        
        ## Initializes data visualization parameters. Defaults to slice view.
        self.plot_type = 'Z Slice'
        plot_view_list = ['Z Slice','Y Sinogram', 'X Sinogram']
        self.visualization_box = wx.RadioBox(self.panel, label = 'Data Visuzalization', choices = plot_view_list, style = wx.RA_SPECIFY_ROWS)
        self.visualization_box.Bind(wx.EVT_RADIOBOX, self.OnRadiobox)
        self.z_lble = wx.StaticText(self.panel, label = 'Slice to view: ')
        self.z_dlg = wx.TextCtrl(self.panel, value = 'Enter Slice')
        self.z = self.z_dlg.GetValue()     
        plot_button = wx.Button(self.panel, -1, label ='Plot Image', size = (-1,-1))
        plot_button.Bind(wx.EVT_BUTTON, self.plotData)     
        movie_button = wx.Button(self.panel, -1, label = 'Display Movie', size = (-1,-1))
        movie_button.Bind(wx.EVT_BUTTON, self.movie_maker)
        
        ## Initializes post processing filter choices. These are not automatically applied.
        pp_label = wx.StaticText(self.panel, label = "Post Processing")  #needs to be on own Sizer.
        pp_filter_label = wx.StaticText(self.panel, -1, label = 'Post Processing Filter: ', size = (-1,-1))
        pp_filter_list = [
                'gaussian_filter',
                'median_filter',
                'sobel_filter'
                ]
        self.pp_filter_menu = wx.ComboBox(self.panel, value = 'none', choices = pp_filter_list)
        self.pp_filter_menu.Bind(wx.EVT_COMBOBOX, self.OnppFilterCombo)
        self.pp_filter_button = wx.Button(self.panel, -1, label = 'Filter', size = (-1,-1))
        self.pp_filter_button.Bind(wx.EVT_BUTTON, self.filter_pp_data)

        ## Initializes data export choices.
        self.save_dtype = 'f4'
        self.save_dtype_list = [
                '8 bit', #u1
                '16 bit', #i2 
                '32 bit float'#f4
                ]    
        self.save_dtype_menu = wx.ComboBox(self.panel, value = '32 bit float', choices = self.save_dtype_list)
        self.save_dtype_menu.Bind(wx.EVT_COMBOBOX, self.OnSaveDtypeCombo)
        self.save_data_type = '.vol'
        self.save_data_list = [
                '.tif',
                '.vol'
                ]
        self.save_data_type_menu = wx.ComboBox(self.panel, value = '.vol', choices = self.save_data_list)
        self.save_data_type_menu.Bind(wx.EVT_COMBOBOX, self.OnSaveDataTypeCombo)
        
        save_recon_button = wx.Button(self.panel, -1, label = "Save Reconstruction", size = (-1,-1))
        save_recon_button.Bind(wx.EVT_BUTTON, self.save_recon)
        
        '''
        Setting up the GUI Sizers for layout of initialized widgets.
        '''
        ## Window is broken up into two columns.
        windowSizer = wx.BoxSizer(wx.HORIZONTAL)
        leftSizer = wx.BoxSizer(wx.VERTICAL)
        rightSizer = wx.BoxSizer(wx.VERTICAL)
        
        ## Creating Sizers for the left column.
        info_fname_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        info_path_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        info_status_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        preprocessing_title_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        preprocessing_panel_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        preprocessing_pad_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        preprocessing_zinger_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        centering_title_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        recon_upper_center_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        recon_lower_center_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        centering_method_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        centering_button_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        recon_algo_title_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        recon_algo_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        recon_filter_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        recon_button_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        ring_removal_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        ## Creating Sizers for the right column.
        dim_title_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        dim_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        viz_box_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        slice_view_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        plotting_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        pp_label_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        pp_filter_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        save_recon_Sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        '''
        Adding widgets to LEFT Sizer.
        '''
        ## Adding title to topSizer
        leftSizer.Add(title_label, 1, wx.ALL|wx.EXPAND, 5)
        
        ## Adding to info panel.
        info_fname_Sizer.Add(file_label, 0, wx.ALL|wx.EXPAND, 5)
        info_fname_Sizer.Add(self.file_ID, wx.ALL|wx.EXPAND, 5)
        info_path_Sizer.Add(path_label,  0, wx.ALL|wx.EXPAND, 5)
        info_path_Sizer.Add(self.path_ID, 0, wx.ALL|wx.EXPAND, 5)
        info_status_Sizer.Add(status_label, 0, wx.ALL|wx.EXPAND, 5)
        info_status_Sizer.Add(self.status_ID, 0, wx.ALL|wx.EXPAND, 5)
        
        ## Adding to Preprocessing panel.
        preprocessing_title_Sizer.Add(preprocess_label, wx.ALL, 5)
        preprocessing_panel_Sizer.Add(dark_label, wx.ALL, 5)
        preprocessing_panel_Sizer.Add(self.dark_ID, wx.ALL, 5)
        preprocessing_panel_Sizer.Add(self.pad_size_combo, wx.ALL, 5)
        preprocessing_zinger_Sizer.Add(zinger_button, wx.ALL, 5)
        preprocessing_zinger_Sizer.Add(preprocess_button, wx.ALL, 5)
        
        ## Adding to centering panel.
        centering_title_Sizer.Add(centering_label, 0, wx.ALL, 5)
        recon_upper_center_Sizer.Add(upper_slice_label, 0, wx.ALL, 5)
        recon_upper_center_Sizer.Add(self.upper_rot_slice_blank, 0, wx.ALL, 5)
        recon_upper_center_Sizer.Add(self.upper_rot_center_blank, 0, wx.ALL, 5)
        recon_upper_center_Sizer.Add(upper_slice_recon_button, 0, wx.ALL, 5)
        recon_lower_center_Sizer.Add(lower_slice_label, 0, wx.ALL, 5)
        recon_lower_center_Sizer.Add(self.lower_rot_slice_blank, 0, wx.ALL, 5)
        recon_lower_center_Sizer.Add(self.lower_rot_center_blank, 0, wx.ALL, 5)
        recon_lower_center_Sizer.Add(lower_slice_recon_button, 0, wx.ALL, 5)
            
        centering_method_Sizer.Add(center_method_title, 0, wx.ALL, 5)
        centering_method_Sizer.Add(self.find_center_menu, wx.ALL, 5)
        centering_method_Sizer.Add(tol_title, wx.ALL,5)
        centering_method_Sizer.Add(self.tol_blank, wx.ALL, 5)
        centering_button_Sizer.Add(rot_center_title, 0, wx.ALL, 10)
        centering_button_Sizer.Add(self.est_rot_center_blank, wx.ALL, 5)
        centering_button_Sizer.Add(rot_center_button, 0, wx.ALL, 5)
        
        ## Adding to reconstruction panel.
        recon_algo_title_Sizer.Add(recon_algo_title, 0, wx.ALL, 5)
        recon_algo_Sizer.Add(recon_type_label, 0, wx.ALL, 5)
        recon_algo_Sizer.Add(self.recon_menu, 0, wx.ALL, 5)
        recon_algo_Sizer.Add(filter_label, 0, wx.ALL, 5)
        recon_algo_Sizer.Add(self.filter_menu, 0, wx.ALL, 5)
        recon_button_Sizer.Add(tilt_button, 0, wx.ALL, 5)
        recon_button_Sizer.Add(recon_button, 0, wx.ALL, 5)
        recon_button_Sizer.Add(ring_remove_button, 0, wx.ALL, 5)

        
        
        '''
        Adding all widgets to the RIGHT Sizer.
        '''
        ## Dimensions panel
        dim_title_Sizer.Add(dim_label, wx.ALL, 5)
        dim_Sizer.Add(sx_label, wx.ALL|wx.EXPAND, 5)
        dim_Sizer.Add(self.sx_ID, wx.ALL|wx.EXPAND, 5)
        dim_Sizer.Add(sy_label, wx.ALL|wx.EXPAND, 5)
        dim_Sizer.Add(self.sy_ID, wx.ALL|wx.EXPAND, 5)
        dim_Sizer.Add(sz_label, wx.ALL|wx.EXPAND, 5)
        dim_Sizer.Add(self.sz_ID, wx.ALL|wx.EXPAND, 5)
        
        ## Data visualization panel.
        viz_box_Sizer.Add(self.visualization_box, wx.ALL|wx.EXPAND, 5)
        
        ## Slice and plotting panel.
        slice_view_Sizer.Add(self.z_lble, wx.ALL|wx.EXPAND, 5)
        slice_view_Sizer.Add(self.z_dlg, wx.ALL|wx.EXPAND, 5)
        plotting_Sizer.Add(plot_button, wx.ALL|wx.EXPAND, 5)
        plotting_Sizer.Add(movie_button, wx.ALL|wx.EXPAND, 5)
        
        ## Post processing filters panel.
        pp_label_Sizer.Add(pp_label, wx.ALL|wx.EXPAND, 5)
        pp_filter_Sizer.Add(pp_filter_label, wx.ALL|wx.EXPAND, 5)
        pp_filter_Sizer.Add(self.pp_filter_menu, wx.ALL|wx.EXPAND, 5)
        pp_filter_Sizer.Add(self.pp_filter_button, wx.ALL|wx.EXPAND, 5)
        
        ## Data export panel.
        save_recon_Sizer.Add(self.save_dtype_menu, wx.ALL|wx.EXPAND,5)
        save_recon_Sizer.Add(self.save_data_type_menu, wx.ALL|wx.EXPAND, 5)
        save_recon_Sizer.Add(save_recon_button, wx.ALL|wx.EXPAND, 5)
        
        '''
        Adding to leftSizer.
        '''
        ## Adding all subpanels to the topSizer panel. Allows overall aligment.
        leftSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(info_fname_Sizer, 0, wx.EXPAND)
        leftSizer.Add(info_path_Sizer, 0, wx.EXPAND)
        leftSizer.Add(info_status_Sizer, 0, wx.EXPAND)
        leftSizer.Add(wx.StaticLine(self.panel),0,wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(preprocessing_title_Sizer, 0, wx.ALL|wx.EXPAND,5)
        leftSizer.Add(preprocessing_panel_Sizer, 0, wx.EXPAND, 10)
        leftSizer.Add(preprocessing_pad_Sizer, 0, wx.EXPAND,5)
        leftSizer.Add(preprocessing_zinger_Sizer, 0, wx.EXPAND, 5)
        leftSizer.Add(wx.StaticLine(self.panel),0,wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(centering_title_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(recon_upper_center_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(recon_lower_center_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(centering_method_Sizer, 0, wx.ALL|wx.EXPAND)
        leftSizer.Add(centering_button_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND,5)
        leftSizer.Add(recon_algo_title_Sizer, 0, wx.ALL|wx.EXPAND,5)
        leftSizer.Add(recon_algo_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(recon_filter_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(recon_button_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        leftSizer.Add(ring_removal_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        
        '''
        Adding to rightSizer.
        '''
        rightSizer.Add(dim_title_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        rightSizer.Add(dim_Sizer, 0, wx.ALL|wx.EXPAND,5)
        rightSizer.Add(viz_box_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        rightSizer.Add(slice_view_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        rightSizer.Add(plotting_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        rightSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND, 5)
        rightSizer.Add(pp_label_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        rightSizer.Add(pp_filter_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        rightSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND, 5)
        rightSizer.Add(save_recon_Sizer, 0, wx.ALL|wx.EXPAND, 5)
        
        '''
        Adding left and right sizers to main sizer.
        '''
        windowSizer.Add(leftSizer, 0, wx.ALL|wx.EXPAND, 10)
        windowSizer.AddSpacer(60)
        windowSizer.Add(rightSizer, 0, wx.ALL|wx.EXPAND, 10)
        self.panel.SetSizer(windowSizer)
        windowSizer.Fit(self)
        

        
    '''
    Methods called by widgets from above. Organized by location. 
    First set of methods are closely associated with the main menu bar.
    '''
    def client_read_nc(self, event):
        '''
        Reads in tomography data.
        '''
        with wx.FileDialog(self, "Select Data File", wildcard="Data files (*.nc; *.volume)|*.nc;*.volume",
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST|wx.FD_CHANGE_DIR) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # for if the user changed their mind
            ## Setting up timestamp.
            t0 = time.time()
            ## Loading path and updating status label on GUI.
            path = fileDialog.GetPath()
            self.status_ID.SetLabel('Please wait. Reading in the data.')
            ## Loading in file that was just chosen by user.
            try:
                with open(path, 'r') as file:
                    fname = file
                    _path, _fname = os.path.split(path)
                    self.fname1 = file 
                    ## Number of cores is specified for now. May later add text
                    ## box user option. 
                    self.ncore = 4
                    if _fname.endswith('.nc'):
                        '''
                        Reading in .nc files. APS 13BM format. 
                        Reads in 2 flats (.nc), .setup, and data (.nc).
                        '''
                        ## Gather list of all .nc files sharing same fname string.
                        fname = glob.glob("*[1-3].nc") 
                        ## Entries 1 and 3 of fname list are flat fields.
                        ## Read in second entry (fname[1]), which houses the data.
                        self.data = dx.exchange.read_aps_13bm(fname[1],format='netcdf4')
                        print('read in data', self.data.shape)
                        ## Read .setup file, convert lines to rows, identify dark current.
                        setup = glob.glob("*.setup")
                        setup = open(setup[0], 'r')
                        setup_data = setup.readlines()
                        result = {}
                        for line in setup_data:
                            words = line[:-1].split(':',1)
                            result[words[0].lower()] = words[1]
                        self.dark = float(result['dark_current'])                       
                        ## Read in both flat field files.
                        self.flat1 = dx.exchange.read_aps_13bm(fname[0],format = 'netcdf4')
                        self.flat2 = dx.exchange.read_aps_13bm(fname[2],format = 'netcdf4')
                        ## Storing angles.
                        self.theta = tp.angles(self.data.shape[0])
                        ## Storing the dimensions for updating GUI.
                        self.sx = self.data.shape[2]
                        self.sy = self.data.shape[1]
                        self.sz = self.data.shape[0]                        
                        ## Updating the GUI.
                        self._fname = _fname[0:-5]
                        self.update_info(path=_path, 
                                         fname=self._fname, 
                                         sx=self.sx, 
                                         sy=self.sy, 
                                         sz=self.sz, 
                                         dark=self.dark)
                        self.status_ID.SetLabel('Data Imported') 
                        ## Time stamping.
                        t1 = time.time()
                        total = t1-t0
                        print('Time reading in files ', total)
                        setup.close()
                    if _fname.endswith('.volume'):
                        '''
                        Reads in .volume files generated from tomoRecon.
                        '''
                        data = Dataset(_fname,'r', format = 'NETCDF4')
                        self.data = data.variables['VOLUME'][:]
                        data.close()
                        # Storing angles.
                        self.theta = tp.angles(self.data.shape[0])
                        # Storing the dimensions for updating GUI.
                        self.sx = self.data.shape[2]
                        self.sy = self.data.shape[1]
                        self.sz = self.data.shape[0]                        
                        ## Updating the GUI.
                        self._fname = _fname[0:-5]
                        self.dark = 'NA'
                        self.update_info(path=_path, fname=self._fname, sx=self.sx, sy=self.sy, sz=self.sz, dark=self.dark)
                        self.status_ID.SetLabel('Data Imported')
                        ## Time stamping.
                        t1 = time.time()
                        total = t1-t0
                        print('Time reading in files ', total)            
            except IOError:
                wx.LogError("Cannot open file '%s'." % newfile)
       
         
    def update_info(self, path=None, fname=None, sx=None, sy=None, sz=None, dark=None):
        '''
        Updates GUI info when files are imported
        as well as when files are adjusted later.
        '''
        if path is not None:
            self.path_ID.SetLabel(path)
        if sx is not None:
            self.sx_ID.SetLabel(str(self.sx))
        if sy is not None:
            self.sy_ID.SetLabel(str(self.sy))
        if sz is not None:
            self.sz_ID.SetLabel(str(self.sz))
        if fname is not None:
            self.file_ID.SetLabel(fname) 
        if dark is not None:
            self.dark_ID.SetLabel(str(self.dark))
    

    def change_dir(self, event):
        '''
        Allows user to change directory where files will be saved.
        This does not automatically read in files within the newly 
        specified directory.
        '''
        dlg =  wx.DirDialog(self, "Choose Directory","",
                           wx.DD_DEFAULT_STYLE|wx.DD_CHANGE_DIR)
        try:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
        except Exception:
            wx.LogError('Failed to open directory!')
            raise
        finally:
            dlg.Destroy()
        if len(path) > 0:
            self.path_ID.SetLabel(path)
            os.chdir(path)
        print('new dir', os.getcwd)   
    
    
    def client_free_mem(self, event):
        '''
        Deletes stored variables from memory, and resets labels on GUI.
        '''
        if self.data is None:
            return
        else:
            del self.data
            self.path_ID.SetLabel('')
            self.file_ID.SetLabel('')
            self.status_ID.SetLabel('Memory Cleared')
            gc.collect()
            print('fname and path released')


    def OnExit(self, event):
        '''
        Closes the GUI program.
        '''
        try:
            if self.plotframe != None:  self.plotframe.onExit()
        except:
            pass
        self.Destroy() 
   
    
    

    '''
    The following section houses methods specific to widgets on the GUI.
    '''     
    def pad_size_combo_recall (self, event = None):
        '''
        Sets sinogram pad size if user adjusts from default.
        '''
        new_pad = self.pad_size_combo.GetStringSelection()
        if new_pad == 'No Padding':
            self.pad_size = int(0)
            self.npad = int(0)
        else:
            self.pad_size = int(new_pad)
        print('pad size changed to ',self.pad_size)
    

    def zinger_removal(self, event):
        '''
        Remove zinger artifact from raw data.
        '''
        self.status_ID.SetLabel('Removing Zingers')
        t0 = time.time()
        self.data = tp.prep.stripe.remove_stripe_fw(self.data)
        t1 = time.time()
        print('Zinger removal: ', t1-t0)
        self.status_ID.SetLabel('Zingers removed.')
    

    def normalization(self, event):
        '''
        Normalizes the data (1) using the flat fields and dark current,
        then by using the air pixels on edge of sinogram.
        '''
        self.status_ID.SetLabel('Preprocessing')
        ## Setting up timestamp.
        t0 = time.time()
        ## Flats from APS 13BM are in seperate arrays. Average then delete.
        self.flat = np.concatenate((self.flat1, self.flat2),axis=0)
        del self.flat1
        del self.flat2
        ## Only single value is collected for dark current from APS 13BM.
        ## Allow user to adjust this value.
        ## Create array of same size for normalizing.
        self.dark = float(self.dark_ID.GetValue())
        self.dark = self.flat*0+self.dark
        ## First normalization using flats and dark current.
        self.data = tp.normalize(self.data, 
                                 flat=self.flat, 
                                 dark=self.dark, 
                                 ncore = self.ncore)
        ## Additional normalization using the 10 outter most air pixels.
        self.data = tp.normalize_bg(self.data,
                                    air = 10)
        ## Allows user to pad sinogram.
        if self.pad_size != 0:
            self.npad = 0
            if int(self.pad_size) < self.data.shape[2]:
                self.status_ID.SetLabel('Pad Size too small for dataset. No padding done.')
                return
            else:
                self.npad = int( (int(self.pad_size) - self.data.shape[2] ) / 2)
                self.data = tp.misc.morph.pad(self.data, axis = 2, npad =self.npad, mode = 'edge')
#                self.sx = self.data.shape[2]
#                self.sx_ID.SetLabel(str(self.sx))
        ## Removing extreme values. Code directly from Francesco De Carlo's GUI code.
        ## https://github.com/tomography/ufot
        ## Accessed 10/9/2018
        upper = np.percentile(self.data, 99)
        lower = np.percentile(self.data, 1)
        self.data[self.data > upper] = upper
        self.data[self.data < lower] = lower
        ## Set status update for user.
        self.status_ID.SetLabel('Preprocessing Complete')
        ## Delete dark field array as we no longer need it.
        del self.dark
        ## Timestamping.
        t1 = time.time()
        total = t1-t0
        print('data dimensions ',self.data.shape, type(self.data), self.data.dtype, 'min ', self.data.min(), 'max', self.data.max())
        print('Normalization time was ', total)
    

    def up_recon_slice (self, event):
        '''
        Slice reconstruction methods. 
        '''
        self.status_ID.SetLabel('Reconstructing slice.')
        t0 = time.time()
        self.upper_rot_center = float(self.upper_rot_center_blank.GetValue())
        start = int(self.upper_rot_slice_blank.GetValue())        
        self.data_slice = tp.minus_log(self.data[:,start:start+1,:])
        self.data_slice = tp.recon(self.data_slice,
                                   self.theta,
                                   center = self.upper_rot_center,
                                   sinogram_order = False,
                                   algorithm = self.recon_type,
                                   )
        t1 = time.time()
        print('Slice recon time ', t1-t0)
        self.status_ID.SetLabel('Slice Reconstructed.')
        self.plot_slice_data()


    def lower_recon_slice (self, event):
        '''
        Slice reconstruction methods. 
        '''
        self.status_ID.SetLabel('Reconstructing slice.')
        t0 = time.time()
        self.lower_rot_center = float(self.lower_rot_center_blank.GetValue())
        start = int(self.lower_rot_slice_blank.GetValue())        
        self.data_slice = tp.minus_log(self.data[:,start:start+1,:])
        self.data_slice = tp.recon(self.data_slice,
                                   self.theta,
                                   center = self.lower_rot_center,
                                   sinogram_order = False,
                                   algorithm = self.recon_type,
                                   )
        t1 = time.time()
        print('Slice recon time ', t1-t0)
        self.status_ID.SetLabel('Slice Reconstructed.')
        self.plot_slice_data()
    

    def find_rot_center(self, event=None):
        '''
        Allows user to find rotation centers of two slices. Then displays the 
        average of those centers.
        '''
        self.status_ID.SetLabel('Centering')
        ## Setting up timestamp.
        t0 = time.time()
        ## Tolerance used for TomoPy centering algorithms.
        tol = float(self.tol_blank.GetValue())
        upper_slice = int(self.upper_rot_slice_blank.GetValue())
        lower_slice = int(self.lower_rot_slice_blank.GetValue())
        upper_center = float(self.upper_rot_center_blank.GetValue())
        lower_center = float(self.lower_rot_center_blank.GetValue())   
        if self.find_center_type == 'Entropy':
            self.upper_rot_center = tp.find_center(self.data[upper_slice:upper_slice+1,:,:], 
                                                   self.theta, 
                                                   init=upper_center, 
                                                   tol=tol)
            self.lower_rot_center = tp.find_center(self.data[lower_slice:lower_slice+1,:,:],
                                                   self.theta,
                                                   init = lower_center,
                                                   tol = tol)
            self.rot_center = (self.upper_rot_center + self.lower_rot_center) / 2
        if self.find_center_type == '0-180':
            if upper_slice > self.data.shape[2]:
                self.status_ID.SetLabel('Upper slice out of range.')
                return
            if lower_slice > self.data.shape[2]:
                self.status_ID.SetLabel('Lower slice out of range.')
                return
            upper_proj1 = self.data[upper_slice,:,:]
            u_slice2 = (upper_slice + int(self.data.shape[0]/2))%self.data.shape[0]
            upper_proj2 = self.data[u_slice2,:,:]
            self.upper_rot_center = tp.find_center_pc(upper_proj1, 
                                                      upper_proj2, 
                                                      tol = tol)
            lower_proj1 = self.data[lower_slice,:,:]
            l_slice2 = (lower_slice + int(self.data.shape[0]/2))%self.data.shape[0]
            lower_proj2 = self.data[l_slice2,:,:]
            self.lower_rot_center = tp.find_center_pc(lower_proj1,
                                                      lower_proj2,
                                                      tol = tol)
            self.rot_center = (self.upper_rot_center + self.lower_rot_center) / 2
        ## Vghia Vo works very well with 13BM data.   
        if self.find_center_type == 'Vghia Vo':
            self.upper_rot_center = tp.find_center_vo(self.data[:,upper_slice:upper_slice+1,:])
            self.lower_rot_center = tp.find_center_vo(self.data[:,lower_slice:lower_slice+1,:])
            self.rot_center = (self.upper_rot_center + self.lower_rot_center) / 2	 
        ## Timestamping.
        t1 = time.time()
        total = t1-t0
        print('Time to find center was ', total)
        self.status_ID.SetLabel('Rotation Center found.')
        print('success, rot center is ', self.rot_center)
        ## Updating the GUI for the calculated values. 
        try:
            self.est_rot_center_blank.SetValue(str(self.rot_center-self.npad))
            self.upper_rot_center_blank.SetLabel(str((self.upper_rot_center-self.npad)))
            self.lower_rot_center_blank.SetLabel(str((self.lower_rot_center-self.npad)))
        except:
            self.status_ID.SetLabel('Select No Padding and re-run Centering.')
    

    def find_center_algo_type (self, event):
        '''
        Sets the user's choice for identifying center.
        '''
        self.find_center_type = self.find_center_menu.GetStringSelection()
        print('Center algorithm is ', self.find_center_type)


    def OnReconCombo(self, event):
        '''
        Sets the reconstruction type if changed from default.
        '''
        self.recon_type = self.recon_menu.GetStringSelection()
        if self.recon_type == 'Algebraic':
            self.recon_type = 'art'
        if self.recon_type == 'Block Algebraic':
            self.recon_type = 'bart'
        if self.recon_type == 'Filtered Back-projection':
            self.recon_type = 'fbp' 
        if self.recon_type == 'Gridrec':
            self.recon_type = 'gridrec'
        if self.recon_type == 'Max-likelihood Expectation':
            self.recon_type = 'mlem'
        if self.recon_type == 'Ordered-subset Expectation':
            self.recon_type = 'osem'
        if self.recon_type == 'ospml_hybrid':
            self.recon_type = 'ospml_hybrid'
        if self.recon_type == 'ospml_quad':
            self.recon_type = 'ospml_quad'
        if self.recon_type == 'pml_hybrid':
            self.recon_type = 'pml_hybrid'
        if self.recon_type == 'pml_quad':
            self.recon_type = 'pml_quad'
        if self.recon_type == 'Simultaneous Algebraic':
            self.recon_type = 'sirt'
        if self.recon_type == 'Total Variation':
            self.recon_type = 'tv',
        if self.recon_type == 'Gradient Descent':
            self.recon_type = 'grad'
        print('Recon algorithm is ', self.recon_type)
        

    def OnFilterCombo(self, event):
        '''
        Sets the reconstruction filter if adjusted from default.
        '''
        self.filter_type = self.filter_menu.GetStringSelection()
        print('Filter is ', self.filter_type)
       

    def tilt_correction(self, event):
        '''
        Corrects raw data upper and lower centers do not match.
        Currently this needs to be fixed. Tilt corrected data
        unable to reconstruct after this step.
        '''
        ## This did not come from TomoPy because TomoPy has yet to implement.
        ## This also appears to be returning an array that plotting can't work with.
        self.status_ID.SetLabel('Correcting Tilt')
        ## Setting up timestamp.
        t0 = time.time()
        nangles = self.data.shape[0]
        top_center = float(self.upper_rot_center_blank.GetValue())
        bottom_center = float(self.lower_rot_center_blank.GetValue())
        top_slice = float(self.upper_rot_slice_blank.GetValue())
        bottom_slice = float(self.lower_rot_slice_blank.GetValue())
        angle = (top_center - bottom_center)/(bottom_slice - top_slice)
        print('angle is ', angle)
        for i in range(nangles-1): 
            projection = self.data[i,:,:]
            r = scipy.ndimage.rotate(projection, angle)
            self.data[i,:,:] = float(r) #might need to remove the float from here. Could be breaking it. Integer?
        t1 = time.time()
        print('Time to tilt ', t1-t0)
        print('New dimnsions are ', self.data.shape, 'Data type is', type(self.data))
        self.status_ID.SetLabel('Tilt Corrected')
    

    def reconstruct(self, event):
        '''
        Whole volume reconstruction method.
        '''
        self.status_ID.SetLabel('Reconstructing.')
        ## Setting up timestamp.
        t0 = time.time()
        try: 
            print('original data dimensions are ', self.data.shape, type(self.data), self.data.dtype)
            self.rot_center = float(self.est_rot_center_blank.GetValue())
            if self.npad != 0:
                self.rot_center = float(self.rot_center)+self.npad
            ## Corrects the I/I0 ring artifact surrounding volume after reconstruction.
#            self.data = tp.remove_neg(self.data)
            self.data = tp.minus_log(self.data)
            ## This returns float32.
            self.data = tp.recon(self.data, 
                                 self.theta, 
                                 center = self.rot_center, 
                                 sinogram_order = False,
                                 algorithm = self.recon_type, 
                                 filter_name = self.filter_type,
                                 ncore = self.ncore,
                                 nchunk = 128)
            self.data = tp.remove_nan(self.data)
            print('made it through recon.', self.data.shape, type(self.data), self.data.dtype)        
            self.status_ID.SetLabel('Reconstruction Complete')
            print('reconstruction done')                
        except:
            '''
            Runs if not normalized, so tripped for not having pad value.
            '''
            self.status_ID.SetLabel('Normalization not done, select no padding.')
            return
        t1 = time.time()
        total = t1-t0
        print('Reconstruction time was ', total)
        ## Updates new dimensions.
        self.sx = self.data.shape[2]-2*self.npad
        self.sy = self.data.shape[1]-2*self.npad
        self.sz = self.data.shape[0]
        ## Updates GUI. Variables set to None don't update in self.update_info method.
        path = None
        dark = None
        fname = None
        self.update_info(path=path, 
                         fname=fname, 
                         sx=self.sx, 
                         sy=self.sy, 
                         sz=self.sz, 
                         dark=dark)
        print(self.data)
        
        
    def remove_ring(self, event):
        '''
        Removes ring artifact from reconstructed data.
        '''
        self.status_ID.SetLabel('Removing Ring.')    
        ## Setting up timestamp.
        t0 = time.time()
        self.data = tp.remove_ring(self.data)
        t1 = time.time()
        print('made it through ring removal.', t1-t0)
        self.status_ID.SetLabel('Ring removed.')
        

    def OnRadiobox(self, event):
        '''
        Adjusts what view the user wishes to see in plotting window.
        '''    
        self.plot_type = self.visualization_box.GetStringSelection()
        print('Slice view from Radiobox is ', self.plot_type)          
      

    def OnppFilterCombo(self, event):
        '''
        Sets post processing filter type.
        '''
        self.pp_filter_type = self.pp_filter_menu.GetStringSelection()
        print('filter has been set ', self.pp_filter_type)
        

    def filter_pp_data(self, event):
        '''
        Post processing step. Filters the reconstruction data based on the above
        filter type selection. This is a secondary filter separate from the 
        filtering during reconstruction.
        '''
        self.status_ID.SetLabel('Filtering')
        if self.pp_filter_type == 'gaussian_filter':
            print('gaussian')
            self.data = tp.misc.corr.gaussian_filter(self.data, sigma = 3)
            print('gaussian done')
        if self.pp_filter_type == 'median_filter':
            print('median')
            self.data = tp.misc.corr.median_filter(self.data)
            print('median done')
        if self.pp_filter_type == 'sobel_filter':
            print('sobel')
            self.data = tp.misc.corr.sobel_filter(self.data)
            print('sobel done')
        self.status_ID.SetLabel('Data Filtered')
        

    def OnSaveDtypeCombo (self, event):
        '''
        Data export parameters. All data are exported as intergers with choice of 
        8 bit, 16 bit, or 32 bit.
        '''    
        self.save_dtype = self.save_dtype_menu.GetStringSelection()
        if self.save_dtype == '8 bit':
            self.save_dtype = 'u1'
            print('data type changed to ', self.save_dtype)
        if self.save_dtype == '16 bit':
            self.save_dtype = 'i2'
            print('data type changed to ', self.save_dtype)
        if self.save_dtype == '32 bit float':
            self.save_dtype = 'f4'
            print('data type changed to ', self.save_dtype)
    

    def OnSaveDataTypeCombo(self, event):
        '''
        Data export parameters. Specifies file extension to be used.
        '''
        self.save_data_type = self.save_data_type_menu.GetStringSelection()
        print('Data export type is ', self.save_data_type)
            

    def save_recon(self, event=None):
        '''
        Method for saving. If .tif is used, a new folder called 'temp' will be 
        created in current working directory.
        '''
        self.status_ID.SetLabel('Saving')
        ## Setting up timestamp.
        t0 = time.time()
        ## Setup copy of data to allow user to scale and save at different file
        ## types (e.g. 8 bit, 16 bit, etc.). Must check to see if data are padded.
        if self.npad == 0:
            save_data = self.data[:]
        ## Saving based on padding and reconstruction.
        if self.npad != 0: #was padded.
            if self.data.shape [1] == self.data.shape[2]: #padded and reconstructed.
                save_data = self.data[:,self.npad:self.data.shape[1]-self.npad,self.npad:self.data.shape[2]-self.npad]
            if self.data.shape[1] != self.data.shape[2]: #padded and NOT reconstructed.
                save_data = self.data[:,:,self.npad:self.data.shape[2]-self.npad]
        print('save_data dim are ', save_data.shape, save_data.dtype)
        
        
        
        
        ## Need to scale data according to user input.
        ## These do not work.
        ## If user wants 16 bit image after reconstruction.
#        if save_data.dtype == 'float32' and self.save_dtype == 'i2':
#            print('made it to 16 bit from float32 clause')
#            print('starting data type is ', save_data.dtype)
#            save_data = save_data / save_data.max()
#            save_data = 65535 * save_data
#            print('interger data is ', save_data.dtype)
#            print('save_data converted to uint16')
        ## If user wants 8 bit image (after reconstruction).
#        if save_data.dtype == 'float32' and self.save_dtype == 'u1':  #want 8 bit
#            print('made it to 8 bit from float32 clause')
#            print('starting data type is ', save_data.dtype, 'min', save_data.min(), 'max', save_data.max())
#            save_data = save_data / save_data.max()
#            print('division done ', save_data.mix(), save_data.max())
#            save_data = 255 * save_data
#            print('save data are ', save_data.dtype, 'min', save_data.min(), 'max', save_data.max())
#            save_data = save_data.astype(np.uint8)
#            print('save data are ', save_data.shape, save_data.dtype, 'min', save_data.min(), 'max', save_data.max())
#        
#        
#        
        ## This one works.
        ## If user wants 8 bit image from raw data.
        if (save_data.dtype == 'int16' and self.save_dtype == 'u1'):
            print('made it to 8 bit from int 16 clause')
            print('starting data type is ', save_data.dtype, 'min', save_data.min(), 'max', save_data.max())
            info = np.iinfo(save_data.dtype)
            save_data = save_data / info.max
            save_data = 255 * save_data
            save_data = save_data.astype(np.uint8)
            print('save data are ', save_data.shape, save_data.dtype, 'min', save_data.min(), 'max', save_data.max())
        
        ## Create tif stack within a temp folder in the current working directory.
        if self.save_data_type == '.tif':
            print('Beginning saving tiffs')
            dx.write_tiff_stack(save_data, fname = self._fname, dtype = self.save_dtype, overwrite=True)
        ## Create a .volume netCDF file.
        if self.save_data_type == '.vol':
            print('Beginning saving .vol')
            ## Creates the empty file, and adds metadata.
            ncfile = Dataset(self._fname+'_tomopy_recon.volume', 'w', format = 'NETCDF3_64BIT', clobber = True) # Will overwrite if pre-existing file is found.
            ncfile.description = 'Tomography dataset'                             
            ncfile.source = 'APS GSECARS 13BM'
            ncfile.history = "Created "+time.ctime(time.time())
            ## Creates the correct dimensions for the file.         
            NX = ncfile.createDimension('NX', save_data.shape[2])
            NY = ncfile.createDimension('NY', save_data.shape[1])
            NZ = ncfile.createDimension('NZ', save_data.shape[0])
            print('save_dtype is ', self.save_dtype)
            ## Creates variable for data based on previously constructed dimensions.
            volume = ncfile.createVariable('VOLUME', self.save_dtype, ('NZ','NY','NX',)) 
            ## Copies data into empty file array.
            volume[:] = save_data
            print('volume ', volume.shape, type(volume), volume.dtype)
            ncfile.close()   
        self.status_ID.SetLabel('Saving completed.')
        t1 = time.time()
        total = t1-t0
        print('Time saving data ', total)
    
    
    
    
    
    ''' 
    Below here is where the various plotting definitions occur.
    '''       
    def create_ImageFrame(self):
        '''
        Setups the plotting window.
        '''
        if self.image_frame is None:
            self.image_frame = ImageFrame(self) 
            self.image_frame.Show()
      
        
    def plot_slice_data (self,event=None):

        if self.data_slice is None: # user forgot to enter a slice.
            return
        image_frame = ImageFrame(self) 
        try:
            z = 0
        except ValueError:  # user forgot to enter slice or entered bad slice.
            self.status_ID.SetLabel('Please input an upper slice.')
        ## Plotting data. 
        d_data = self.data_slice[z, ::-1, :]          
        ## Setting up parameters and plotting.
        if d_data is not None:
            image_frame.panel.conf.interp = 'hanning'
            image_frame.display(1.0*d_data, auto_contrast=True, colormap='gist_gray_r')
            image_frame.Show()
            image_frame.Raise()
        else:
            print("cannot figure out how to get data from plot_type ", self.plot_type)


    def plotData(self, event):
        '''
        Plots when the 'Plot Image' button is pressed. 
        Plot view depends on Data Visualization view option and slice.
        Defaults to an additional hanning filter.
        Defaults to gray scale reversed so that bright corresponds to higher 
        density.
        '''
        if self.data is None:   # no data loaded by user.
            return
        ## Calls plotting frame.
        image_frame = ImageFrame(self) 
        try:
            ## Look for slice to display.
            self.z = self.z_dlg.GetValue() 
            z = int(self.z)
            print('read in z and plot_type.', self.z)

        except ValueError:
            print(" cannot read z from Entry ", self.z)
            self.status_ID.SetLabel('Please input a slice.')
            print(" cannot read plot_type from Entry ", self.plot_type)
        ## Plotting data
        d_data = None
        ## Plot an mask if reconstruction is not gridrec.
        if self.recon_type != 'gridrec':
                d_data = tp.circ_mask(d_data, axis = 0, ratio = 0.95)
        ## Plot according to the users input. Default is slice view.        
        if self.plot_type.startswith('Z'): #  Slice':
            d_data = self.data[z, ::-1, :]          
        if self.plot_type.startswith('Y'): #  Sinogram':
            d_data = self.data[::-1,  z, :]
        if self.plot_type.startswith('X'): #  Sinogram':
            d_data = self.data[::-1, :, z]
        ## Setting up parameters and plotting.
        if d_data is not None:       
            image_frame.panel.conf.interp = 'hanning'
            image_frame.display(1.0*d_data, auto_contrast=True, colormap='gist_gray_r')
            image_frame.Show()
            image_frame.Raise()
        else:
            print("cannot figure out how to get data from plot_type ", self.plot_type)
            
            
    def movie_maker (self, event):
        '''
        Yet to be developed.
        Will display a movie to screen slicing through projections.
        '''
        self.status_ID.SetLabel('Movie not yet developed.')




'''
Mainloop of the GUI.
'''
if __name__ == '__main__':
    app = wx.App()
    f = APS_13BM(None,-1)
    f.Show(True)
    app.MainLoop()