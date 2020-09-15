import napari
import numpy as np
from dlclabel.io import handle_path
from dlclabel.layers import KeyPoints
from dlclabel.misc import get_first_layer_of_type
from dlclabel.widgets import DualDropdownMenu
from napari.layers import Image


# TODO Draw polygon on area on mouse drag
# TODO Add vectors for paths trajectory
# TODO Add video reader plugin


class DLCViewer(napari.Viewer):
    def __init__(self):
        super(DLCViewer, self).__init__(title='deeplabcut')
        self.theme = 'light'
        self.class_keymap.update(super(DLCViewer, self).class_keymap)
        self.layers.events.added.connect(self.on_add)
        self.layers.events.removed.connect(self.on_remove)
        self._dropdown_menus = []

        # Hack the QSS style sheet to add a KeyPoints layer type icon
        missing_style = """\n\nQLabel#KeyPoints {
          image: url(":/themes/{{ folder }}/new_points.svg");
        }"""
        self.window.raw_stylesheet += missing_style
        self.window._update_palette(None)

    @property
    def current_step(self):
        return self.dims.current_step[0]

    @property
    def n_steps(self):
        return self.dims.nsteps[0]

    def on_add(self, event):
        layer = event.item
        if isinstance(layer, KeyPoints):
            menu = DualDropdownMenu(layer)
            self._dropdown_menus.append(
                self.window.add_dock_widget(menu, area='bottom')
            )
            layer.smart_reset(event=None)  # Update current_label upon loading data
            self.bind_key('Down', layer.next_keypoint, overwrite=True)
            self.bind_key('Up', layer.prev_keypoint, overwrite=True)
            # Pass the image paths to the KeyPoints layer
            images_layer = get_first_layer_of_type(self.layers, Image)
            if images_layer is not None:
                layer._remap_frame_indices(images_layer.metadata['paths'])
        elif isinstance(layer, Image):
            if len(self.layers) > 1:
                self.layers.move_selected(index=-1, insert=0)
            keypoints_layer = get_first_layer_of_type(self.layers, KeyPoints)
            if keypoints_layer is not None:
                keypoints_layer._remap_frame_indices(layer.metadata['paths'])

    def on_remove(self, event):
        layer = event.item
        if isinstance(layer, KeyPoints):
            while self._dropdown_menus:
                menu = self._dropdown_menus.pop()
                self.window.remove_dock_widget(menu)

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


with napari.gui_qt():
    viewer = DLCViewer()
    # viewer.open('/Users/Jessy/Documents/PycharmProjects/lactic/lactic-jessy-2019-06-16/labeled-data/carllewis')
    viewer.open('/Users/Jessy/Documents/PycharmProjects/deeplabcut/datasets/MultiMouse-Daniel-2019-12-16/labeled-data/videocompressed0')
    # viewer.open('/Users/Jessy/Documents/PycharmProjects/deeplabcut/datasets/MultiMouse-Daniel-2019-12-16/config.yaml')
    # viewer.open('/Users/Jessy/Desktop/exp/multimouse/videocompressed0DLC_resnet50_MultiMouseDec16shuffle1_50000_el.h5')
