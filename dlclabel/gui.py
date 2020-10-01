import napari
import numpy as np
from dlclabel.io import handle_path
from dlclabel.layers import KeyPoints
from dlclabel.widgets import DualDropdownMenu
from napari.layers import Image


# TODO Add vectors for paths trajectory
# TODO Add video reader plugin


class DLCViewer(napari.Viewer):
    def __init__(self):
        super(DLCViewer, self).__init__(title='deeplabcut')
        self.class_keymap.update(super(DLCViewer, self).class_keymap)
        self.layers.events.changed.connect(self.on_change)
        self._dropdown_menus = []

        # Hack the QSS style sheet to add a KeyPoints layer type icon
        missing_style = """\n\nQLabel#KeyPoints {
          image: url(":/themes/{{ folder }}/new_points.svg");
        }"""
        self.window.raw_stylesheet += missing_style
        self.window._update_palette(None)

        # Storage for extra image metadata that are relevant to other layers.
        # These are updated anytime images are added to the Viewer
        # and passed on to the other layers upon creation.
        self._images_meta = dict()

    def on_change(self, event):
        if event.type == 'added':
            layer = event.item
            if isinstance(layer, Image):
                paths = layer.metadata.get('paths')
                if paths is None:
                    return
                # Store the metadata and pass them on to the other layers
                self._images_meta.update({'paths': paths,
                                          'shape': layer.shape})
                for layer_ in self.layers:
                    if not isinstance(layer_, Image):
                        self._remap_frame_indices(layer_)
                # Ensure the images are always underneath the other layers
                n_layers = len(self.layers)
                if n_layers > 1:
                    self.layers.move_selected(event.index, 0)
            elif isinstance(layer, KeyPoints):
                menu = DualDropdownMenu(layer)
                self._dropdown_menus.append(
                    self.window.add_dock_widget(menu, name='dropdown menus', area='bottom')
                )
                layer.smart_reset(event=None)  # Update current_label upon loading data
                self.bind_key('Down', layer.next_keypoint, overwrite=True)
                self.bind_key('Up', layer.prev_keypoint, overwrite=True)
        elif event.type == 'removed':
            layer = event.item
            if isinstance(layer, KeyPoints):
                while self._dropdown_menus:
                    menu = self._dropdown_menus.pop()
                    self.window.remove_dock_widget(menu)
            elif isinstance(layer, Image):
                self._images_meta = dict()

    @property
    def current_step(self):
        return self.dims.current_step[0]

    @property
    def n_steps(self):
        return self.dims.nsteps[0]

    def _remap_frame_indices(self, layer):
        if not self._images_meta:
            return

        new_paths = self._images_meta['paths']
        paths = layer.metadata.get('paths')
        if paths is not None and np.any(layer.data):
            paths_map = dict(zip(range(len(paths)), paths))
            # Discard data if there are missing frames
            missing = [
                i for i, path in paths_map.items() if path not in new_paths
            ]
            if missing:
                if isinstance(layer.data, list):
                    inds_to_remove = [i for i, verts in enumerate(layer.data)
                                      if verts[0, 0] in missing]
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

    def add_points(
        self,
        data=None,
        *,
        properties=None,
        text=None,
        symbol='o',
        size=10,
        edge_width=0,
        edge_color='black',
        edge_color_cycle=None,
        edge_colormap='viridis',
        edge_contrast_limits=None,
        face_color='white',
        face_color_cycle=None,
        face_colormap='viridis',
        face_contrast_limits=None,
        n_dimensional=False,
        name='keypoints',
        metadata=None,
        scale=None,
        translate=None,
        opacity=1,
        blending='translucent',
        visible=True,
    ):
        # Disable the creation of Points layers via the button
        if not properties:
            return

        # Only allow one KeyPoints layer to live at once
        if any(isinstance(layer, KeyPoints) for layer in self.layers):
            return

        if data is None:
            ndim = max(self.dims.ndim, 2)
            data = np.empty([0, ndim])

        layer = KeyPoints(
            data=data,
            viewer=self,
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

        # Hack to avoid napari's silly variable type guess,
        # where property is understood as continuous if
        # there are more than 16 unique categories...
        with layer.block_update_properties():
            layer.face_color = 'label'
        layer.face_color_mode = 'cycle'
        self.add_layer(layer)
        layer.mode = 'add'
        return layer

    def add_layer(self, layer):
        if not isinstance(layer, Image):
            self._remap_frame_indices(layer)
        return super(DLCViewer, self).add_layer(layer)

    def open(self,
        path,
        *,
        stack=False,
        plugin=None,
        layer_type=None,
        **kwargs,
    ):
        super(DLCViewer, self).open(
            handle_path(path),
            stack=stack,
            plugin=plugin,
            layer_type=layer_type,
            **kwargs
        )


def show():
    with napari.gui_qt():
        return DLCViewer()
