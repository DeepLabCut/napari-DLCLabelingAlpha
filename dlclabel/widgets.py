from collections import defaultdict
from PyQt5 import QtWidgets


class DropdownMenu(QtWidgets.QComboBox):
    def __init__(self, labels, parent=None):
        super(DropdownMenu, self).__init__(parent)
        self.addItems(labels)

    def update_to(self, text):
        index = self.findText(text)
        if index >= 0:
            self.setCurrentIndex(index)

    def reset(self):
        self.setCurrentIndex(0)


class DualDropdownMenu(QtWidgets.QWidget):
    def __init__(self, layer, parent=None):
        super(DualDropdownMenu, self).__init__(parent)
        self.layer = layer
        self.layer.events.current_properties.connect(self.update_menus)

        # Map individuals to their respective bodyparts
        self.id2label = defaultdict(list)
        for keypoint in layer.all_keypoints:
            label = keypoint.label
            id_ = keypoint.id
            if label not in self.id2label[id_]:
                self.id2label[id_].append(label)

        self.menus = dict()
        if layer.ids[0]:
            menu = create_dropdown_menu(layer, list(self.id2label), "id")
            menu.currentTextChanged.connect(self.refresh_label_menu)
            self.menus["id"] = menu
        self.menus["label"] = create_dropdown_menu(
            layer, self.id2label[layer.ids[0]], "label"
        )
        layout = QtWidgets.QHBoxLayout()
        for menu in self.menus.values():
            layout.addWidget(menu)
        self.setLayout(layout)

    def update_menus(self, event):
        keypoint = self.layer.current_keypoint
        for attr, menu in self.menus.items():
            val = getattr(keypoint, attr)
            if menu.currentText() != val:
                menu.update_to(val)

    def refresh_label_menu(self, text):
        menu = self.menus["label"]
        menu.blockSignals(True)
        menu.clear()
        menu.addItems(self.id2label[text])
        menu.blockSignals(False)


def create_dropdown_menu(layer, items, attr):
    menu = DropdownMenu(items)

    def item_changed(ind):
        current_item = menu.itemText(ind)
        if current_item is not None:
            setattr(layer, f"current_{attr}", current_item)

    menu.currentIndexChanged.connect(item_changed)
    return menu
