# ------------------------------------------------------------------------------
# Name:        cell_statistics_gdal
# Purpose:     Calculate cell statistics using GDAL
#
# Author:      Stephen Palka
#
# Created:     26/04/2017
# ------------------------------------------------------------------------------

import glob
import numpy as np
import os
import sys

from os import path

try:
    from osgeo import gdal
    from osgeo import osr
except ImportError:
    import gdal
    import osr
from scipy import stats


def cell_statistics(ras_lst, stat_type, out_dir, **kwargs):
    print("Working with rasters in:\n" + path.dirname(ras_lst[-1]))
    ras_count = len(ras_lst)
    print("Total datasets found:", ras_count)
    for ras in ras_lst:
        print(path.basename(ras))

    # Get the last raster from the list
    base_ras = ras_lst[-1]

    # Open dataset in Gdal
    gras = gdal.Open(base_ras)

    # Get descriptive attributes of gras object
    proj = gras.GetProjection()
    trans = gras.GetGeoTransform()
    no_data = gras.GetRasterBand(1).GetNoDataValue()
    cols = gras.RasterXSize
    rows = gras.RasterYSize
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromWkt(proj)

    # Print descriptive information of gras object
    print("Basing information on:", path.basename(base_ras))
    print("projection:\n" + spatial_ref.ExportToPrettyWkt())
    print("affine transformation coefficients:", trans)
    print("no data value:", no_data)
    print("cols/rows:", cols, rows)

    # Insert all rasters into a numpy array.
    print("\nInserting rasters into array...")
    stor_arr = np.zeros((ras_count, rows, cols))
    for i in range(ras_count):
        stor_arr[i, :, :] = np.array(gdal.Open(ras_lst[i]).ReadAsArray())
    print("Inserted all rasters into array.")

    try:
        print("\nCalculating statistic...")

        if stat_type == "mean":
            # calculate mean along columns
            out_arr = np.mean(stor_arr, axis=0, dtype=np.float64)
            print("Calculated statistic.")
        elif stat_type == "min":
            # calculate minimum value of each column
            out_arr = np.min(stor_arr, axis=0)
            print("Calculated statistic.")
        elif stat_type == "max":
            # calculate maximum value of each column
            out_arr = np.max(stor_arr, axis=0)
            print("Calculated statistic.")
        elif stat_type == "median":
            # calculate median value of each column
            out_arr = np.median(stor_arr, axis=0)
            print("Calculated statistic.")
        elif stat_type == "rank":
            # calculate rank of the last value of each column
            # set out_array equeal to - when there are no no_data values in the
            # column, the value returned by scypy.stats.rankdata when applied
            # along the axis column
            out_arr = np.where(
                np.where(stor_arr == no_data, 1, 0).sum(0) > 0,
                0,
                np.apply_along_axis(
                    lambda a: int(stats.rankdata(a, "min")[-1]), 0, stor_arr
                ),
            )
            print("Calculated statistic.")
        elif stat_type == "trend":
            # calculate the trend of each column
            # set out_array equeal to - when there are no no_data values in the
            # column, the value returned by stats.lineregress when applied
            # along the axis column
            out_arr = np.where(
                np.where(stor_arr == no_data, 1, 0).sum(0) > 0,
                no_data,
                np.apply_along_axis(
                    lambda a: stats.linregress(list(range(0, len(a))), a)[0],
                    0,
                    stor_arr,
                ),
            )
            print("Calculated statistic.")
        else:
            raise ValueError(
                "WARNING: Statistic type provided is not valid.\n"
                "Please provide a valid stsatistic type."
            )
    except ValueError as error:
        print(error.args[0])
        sys.exit()

    try:
        print("\nSaving output raster...")

        # Check output directory exists
        if not path.isdir(out_dir):
            raise NotADirectoryError(
                "WARNING: Provided output directory does not exist.\n"
                "Please provide a valid output directory."
            )

        # Check if the user specified a filename for the output.
        if "flnm" in kwargs:
            out_ras_flnm = kwargs["flnm"]
        else:
            out_ras_flnm = "cell_stat_{}".format(stat_type)

        # Set the output raster extension. This will be the same as
        # the input raster extension.
        out_ras_ext = base_ras.split(os.extsep, 1)[-1]

        out_ras = out_dir + os.sep + out_ras_flnm + os.extsep + out_ras_ext
        out_driver = gras.GetDriver()
        if stat_type == "rank":
            out_dep = gdal.GDT_Byte
        else:
            out_dep = gdal.GDT_Float32
        out_ras = out_driver.Create(out_ras, cols, rows, 1, out_dep)
        out_ras.SetGeoTransform(trans)
        out_ras.SetProjection(proj)
        out_ras.GetRasterBand(1).WriteArray(out_arr)
        out_ras.FlushCache()
        if stat_type == "rank":
            out_no_data = 0
        else:
            out_no_data = no_data
        out_ras.GetRasterBand(1).SetNoDataValue(out_no_data)
        print("Saved output raster.")
    except NotADirectoryError as error:
        print(error.args[0])
        sys.exit()


def main():
    # Set path to directory containing rasters to process.
    in_dir = r""

    # Create list of rasters located in input directory.
    # Here you can change the file type to look for or slice the
    # list to only return certain rasters.
    ras_lst = sorted(glob.glob(in_dir + os.sep + "*.tif"))

    # Set the statistic type
    # available statistics: mean, max, min, median, rank, trend
    stat_type = "trend"

    # Set path for output to be written to.
    out_dir = r""

    # optional kwarg: flnm
    # ex. flnm='my_file_name'
    # not e: do not add extionsion to flnm
    # note: no data value will be the same as input file except for rank where
    # the output is saved as 8bit unsigned type and has a no data value of 0
    # note: output raster extension will be the same as the input type
    cell_statistics(ras_lst, stat_type, out_dir)


if __name__ == "__main__":
    main()
