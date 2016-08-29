
from pycovjson.model import *
from pycovjson.readNetCDFOOP import NetCDFReader as Reader
import numpy
import time, json, uuid


class Writer(object):
    """Writer class"""

    def __init__(self, output_name: object, dataset_path: object, vars_to_write: object, tiled=False, tile_shape=[] ) -> object:
        """
        Writer class constructor
        :param output_name: Name of output file
        :param dataset_path: Path to dataset
        :param vars_to_write: List of variables to write
        :param tiled: Boolean value (default False)
        :param tile_shape: List containing shape of tiles
        """
        self.output_name = output_name
        self.dataset_path = dataset_path
        self.tile_shape = tile_shape
        self.vars_to_write = vars_to_write
        self.urlTemplate = 'localhost:8080/{t}.covjson'
        self.tiled = tiled
        if tiled:
            self.range_type = 'TiledNdArray'
        else: self.range_type = 'NdArray'
        self.dataset_path = dataset_path
        self.Reader = Reader(dataset_path)
        self.axis_dict = self.Reader.get_axes()
        self.axis_list = list(self.axis_dict.keys())
        self.ref_list = []
        if 't' in self.axis_list and 'z' in self.axis_list:
            self.ref_list.append(TemporalReferenceSystem())
            self.ref_list.append(SpatialReferenceSystem3d())

        if 't' in self.axis_list and 'z' not in self.axis_list:
            self.ref_list.append(TemporalReferenceSystem())
            self.ref_list.append(SpatialReferenceSystem2d())
        elif 't' not in self.axis_list and 'z' not in self.axis_list:
            self.ref_list.append(SpatialReferenceSystem2d())


    def write(self):
        """
        Writes coverageJSON object to disk
        """

        coverage = self._construct_coverage()
        self._save_covjson(coverage, self.output_name)
        pass


    def _construct_coverage(self):
        """
        Constructs Coverage object from constituent parts
        :return: coverage object
        """
        coverage = Coverage(self._construct_domain(),self._construct_range(), self._construct_params(), self._construct_refs()).to_dict()
        return coverage

    def _construct_domain(self):
        """
        Constructs Domain object, populates with values
        :return: domain object
        """

        domain_type = 'Grid'
        x_values = self.Reader.get_x().flatten().tolist()
        y_values = self.Reader.get_y().flatten().tolist()
        t_values = []
        z_values = []

        if 't' in self.axis_list:

            t_values = self.Reader.get_t()

        if 'z' in self.axis_list:

            z_values = self.Reader.get_z().flatten().tolist()


        domain = Domain(domain_type, x_values, y_values, z_values, t_values)


        return domain

    def _construct_params(self):
        """
        Construct parameters
        :return: Parameter object
        """
        for variable in self.vars_to_write:
            description = self.Reader.get_std_name(variable)
            unit = self.Reader.get_units(variable)
            symbol = self.Reader.dataset[variable].units
            label = self.Reader.dataset[variable].long_name
            params = Parameter(description=description, variable_name=variable, symbol=symbol, unit=unit,observed_property=label )


        return params

    def _construct_refs(self):

        refs = Reference(self.ref_list)

        return refs

    def _construct_range(self):
        # TODO iteration through variable list
        variable = self.vars_to_write[0]


        if self.tiled:
            tile_set = TileSet(self.tile_shape, self.urlTemplate)
            variable_type = self.Reader.get_type(variable)
            variable_shape = self.Reader.get_shape(variable)
            count = 0
            for tile in tile_set.get_tiles(self.tile_shape, self.Reader.dataset[variable].values):
                count +=1
                range = {'ranges':Range('NdArray', data_type=variable_type, axes=tile[1], shape=variable_shape, values=tile[0].flatten().tolist()).to_dict()}
                self.save_covjson_range(range, + str(count) +'.json' )

        axes = self.Reader.get_axis(variable)
        print('Axis Shape: ', axes)
        for dim in self.Reader.dataset[variable].dims:
            print(dim)
            print(self.Reader.dataset[dim].shape)


        shape = self.Reader.get_shape(variable)
        values = self.Reader.get_values(variable).flatten().tolist()
        data_type = self.Reader.get_type(variable)


        range = Range(range_type='NdArray',  data_type=data_type, values=values, shape= shape, variable_name=variable, axes=axes )


        return range

    # Adapted from https://github.com/the-iea/ecem/blob/master/preprocess/ecem/util.py - letmaik
    def _save_json(self, obj, path, **kw):
        with open(path, 'w') as fp:
            print("Converting....")
            start = time.clock()
            jsonstr = json.dumps(obj, fp, cls=CustomEncoder, **kw)
            fp.write(jsonstr)
            stop = time.clock()
            print("Completed in: ", (stop - start), "seconds.")

    def _save_covjson(self, obj, path):
        # skip indentation of certain fields to make it more compact but still human readable
        for axis in obj['domain']['axes'].values():
            self.compact(axis, 'values')
        for ref in obj['domain']['referencing']:
            self.no_indent(ref, 'coordinates')
        for range in obj['ranges'].values():
            self.no_indent(range, 'axisNames', 'shape')
            self.compact(range, 'values')
        self.save_json(obj, path, indent=2)

    def save_json(self, obj, path, **kw):
        with open(path, 'w') as fp:
            print("Converting....")
            start = time.clock()
            jsonstr = json.dumps(obj, fp, cls=CustomEncoder, **kw)
            fp.write(jsonstr)
            stop = time.clock()
            print("Completed in: ", (stop - start), "seconds.")

    def save_covjson_range(self, obj, path):
        for range in obj['ranges'].values():
            self.no_indent(range, 'axisNames', 'shape')
            self.compact(range, 'values')
        self.save_json(obj, path, indent=2)

    def compact(self, obj, *names):
        for name in names:
            obj[name] = Custom(obj[name], separators=(',', ':'))

    def no_indent(self, obj, *names):
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


