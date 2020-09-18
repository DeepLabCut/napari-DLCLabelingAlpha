import cv2
import dask.array as da
import numpy as np
import os
import pandas as pd
import pims
import yaml
from dask import delayed
from dask_image.imread import imread
from dlclabel import misc
from itertools import groupby
from napari.layers import Shapes
from napari.plugins._builtins import napari_write_shapes
from pims import PyAVReaderIndexed
from skimage.io import imsave
from skimage.util import img_as_ubyte


class Video:
    def __init__(self, video_path):
        if not os.path.isfile(video_path):
            raise ValueError(f'Video path "{video_path}" does not point to a file.')
        self.path = video_path
        self.stream = cv2.VideoCapture(video_path)
        if not self.stream.isOpened():
            raise IOError('Video could not be opened.')
        self._n_frames = int(self.stream.get(cv2.CAP_PROP_FRAME_COUNT))
        self._width = int(self.stream.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._frame = np.empty((self._height, self._width, 3), dtype=np.uint8)

    def __len__(self):
        return self._n_frames

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def set_to_frame(self, ind):
        if ind >= len(self) - 1:
            ind = len(self) - 1
        self.stream.set(cv2.CAP_PROP_POS_FRAMES, ind)

    def read_frame(self):
        self._frame[:] = self.stream.read()[1]
        return self._frame[..., ::-1]

    def close(self):
        self.stream.release()


def read_video(path):
    stream = Video(path)
    shape = (len(stream),) + (stream.width, stream.height, 3)

    def _read_frame(video, ind):
        video.set_to_frame(ind)
        return video.read_frame()

    lazy_imread = delayed(_read_frame)
    movie = da.stack(
        [da.from_delayed(lazy_imread(stream, i), shape=shape[1:], dtype=np.uint8)
         for i in range(len(stream))]
    )
    return [(movie, {'metadata': {'paths': []}}, 'image')]


def read_video2(path):
    stream = PyAVReaderIndexed(path)
    shape = stream.frame_shape

    lazy_imread = delayed(stream.get_frame)
    movie = da.stack(
        [da.from_delayed(lazy_imread(i), shape=shape, dtype=np.uint8)
         for i in range(len(stream))]
    )
    return [(movie, {'metadata': {'paths': []}}, 'image')]


def handle_path(path):
    paths = [path] if isinstance(path, str) else path
    paths = [os.fspath(path) for path in paths]
    if not isinstance(paths, (tuple, list)):
        raise ValueError(
            "'path' argument must be a string, list, or tuple"
        )

    # Test first whether a 'labeled-data' folder was passed in
    if len(paths) == 1:
        path = paths[0]
        if os.path.isdir(path):
            images = os.path.join(path, '*.png')
            datafile = ''
            for file in os.listdir(path):
                if file.endswith('h5'):
                    datafile = os.path.join(path, file)
                    break
            if datafile:
                return [images, datafile]
            return [images]
    return paths


def _populate_metadata(header, labels=None, ids=None, likelihood=None,
                       paths=None, size=8, pcutoff=0.6, colormap='viridis'):
    if labels is None:
        labels = header.bodyparts
    if ids is None:
        ids = header.individuals
    if likelihood is None:
        likelihood = np.ones(len(labels))
    label_colors = misc.build_color_cycle(len(header.bodyparts), colormap)
    id_colors = misc.build_color_cycle(len(header.individuals), colormap)
    face_color_cycle_maps = {'label': dict(zip(header.bodyparts, label_colors)),
                             'id': dict(zip(header.individuals, id_colors))}
    return {
        'name': 'keypoints',
        'text': 'label',
        'properties': {'label': list(labels),
                       'id': list(ids),
                       'likelihood': likelihood,
                       'valid': likelihood > pcutoff},
        'face_color_cycle': label_colors,
        'edge_color': 'valid',
        'edge_color_cycle': ['black', 'red'],
        'size': size,
        'metadata': {
            'header': header,
            'face_color_cycle_maps': face_color_cycle_maps,
            'paths': paths or []
        }
    }


def read_config(configname):
    with open(configname) as file:
        config = yaml.safe_load(file)
    header = misc.DLCHeader.from_config(config)
    metadata = _populate_metadata(
        header=header,
        size=config['dotsize'],
        pcutoff=config['pcutoff'],
        colormap=config['colormap']
    )
    return [(np.empty([0, 3]), metadata, 'points')]


def read_images(path):
    if isinstance(path, list):
        root, ext = os.path.splitext(path[0])
        path = os.path.join(os.path.dirname(root), f'*{ext}')
    # Retrieve filepaths exactly as parsed by pims
    with pims.open(path) as imgs:
        filepaths = []
        for filepath in imgs._filepaths:
            _, *relpath = filepath.rsplit(os.sep, 3)
            filepaths.append(os.path.join(*relpath))
    params = {
        'name': 'images',
        'metadata': {'paths': filepaths}
    }
    return [(imread(path), params, 'image')]


def read_hdf(filename):
    temp = pd.read_hdf(filename)
    header = misc.DLCHeader(temp.columns)
    temp = temp.droplevel('scorer', axis=1)
    if 'individuals' not in temp.columns.names:
        # Append a fake level to the MultiIndex
        # to make it look like a multi-animal DataFrame
        old_idx = temp.columns.to_frame()
        old_idx.insert(0, 'individuals', '')
        temp.columns = pd.MultiIndex.from_frame(old_idx)
    df = temp.stack(['individuals', 'bodyparts']).reset_index()
    nrows = df.shape[0]
    data = np.empty((nrows, 3))
    image_paths = df['level_0']
    if np.issubdtype(image_paths.dtype, np.number):
        image_inds = image_paths.values
        paths2inds = []
    else:
        image_inds, paths2inds = misc.encode_categories(image_paths, return_map=True)
    data[:, 0] = image_inds
    data[:, 1:] = df[['y', 'x']].to_numpy()
    metadata = _populate_metadata(
        header=header,
        labels=df['bodyparts'],
        ids=df['individuals'],
        likelihood=df.get('likelihood'),
        paths=list(paths2inds)
    )
    return [(data, metadata, 'points')]


def write_hdf(filename, data, metadata):
    file, _ = os.path.splitext(filename)
    filename = file + '.h5'
    temp = pd.DataFrame(data[:, -1:0:-1], columns=['x', 'y'])
    properties = metadata['properties']
    meta = metadata['metadata']
    temp['bodyparts'] = properties['label']
    temp['individuals'] = properties['id']
    temp['inds'] = data[:, 0].astype(int)
    temp['likelihood'] = properties['likelihood']
    temp['scorer'] = meta['header'].scorer
    df = temp.set_index(['scorer', 'individuals', 'bodyparts', 'inds']).stack()
    df.index = df.index.set_names('coords', -1)
    df = df.unstack(['scorer', 'individuals', 'bodyparts', 'coords'])
    df.index.name = None
    if not properties['id'][0]:
        df = df.droplevel('individuals', axis=1)
    df = df.reindex(meta['header'].columns, axis=1)
    # Fill unnannotated rows with NaNs
    # df = df.reindex(range(len(meta['paths'])))
    # df.index = meta['paths']
    df.index = [meta['paths'][i] for i in df.index]
    df.to_hdf(filename, key='keypoints')
    return filename


def write_masks(foldername, data, metadata):
    folder, _ = os.path.splitext(foldername)
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, '{}_obj_{}.png')
    shapes = Shapes(data, shape_type='polygon')
    meta = metadata['metadata']
    frame_inds = [int(array[0, 0]) for array in data]
    shape_inds = []
    for _, group in groupby(frame_inds):
        shape_inds += range(sum(1 for _ in group))
    masks = shapes.to_masks(mask_shape=meta['shape'][1:])
    for n, mask in enumerate(masks):
        image_name = os.path.basename(meta['paths'][frame_inds[n]])
        output_path = filename.format(
            os.path.splitext(image_name)[0], shape_inds[n]
        )
        imsave(output_path,
               img_as_ubyte(mask).squeeze(),
               check_contrast=False)
    napari_write_shapes(os.path.join(folder, 'vertices.csv'), data, metadata)
    return folder
