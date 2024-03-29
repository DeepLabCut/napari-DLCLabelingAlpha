import warnings
from typing import List, Optional, Sequence, Union

import napari
import numpy as np
from napari.layers import Image, Layer
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from dlclabel.io import handle_path
from dlclabel.layers import KeyPoints
from dlclabel.misc import to_os_dir_sep
from dlclabel.widgets import KeypointsDropdownMenu

# TODO Add vectors for paths trajectory
# TODO Add video reader plugin
# TODO Refactor KeyPoints with KeyPointsData


# Hack to save a KeyPoints layer without showing the Save dialog
def _save_layers_dialog(self, selected=False):
    """Save layers (all or selected) to disk, using ``LayerList.save()``.

    Parameters
    ----------
    selected : bool
        If True, only layers that are selected in the viewer will be saved.
        By default, all layers are saved.
    """
    selected_layers = self.viewer.layers.selected
    msg = ""
    if not len(self.viewer.layers):
        msg = "There are no layers in the viewer to save"
    elif selected and not len(selected_layers):
        msg = (
            'Please select one or more layers to save,'
            '\nor use "Save all layers..."'
        )
    if msg:
        QMessageBox.warning(self, "Nothing to save", msg, QMessageBox.Ok)
        return
    if len(selected_layers) == 1 and isinstance(selected_layers[0], KeyPoints):
        self.viewer.layers.save("", selected=True)
    else:
        filename, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption=f'Save {"selected" if selected else "all"} layers',
            directory=self._last_visited_dir,  # home dir by default
        )
        if filename:
            self.viewer.layers.save(filename, selected=selected)


class DLCViewer(napari.Viewer):
    def __init__(self):
        super(DLCViewer, self).__init__(title="deeplabcut")
        # Inherit parent class' key bindings
        self.class_keymap.update(super(DLCViewer, self).class_keymap)
        self.layers.events.changed.connect(self.on_change)
        self._dock_widgets = []

        # Hack the QSS style sheet to add a KeyPoints layer type icon
        missing_style = """\n\nQLabel#KeyPoints {
          image: url(":/themes/{{ folder }}/new_points.svg");
        }"""
        self.window.raw_stylesheet += missing_style
        self.window._update_palette(None)

        # Substitute default menu action with custom one
        for action in self.window.file_menu.actions():
            if "save selected layer" in action.text().lower():
                action.disconnect()
                action.triggered.connect(
                    lambda: _save_layers_dialog(
                        self.window.qt_viewer,
                        selected=True,
                    )
                )
                break

        # Storage for extra image metadata that are relevant to other layers.
        # These are updated anytime images are added to the Viewer
        # and passed on to the other layers upon creation.
        self._images_meta = dict()

    def on_change(self, event):
        if event.type == "added":
            layer = event.item
            root = layer.metadata.get("root")
            # Hack to have the save dialog open right in the labeled-data folder
            if root:
                self.window.qt_viewer._last_visited_dir = root
            if isinstance(layer, Image):
                paths = layer.metadata.get("paths")
                if paths is None:
                    return
                # Store the metadata and pass them on to the other layers
                with warnings.catch_warnings():
                    warnings.simplefilter(action="ignore", category=FutureWarning)
                    self._images_meta.update({"paths": paths, "shape": layer.shape})
                for layer_ in self.layers:
                    if not isinstance(layer_, Image):
                        self._remap_frame_indices(layer_)
                # Ensure the images are always underneath the other layers
                n_layers = len(self.layers)
                if n_layers > 1:
                    self.layers.move_selected(event.index, 0)
            elif isinstance(layer, KeyPoints):
                if not self._dock_widgets:
                    menu = KeypointsDropdownMenu(layer)
                    self._dock_widgets.append(
                        self.window.add_dock_widget(
                            menu, name="keypoints menu", area="bottom"
                        )
                    )
                layer.smart_reset(event=None)  # Update current keypoint upon loading data
                self.bind_key("Down", layer.next_keypoint, overwrite=True)
                self.bind_key("Up", layer.prev_keypoint, overwrite=True)
        elif event.type == "removed":
            layer = event.item
            if isinstance(layer, KeyPoints):
                while self._dock_widgets:
                    widget = self._dock_widgets.pop()
                    self.window.remove_dock_widget(widget)
            elif isinstance(layer, Image):
                self._images_meta = dict()

    def _remap_frame_indices(self, layer: Layer):
        """Ensure consistency between layers' data and the corresponding images."""
        if not self._images_meta:
            return

        # Make missing frame detection independent of OS directory separator:
        # if existing "CollectedData" or "machinelabels" file contains relative
        # image paths using a directory separator different from the OS on which
        # this scirpt is run, then the matchin of image paths fails and missing
        # frames are detected erroneously.
        new_paths = [to_os_dir_sep(p) for p in self._images_meta["paths"]]
        paths = layer.metadata.get("paths")

        if paths is not None and np.any(layer.data):
            paths_map = dict(zip(range(len(paths)), map(to_os_dir_sep, paths)))
            # Discard data if there are missing frames
            missing = [i for i, path in paths_map.items() if path not in new_paths]
            if missing:
                if isinstance(layer.data, list):
                    inds_to_remove = [
                        i
                        for i, verts in enumerate(layer.data)
                        if verts[0, 0] in missing
                    ]
                else:
                    inds_to_remove = np.flatnonzero(np.isin(layer.data[:, 0], missing))
                layer.selected_data = inds_to_remove
                layer.remove_selected()
                for i in missing:
                    paths_map.pop(i)

            # Check now whether there are new frames
            temp = {k: new_paths.index(v) for k, v in paths_map.items()}
            data = layer.data
            if isinstance(data, list):
                for verts in data:
                    verts[:, 0] = np.vectorize(temp.get)(verts[:, 0])
            else:
                data[:, 0] = np.vectorize(temp.get)(data[:, 0])
            layer.data = data
        layer.metadata.update(self._images_meta)

    def _advance_step(self, event):
        ind = (self.dims.current_step[0] + 1) % self.dims.nsteps[0]
        self.dims.set_current_step(0, ind)

    def add_points(
        self,
        data=None,
        *,
        properties=None,
        text=None,
        symbol="o",
        size=10,
        edge_width=0,
        edge_color="black",
        edge_color_cycle=None,
        edge_colormap="viridis",
        edge_contrast_limits=None,
        face_color="white",
        face_color_cycle=None,
        face_colormap="viridis",
        face_contrast_limits=None,
        n_dimensional=False,
        name="keypoints",
        metadata=None,
        scale=None,
        translate=None,
        opacity=1,
        blending="translucent",
        visible=True,
    ) -> Optional[KeyPoints]:
        # Disable the creation of Points layers via the button
        if not properties:
            return

        layer = KeyPoints(
            data=data,
            properties=properties,
            text=text,
            symbol=symbol,
            size=size,
            edge_width=edge_width,
            edge_color=edge_color,
            edge_color_cycle=edge_color_cycle,
            edge_colormap=edge_colormap,
            edge_contrast_limits=edge_contrast_limits,
            face_color=face_color,
            face_color_cycle=face_color_cycle,
            face_colormap=face_colormap,
            face_contrast_limits=face_contrast_limits,
            n_dimensional=n_dimensional,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            opacity=opacity,
            blending=blending,
            visible=visible,
        )

        self.dims.events.current_step.connect(layer.smart_reset, position="last")
        layer.events.query_next_frame.connect(self._advance_step)

        # Hack to avoid napari's silly variable type guess,
        # where property is understood as continuous if
        # there are more than 16 unique categories...
        with layer.block_update_properties():
            layer.face_color = "label"
        layer.face_color_mode = "cycle"
        self.add_layer(layer)
        layer.mode = "add"
        return layer

    def add_layer(self, layer: Layer) -> Layer:
        if not isinstance(layer, Image):
            self._remap_frame_indices(layer)
        return super(DLCViewer, self).add_layer(layer)

    def open(
        self,
        path: Union[str, Sequence[str]],
        *,
        stack: bool = False,
        plugin: Optional[str] = None,
        layer_type: Optional[str] = None,
        **kwargs,
    ) -> List[Layer]:
        return super(DLCViewer, self).open(
            handle_path(path),
            stack=stack,
            plugin=plugin,
            layer_type=layer_type,
            **kwargs,
        )


def show():
    with napari.gui_qt():
        return DLCViewer()
