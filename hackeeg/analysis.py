# Python 3.11
# 2023-10-31

# Leonardo Fortaleza
# Canadian Space Mining Corporation (CSMC) / McGill University
# leonardo.fortaleza@mail.mcgill.ca
# leonardo.fortaleza@csmc-scms.ca

import os
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
# import scienceplots
from scipy.fftpack import fft
from scipy import signal
import pandas as pd

sys.path.insert(1, str(Path(__file__).resolve().parents[1]))
# current_folder = globals()['_dh'][0]
# sys.path.insert(0, str(Path(current_folder).resolve().parents[0]))
# sys.path.insert(0, str("".join((str(current_folder.resolve().parents[0]),'/data/'))))

from hackeeg.multi_melt import multi_melt

# TODO: use lineplot/seaborn for quick_fftplot using groupby

def quick_scatterplot(df, x='sample_number', y='voltage', hue='ch', style='ch', normalization=None):
    """
    Creates a scatterplot using Seaborn library with the given dataframe and parameters.

    Parameters:
    df: pandas.DataFrame
        The dataframe to be plotted.
    x: str
        The column name to be used as the x-axis. Default is 'sample_number'.
    y: str
        The column name to be used as the y-axis. Default is 'voltage'.
    hue: str
        The column name to be used for color encoding. Default is 'ch'.
    style: str
        The column name to be used for marker style encoding. Default is 'ch'.
    normalization: {'minmax', 'zscore', None}
        The normalization method to be applied to the y-axis. Default is None.

    Returns:
    ax (matplotlib.axes._subplots.AxesSubplot): The resulting scatterplot.
    """

    if 'loff_statn' in df.columns:
        df = extract_data_from_df(df, errors='ignore')
    df = wide2long_eeg(df, value_vars_primitives=['ch','raw_ch'], value_names=['voltage','raw_voltage'],
                    id_vars = ['timestamp', 'sample_number', 'total_samples', 'total_duration', 'avg_sample_rate',
                        'gain', 'ch_unit', 'num_chs'],
                    rename_ch2int=True)

    if normalization is not None:
        df = normalize(df, column=y, method=normalization)

    ax = sns.scatterplot(data=df, x=x, y=y, hue=hue, legend='full')
    ax.set(xlabel='sample number', ylabel='voltage (mV)')
    sns.move_legend(ax, "center right", bbox_to_anchor=(1.15, 0.5), ncol=1)

    return ax

def quick_lineplot(df, x='sample_number', y='voltage', hue='ch', style='ch', normalization=None):
    """
    Plots a line plot of the given dataframe with the specified parameters.

    Parameters:
    df: pandas.DataFrame
        The dataframe to plot.
    x: str
        The column name to use for the x-axis. Defaults to 'sample_number'.
    y: str
        The column name to use for the y-axis. Defaults to 'voltage'.
    hue: str
        The column name to use for the color encoding. Defaults to 'ch'.
    style: str
        The column name to use for the style encoding. Defaults to 'ch'.
    normalization: {'minmax', 'zscore', None}, optional
        The normalization method to use. Defaults to None.

    Returns:
    ax (matplotlib.axes.Axes): The resulting lineplot.
    """

    if 'loff_statn' in df.columns:
        df = extract_data_from_df(df, errors='ignore')
    df = wide2long_eeg(df, value_vars_primitives=['ch','raw_ch'], value_names=['voltage','raw_voltage'],
                    id_vars = ['timestamp', 'sample_number', 'total_samples', 'total_duration', 'avg_sample_rate',
                        'gain', 'ch_unit', 'num_chs'],
                    rename_ch2int=True)

    if normalization is not None:
        df = normalize(df, column=y, method=normalization)

    ax = sns.lineplot(data=df, x=x, y=y, hue=hue, legend='full')
    ax.set(xlabel='sample number', ylabel='voltage (mV)')
    sns.move_legend(ax, "center right", bbox_to_anchor=(1.15, 0.5), ncol=1)

    return ax

def quick_fftplot(df, scale='dB', normalization=None, xlim=1000):
    """
    Plots the Fast Fourier Transform (FFT) of the input DataFrame.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing the EEG data.
    scale : str or float, optional
        Scale of the y-axis. If 'dB', the y-axis is in decibels. If a float, the y-axis is scaled by that factor.
        Default is 'dB'.
    normalization : {'minmax', 'zscore', None}, optional
        Method used to normalize the data. If None, no normalization is applied. Otherwise, the normalization method
        must be one of the following: 'minmax', 'zscore', 'robust', 'median'. Default is None.

    Returns:
    --------
    None
    """

    if 'loff_statn' in df.columns:
        df = extract_data_from_df(df, errors='ignore')
    df = wide2long_eeg(df, value_vars_primitives=['ch','raw_ch'], value_names=['voltage','raw_voltage'],
                    id_vars = ['timestamp', 'sample_number', 'total_samples', 'total_duration', 'avg_sample_rate',
                        'gain', 'ch_unit', 'num_chs'],
                    rename_ch2int=True)

    if normalization is not None:
        df = normalize(df, column=y, method=normalization)

    # Number of sample points
    N = df.sample_number.max()
    # sample spacing
    T = 1.0 / N

    plt.figure(figsize=(20,10))
    for i in df.ch.unique():
        yf = fft(df.loc[df.ch.eq(i), 'voltage'].values)
        xf = np.linspace(0.0, 1.0/(2.0*T), N//2)
        if scale == 'dB' or scale == 'db' or scale == 'DB':
            plt.plot(xf, 2.0/N * 20*np.log10(np.abs(yf[0:N//2])), label=f'ch{i:02d}')
        elif isinstance(scale, (int, float, complex)):
            plt.plot(xf, scale*2.0/N * np.abs(yf[0:N//2]), label=f'ch{i:02d}')
        else:
            plt.plot(xf, 2.0/N * np.abs(yf[0:N//2]), label=f'ch{i:02d}')
    plt.grid()
    plt.title('FFT')
    plt.xlabel('frequency (Hz)')
    if scale == 'dB' or scale == 'db' or scale == 'DB':
        plt.ylabel('Power (dB)')
    else:
        plt.ylabel('amplitude (mV)')
    plt.legend(loc='center right', bbox_to_anchor=(1.15, 0.5), ncol=1)
    if isinstance(xlim, (int, float, complex)):
        plt.xlim(0, xlim)
        plt.autoscale(enable=True, axis='y', tight=True)
    else:
        plt.autoscale(enable=True, tight=True)

def extract_data_from_df(df, errors='ignore'):
    """
    df = df.drop(['C', 'D', 'ads_status', 'ads_gpio',
                    'loff_statn', 'loff_statp', 'extra', 'data_hex',
                    'data_raw'], axis=1, errors=errors)
    Extracts relevant data from a pandas DataFrame object.

    Drops the following columns:

    ['C', 'D', 'ads_status', 'ads_gpio', 'loff_statn', 'loff_statp', 'extra', 'data_hex', 'data_raw']]

    Args:
    - df: pandas.DataFrme
        A pandas DataFrame object containing EEG data.
    - errors: {'ignore', 'raise'}
        Determines how errors are handled. The default is 'ignore', which silently ignores errors.

    Returns:
    - A new pandas DataFrame object with irrelevant columns removed.
    """
    return df.drop(['C', 'D', 'ads_status', 'ads_gpio',
                    'loff_statn', 'loff_statp', 'extra', 'data_hex',
                    'data_raw'], axis=1, errors=errors)

def wide2long_eeg(df, value_vars_primitives=['ch','raw_ch'], value_names=['voltage','raw_voltage'],
                    id_vars = ['timestamp', 'sample_number', 'total_samples', 'total_duration', 'avg_sample_rate',
                        'gain', 'ch_unit', 'num_chs'],
                    rename_ch2int=True):
    """
    Converts a wide-format EEG dataframe to a long-format EEG dataframe.

    Args:
        df: pandas.DataFrame:
            The wide-format EEG dataframe to convert.
        value_vars_primitives: list
             A list of strings representing the prefixes of the columns to be melted.
             Default is ['ch','raw_ch'].
        value_names: list
            A list of strings representing the names of the new columns created by melting.
            Default is ['voltage','raw_voltage'].
        id_vars: list
            A list of strings representing the columns to keep as is.
            Default is ['timestamp', 'sample_number', 'total_samples', 'total_duration', 'avg_sample_rate',
                        'gain','ch_unit'].
        rename_ch2int: bool
            Whether to rename the value_vars (channel) columns from string (e.g. 'ch01') to integers.
            Also drops 'raw_ch' column, which is redundant.
            Default is True.

    Returns:
        pandas.DataFrame: The long-format EEG dataframe.
    """
    if check_if_wide(df):
        value_vars = []
        for n in np.arange(len(value_vars_primitives)):
            value_vars.append([f'{value_vars_primitives[n]}{i:02d}' for i in np.arange(1, df.num_chs.max()+1)])
        df = df.pipe(multi_melt,
                    id_vars=id_vars,
                    value_vars=value_vars,
                    var_name=value_vars_primitives,
                    value_name=value_names
                    )

        #update values in 'var_name' columns to extract number from strings
        if rename_ch2int:
            df['ch'] = df.ch.str.extract(r'(\d+)').astype(int)
            df.drop(['raw_ch'], inplace=True, axis=1)
    else:
        print('The DataFrame is already in long format.')

    return df

def revert_wide2long_eeg(df, value_vars_primitives=['ch','raw_ch'], value_names=['voltage','raw_voltage'],
                    id_vars = ['timestamp', 'sample_number', 'total_samples', 'total_duration', 'avg_sample_rate',
                        'gain', 'ch_unit', 'num_chs'],
                    rename_ch2int=True):
    """
    Converts a long-format EEG dataframe to a wide-format EEG dataframe.
    """
    # TODO: Verify this function works properly
    if not check_if_wide(df):
        df = df.pivot_table(index=id_vars,
                            columns=value_vars_primitives,
                            values=value_names)
        df.reset_index(inplace=True)
        # df.columns.name = None
        # if rename_ch2int:
        #     df.columns = df.columns.map('{0[0]}{0[1]:02d}'.format)
    else:
        print('The DataFrame is already in wide format.')

    return df

def normalize(df, column='voltage', method='minmax'):
    """
    Normalizes the voltage data in a HackEEG DataFrame.

    Args:
        df: pandas.DataFrame
            The DataFrame to normalize.
        method: {'minmax', 'zscore'}
            The normalization method to use. Default is 'minmax'.

    Returns:
        pandas.DataFrame: The normalized DataFrame.
    """
    # TODO: Fix!!!
    df = wide2long_eeg(df, value_vars_primitives=['ch','raw_ch'], value_names=['voltage','raw_voltage'],
                    id_vars = ['timestamp', 'sample_number', 'total_samples', 'total_duration', 'avg_sample_rate',
                        'gain', 'ch_unit', 'num_chs'],
                    rename_ch2int=True)
    if method == 'minmax':
        return df.groupby(id_vars + ['ch']).apply(lambda x: (x[column] - x[column].min()) / (x[column].max() - x[column].min())).reset_index()
    elif method == 'zscore':
        return df.groupby('ch').apply(lambda x: (x[column] - x[column].mean()) / x[column].std()).reset_index()
    else:
        print('Unrecognized normalization method. Please use either "minmax" or "zscore".')

def check_if_wide(df):
    """
    Checks if a HackEEG DataFrame is in wide format.

    Simply checks if the column 'ch01' exists, since this column is only present in wide-format DataFrames.

    Args:
        df: pandas.DataFrame
            The DataFrame to check.

    Returns:
        bool: True if the DataFrame is in wide format, False otherwise.
    """
    if 'ch01' in df.columns:
        return True
    else:
        return False