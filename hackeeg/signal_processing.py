# Python 3.12
# 2024-02-06

# Leonardo Fortaleza
# leonardo.fortaleza@csmc-scms.ca
# leonardo.fortaleza@mail.mcgill.ca

"""
 Description:
        Module for performing preliminary signal processing on Pandas DataFrames from TIMS.

Functions::

        filter_signals : 

Written by: Leonardo Fortaleza
"""
# Standard library imports
# import datetime
# import os
# import os.path
from pathlib import Path
# import re
import sys
# from contextlib import redirect_stderr
# import io

# Third party imports
from scipy import signal
from scipy.ndimage import median_filter
# from natsort import natsorted
import numpy as np
import pandas as pd
# from tqdm import tqdm # when using terminal
from tqdm.notebook import tqdm # when using Jupyter Notebook

sys.path.append("".join((str(Path(__file__).resolve().parents[1]), "/build")))

# Local imports
from hackeeg.matlab_bandpass import matlab_bandpass

# def filter_signals(df, pattern = '^ch\\d+', filter_function='matlab_bandpass', use_filtfilt = False):
#     """Apply bandpass filter to uwb system raw signals.

#     Uses matlab_bandpass to emulate MATLAB's bandpass function.

#     Parameters
#     ----------
#     df : Pandas df
#         input DataFrame with UWB data.
#     pattern : str, optional
#         regex pattern to filter columns, by default '^ch\d+' (provides mV channel data only)
#     filter_function : function, optional
#         function to use as filter, by default matlab_bandpass

#     Returns
#     -------
#     Pandas df
#         output DataFrame with UWB data including filtered signal
#     """
#     # Filter columns based on the regex pattern
#     columns = df.columns[df.columns.str.match(pattern)]

#     f_low = df.loc[:, "f_low"].unique()[0]
#     f_high = df.loc[:, "f_high"].unique()[0]
#     samp_rate = df.loc[:, "samp_rate"].unique()[0]

#     for col in columns: # performs routine for each column
#         # first extracts data to numpy array of shape (# of samples, # of pairs)
#         # IMPORTANT: np.reshape and later np.flatten need to use Fortran order ('F'), otherwise signals get mixed up
#         x = df[col].to_numpy(dtype = np.float64, copy = True).reshape(df[col].count() // df.pair.nunique(), df.pair.nunique(), order = 'F')
#         if use_filtfilt:
#             rd = filter_function(x,
#                                 fpass = [f_low, f_high],
#                                 fs = samp_rate,
#                                 use_filtfilt = True)
#             rd = signal.sosfiltfilt(filter_function, x, axis = 0)
#         else:
#             rd = filter_function(x,
#                                 fpass = [f_low, f_high],
#                                 fs = samp_rate)

#         data = rd.flatten(order = 'F')

#         df.loc[:, col] = data

#     return df

def bandpass_filter_signals(df, pattern = '^ch\\d+', start_pt = None, nSamples = 1000, fpass = (100,2000)):
    """Apply MATLAB bandpass filter to uwb system raw signals, with optional prior windowing of samples.

    Uses scipy.ndimage.median_filter to perform median filtering.

    Attention: if start_pt and nSamples are used to window, the output DataFrame has dropped unused rows.

    Parameters
    ----------
    df : Pandas df
        input DataFrame with UWB data.
    pattern : str, optional
        regex pattern to filter columns, by default '^ch\d+' (provides mV channel data only)
    start_pt : int, optional
        initial sample for optional signal windowing, by default None
    nSamples : int, optional
        number of samples for optional signal windowing, by default 1000
        used only if start_pt is not None.
    kernel_size : int, optional
        size of the median filter, by default 50

    Returns
    -------
    Pandas df
        output DataFrame with UWB data including median filtered signal
        Note: if start_pt and nSamples are used to window, the output DataFrame has dropped unused rows.
    """
    speeds = [250, 500, 1000, 2000, 4000, 8000, 16000]
    avg_sample_rate = df.avg_sample_rate.unique()
    # find fs within speeds nearest to avg_sample_rate:
    fs = min(speeds, key = lambda x: abs(x- avg_sample_rate))

    numpy_array = extract_data(df, pattern, start_pt, nSamples)

    # Apply median filter to the numpy array
    filtered = matlab_bandpass(numpy_array, fpass=fpass, fs=fs)

    return filtered

def medfilter_signals(df, pattern = '^ch\\d+', start_pt = None, nSamples = 1000, kernel_size = 50):
    """Apply median filter to uwb system raw signals, with optional prior windowing of samples.

    Uses scipy.ndimage.median_filter to perform median filtering.

    Attention: if start_pt and nSamples are used to window, the output DataFrame has dropped unused rows.

    Parameters
    ----------
    df : Pandas df
        input DataFrame with UWB data.
    pattern : str, optional
        regex pattern to filter columns, by default '^ch\d+' (provides mV channel data only)
    start_pt : int, optional
        initial sample for optional signal windowing, by default None
    nSamples : int, optional
        number of samples for optional signal windowing, by default 1000
        used only if start_pt is not None.
    kernel_size : int, optional
        size of the median filter, by default 50

    Returns
    -------
    Pandas df
        output DataFrame with UWB data including median filtered signal
        Note: if start_pt and nSamples are used to window, the output DataFrame has dropped unused rows.
    """
    numpy_array = extract_data(df, pattern, start_pt, nSamples)

    # Apply median filter to the numpy array
    med_filtered = median_filter(numpy_array, size = kernel_size)

    return med_filtered

# def filter_signals(df, input_col_names = ['raw_signal'], output_col_names = ['signal'], start_pt = None, nSamples = 1000, detrend = True):
#     """Apply bandpass and detrend filters to uwb system raw signals, with optional prior windowing of samples.

#     Uses matlab_bandpass to emulate MATLAB's bandpass function. Detrend is performed with scipy.signal.detrend(x, type = 'linear').

#     Attention: if start_pt and nSamples are used to window, the output DataFrame has dropped unused rows.

#     Attempt to optimize function.

#     Parameters
#     ----------
#     df : Pandas df
#         input DataFrame with UWB data.
#     input_col_names : list, optional
#         input column names to filter, by default ['raw_signal']
#     output_col_names : list, optional
#         output column names for filtered signal, by default ['signal']
#         IndexError occurs if len(output_col_names) ~= len(input_col_names).
#     start_pt : int, optional
#         initial sample for optional signal windowing, by default None
#     nSamples : int, optional
#         number of samples for optional signal windowing, by default 1000
#         used only if start_pt is not None.
#     detrend : bool, optional
#         set to False to only apply bandpass filter, skipping subsequent linear detrending, by default True

#     Returns
#     -------
#     Pandas df
#         output DataFrame with UWB data including filtered signal
#         Note: if start_pt and nSamples are used to window, the output DataFrame has dropped unused rows.
#     """
#     if (start_pt is not None):
#         df = df.loc[df.samples.between(start_pt, start_pt + nSamples, inclusive=True)]

#     f_low = df.loc[:, "f_low"].unique()[0]
#     f_high = df.loc[:, "f_high"].unique()[0]
#     samp_rate = df.loc[:, "samp_rate"].unique()[0]

#     for i, col in enumerate(input_col_names): # performs routine for each input column
#         # first extracts data to numpy array of shape (# of samples, # of pairs)
#         # IMPORTANT: np.reshape and later np.flatten need to use Fortran order ('F'), otherwise signals get mixed up
#         x = df[col].to_numpy(dtype = np.float64, copy = True).reshape(df[col].count() // df.pair.nunique(), df.pair.nunique(), order = 'F')
#         rd = matlab_bandpass(x,
#                                 fpass = [f_low, f_high],
#                                 fs = samp_rate)

#         if detrend:
#             data = signal.detrend(rd, axis = 0, type = 'linear')
#             data = data.flatten(order = 'F')
#         else:
#             data = rd.flatten(order = 'F')

#         try:
#             df.loc[:, output_col_names[i]] = data
#         except IndexError:
#             tqdm.write("IndexError: output_col_names index does not match input_col_names!")
#             return -1

#     return df

def extract_data(df, pattern = '^ch\d+', start_pt = None, nSamples = 1000, return_cols = False):
    """Extracts data from Pandas DataFrame, with optional prior windowing of samples.

    Attention: if start_pt and nSamples are used to window, the output DataFrame has dropped unused rows.

    Parameters
    ----------
    df : Pandas df
        input DataFrame with UWB data.
    pattern : str, optional
        regex pattern to filter columns, by default '^ch\d+' (provides mV channel data only)
    start_pt : int, optional
        initial sample for optional signal windowing, by default None
    nSamples : int, optional
        number of samples for optional signal windowing, by default 1000
        used only if start_pt is not None.
    return_cols : bool, optional
        set to True to return column names, by default False

    Returns
    -------
    np.array
        output numpy array with selected data
        Note: if start_pt and nSamples are used to window, the output has dropped unused rows.
    columns: list of str, optional
        list of column names, returned only if return_cols is True
    """

    # Filter columns based on the regex pattern
    columns = df.columns[df.columns.str.match(pattern)]

    if (start_pt is not None):
        df = df.loc[df.sample_number.between(start_pt, start_pt + nSamples, inclusive=True)]

    # Convert the filtered dataframe to a numpy array
    numpy_array = df[columns].to_numpy(copy=True)

    if return_cols:
        return numpy_array, columns
    else:
        return numpy_array