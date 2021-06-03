from . import star
from . import pysex
from . import quad
from os import path


class ImgCat:
    """
    Represent an individual image and its associated catalog, starlist, quads etc.
    """

    def __init__(self, filepath, hdu=0, cat=None):
        """

        :param filepath: Path to the FITS file, or alternatively just a string to identify the image.
        :type filepath: string

        :param cat: Catalog generated by SExtractor (if available -- if not, we'll make our own)
        :type cat: asciidata catalog

        :param hdu: The hdu containing the science data from which I should build the catalog.
        0 is primary. If multihdu, 1 is usually science.

        """
        self.filepath = filepath

        (imgdir, filename) = path.split(filepath)
        (common, ext) = path.splitext(filename)
        self.name = common

        self.hdu = hdu
        self.cat = cat
        self.starlist = []
        self.mindist = 0.0
        self.xlim = (0.0, 0.0)  # Will be set using the catalog -- no need for the FITS image.
        self.ylim = (0.0, 0.0)

        self.quadlist = []
        self.quadlevel = 0  # encodes what kind of quads have already been computed

    def __str__(self):
        return "%20s: approx %4i x %4i, %4i stars, %4i quads, quadlevel %i" % (path.basename(self.filepath),
                                                                               self.xlim[1] - self.xlim[0],
                                                                               self.ylim[1] - self.ylim[0],
                                                                               len(self.starlist), len(self.quadlist),
                                                                               self.quadlevel)

    def makecat(self, rerun=True, keepcat=False, verbose=True, polarMode=None, camera=None):
        self.cat = pysex.run(self.filepath, conf_args={'DETECT_THRESH': 3.0, 'ANALYSIS_THRESH': 3.0,
                                                       'DETECT_MINAREA': 10, 'PIXEL_SCALE': 1.0, 'SEEING_FWHM': 2.0,
                                                       "FILTER": "Y", 'VERBOSE_TYPE': 'NORMAL' if verbose else 'QUIET'},
                             params=['NUMBER', 'X_IMAGE', 'Y_IMAGE', 'FLUX_AUTO', 'FWHM_IMAGE', 'FLAGS', 'ELONGATION'],
                             rerun=rerun, keepcat=keepcat, catdir="alipy_cats", polarMode=polarMode, camera=camera)

    def makestarlist(self, skipsaturated=False, n=200, verbose=True):
        if self.cat:
            if skipsaturated:
                maxflag = 3
            else:
                maxflag = 7
            self.starlist = star.sortstarlistbyflux(star.readsexcat(self.cat, hdu=self.hdu, maxflag=maxflag,
                                                                    verbose=verbose))[:n]
            (xmin, xmax, ymin, ymax) = star.area(self.starlist, border=0.01)
            self.xlim = (xmin, xmax)
            self.ylim = (ymin, ymax)

            # Given this starlists, what is a good minimal distance for stars in quads ?
            self.mindist = min(min(xmax - xmin, ymax - ymin) / 10.0, 30.0)
            return 0

        else:
            return 1

    def makemorequads(self, verbose=True):
        """
        We add more quads, following the quadlevel.
        """
        # if not add:
        #    self.quadlist = []
        if verbose:
            print("Making more quads, from quadlevel %i ..." % self.quadlevel)
        if self.quadlevel == 0:
            self.quadlist.extend(quad.makequads1(self.starlist, n=7, d=self.mindist, verbose=verbose))
        elif self.quadlevel == 1:
            self.quadlist.extend(quad.makequads2(self.starlist, f=3, n=5, d=self.mindist, verbose=verbose))
        elif self.quadlevel == 2:
            self.quadlist.extend(quad.makequads2(self.starlist, f=6, n=5, d=self.mindist, verbose=verbose))
        elif self.quadlevel == 3:
            self.quadlist.extend(quad.makequads2(self.starlist, f=12, n=5, d=self.mindist, verbose=verbose))
        elif self.quadlevel == 4:
            self.quadlist.extend(quad.makequads2(self.starlist, f=10, n=6, s=3, d=self.mindist, verbose=verbose))

        else:
            return False

        self.quadlist = quad.removeduplicates(self.quadlist, verbose=verbose)
        self.quadlevel += 1
        return True
