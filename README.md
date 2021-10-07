# DeepLabCut-label

A napari-based GUI for fast and interactive annotation and segmentation of images.

## Installation
### from source

We recommend the use of anaconda (or miniconda).
To clone the repository locally and install all required packages, use:
```sh
git clone --single-branch https://github.com/jeylau/DeepLabCut-label.git
cd DeepLabCut-label
conda env create -f environment.yml
conda activate dlclabel
```

## Use

The GUI is opened with:
```
ipython
import dlclabel
dlclabel.show()
```
All accepted files (config.yaml, images, data files, list of polygon vertices) can be loaded 
either by dropping them directly onto the canvas or via the File menu.
The easiest way to get started is to drop a folder (typically from the DeepLabCut
labeled-data directory), and—if labeling from scratch—the corresponding config.yaml
to automatically add a KeyPoints layer and populate the dropdown menus.

Some useful shortcuts are:
P and S, to easily switch between labeling and selection mode;
M, to cycle through regular (sequential), quick, and cycle annotation mode (see the description [here](https://github.com/jeylau/DeepLabCut-label/blob/ee71b0e15018228c98db3b88769e8a8f4e2c0454/dlclabel/layers.py#L9-L19));
Z, to enable pan & zoom (which is achieved using the mouse wheel or finger scrolling on the Trackpad);
E, to enable edge coloring (by default, points with a confidence lower than 0.6 are marked
in red); F, to toggle between animal and bodypart color scheme. 

To draw masks, simply add a Shapes layer and start drawing polygons over the images.

Annotations and segmentations are saved with File > Save Selected Layer(s)...
(or its shortcut Ctrl+S). Note that when saving segmentation masks, data will be stored into
a folder bearing the name provided in the dialog window.
