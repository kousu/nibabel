# emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the NiBabel package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os

from .pkg_info import __version__
from .info import long_description as __doc__
__doc__ += """
Quickstart
==========

::

   import nibabel as nib

   img1 = nib.load('my_file.nii')
   img2 = nib.load('other_file.nii.gz')
   img3 = nib.load('spm_file.img')

   data = img1.get_fdata()
   affine = img1.affine

   print(img1)

   nib.save(img1, 'my_file_copy.nii.gz')

   new_image = nib.Nifti1Image(data, affine)
   nib.save(new_image, 'new_image.nii.gz')

For more detailed information see the :ref:`manual`.
"""

# module imports
from . import analyze as ana
from . import spm99analyze as spm99
from . import spm2analyze as spm2
from . import nifti1 as ni1
from . import ecat
# object imports
from .fileholders import FileHolder, FileHolderError
from .loadsave import load, save
from .arrayproxy import is_proxy
from .analyze import AnalyzeHeader, AnalyzeImage
from .spm99analyze import Spm99AnalyzeHeader, Spm99AnalyzeImage
from .spm2analyze import Spm2AnalyzeHeader, Spm2AnalyzeImage
from .nifti1 import Nifti1Header, Nifti1Image, Nifti1Pair
from .nifti2 import Nifti2Header, Nifti2Image, Nifti2Pair
from .minc1 import Minc1Image
from .minc2 import Minc2Image
from .cifti2 import Cifti2Header, Cifti2Image
from .gifti import GiftiImage
from .minc1 import MincImage
from .freesurfer import MGHImage
from .funcs import (squeeze_image, concat_images, four_to_three,
                    as_closest_canonical)
from .orientations import (io_orientation, orientation_affine,
                           flip_axis, OrientationError,
                           apply_orientation, aff2axcodes)
from .imageclasses import class_map, ext_map, all_image_classes
from . import mriutils
from . import streamlines
from . import viewers

from .pkg_info import get_pkg_info as _get_pkg_info


def get_info():
    return _get_pkg_info(os.path.dirname(__file__))


def test(label=None, verbose=1, extra_argv=None,
         doctests=False, coverage=False, raise_warnings=None,
         timer=False):
    """
    Run tests for nibabel using pytest

    The protocol mimics the ``numpy.testing.NoseTester.test()``.
    Not all features are currently implemented.

    Parameters
    ----------
    label : None
        Unused.
    verbose: int, optional
        Verbosity value for test outputs. Positive values increase verbosity, and
        negative values decrease it. Default is 1.
    extra_argv : list, optional
        List with any extra arguments to pass to pytest.
    doctests: bool, optional
        If True, run doctests in module. Default is False.
    coverage: bool, optional
        If True, report coverage of NumPy code. Default is False.
        (This requires the
        `coverage module <https://nedbatchelder.com/code/modules/coveragehtml>`_).
    raise_warnings : None
        Unused.
    timer : False
        Unused.

    Returns
    -------
    code : ExitCode
        Returns the result of running the tests as a ``pytest.ExitCode`` enum
    """
    import pytest
    args = []

    if label is not None:
        raise NotImplementedError("Labels cannot be set at present")

    verbose = int(verbose)
    if verbose > 0:
        args.append("-" + "v" * verbose)
    elif verbose < 0:
        args.append("-" + "q" * -verbose)

    if extra_argv:
        args.extend(extra_argv)
    if doctests:
        args.append("--doctest-modules")
    if coverage:
        args.extend(["--cov", "nibabel"])
    if raise_warnings is not None:
        raise NotImplementedError("Warning filters are not implemented")
    if timer:
        raise NotImplementedError("Timing is not implemented")

    args.extend(["--pyargs", "nibabel"])

    return pytest.main(args=args)


def bench(label=None, verbose=1, extra_argv=None):
    """
    Run benchmarks for nibabel using pytest

    The protocol mimics the ``numpy.testing.NoseTester.bench()``.
    Not all features are currently implemented.

    Parameters
    ----------
    label : None
        Unused.
    verbose: int, optional
        Verbosity value for test outputs. Positive values increase verbosity, and
        negative values decrease it. Default is 1.
    extra_argv : list, optional
        List with any extra arguments to pass to pytest.

    Returns
    -------
    code : ExitCode
        Returns the result of running the tests as a ``pytest.ExitCode`` enum
    """
    from pkg_resources import resource_filename
    config = resource_filename("nibabel", "benchmarks/pytest.benchmark.ini")
    args = []
    if extra_argv is not None:
        args.extend(extra_argv)
    args.extend(["-c", config])
    return test(label, verbose, extra_argv=args)
