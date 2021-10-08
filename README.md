# Napari + DeepLabCut Annotation Tool

Welcome! This is an alpha release of our napari-based GUI for fast and interactive annotation of images for using with DeepLabCut. We will working towards a napari plug-in for annotation, but in the meantime you can use this as a stand-alone GUI! It allows you to load images from a project, annotate, and saves back into the proper spot in your DLC project folder. Please note, as this itself will not be developed as a stand-alone, we are open sourcing it to get community feedback. If you have a feature request, please open an issue! Thank you - teamDLC.


## Installation
### from source


First, you should have DeepLabCut installed as described at https://deeplabcut.github.io/DeepLabCut/docs/intro.html
Then, to clone the repository locally and install all required packages, use:
```sh
git clone --single-branch https://github.com/DeepLabCut/DeepLabCut-label.git
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
