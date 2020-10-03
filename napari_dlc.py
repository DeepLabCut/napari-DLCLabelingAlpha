from dlclabel import io
from napari_plugin_engine import napari_hook_implementation
from napari.types import ReaderFunction, WriterFunction
from typing import Any, Dict, List, Optional, Union


SUPPORTED_IMAGES = "jpg", "jpeg", "png"


@napari_hook_implementation(tryfirst=True, specname="napari_get_reader")
def load_images(path: Union[str, List[str]]) -> Optional[ReaderFunction]:
    if isinstance(path, str):
        path = [path]
    if any(path[0].endswith(ext) for ext in SUPPORTED_IMAGES):
        return io.read_images
    return None


@napari_hook_implementation(specname="napari_get_reader")
def load_labeled_data(path: str) -> Optional[ReaderFunction]:
    if isinstance(path, str) and path.endswith("h5"):
        return io.read_hdf
    return None


@napari_hook_implementation(specname="napari_get_reader")
def load_config(path: str) -> Optional[ReaderFunction]:
    if isinstance(path, str) and path.endswith("yaml"):
        return io.read_config
    return None


@napari_hook_implementation(tryfirst=True, specname="napari_write_points")
def save_keypoints(path: str, data: Any, meta: Dict) -> Optional[WriterFunction]:
    return io.write_hdf(path, data, meta)


@napari_hook_implementation(tryfirst=True, specname="napari_write_shapes")
def save_masks(path: str, data: Any, meta: Dict) -> Optional[WriterFunction]:
    return io.write_masks(path, data, meta)
