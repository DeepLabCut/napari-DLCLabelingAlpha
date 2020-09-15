import numpy as np
import pandas as pd
from enum import Enum, EnumMeta
from itertools import cycle
from napari.utils import colormaps


def unsorted_unique(array):
    _, inds = np.unique(array, return_index=True)
    return np.asarray(array)[np.sort(inds)]


def encode_categories(cat, return_map=False):
    unique_cat = unsorted_unique(cat)
    map_ = dict(zip(unique_cat, range(len(unique_cat))))
    inds = np.vectorize(map_.get)(cat)
    if return_map:
        return inds, map_
    return inds


def build_color_cycle(n_colors, colormap='viridis'):
    cmap = colormaps.ensure_colormap(colormap)
    return cmap.map(np.linspace(0, 1, n_colors))


def get_first_layer_of_type(layers, type_):
    target = None
    for layer in layers:
        if isinstance(layer, type_):
            target = layer
            break
    return target


class DLCHeader:
    def __init__(self, columns):
        self.columns = columns

    @classmethod
    def from_config(cls, config):
        multi = config.get('multianimalproject', False)
        scorer = [config['scorer']]
        if multi:
            columns = pd.MultiIndex.from_product(
                [scorer, config['individuals'], config['multianimalbodyparts'], ['x', 'y']]
            )
            if len(config['uniquebodyparts']):
                temp = pd.MultiIndex.from_product(
                    [scorer, ['single'], config['uniquebodyparts'], ['x', 'y']]
                )
                columns = columns.append(temp)
            columns.set_names(['scorer', 'individuals', 'bodyparts', 'coords'],
                              inplace=True)
        else:
            columns = pd.MultiIndex.from_product(
                [scorer, config['bodyparts'], ['x', 'y']],
                names=['scorer', 'bodyparts', 'coords']
            )
        return cls(columns)

    def form_individual_bodypart_pairs(self):
        to_drop = [name for name in self.columns.names
                   if name not in ('individuals', 'bodyparts')]
        temp = self.columns.droplevel(to_drop).unique()
        if 'individuals' not in temp.names:
            temp = pd.MultiIndex.from_product([self.individuals, temp])
        return temp.to_list()

    @property
    def scorer(self):
        return self._get_unique('scorer')[0]

    @property
    def individuals(self):
        individuals = self._get_unique('individuals')
        if individuals is None:
            return ['']
        return individuals

    @property
    def bodyparts(self):
        return self._get_unique('bodyparts')

    @property
    def coords(self):
        return self._get_unique('coords')

    def _get_unique(self, name):
        if name in self.columns.names:
            return unsorted_unique(self.columns.get_level_values(name))
        return None


class CycleEnumMeta(EnumMeta):
    def __new__(metacls, cls, bases, classdict):
        enum_ = super().__new__(metacls, cls, bases, classdict)
        enum_._cycle = cycle(enum_._member_map_[name]
                             for name in enum_._member_names_)
        return enum_

    def __iter__(cls):
        return cls._cycle

    def __next__(cls):
        return next(cls.__iter__())

    def __getitem__(self, item):
        if isinstance(item, str):
            item = item.upper()
        return super().__getitem__(item)

    def keys(self):
        return list(map(str, self))


class CycleEnum(Enum, metaclass=CycleEnumMeta):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    def __str__(self):
        return self.value
