### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###
#
#    Python interface to the NIfTI file format
#
#    Copyright (C) 2006-2007 by
#    Michael Hanke <michael.hanke@gmail.com>
#
#    This package is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    version 2 of the License, or (at your option) any later version.
#
#    This package is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###
# SVN version control block - do not edit manually
# $Id$
# $Rev$
# $Date$
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###

import clibs
import os
import numpy


nifti_unit_ids = [ 'm', 'mm', 'um' ]

   
class NiftiFile(object):
    """Wrapper class for convenient access to NIfTI data.
    
    The class can either load an image from file or convert a NumPy 
    array into a NIfTI file structure. Either way is automatically determined
    by the type of the 'source' argument (string == filename, array == Numpy).

    One can optionally specify whether the image data should be loaded into 
    memory when opening NIfTI data from files ('load'). When converting a NumPy
    array one can optionally specify a dictionary with NIfTI header data as 
    available via the 'header' attribute.
    """

    filetypes = [ 'ANALYZE', 'NIFTI', 'NIFTI_PAIR', 'ANALYZE_GZ', 'NIFTI_GZ',
                  'NIFTI_PAIR_GZ' ]

    numpy2nifti_dtype_map = { numpy.uint8: clibs.NIFTI_TYPE_UINT8,
                              numpy.int8 : clibs.NIFTI_TYPE_INT8,
                              numpy.uint16: clibs.NIFTI_TYPE_UINT16,
                              numpy.int16 : clibs.NIFTI_TYPE_INT16,
                              numpy.uint32: clibs.NIFTI_TYPE_UINT32,
                              numpy.int32 : clibs.NIFTI_TYPE_INT32,
                              numpy.uint64: clibs.NIFTI_TYPE_UINT64,
                              numpy.int64 : clibs.NIFTI_TYPE_INT64,
                              numpy.float32: clibs.NIFTI_TYPE_FLOAT32,
                              numpy.float64: clibs.NIFTI_TYPE_FLOAT64,
                              numpy.complex128: clibs.NIFTI_TYPE_COMPLEX128
                            }


    @staticmethod
    def numpydtype2niftidtype(array):
        """ Return the NIfTI datatype id for a corrsponding numpy array 
        datatype.
        """
        # get the real datatype from numpy type dictionary
        dtype = numpy.typeDict[str(array.dtype)]

        if not NiftiFile.numpy2nifti_dtype_map.has_key(dtype):
            raise ValueError, "Unsupported datatype '%s'" % str(array.dtype)

        return NiftiFile.numpy2nifti_dtype_map[dtype]


    @staticmethod
    def splitFilename(filename):
        """ Split a NIfTI filename and returns a tuple of basename and 
        extension. If no valid NIfTI filename extension is found, the whole
        string is returned as basename and the extension string will be empty.
        """

        parts = filename.split('.')

        if parts[-1] == 'gz':
            if parts[-2] != 'nii' and parts[-2] != 'hdr':
                return filename, ''
            else:
                return '.'.join(parts[:-2]), '.'.join(parts[-2:])
        else:
            if parts[-1] != 'nii' and parts[-1] != 'hdr':
                return filename, ''
            else:
                return '.'.join(parts[:-1]), parts[-1]

    
    @staticmethod
    def nhdr2dict(nhdr):
        """ Convert a NIfTI header struct into a python dictionary.

        While most elements of the header struct will be translated 
        1:1 some (e.g. sform matrix) are converted into more convenient 
        datatypes (i.e. 4x4 matrix instead of 16 separate values).
        """
        h = {}
        
        # the following header elements are converted in a simple loop
        # as they do not need special handling
        auto_convert = [ 'session_error', 'extents', 'sizeof_hdr', 
                         'slice_duration', 'slice_start', 'xyzt_units',
                         'cal_max', 'intent_p1', 'intent_p2', 'intent_p3',
                         'intent_code', 'sform_code', 'cal_min', 'scl_slope',
                         'slice_code', 'bitpix', 'descrip', 'glmin', 'dim_info',
                         'glmax', 'data_type', 'aux_file', 'intent_name',
                         'vox_offset', 'db_name', 'scl_inter', 'magic', 
                         'datatype', 'regular', 'slice_end', 'qform_code', 
                         'toffset' ]


        # now just dump all attributes into a dict
        for attr in auto_convert:
            h[attr] = eval('nhdr.' + attr)

        # handle a few special cases
        # handle 'pixdim'
        pixdim = clibs.floatArray_frompointer(nhdr.pixdim)
        h['pixdim'] = [ pixdim[i] for i in range(8) ]

        # handle dim
        dim = clibs.shortArray_frompointer(nhdr.dim)
        h['dim'] = [ dim[i] for i in range(8) ]

        # handle sform
        srow_x = clibs.floatArray_frompointer( nhdr.srow_x )
        srow_y = clibs.floatArray_frompointer( nhdr.srow_y )
        srow_z = clibs.floatArray_frompointer( nhdr.srow_z )

        h['sform'] = numpy.array( [ [ srow_x[i] for i in range(4) ],
                                    [ srow_y[i] for i in range(4) ],
                                    [ srow_y[i] for i in range(4) ],
                                    [ 0.0, 0.0, 0.0, 1.0 ] ] )

        # handle qform stuff
        h['quatern'] = [ nhdr.quatern_b, nhdr.quatern_c, nhdr.quatern_d ]
        h['qoffset'] = [ nhdr.qoffset_x, nhdr.qoffset_y, nhdr.qoffset_z ]

        return h

    
    @staticmethod
    def updateNiftiHeaderFromDict(nhdr, hdrdict):
        """ Update a NIfTI header struct with data from a dictionary.
        
        The supplied dictionary might contain additonal data elements 
        that do not match any nifti header element. These are silently ignored.

        Several checks are performed to ensure validity of the resulting 
        nifti header struct. If any check fails a ValueError exception will be
        thrown. However, some tests are still missing.
        """
        # this function is still incomplete. add more checks

        if hdrdict.has_key('data_type'):
            if len(hdrdict['data_type']) > 9:
                raise ValueError, "Nifti header property 'data_type' must not be longer than 9 characters."
            nhdr.data_type = hdrdict['data_type']
        if hdrdict.has_key('db_name'):
            if len(hdrdict['db_name']) > 79:
                raise ValueError, "Nifti header property 'db_name' must not be longer than 17 characters."
            nhdr.db_name = hdrdict['db_name']

        if hdrdict.has_key('extents'):
            nhdr.extents = hdrdict['extents']
        if hdrdict.has_key('session_error'):
            nhdr.session_error = hdrdict['session_error']

        if hdrdict.has_key('regular'):
            if len(hdrdict['regular']) > 1:
                raise ValueError, "Nifti header property 'regular' has to be a single character."
            nhdr.regular = hdrdict['regular']
        if hdrdict.has_key('dim_info'):
            if len(hdrdict['dim_info']) > 1:
                raise ValueError, "Nifti header property 'dim_info' has to be a single character."
            nhdr.dim_info = hdrdict['dim_info']

        if hdrdict.has_key('dim'):
            dim = clibs.shortArray_frompointer(nhdr.dim)
            for i in range(8): dim[i] = hdrdict['dim'][i]
        if hdrdict.has_key('intent_p1'):
            nhdr.intent_p1 = hdrdict['intent_p1']
        if hdrdict.has_key('intent_p2'):
            nhdr.intent_p2 = hdrdict['intent_p2']
        if hdrdict.has_key('intent_p3'):
            nhdr.intent_p3 = hdrdict['intent_p3']
        if hdrdict.has_key('intent_code'):
            nhdr.intent_code = hdrdict['intent_code']
        if hdrdict.has_key('datatype'):
            nhdr.datatype = hdrdict['datatype']
        if hdrdict.has_key('bitpix'):
            nhdr.bitpix = hdrdict['bitpix']
        if hdrdict.has_key('slice_start'):
            nhdr.slice_start = hdrdict['slice_start']
        if hdrdict.has_key('pixdim'):
            pixdim = clibs.floatArray_frompointer(nhdr.pixdim)
            for i in range(8): pixdim[i] = hdrdict['pixdim'][i]
        if hdrdict.has_key('vox_offset'):
            nhdr.vox_offset = hdrdict['vox_offset']
        if hdrdict.has_key('scl_slope'):
            nhdr.scl_slope = hdrdict['scl_slope']
        if hdrdict.has_key('scl_inter'):
            nhdr.scl_inter = hdrdict['scl_inter']
        if hdrdict.has_key('slice_end'):
            nhdr.slice_end = hdrdict['slice_end']
        if hdrdict.has_key('slice_code'):
            nhdr.slice_code = hdrdict['slice_code']
        if hdrdict.has_key('xyzt_units'):
            nhdr.xyzt_units = hdrdict['xyzt_units']
        if hdrdict.has_key('cal_max'):
            nhdr.cal_max = hdrdict['cal_max']
        if hdrdict.has_key('cal_min'):
            nhdr.cal_min = hdrdict['cal_min']
        if hdrdict.has_key('slice_duration'):
            nhdr.slice_duration = hdrdict['slice_duration']
        if hdrdict.has_key('toffset'):
            nhdr.toffset = hdrdict['toffset']
        if hdrdict.has_key('glmax'):
            nhdr.glmax = hdrdict['glmax']
        if hdrdict.has_key('glmin'):
            nhdr.glmin = hdrdict['glmin']

        if hdrdict.has_key('descrip'):
            if len(hdrdict['descrip']) > 79:
                raise ValueError, "Nifti header property 'descrip' must not be longer than 79 characters."
            nhdr.descrip = hdrdict['descrip']
        if hdrdict.has_key('aux_file'):
            if len(hdrdict['aux_file']) > 23:
                raise ValueError, "Nifti header property 'aux_file' must not be longer than 23 characters."
            nhdr.aux_file = hdrdict['aux_file']

        if hdrdict.has_key('qform_code'):
            nhdr.qform_code = hdrdict['qform_code']

        if hdrdict.has_key('sform_code'):
            nhdr.sform_code = hdrdict['sform_code']

        if hdrdict.has_key('quatern'):
            if not len(hdrdict['quatern']) == 3:
                raise ValueError, "Nifti header property 'quatern' must be 3-tuple of floats."
            
            nhdr.quatern_b = hdrdict['quatern'][0]
            nhdr.quatern_c = hdrdict['quatern'][1]
            nhdr.quatern_d = hdrdict['quatern'][2]

        if hdrdict.has_key('qoffset'):
            if not len(hdrdict['qoffset']) == 3:
                raise ValueError, "Nifti header property 'qoffset' must be 3-tuple of floats."
            
            nhdr.qoffset_x = hdrdict['qoffset'][0]
            nhdr.qoffset_y = hdrdict['qoffset'][1]
            nhdr.qoffset_z = hdrdict['qoffset'][2]

        if hdrdict.has_key('sform'):
            if not hdrdict['sform'].shape == (4,4):
                raise ValueError, "Nifti header property 'sform' must be 4x4 matrix."

            srow_x = clibs.floatArray_frompointer(nhdr.srow_x)
            for i in range(4): srow_x[i] = hdrdict['sform'][0][i]
            srow_y = clibs.floatArray_frompointer(nhdr.srow_y)
            for i in range(4): srow_y[i] = hdrdict['sform'][1][i]
            srow_z = clibs.floatArray_frompointer(nhdr.srow_z)
            for i in range(4): srow_z[i] = hdrdict['sform'][2][i]

        if hdrdict.has_key('intent_name'):
            if len(hdrdict['intent_name']) > 15:
                raise ValueError, "Nifti header property 'intent_name' must not be longer than 15 characters."
            nhdr.intent_name = hdrdict['intent_name']
        
        if hdrdict.has_key('magic'):
            if hdrdict['magic'] != 'ni1' and hdrdict['magic'] != 'n+1':
                raise ValueError, "Nifti header property 'magic' must be 'ni1' or 'n+1'."
            nhdr.magic = hdrdict['magic']


    def __init__(self, source, load=False, header = {} ):
        """ Create a Niftifile object.

        This method decides whether to load a nifti image from file or create
        one from array data, depending on the datatype of 'source'. If source 
        is a string, it is assumed to be a filename and an attempt will be made
        to open the corresponding niftifile. If 'load' is set to True the image 
        data will be loaded into memory.

        If 'source' is a numpy array the array data will be used for the to be 
        created nifti image and a matching nifti header is generated. Additonal
        header data might be supplied in a dictionary. However, dimensionality
        and datatype are determined from the numpy array and not taken from 
        a header dictionary.

        If an object of a different type is supplied as 'source' as ValueError 
        exception will be thrown.
        """

        self.__nimg = None

        if type( source ) == numpy.ndarray:
            self.__newFromArray( source, header )
        elif type ( source ) == str:
            self.__newFromFile( source, load )
        else:
            raise ValueError, "Unsupported source type. Only NumPy arrays and filename string are supported."

        
    def __del__(self):
        self.__close()


    def __close(self):
        """Close the file and free all unnecessary memory.
        """
        if self.__nimg:
            clibs.nifti_image_free(self.__nimg)
            self.__nimg = None


    def __newFromArray(self, data, hdr = {}):
        """ Create a nifti image struct from a numpy array and optional header
        data.
        """

        # check array
        if len(data.shape) > 7:
            raise ValueError, "NIfTI does not support data with more than 7 dimensions."
        
        # create template nifti header struct
        niptr = clibs.nifti_simple_init_nim()
        nhdr = clibs.nifti_convert_nim2nhdr(niptr)
        
        # intermediate cleanup
        clibs.nifti_image_free(niptr)

        # convert virgin nifti header to dict to merge properties
        # with supplied information and array properties
        hdic = NiftiFile.nhdr2dict(nhdr)

        # copy data from supplied header dict
        for k, v in hdr.iteritems():
            hdic[k] = v

        # finally set header data that is determined by the data array
        # convert numpy to nifti datatype
        hdic['datatype'] = self.numpydtype2niftidtype(data)
        
        # set number of dims
        hdic['dim'][0] = len(data.shape)
        
        # set size of each dim (and reverse the order to match nifti format
        # requirements)
        for i, s in enumerate(data.shape):
            hdic['dim'][len(data.shape)-i] = s

        # set magic field to mark as nifti file
        hdic['magic'] = 'n+1'

        # update nifti header with information from dict
        NiftiFile.updateNiftiHeaderFromDict(nhdr, hdic)
        
        # make clean table
        self.__close()

        # convert nifti header to nifti image struct
        self.__nimg = clibs.nifti_convert_nhdr2nim(nhdr, 'pynifti_none')
        
        if not self.__nimg:
            raise RuntimeError, "Could not create nifti image structure."
        
        # kill filename for nifti images from arrays
        self.__nimg.fname = ''
        self.__nimg.iname = ''

        # allocate memory for image data
        if not clibs.allocateImageMemory(self.__nimg):
            raise RuntimeError, "Could not allocate memory for image data."

        # assign data
        self.asarray()[:] = data[:]


    def __newFromFile(self, filename, load=False):
        """Open a NIfTI file.

        If there is already an open file it is closed first. If 'load' is True
        the image data is loaded into memory.
        """
        self.__close()
        self.__nimg = clibs.nifti_image_read( filename, int(load) )

        if not self.__nimg:
            raise RuntimeError, "Error while opening nifti header."
        
        if load:
            self.load()

    
    def save(self, filename=None, filetype='NIFTI'):
        """Save the image.

        If the image was created using array data (not loaded from a file) one
        has to specify a filename. 
        
        Calling save() without a specified filename on a NiftiFile loaded from 
        a file, will overwrite the original file.

        If a filename is specified, it will be made an attempt to guess the 
        corresponding filetype. A filename has to be the name of the 
        corresponding headerfile -- including the filename extension (.hdr,
        .nii, .hdr.gz or .nii.gz). In ambigous cases (.hdr might stand for 
        ANALYZE or uncompressed NIFTI file pairs) one can use the filetype 
        parameter to choose a certain type. If no filetype parameter is 
        specified NIfTI files will be written by default.

        If filename is only the basefilename (i.e. does not have a valid 
        extension of NIfTI/ANALYZE header files '.nii' is appended 
        automatically and a NIfTI single file will be written.

        If not yet done already, the image data will be loaded into memory 
        before saving the file.

        Warning: There will be no exception if writing fails for any reason, 
        as the underlying function nifti_write_hdr_img() from libniftiio does
        not provide any feedback. Suggestions for improvements are appreciated.
        """

        # If image data is not yet loaded, do it now.
        # It is important to do it already here, because nifti_image_load
        # depends on the correct filename set in the nifti_image struct
        # and this will be modified in this function!
        if not self.__haveImageData():
            self.load()

        # update header information
        self.updateCalMinMax()

        # saving for the first time?
        if not self.filename or filename:
            if not filename:
                raise ValueError, "When saving an image for the first time a filename has to be specified."
            

            # check for valid filetype specifier
            if not filetype in self.filetypes:
                raise ValueError, \
                    "Unknown filetype '%s'. Known filetypes are: %s" % (filetype, ' '.join(nifti_filetype_ids))

            base, ext = NiftiFile.splitFilename(filename)

            # if no extension default to nifti single files
            if ext == '': ext = 'nii'

            # Determine the filetype and set header and image filename 
            # appropriately. If the filename extension is ambiguous the 
            # filetype setting is used to determine the intended format.

            # nifti single files are easy
            if ext == 'nii.gz' or ext == 'nii':
                self.__nimg.fname = base + '.' + ext
                self.__nimg.iname = base + '.' + ext
                self.__nimg.nifti_type = clibs.NIFTI_FTYPE_NIFTI1_1
            # uncompressed file pairs
            elif ext == 'hdr':
                self.__nimg.fname = base + '.hdr'
                self.__nimg.iname = base + '.img'
                if filetype.startswith('NIFTI'):
                    self.__nimg.nifti_type = clibs.NIFTI_FTYPE_NIFTI1_2
                else:
                    self.__nimg.nifti_type = clibs.NIFTI_FTYPE_ANALYZE
            # compressed file pairs
            elif ext == 'hdr.gz':
                self.__nimg.fname = base + '.hdr.gz'
                self.__nimg.iname = base + '.img.gz'
                if filetype.startswith('NIFTI'):
                    self.__nimg.nifti_type = clibs.NIFTI_FTYPE_NIFTI1_2
                else:
                    self.__nimg.nifti_type = clibs.NIFTI_FTYPE_ANALYZE
            else:
                raise RuntimeError, "Unhandled filetype."
        
        # now save it
        clibs.nifti_image_write_hdr_img(self.__nimg, 1, 'wb')


    def __haveImageData(self):
        """Returns true if the image data was loaded into memory.
        or False if not.

        See: load(), unload()
        """
        self.__ensureNiftiImage()

        if self.__nimg.data:
            return True
        else:
            return False


    def load(self):
        """Load the image data into memory.

        It is save to call this method several times.
        """
        self.__ensureNiftiImage()

        if clibs.nifti_image_load( self.__nimg ) < 0:
            raise RuntimeError, "Unable to load image data." 
    

    def unload(self):
        """Unload image data and free allocated memory.
        """
        self.__ensureNiftiImage()
        
        clibs.nifti_image_unload(self.__nimg)
    

    def getDataArray(self):
        """ Calls asarray(False) to return the NIfTI image data wrapped into
        a NumPy array. 

        Attention: The array shares the data with the NiftiFile object. Any 
        resize operation or datatype conversion will most likely result in a
        fatal error. If you need to perform such things, get a copy
        of the image data by using asarray(copy=True).
        """
        return self.asarray(False)
    

    def asarray(self, copy = True):
        """Convert the image data into a multidimensional array.

        Attention: If copy == False (the default) the array only wraps 
        the image data. Any modification done to the array is also done 
        to the image data. 
        
        If copy is true the array contains a copy of the image data.

        Changing the shape, size or data of a wrapping array is not supported
        and will most likely result in a fatal error. If you want to data 
        anything else to the data but reading or simple value assignment
        use a copy of the data by setting the copy flag. Later you can convert
        the modified data array into a NIfTi file again.
        """
        if not self.__haveImageData():
            self.load()

        a = clibs.wrapImageDataWithArray(self.__nimg)

        if copy:
            return a.copy()
        else:
            return a


    def __ensureNiftiImage(self):
        """Check whether a NIfTI image is present.

        Returns True if there is a nifti image file structure or False otherwise.
        One can create a file structure by calling open().
        """
        if not self.__nimg:
            raise RuntimeError, "There is no NIfTI image file structure."

    
    def updateCalMinMax(self):
        """ Update the image data maximum and minimum value in the
        nifti header.
        """
        self.__nimg.cal_max = float(self.data.max())
        self.__nimg.cal_min = float(self.data.min())
        
    def getVoxDims(self):
        """ Returns a 3-tuple a voxel dimensions/size in (x,y,z).
        """
        return ( self.__nimg.dx, self.__nimg.dy, self.__nimg.dz )


    def setVoxDims(self, value):
        """ Set voxel dimensions/size.

        This method takes a 3-tuple of floats as argument. The qform matrix 
        and its inverse will be recalculated automatically.
        """
        if len(value) != 3:
            raise ValueError, 'Requires 3-tuple.'

        self.__nimg.dx = float(value[0])
        self.__nimg.dy = float(value[1])
        self.__nimg.dz = float(value[2])

        self.updateQFormFromQuaternion()


    def getHeader(self):
        """ Returns the header data of the nifti image in a dictionary. 
        """
        h = {}
        
        # Convert nifti_image struct into nifti1 header struct.
        # This get us all data that will actually make it into a
        # NIfTI file.
        nhdr = clibs.nifti_convert_nim2nhdr(self.__nimg)

        return NiftiFile.nhdr2dict(nhdr)

    def updateHeader(self, hdrdict):
        """ Update NIfTI header information.

        Updated header data is read from the supplied dictionary. One cannot
        modify dimensionality and datatype of the image data. If such 
        information is present in the header dictionary it is removed before
        the update. If such modifications are necessary one has to convert the
        image data into a separate array ( NiftiFile.assarray(copy=True) ) and
        perform resize and data manipulations on this array. When finished,
        the array can be converted into a nifti file by calling the NiftiFile 
        constructor with the modified array as 'source' and the nifti header 
        of the original NiftiFile object as 'header'.
        
        It is save to call this method with and without loaded image data.

        The actual update is done by NiftiFile.updateNiftiHeaderFromDict().
        """
        # rebuild nifti header from current image struct
        nhdr = clibs.nifti_convert_nim2nhdr(self.__nimg)

        # remove settings from the hdrdict that are determined by 
        # the data set and must not be modified to preserve data integrity
        if hdrdict.has_key('datatype'):
            del hdrdict['datatype']
        if hdrdict.has_key('dim'):
            del hdrdict['dim']

        # update the nifti header
        NiftiFile.updateNiftiHeaderFromDict(nhdr, hdrdict)

        # recreate nifti image struct
        new_nimg = clibs.nifti_convert_nhdr2nim(nhdr, self.filename)
        if not new_nimg:
            raise RuntimeError, "Could not recreate NIfTI image struct from updated header."
        
        # replace old image struct by new one
        # be careful with memory leak (still not checked whether successful)

        # rescue data ptr
        new_nimg.data = self.__nimg.data
        
        # and remove it from old image struct
        self.__nimg.data = None

        # to be able to call the cleanup function without lossing the data
        self.__close()

        # assign the new image struct
        self.__nimg = new_nimg


    def setSlope(self, value):
        """ Set the slope attribute in the NIfTI header.
        """
        self.__nimg.scl_slope = float(value)


    def setIntercept(self, value):
        """ Set the intercept attribute in the NIfTI header.
        """
        self.__nimg.scl_inter = float(value)

    
    def setDescription(self, value):
        """ Set the description element in the NIfTI header.

        Descriptions must not be longer than 79 characters.
        """
        if len(value) > 79:
            raise ValueError, "The NIfTI format only supports descriptions shorter than 80 chars."

        self.__nimg.descrip = value

    def getSForm(self):
        """ Returns the sform matrix.
        """
        return clibs.mat442array(self.__nimg.sto_xyz)

    def setSForm(self, m):
        """ Sets the sform matrix.
        The supplied value has to be a 4x4 matrix. The matrix elements will be 
        converted to floats. By definition the last row of the sform matrix has 
        to be (0,0,0,1). However, different values can be assigned, but will 
        not be stored when the niftifile is saved.

        The inverse sform matrix will be automatically recalculated.
        """
        if m.shape != (4,4):
            raise ValueError, "SForm matrix has to be of size 4x4."
       
        # make sure it is float
        m = m.astype('float')

        clibs.set_mat44( self.__nimg.sto_xyz,
                         m[0,0], m[0,1], m[0,2], m[0,3],
                         m[1,0], m[1,1], m[1,2], m[1,3],
                         m[2,0], m[2,1], m[2,2], m[2,3],
                         m[3,0], m[3,1], m[3,2], m[3,3] )

        # recalculate inverse 
        self.__nimg.sto_ijk = clibs.nifti_mat44_inverse( self.__nimg.sto_xyz )

    
    def getInverseSForm(self):
        """ Returns the inverse sform matrix.
        """
        return clibs.mat442array(self.__nimg.sto_ijk)


    def getQForm(self):
        """ Returns the qform matrix.
        """
        return clibs.mat442array(self.__nimg.qto_xyz)


    def getInverseQForm(self):
        """ Returns the inverse qform matrix.
        """
        return clibs.mat442array(self.__nimg.qto_ijk)


    def setQForm(self, m):
        """ Sets the qform matrix.
        The supplied value has to be a 4x4 matrix. The matrix will be converted
        to float. 
        
        The inverse qform matrix and the quaternion representation will be 
        automatically recalculated.
        """
        if m.shape != (4,4):
            raise ValueError, "QForm matrix has to be of size 4x4."
       
        # make sure it is float
        m = m.astype('float')

        clibs.set_mat44( self.__nimg.qto_xyz,
                         m[0,0], m[0,1], m[0,2], m[0,3],
                         m[1,0], m[1,1], m[1,2], m[1,3],
                         m[2,0], m[2,1], m[2,2], m[2,3],
                         m[3,0], m[3,1], m[3,2], m[3,3] )

        # recalculate inverse 
        self.__nimg.qto_ijk = clibs.nifti_mat44_inverse( self.__nimg.qto_xyz )

        # update quaternions
        ( self.__nimg.quatern_b, self.__nimg.quatern_b, self.__nimg.quatern_b,
          self.__nimg.qoffset_x, self.__nimg.qoffset_y, self.__nimg.qoffset_z,
          self.__nimg.dx, self.__nimg.dy, self.__nimg.dz,
          self.__nimg.qfac ) = clibs.nifti_mat44_to_quatern( self.__nimg.qto_xyz )


    def updateQFormFromQuaternion(self):
        """ Recalculates the qform matrix (and the inverse) from the quaternion
        representation.
        """
        # recalculate qform
        self.__nimg.qto_xyz = clibs.nifti_quatern_to_mat44 (
          self.__nimg.quatern_b, self.__nimg.quatern_b, self.__nimg.quatern_b,
          self.__nimg.qoffset_x, self.__nimg.qoffset_y, self.__nimg.qoffset_z,
          self.__nimg.dx, self.__nimg.dy, self.__nimg.dz,
          self.__nimg.qfac )


        # recalculate inverse 
        self.__nimg.qto_ijk = clibs.nifti_mat44_inverse( self.__nimg.qto_xyz )


    def setQuaternion(self, value):
        """ Set Quaternion from 3-tuple (qb, qc, qd).
        
        The qform matrix and its inverse are re-computed automatically.
        """
        if len(value) != 3:
            raise ValueError, 'Requires 3-tuple.'

        self.__nimg.quatern_b = float(value[0])
        self.__nimg.quatern_c = float(value[1])
        self.__nimg.quatern_d = float(value[2])

        self.updateQFormFromQuaternion()


    def getQuaternion(self):
        """ Returns a 3-tuple containing (qb, qc, qd).
        """
        return( ( self.__nimg.quatern_b, self.__nimg.quatern_c, self.__nimg.quatern_d ) )


    def setQOffset(self, value):
        """ Set QOffset from 3-tuple (qx, qy, qz).
        
        The qform matrix and its inverse are re-computed automatically.
        """
        if len(value) != 3:
            raise ValueError, 'Requires 3-tuple.'

        self.__nimg.qoffset_x = float(value[0])
        self.__nimg.qoffset_y = float(value[1])
        self.__nimg.qoffset_z = float(value[2])

        self.updateQFormFromQuaternion()


    def getQOffset(self):
        """ Returns a 3-tuple containing (qx, qy, qz).
        """
        return( ( self.__nimg.qoffset_x, self.__nimg.qoffset_y, self.__nimg.qoffset_z ) )


    def setQFac(self, value):
        """ Set qfac.
        
        The qform matrix and its inverse are re-computed automatically.
        """
        self.__nimg.qfac = float(value)
        self.updateQFormFromQuaternion()


    def getQOrientation(self, as_string = False):
        """ Returns to orientation of the i,j and k axis as stored in the
        qform matrix.

        By default NIfTI orientation codes are returned, but if 'as_string' is
        set to true a string representation ala 'Left-to-right' is returned 
        instead.
        """
        codes = clibs.nifti_mat44_to_orientation(self.__nimg.qto_xyz)
        if as_string:
            return [ clibs.nifti_orientation_string(i) for i in codes ]
        else:
            return codes


    def getSOrientation(self, as_string = False):
        """ Returns to orientation of the i,j and k axis as stored in the
        sform matrix.

        By default NIfTI orientation codes are returned, but if 'as_string' is
        set to true a string representation ala 'Left-to-right' is returned 
        instead.
        """
        codes = clibs.nifti_mat44_to_orientation(self.__nimg.sto_xyz)
        if as_string:
            return [ clibs.nifti_orientation_string(i) for i in codes ]
        else:
            return codes


    # class properties
    # read only
    filename =      property(fget=lambda self: self.__nimg.fname)
    nvox =          property(fget=lambda self: self.__nimg.nvox)
    max =           property(fget=lambda self: self.__nimg.cal_max)
    min =           property(fget=lambda self: self.__nimg.cal_min)
    data =          property(fget=getDataArray)
    sform_inv =     property(fget=getInverseSForm)
    qform_inv =     property(fget=getInverseQForm)

    # read and write
    slope =         property(fget=lambda self: self.__nimg.scl_slope,
                             fset=setSlope)
    intercept =     property(fget=lambda self: self.__nimg.scl_inter,
                             fset=setIntercept)
    voxdim =        property(fget=getVoxDims, fset=setVoxDims)
    description =   property(fget=lambda self: self.__nimg.descrip, 
                             fset=setDescription)
    header =        property(fget=getHeader, fset=updateHeader)
    sform =         property(fget=getSForm, fset=setSForm)
    qform =         property(fget=getQForm, fset=setQForm)
    quatern =       property(fget=getQuaternion, fset=setQuaternion)
    qoffset =       property(fget=getQOffset, fset=setQOffset)
    qfac =          property(fget=lambda self: self.__nimg.qfac, fset=setQFac)

