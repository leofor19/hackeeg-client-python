"""
This module provides a function to melt multiple columns of a pandas DataFrame simultaneously.

By: FirefoxMetzger
From: https://stackoverflow.com/a/71251931

Functions
---------
multi_melt(df, id_vars=None, value_vars=None, var_name=None, value_name="value", col_level=None, ignore_index=True)
    Melt multiple columns of a DataFrame simultaneously.

Returns
-------
pd.DataFrame
    The melted DataFrame.
"""

from itertools import cycle
import pandas as pd


def is_scalar(obj):
    """
    Determines whether an object is a scalar or not.

    Parameters:
    obj (any): The object to be checked.

    Returns:
    bool: True if the object is a scalar, False otherwise.
    """
    if isinstance(obj, str):
        return True
    elif hasattr(obj, "__iter__"):
        return False
    else:
        return True


import pandas as pd
from itertools import cycle
from pandas.api.types import is_scalar

def multi_melt(
    df: pd.DataFrame,
    id_vars=None,
    value_vars=None,
    var_name=None,
    value_name="value",
    col_level=None,
    ignore_index=True,
) -> pd.DataFrame:
    """
    Melt multiple columns of a DataFrame simultaneously.

    Parameters:
    -----------
    df : pandas.DataFrame
        The DataFrame to melt.
    id_vars : list-like or None, default None
        Column(s) to use as identifier variables.
    value_vars : list-like or None, default None
        Column(s) to unpivot. If not specified, uses all columns that are not set as `id_vars`.
    var_name : scalar or None, default None
        Name to use for the `variable` column. If None, uses `variable`.
    value_name : scalar, default 'value'
        Name to use for the `value` column.
    col_level : int or str, default None
        If columns are a MultiIndex, use this level to melt.
    ignore_index : bool, default True
        If True, the resulting DataFrame will have a new RangeIndex.

    Returns:
    --------
    pandas.DataFrame
        A DataFrame with the melted columns.
    """
    # Note: we don't broadcast value_vars ... that would seem unintuitive
    value_vars = value_vars if not is_scalar(value_vars[0]) else [value_vars]
    var_name = var_name if not is_scalar(var_name) else cycle([var_name])
    value_name = value_name if not is_scalar(value_name) else cycle([value_name])

    melted_dfs = [
        (
            df.melt(
                id_vars,
                *melt_args,
                col_level,
                ignore_index,
            ).pipe(lambda df: df.set_index([*id_vars, df.groupby(id_vars).cumcount()]))
        )
        for melt_args in zip(value_vars, var_name, value_name)
    ]

    return (
        pd.concat(melted_dfs, axis=1)
        .sort_index(level=2)
        .reset_index(level=2, drop=True)
        .reset_index()
    )