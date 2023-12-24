import os
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xmltodict
import yaml


def parse_xmls_as_dataframe(xmls, stop_on_error=False, logger=None) -> pd.DataFrame:
    """Parse a bunch of xmls and return a flag dataframe, XML does not have to be present, if it does not exist, no parsing is done."""
    df = None
    for xml in xmls:
        if os.path.exists(xml):
            try:
                xml_data: dict = parse_xml_to_dict(xml)
                meta_data = pd.DataFrame(xml_data, index=[0])
                meta_data.columns = [_cleanup(c) for c in meta_data.columns]

                if df is None:
                    df = meta_data
                else:
                    df = df.join(meta_data)
            except Exception as e:
                if logger is not None:
                    logger.warn("Exception occured while parsing {}: {}".format(xml, e))
                if not stop_on_error:
                    continue
                else:
                    raise e
    return df


def parse_xml_to_dict(xml_fp: str, flatten=True) -> dict:
    """Parses a XML as an orderd dict. Attributes in the XML will be prefixed with @"""
    with open(xml_fp) as xml_file:
        data_dict = xmltodict.parse(xml_file.read())

    if flatten:
        data_dict = flatten_dict(data_dict)
    return data_dict


def flatten_dict(d: dict, sep="."):
    """Recursively flatten a nested dict into a single dict with nested keys becoming Root.Node.Key=XXX, where the separator can be customized"""

    def items():
        for key, value in d.items():
            if isinstance(value, dict):
                for subkey, subvalue in flatten_dict(value).items():
                    yield key + sep + subkey, subvalue
            elif isinstance(value, list):
                for i, listval in enumerate(value):
                    listkey = "{}{}".format(key, i + 1)
                    if isinstance(listval, dict):
                        for subkey, subvalue in flatten_dict(listval).items():
                            yield listkey + sep + subkey, subvalue
                    else:
                        yield listkey, listval
            else:
                yield key, value

    return dict(items())


def substitute(line: str, **extra):
    """Performs replacement of all occurences of ${key} in string with `value` passed in as keyword arguments of this function
    i.e. `substitute(line, foo = bar, bo = Rob)` would replace '${foo}' with 'bar' and '${bo}' with 'Rob' in the string line,
        also performs environmental variable substitution
    """
    if len(extra) > 0:
        line = deepcopy(line)
        for k, v in extra.items():
            # {{  }} is how we escape the curly braces, the most inner one does the substitution
            line = line.replace("${{{}}}".format(k), str(v))
    return os.path.expandvars(line)


def map_variables(tree: dict, node: dict = None):
    """Use DFS to perform variable substitution on values in the config dictionary with other values
    i.e. say there's is a list of nested data structure located at key - ['global']['basepaths']

         if we want to use the values defined here elsewhere, we can just use $${global.basepaths}, this will be substituted with the appropriate values at
         config['global]['basepaths']

         Before mapping:
         {'global': {'something': 'nothing', 'foo': 'bar', 'fizz': [1, 2, 3, 4, 5]},
          'plugins': {'overview_simple': '${global.fizz}'}}


         After mapping:
            {'global': {'something': 'nothing', 'foo': 'bar', 'fizz': [1, 2, 3, 4, 5]},
              'plugins': {'overview_simple': [1, 2, 3, 4, 5]}}
    """
    if node is None:
        node = tree

    for k, v in node.items():
        if isinstance(v, dict):
            map_variables(tree, v)
        elif isinstance(v, str) and v.startswith("$${") and v.endswith("}"):
            # 2:-1 removes the ${...} and gives us just the ...
            new_v_path = v[3:-1].split(".")
            # get the val
            new_val = tree
            while len(new_v_path) > 0:
                new_val = new_val[new_v_path.pop(0)]
            node[k] = new_val


def load_config(config_file: str, map_var=True, **extra) -> dict:
    """Load main config file, and override keys specified in the override config file with the new value
    @params:
        config_file : path to a yaml config file
        extra : a dictionary of config values to be substituted, key appears as "${key}" in the config file will
                be substituted with the value in the dictionary
    """
    config = {}
    with open(config_file, "r") as fin:
        try:
            lines = fin.readlines()
            yaml_string = "\n".join([substitute(line, **extra) for line in lines])

            config = yaml.load(yaml_string, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            config = {}

    if map_var:
        map_variables(config)
    return config


def get_xml_file_from_folder(path: str, name: str = None):
    """Gets first xml file found in folder"""
    xml_file = [f for f in os.listdir(path) if f.endswith(".xml")]
    if name:
        xml_file = [f for f in xml_file if name.lower() in f.lower()]
    xml_file = xml_file[0]
    return xml_file


def map_col_from_xml(path, c, key, func):
    root = get_xml_root(path)
    d = {}

    if not root:
        return

    l = root.findall(key)

    for n, i in enumerate(l, 1):
        v = func(i)
        d[n] = v
    new_c = c.map(d)
    return new_c


def get_xml_root(p):
    if not os.path.exists(p):
        return
    xml_tree = ET.parse(p)
    root = xml_tree.getroot()
    return root


def get_date_time():
    today = datetime.today().strftime("%Y_%m_%d_%H_%M_%S")
    return today


def average_all_columns_by_group(data, group_list, method="mean"):
    "Group and take average of numeric columns then merge first non-numeric from each group back in"
    # Drop NAN col and rows
    data.dropna(inplace=True, axis=0, how="all")
    data.dropna(inplace=True, axis=1, how="all")
    # Reset index
    # data = data.reset_index()
    # list of columns to group by and average

    if method == "std":
        df = data.groupby(by=group_list, as_index=False, sort=True).std()
    if method == "mean":
        df = data.groupby(by=group_list, as_index=False, sort=True).mean(
            numeric_only=True
        )
    elif method == "median":
        df = data.groupby(by=group_list, as_index=False, sort=True).median(
            numeric_only=True
        )

    # Get list of columns that were dropped during averaged (wrong type)
    init_columns = list(data.columns)
    post_columns = list(df.columns)
    dropped_list = list_diff(init_columns, post_columns)

    if dropped_list:
        dropped_list = dropped_list + group_list
        # Get dropped columns as df
        data = data[dropped_list]
        data = data.groupby(by=group_list, as_index=True).nth(0)
        data = data.applymap(replace_list_with_string)
        if isinstance(data, pd.Series):
            data = data.to_frame().transpose()
        # Merge dropped columns back into averaged data
        df = pd.merge(
            df,
            data,
            how="left",
            left_on=group_list,
            right_index=True,
        )
    return df


def print_time_diff(t1, t2):
    """Print difference between two time objects"""
    seconds = round(t1 - t2, 1)
    hours = round(seconds / 3600, 2)
    print(f"Time: {hours}h ({seconds}s)")


def mk_dirs(path):
    dir = Path(path)
    if not dir.exists():
        os.mkdir(dir)


def replace_list_with_string(value):
    if isinstance(value, np.ndarray):
        # value = np.core.defchararray.join(",",value)
        value = ",".join(value)
    return value


def drop_ordered_list_duplicates(l):
    """Drop list duplicates (keep order)"""
    res = [i for n, i in enumerate(l) if i not in l[:n]]
    return res


def drop_unordered_list_duplicates(l):
    """Drop list duplicates (don't keep order)"""
    res = [*set(l)]
    return res


def list_diff(li1, li2):
    li_dif = [i for i in li1 + li2 if i not in li1 or i not in li2]
    return li_dif


def list_intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3


def get_items_containing_substring(items, substrings):
    """Get list of items containing any of a list of substrings"""
    substrings = [str(s) for s in substrings]
    items = [i for i in items if any(s in i for s in substrings)]
    return items


def get_root():
    """Get path to root dir"""
    path = os.path.dirname(os.path.realpath("__file__"))
    return path


def open_csv_chunks(path, **kwargs):
    """Open csv using pd.read_csv with chunking"""
    df_iter = pd.read_csv(path, low_memory=False, chunksize=1000, **kwargs)
    df = pd.concat(df_iter)
    return df
