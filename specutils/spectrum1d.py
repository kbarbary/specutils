# Licensed under a 3-clause BSD style license - see LICENSE.rst
# This module implements the Spectrum1D class.

from __future__ import print_function, division

__all__ = ['Spectrum1D', 'spec_operation']

from astropy import log
from astropy.nddata import NDData

import numpy as np


class Spectrum1D(NDData):
    """A subclass of `NDData` for a one dimensional spectrum in Astropy.
    
    This class inherits all the base class functionality from the NDData class
    and is communicative with other Spectrum1D objects in ways which make sense.
    """
    
    
    @classmethod
    def from_array(cls, disp, flux, error=None, mask=None, flags=None, meta=None,
                   units=None, copy=True):
        """Initialize `Spectrum1D`-object from two `numpy.ndarray` objects
        
        Parameters:
        -----------
        disp : `~numpy.ndarray`
            The dispersion for the Spectrum (i.e. an array of wavelength points).
        
        flux : `~numpy.ndarray`
            The flux level for each wavelength point. Should have the same length
            as `disp`.

        error : `~astropy.nddata.NDError`, optional
            Errors on the data. 

        mask : `~numpy.ndarray`, optional
            Mask for the data, given as a boolean Numpy array with a shape
            matching that of the data. The values should be ``False`` where the
            data is *valid* and ``True`` when it is not (as for Numpy masked
            arrays).

        flags : `~numpy.ndarray` or `~astropy.nddata.FlagCollection`, optional
            Flags giving information about each pixel. These can be specified
            either as a Numpy array of any type with a shape matching that of the
            data, or as a `~astropy.nddata.FlagCollection` instance which has a
            shape matching that of the data. 

        meta : `dict`-like object, optional
            Metadata for this object. "Metadata here means all information that
            is included with this object but not part of any other attribute
            of this particular object. e.g., creation date, unique identifier,
            simulation parameters, exposure time, telescope name, etc.

        units : undefined, optional
            The units of the data. See `~NDData` for more current information.

        copy : bool, optional
            If True, the array will be *copied* from the provided `data`,
            otherwise it will be referenced if possible (see `numpy.array` :attr:`copy`
            argument for details).
        
        Raises
        ------
        ValueError
            If the `disp` and `flux` arrays cannot be broadcast (e.g. their shapes
            do not match), or the input arrays are not one dimensional.

        """
        
        if disp.ndim != 1 or disp.shape != flux.shape:
            raise ValueError("disp and flux need to be one-dimensional Numpy arrays with the same shape")
            
        return cls(data=flux, wcs=disp, *args, **kwargs)
    
    @classmethod
    def from_table(cls, table, error=None, mask=None, disp_col='disp', flux_col='flux'):
        flux = table[flux_col]
        disp = table[disp_col]
        return cls(data=flux, wcs=disp, error=error, mask=mask)
        
    
    
    @classmethod
    def from_ascii(cls, filename, error=None, mask=None, dtype=np.float, comments='#',
                   delimiter=None, converters=None, skiprows=0,
                   usecols=None):
        raw_data = np.loadtxt(filename, dtype=dtype, comments=comments,
                   delimiter=delimiter, converters=converters,
                   skiprows=skiprows, usecols=usecols, ndmin=2)
    
        if raw_data.shape[1] != 2:
            raise ValueError('data contained in filename must have exactly two columns')
        
        return cls(data=raw_data[:,1], wcs=raw_data[:,0], error=error, mask=mask)
        
    @classmethod
    def from_fits(cls, filename, error=None):
        """This is an example function to demonstrate how
        classmethods are a clean way to instantiate Spectrum1D objects"""
        raise NotImplementedError('This function is not implemented yet')
    
    
    @property
    def flux(self):
        #returning the flux
        return self.data
        
    @flux.setter
    def flux_setter(self, flux):
        self.data = flux
    
    @property
    def disp(self):
        #returning the disp
        return self.wcs
    
        
    def interpolate(self, new_disp, kind='linear', bounds_error=True, fill_value=np.nan):
        """Interpolates onto a new wavelength grid and returns a new `Spectrum1D`-object.
        
        Parameters
        ----------
        new_disp : `~numpy.ndarray`
            The dispersion array to interpolate the flux on to.
        
        kind : `str` or `int`, optional
            Specifies the kind of interpolation as a string
            ('linear', 'nearest', 'zero', 'slinear', 'quadratic', 'cubic')
            or as an integer specifying the order of the spline interpolator
            to use. Default is 'linear'.
        
        bounds_error : `bool`, optional
            If True, an error is thrown any time interpolation is attempted on a
            dispersion point outside of the range of the original dispersion map
            (where extrapolation is necessary). If False, out of bounds values
            are assigned `fill_value`. By default, an error is raised.
            
        fill_value : `float`, optional
            If provided, then this value will be used to fill in for requested
            dispersion points outside of the original dispersion map. If not
            provided, then the default is NaN.
        
        Raises
        ------
        ImportError
            If the `SciPy interpolate interp1d <http://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.interp1d.html>`_
            function cannot be imported.
            
        Notes
        -----
        When the `Spectrum1D` class has an associated error array, the nearest
        uncertainty is taken for each new dispersion point.
        
        """
        
        # Check for SciPy availability
        try:
            from scipy import interpolate
        except ImportError as e:
            raise ImportError("Could not import interpolate from scipy; cannot"+
                              " interpolate to new dispersion map without this"+
                              " (need scipy.interpolate.interp1d)")
        
        spectrum_interp = interpolate.interp1d(self.disp,
                                               self.flux,
                                               kind=kind,
                                               bounds_error=bounds_error,
                                               fill_value=fill_value)
        
        new_flux = spectrum_interp(new_disp)
        
        # We need to perform error calculation for the new dispersion map
        if self.error is None:
            new_error = None
        else:
            # After having a short think about it, it seems reasonable to me only to
            # take the nearest uncertainty for each interpolated dispersion point
            
            new_error = interpolate.interp1d(self.disp,
                                             self.flux,
                                             kind=1, # Nearest
                                             bounds_error=bounds_error,
                                             fill_value=fill_value)
        
        # The same should also apply for masks
        if self.mask is None:
            new_mask = None
        else:
            new_mask = interpolate.interp1d(self.disp,
                                            self.flux,
                                            kind=1, # Nearest
                                            bounds_error=bounds_error,
                                            fill_value=fill_value)
            
        # As for flags it is not entirely clear to me what the best behaviour is
        # In the face of uncertainty, for the time being, I am discarding flags
        
        return self.__class__.from_array(new_disp,
                                         new_flux,
                                         error=new_error,
                                         mask=new_mask,
                                         meta=self.meta)
        
        
    def slice_dispersion(self, start=None, stop=None):
        """Slice the spectrum within a given start and end dispersion value.
        
        Parameters
        ----------
        start : `float`
            Starting slice point.
        stop : `float`
            Stopping slice point.
        
        Notes
        -----
        Often it is useful to slice out a portion of a `Spectrum1D` objects
        either by two dispersion points (e.g. two wavelengths) or by the indices
        of the dispersion/flux arrays (see `~Spectrum1D.slice_index` for this
        functionality).
        
        For example::
        
            >>> from astropy.specutils import Spectrum1D
            >>> from astropy.units import Units as unit
            >>> import numpy as np
            
            >>> dispersion = np.arange(4000, 5000, 0.12)
            >>> flux = np.random(len(dispersion))
            >>> mySpectrum = Spectrum1D.from_array(dispersion,
                                                   flux,
                                                   units=unit.Wavelength)
            
            >>> # Now say we wanted a slice near H-beta at 4861 Angstroms
            >>> hBeta = mySpectrum.slice_dispersion(4851.0, 4871.0)
            >>> hBeta
            <hBeta __repr__ #TODO>
        
        See Also
        --------
        `~Spectrum1D.slice_index`
        """
        
        # Transform the dispersion end points to index space
        start_index, stop_index = self.disp.searchsorted([start, stop])
        
        return self.slice_index(start_index, stop_index)
    
    
    def slice_index(self, start=None, stop=None):
        """Slice the spectrum within a given start and end index.
        
        Parameters
        ----------
        start : `float`
            Starting slice point.
        stop : `float`
            Stopping slice point.
        
        Notes
        -----
        Often it is useful to slice out a portion of a `Spectrum1D` objects
        either by two index points (see `~Spectrum1D.slice_dispersion`) or by
        the indices of the dispersion/flux array.
        
        See Also
        --------
        `~Spectrum1D.slice_dispersion`
        """
        
        # We need to slice the following items:
        # >> disp, flux, error, mask, and flags
        # Which are all common NDData objects, therefore I am (perhaps
        # reasonably) assuming that __slice__ will be a NDData base function
        # which we will inherit.
        
        return self.__slice__(start_index, stop_index)
        
        
        
    
    @spec_operation
    def __add__(self, operand):
        
        """Adds two spectra together, or adds finite real numbers across an entire spectrum."""
        
        return self.__class__.from_array(self.disp, self.flux + operand)
        

    @spec_operation
    def __sub__(self, operand):
        
        """Subtracts two spectra, or subtracts a finite real numbers from an entire spectrum."""
        
        return self.__class__.from_array(self.disp, self.flux - operand)
        

    @spec_operation
    def __mul__(self, operand):
        
        """Multiplies two spectra, or multiplies a finite real numbers across an entire spectrum."""
        
        return self.__class__.from_array(self.disp, self.flux * operand)
        

    @spec_operation
    def __div__(self, operand):
        
        """Divides two spectra, or divides a finite real numbers across an entire spectrum."""
        
        return self.__class__.from_array(self.disp, self.flux / operand)
        
    @spec_operation
    def __pow__(self, operand):
        
        """Performs power operations on spectra."""
        
        return self.__class__.from_array(self.disp, self.flux ** operand)
        

    def __len__(self):
        return len(self.disp)


    # Mirror functions
    
    def __radd__(self, spectrum, **kwargs):
        return self.__add__(spectrum, **kwargs)
        
    def __rsub__(self, spectrum, **kwargs):
        return self.__sub__(spectrum, **kwargs)
        
    def __rmul__(self, spectrum, **kwargs):
        return self.__mul__(spectrum, **kwargs)
            
    def __rdiv__(self, spectrum, **kwargs):
        return self.__div__(spectrum, **kwargs)
    
    def __rpow__(self, spectrum, **kwargs):
        return self.__pow__(spectrum, **kwargs)
        
        


def spec_operation(func):
    def convert_operands(self, operand):
        if isinstance(operand, self.__class__):
            if all(self.disp == operand.disp):
                return func(self, operand.flux)
            else:
                new_disp = np.union1d(self.disp, operand.disp)
                return func(self.interpolate(new_disp), operand.interpolate(new_disp).flux)

        elif np.isscalar(operand):
            return func(self, operand)
        else:
            raise ValueError("unsupported operand type(s) for operation: %s and %s" %
                             (type(self), type(operand)))
    return convert_operands
        
