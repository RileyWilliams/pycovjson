import json
import os.path
import uuid
from collections import OrderedDict

import pycovjson.readNetCDF as rnc

from pycovjson import util

#File Locations
json_template_path = 'data/jsont_template.json'
ncdf_file = rnc.ncdf_file
json_file = 'json_output_test.json'
json_ranges = 'data/ranges.json'
json_parameter ='data/parameter.json'
json_referencing ='data/referencing.json'

domain_type = "Grid" # Default

PATH_DATA = os.path.join(os.path.dirname(__file__), '..', 'data')

#Creating NetCDF dataset object
dset = rnc.load_netcdf(ncdf_file)

# ReadNetCDF data
var_names = rnc.get_var_names(dset)
rnc.extract_var_data(var_names)

#TEST - REPLACE WITH FUNCTION TO TAKE OPTIONS FROM USER
user_opts = ['ICEC']

print(rnc.get_var_names(dset))



def load_json(path):
    with open(path, 'r') as fp:
        return json.load(fp, object_pairs_hook=OrderedDict)

json_template = load_json(json_template_path)


def construct_range(var_name):

    ranges = load_json(json_ranges)
    ranges['dataType'] = str(rnc.get_type(var_name))
    ranges['shape'] = rnc.get_shape(var_name)
    #Debug
    print("Construct range ran successfully...")
    return ranges

def construct_parameters(var_name):
    parameters = load_json(json_parameter)
    #parameters[var_name]['description'] = rnc.get_long_name(var_name)
    return parameters

def construct_referencing(var_name):
    referencing = load_json(json_referencing)
    return referencing

def update_json(json_template, data, domain_type, user_opts):

    """
    :param json_template:
    :param data:
    :param domain_type:
    :return:
    """

    json_template['domain']['domainType'] = domain_type

    # Coordinate data
    json_template['domain']['axes']['x']['values'] = (data['lon'].tolist())
    json_template['domain']['axes']['y']['values'] = (data['lat'].tolist())
    json_template['domain']['axes']['t'] = {'values': []}
    json_template['domain']['axes']['t']['values']= rnc.convert_time('time')



    # if 't' in json_template['domain']['axes']:
    #     json_template['domain']['axes']['t']['values'] = (data[time].tolist())

    #Variable data
    # json_template['ranges'][main_var]['values'] = (data[main_var].ravel().tolist())[0:1]

    for var in user_opts:

        json_template['ranges'][var] = construct_range(var)
        json_template['ranges'][var]['values'] = (data[var].ravel().tolist()) #For testing, limit dataset

        json_template['parameters'][var] = construct_parameters(var)
        json_template['parameters'][var]['description'] = rnc.get_long_name(var)
        json_template['parameters'][var]['unit'] = rnc.get_units(var)

    #print(json.dumps(json_template, indent=4))
    # Debugjson_template['domain']['axes']['t']
    #print(json.dumps(json_template,indent=4))

    return json_template
#Adapted from https://github.com/the-iea/ecem/blob/master/preprocess/ecem/util.py - letmaik
def save_json(obj, path, **kw):
    with open(path, 'w') as fp:
        #Change to json.dump
        #json.dump(obj,fp, cls=CustomEncoder, **kw)
        jsonstr = json.dumps(obj, fp, cls=CustomEncoder, **kw)
        fp.write(jsonstr)
        #jsonstr = json.dumps(obj, cls=CustomEncoder, **kw)
        #fp.write(jsonstr)

def save_covjson(obj, path):
    # skip indentation of certain fields to make it more compact but still human readable
    for axis in obj['domain']['axes'].values():
        compact(axis, 'values')
    for ref in obj['domain']['referencing']:
        no_indent(ref, 'components')
    for range in obj['ranges'].values():
        no_indent(range, 'axisNames', 'shape')
        compact(range, 'values')
    save_json(obj, path, indent=2)


def compact(obj, *names):
    for name in names:
        obj[name] = Custom(obj[name], separators=(',', ':'))


def no_indent(obj, *names):
    for name in names:
        obj[name] = Custom(obj[name])


# From http://stackoverflow.com/a/25935321
class Custom(object):
    def __init__(self, value, **custom_args):
        self.value = value
        self.custom_args = custom_args


class CustomEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super(CustomEncoder, self).__init__(*args, **kwargs)
        self._replacement_map = {}

    def default(self, o):
        if isinstance(o, Custom):
            key = uuid.uuid4().hex
            self._replacement_map[key] = json.dumps(o.value, **o.custom_args)
            return "@@%s@@" % (key,)
        else:
            return super(CustomEncoder, self).default(o)

    def encode(self, o):
        result = super(CustomEncoder, self).encode(o)
        for k, v in self._replacement_map.items():
            result = result.replace('"@@%s@@"' % (k,), v)
        return result


out_file = open(json_file, "w")

json.dumps(json_template,indent=4)


# Test parameters
var_names = rnc.get_var_names(dset)
data = rnc.extract_var_data(var_names)
json_obj = update_json(json_template, rnc.extract_var_data(var_names), domain_type, user_opts)

save_covjson(json_obj, json_file)









