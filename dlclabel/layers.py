import numpy as np
from collections import namedtuple
from dlclabel.misc import CycleEnum
from enum import auto
from napari.layers import Points
from napari.utils.events import Event
from napari.utils.status_messages import format_float
from typing import List, Sequence, Union


class LabelMode(CycleEnum):
    """
    Labeling modes.

    SEQUENTIAL: points are placed in sequence, then frame after frame;
        clicking to add an already annotated point has no effect.
    QUICK: similar to SEQUENTIAL, but trying to add an already
        annotated point actually moves it to the cursor location.
    LOOP: the first point is placed frame by frame, then it wraps
        to the next label at the end and restart from frame 1, etc.
    """

    SEQUENTIAL = auto()
    QUICK = auto()
    LOOP = auto()

    @classmethod
    def default(cls):
        return cls.SEQUENTIAL


KeyPoint = namedtuple("KeyPoint", ["label", "id"])


class KeyPoints(Points):
    def __init__(self, data=None, **kwargs):
        if data is None:
            data = np.empty([0, 3])
        super(KeyPoints, self).__init__(data, **kwargs)
        self.class_keymap.update(
            super(KeyPoints, self).class_keymap
        )  # Inherit parent class' key bindings
        all_pairs = self.metadata["header"].form_individual_bodypart_pairs()
        self._keypoints = [
            KeyPoint(label, id_) for id_, label in all_pairs
        ]  # Ordered references to all possible keypoints
        self._label_mode = LabelMode.default()
        self._text.visible = False

        # Hack to make text annotation work when labeling from scratch
        if self.text.values is None:
            text = kwargs["text"]
            fake_text = {"text": text, "n_text": 1, "properties": {text: np.array([])}}
            self.text._set_text(**fake_text)

        # Remap face colors to guarantee original ordering
        self._face_color_property = "label"
        self.refresh_color_cycle_map()
        # Ensure red are invalid (low confidence) keypoints
        self.edge_color_cycle_map = {
            True: np.array([0, 0, 0, 1]),
            False: np.array([1, 0, 0, 1]),
        }

        self.events.add(query_next_frame=Event)

    @Points.bind_key("E")
    def toggle_edge_color(self):
        self.edge_width ^= 2  # Trick to toggle between 0 and 2

    @Points.bind_key("F")
    def toggle_face_color(self):
        self._face_color_property = (
            "label" if self._face_color_property == "id" else "id"
        )
        self.refresh_color_cycle_map()

    def refresh_color_cycle_map(self):
        self.face_color_cycle_map = self.metadata["face_color_cycle_maps"][
            self._face_color_property
        ]
        self._refresh_color("face", False)

    @Points.bind_key("M")
    def cycle_through_label_modes(self):
        self.label_mode = next(LabelMode)

    @property
    def label_mode(self) -> str:
        return str(self._label_mode)

    @label_mode.setter
    def label_mode(self, mode: Union[str, LabelMode]):
        self._label_mode = LabelMode(mode)
        self.status = self.label_mode

    @property
    def _type_string(self):
        # Fool the writer plugin
        return "points"

    @property
    def labels(self) -> List[str]:
        return self.metadata["header"].bodyparts

    @property
    def current_label(self) -> str:
        return self.current_properties["label"][0]

    @current_label.setter
    def current_label(self, label: str):
        if not len(self.selected_data):
            current_properties = self.current_properties
            current_properties["label"] = np.asarray([label])
            self.current_properties = current_properties

    @property
    def ids(self) -> List[str]:
        return self.metadata["header"].individuals

    @property
    def current_id(self) -> str:
        return self.current_properties["id"][0]

    @current_id.setter
    def current_id(self, id_: str):
        if not len(self.selected_data):
            current_properties = self.current_properties
            current_properties["id"] = np.asarray([id_])
            self.current_properties = current_properties

    @property
    def annotated_keypoints(self) -> List[KeyPoint]:
        mask = self.current_mask
        keys = self.properties.keys()
        keypoints = []
        for values in zip(*[v[mask] for v in self.properties.values()]):
            dict_ = dict(zip(keys, values))
            keypoints.append(KeyPoint(label=dict_["label"], id=dict_["id"]))
        return keypoints

    @property
    def current_keypoint(self) -> KeyPoint:
        props = self.current_properties
        return KeyPoint(label=props["label"][0], id=props["id"][0])

    @current_keypoint.setter
    def current_keypoint(self, keypoint: KeyPoint):
        # Avoid changing the properties of a selected point
        if not len(self.selected_data):
            current_properties = self.current_properties
            current_properties["label"] = np.asarray([keypoint.label])
            current_properties["id"] = np.asarray([keypoint.id])
            self.current_properties = current_properties

    def add(self, coord):
        if self.current_keypoint not in self.annotated_keypoints:
            super(KeyPoints, self).add(coord)
        elif self._label_mode is LabelMode.QUICK:
            ind = self.annotated_keypoints.index(self.current_keypoint)
            data = self.data
            data[np.flatnonzero(self.current_mask)[ind]] = coord
            self.data = data
        self.selected_data = set()
        if self._label_mode is LabelMode.LOOP:
            self.events.query_next_frame()
        else:
            self.next_keypoint()

    @Points.current_size.setter
    def current_size(self, size: int):
        """Resize all points at once regardless of the current selection."""
        self._current_size = size
        if self._update_properties:
            self.size = (self.size > 0) * size
            self.refresh()
            self.events.size()
        self.status = format_float(self.current_size)

    def smart_reset(self, event):
        """Set current keypoint to the first unlabeled one."""
        unannotated = ""
        already_annotated = self.annotated_keypoints
        for keypoint in self._keypoints:
            if keypoint not in already_annotated:
                unannotated = keypoint
                break
        self.current_keypoint = unannotated if unannotated else self._keypoints[0]

    def next_keypoint(self, *args):
        ind = self._keypoints.index(self.current_keypoint) + 1
        if ind <= len(self._keypoints) - 1:
            self.current_keypoint = self._keypoints[ind]

    def prev_keypoint(self, *args):
        ind = self._keypoints.index(self.current_keypoint) - 1
        if ind >= 0:
            self.current_keypoint = self._keypoints[ind]

    @property
    def current_mask(self) -> Sequence[bool]:
        return np.asarray(self.data[:, 0] == self._slice_indices[0])

    def _paste_data(self):
        """Paste only currently unannotated data."""
        properties = self._clipboard.get("properties")
        if properties is None:
            return
        unannotated = [
            KeyPoint(label, id_) not in self.annotated_keypoints
            for label, id_ in zip(properties["label"], properties["id"])
        ]
        new_properties = {k: v[unannotated] for k, v in properties.items()}
        new_indices = self._clipboard["indices"][:1] + tuple(
            inds
            for inds, keep in zip(self._clipboard["indices"][1:], unannotated)
            if keep
        )
        self._clipboard.pop("properties")
        self._clipboard.pop("indices")
        self._clipboard = {k: v[unannotated] for k, v in self._clipboard.items()}
        self._clipboard["properties"] = new_properties
        self._clipboard["indices"] = new_indices
        super(KeyPoints, self)._paste_data()
