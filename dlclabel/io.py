import glob
import os
from itertools import groupby
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd
import yaml
from dask_image.imread import imread
from napari.layers import Shapes
from napari.plugins._builtins import napari_write_shapes
from napari.types import LayerData
from skimage.io import imsave
from skimage.util import img_as_ubyte

from dlclabel import misc

SUPPORTED_IMAGES = "jpg", "jpeg", "png"


def handle_path(path: Union[str, Sequence[str]]) -> Union[str, Sequence[str]]:
    """Dispatch files in folder to the relevant plugin readers."""
    paths = [path] if isinstance(path, str) else path
    paths = [os.fspath(path) for path in paths]
    if not isinstance(paths, (tuple, list)):
        raise ValueError("'path' argument must be a string, list, or tuple")

    # Test first whether a 'labeled-data' folder was passed in
    if len(paths) == 1:
        path = paths[0]
        if os.path.isdir(path):
            files = os.listdir(path)
            images = ""
            for file in files:
                if any(file.endswith(ext) for ext in SUPPORTED_IMAGES):
                    images = os.path.join(path, f"*{os.path.splitext(file)[1]}")
                    break
            if not images:
                raise IOError("No supported images were found.")

            datafile = ""
            for file in files:
                if file.endswith(".h5"):
                    datafile = os.path.join(path, "*.h5")
                    break
            if datafile:
                return [images, datafile]
            return [images]
    return paths


def _populate_metadata(
    header: misc.DLCHeader,
    *,
    labels: Optional[Sequence[str]] = None,
    ids: Optional[Sequence[str]] = None,
    likelihood: Optional[Sequence[float]] = None,
    paths: Optional[List[str]] = None,
    size: Optional[int] = 8,
    pcutoff: Optional[float] = 0.6,
    colormap: Optional[str] = "viridis",
) -> Dict:
    if labels is None:
        labels = header.bodyparts
    if ids is None:
        ids = header.individuals
    if likelihood is None:
        likelihood = np.ones(len(labels))
    label_colors = misc.build_color_cycle(len(header.bodyparts), colormap)
    id_colors = misc.build_color_cycle(len(header.individuals), colormap)
    face_color_cycle_maps = {
        "label": dict(zip(header.bodyparts, label_colors)),
        "id": dict(zip(header.individuals, id_colors)),
    }
    return {
        "name": "keypoints",
        "text": "label",
        "properties": {
            "label": list(labels),
            "id": list(ids),
            "likelihood": likelihood,
            "valid": likelihood > pcutoff,
        },
        "face_color_cycle": label_colors,
        "edge_color": "valid",
        "edge_color_cycle": ["black", "red"],
        "size": size,
        "metadata": {
            "header": header,
            "face_color_cycle_maps": face_color_cycle_maps,
            "paths": paths or [],
        },
    }


def _load_config(config_path: str):
    with open(config_path) as file:
        return yaml.safe_load(file)


def read_config(configname: str) -> List[LayerData]:
    config = _load_config(configname)
    header = misc.DLCHeader.from_config(config)
    metadata = _populate_metadata(
        header,
        size=config["dotsize"],
        pcutoff=config["pcutoff"],
        colormap=config["colormap"],
    )
    metadata["name"] = f"CollectedData_{config['scorer']}"
    # Set 'root' key to DLC project root directory.  We use this later to
    # construct the path to any image folder under 'labeled-data' to store
    # CollectedData files.
    metadata['metadata']['root'] = os.path.split(configname)[0]
    return [(None, metadata, "points")]


def read_images(path: Union[str, List[str]]) -> List[LayerData]:
    if isinstance(path, list):
        root, ext = os.path.splitext(path[0])
        path = os.path.join(os.path.dirname(root), f"*{ext}")
    # Retrieve filepaths exactly as parsed by pims
    filepaths = []
    for filepath in sorted(glob.glob(path)):
        _, *relpath = filepath.rsplit(os.sep, 3)
        filepaths.append(os.path.join(*relpath))
    params = {
        # Set image layer name to image folder name.
        "name": os.path.split(os.path.dirname(path))[-1],
        "metadata": {
            "paths": filepaths,
            # XXX: Is root of image layer ever used? Set it to
            # point to DLC project root directory for consistency?
            "root": os.path.split(path)[0]
        }
    }
    return [(imread(path), params, "image")]


def read_hdf(filename: str) -> List[LayerData]:
    layers = []
    for filename in glob.glob(filename):
        temp = pd.read_hdf(filename)
        header = misc.DLCHeader(temp.columns)
        temp = temp.droplevel("scorer", axis=1)
        if "individuals" not in temp.columns.names:
            # Append a fake level to the MultiIndex
            # to make it look like a multi-animal DataFrame
            old_idx = temp.columns.to_frame()
            old_idx.insert(0, "individuals", "")
            temp.columns = pd.MultiIndex.from_frame(old_idx)
        df = temp.stack(["individuals", "bodyparts"]).reset_index()
        nrows = df.shape[0]
        data = np.empty((nrows, 3))

        # Support path-agnostic MultiIndex (DLC v2.2.0.4+)
        if 'level_1' in df.columns and 'level_2' in df.columns:
            image_paths = df[['level_0', 'level_1', 'level_2']].agg(os.path.sep.join, axis=1)
        else:
            image_paths = df["level_0"]

        if np.issubdtype(image_paths.dtype, np.number):
            image_inds = image_paths.values
            paths2inds = []
        else:
            image_inds, paths2inds = misc.encode_categories(image_paths, return_map=True)
        data[:, 0] = image_inds
        data[:, 1:] = df[["y", "x"]].to_numpy()
        metadata = _populate_metadata(
            header,
            labels=df["bodyparts"],
            ids=df["individuals"],
            likelihood=df.get("likelihood"),
            paths=list(paths2inds),
        )
        # Name of CollectedData / machinelabels file.
        metadata["name"] = os.path.split(filename)[1].split(".")[0]
        # We make the assumption here that CollectedData/machinelabel files are
        # always placed within their ususal location following the DLC project
        # layout, i.e., they are within an image folder under
        # <dlc_root>/labeled-data/.
        # TODO: Add error handling in case the assumption does not hold.
        metadata["metadata"]["root"] = filename.rsplit(os.sep, 3)[0]
        layers.append((data, metadata, "points"))
    return layers


def write_hdf(filename: str, data: Any, metadata: Dict) -> Optional[str]:
    temp = pd.DataFrame(data[:, -1:0:-1], columns=["x", "y"])
    properties = metadata["properties"]
    meta = metadata["metadata"]
    temp["bodyparts"] = properties["label"]
    temp["individuals"] = properties["id"]
    temp["inds"] = data[:, 0].astype(int)
    temp["likelihood"] = properties["likelihood"]
    temp["scorer"] = meta["header"].scorer
    df = temp.set_index(["scorer", "individuals", "bodyparts", "inds"]).stack()
    df.index = df.index.set_names("coords", level=-1)
    df = df.unstack(["scorer", "individuals", "bodyparts", "coords"])
    df.index.name = None
    if not properties["id"].size:  # 'id' array with 0 entries
        df = df.droplevel("individuals", axis=1)
    df = df.reindex(meta["header"].columns, axis=1)
    root = meta["root"]

    # XXX: Can 'paths' value be empty?
    # In case 'paths' is empty, store CollectedData under DLC project root.
    # Does this make sense or should an error be raised?
    img_folder = root

    if meta["paths"]:
        df.index = [meta["paths"][i] for i in df.index]
        # Create path-agnostic MultiIndex (DLC v2.2.0.4+)
        splits = tuple(df.index.str.split(os.path.sep))
        # Fails if `df` is empty, i.e., no images have been annotated.
        df.index = pd.MultiIndex.from_tuples(splits)
        # Take the relative path of the first image in `paths`, split off
        # the image name, and append it to the DLC project root directory
        # to get the absolute path to the image folder.
        img_folder = os.path.join(root, os.path.split(meta['paths'][0])[0])

    name = metadata["name"]

    if "machine" in name:  # We are attempting to save refined model predictions
        # XXX: df does not seem to have a 'likelihood' column => ignore error
        df.drop("likelihood", axis=1, level="coords", inplace=True, errors='ignore')
        header = misc.DLCHeader(df.columns)
        gt_file = ""
        for file in os.listdir(img_folder):
            if file.startswith("CollectedData") and file.endswith("h5"):
                gt_file = file
                break
        if gt_file:  # Refined predictions must be merged into the existing data
            df_gt = pd.read_hdf(os.path.join(img_folder, gt_file))
            new_scorer = df_gt.columns.get_level_values("scorer")[0]
            header.scorer = new_scorer
            df.columns = header.columns
            df = pd.concat((df, df_gt))
            df = df[~df.index.duplicated(keep="first")]
            name = os.path.splitext(gt_file)[0]
        else:
            # Let us fetch the config.yaml file to get the scorer name...
            config = _load_config(os.path.join(root, "config.yaml"))
            new_scorer = config["scorer"]
            header.scorer = new_scorer
            df.columns = header.columns
            name = f"CollectedData_{new_scorer}"

    df.sort_index(inplace=True)

    filename = name
    filepath = os.path.join(img_folder, filename)
    df.to_hdf(filepath + '.h5', key="df_with_missing")
    # XXX: Temp for debugging: also store dataframe as CSV.
    df.to_csv(filepath + '.csv')
    
    return filename


def write_masks(foldername: str, data: Any, metadata: Dict) -> Optional[str]:
    folder, _ = os.path.splitext(foldername)
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, "{}_obj_{}.png")
    shapes = Shapes(data, shape_type="polygon")
    meta = metadata["metadata"]
    frame_inds = [int(array[0, 0]) for array in data]
    shape_inds = []
    for _, group in groupby(frame_inds):
        shape_inds += range(sum(1 for _ in group))
    masks = shapes.to_masks(mask_shape=meta["shape"][1:])
    for n, mask in enumerate(masks):
        image_name = os.path.basename(meta["paths"][frame_inds[n]])
        output_path = filename.format(os.path.splitext(image_name)[0], shape_inds[n])
        imsave(output_path, img_as_ubyte(mask).squeeze(), check_contrast=False)
    napari_write_shapes(os.path.join(folder, "vertices.csv"), data, metadata)
    return folder
