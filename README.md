# Napari + DeepLabCut Annotation Tool

Welcome! This is an **alpha** release of a napari-based GUI for fast and interactive annotation of images with DeepLabCut. 

It allows you to load images from a DLC project, annotate, and saves back into the proper spot in your DLC project folder. 

## Use cases:

-  You should have DeepLabCut installed (see https://deeplabcut.github.io/DeepLabCut/docs/intro.html)
-  This GUI can be used as an alternative for the [(D) Labeling Frames GUI within DeepLabCut](https://deeplabcut.github.io/DeepLabCut/docs/standardDeepLabCut_UserGuide.html#d-label-frames) or the [(K) Refine Label GUI](https://deeplabcut.github.io/DeepLabCut/docs/standardDeepLabCut_UserGuide.html#k-refine-labels-augmentation-of-the-training-dataset).
-  In other words, complete steps A-C (from [here](https://deeplabcut.github.io/DeepLabCut/docs/standardDeepLabCut_UserGuide.html)) within DeepLabCut, then you can start labeling with this GUI, or re-start labeling with this GUI. You can also use this GUI for refinement of labels.

## Feedback welcome! 

-  We are working on a [napari plug-in](https://napari.org/plugins/stable/) for annotation that will ultimately replace this, but in the meantime you can already use this alpha-version as a stand-alone GUI.
-  Please note, this GUI will not be developed further as a stand-alone, but we are open-sourcing it to get community feedback, which we will consider for the plugin. *If you have a feature request or comment, please open an issue!*


## Installation Instructions:

- Open the terminal (and consider what directory you are in) and run the following, which will clone the repository locally and install all required packages:
```sh
git clone --single-branch https://github.com/DeepLabCut/DeepLabCut-label.git
cd DeepLabCut-label
conda env create -f environment.yml
conda activate dlclabel
```

## Open GUI & Usage:

```
ipython (or pythonw for macOS users)
import dlclabel
dlclabel.show()
```
All accepted files (config.yaml, images, data files, list of polygon vertices) can be loaded 
either by dropping them directly onto the canvas or via the File menu.

The easiest way to get started is to drop a folder (typically a folder from within a DeepLabCut' projects `labeled-data` directory), and, if labeling from scratch, drop the corresponding `config.yaml` to automatically add a` KeyPoints layer` and populate the dropdown menus.

**Tools & shortcuts are:**

- `P` and `S`, to easily switch between labeling and selection mode
- `M`, to cycle through regular (sequential), quick, and cycle annotation mode (see the description [here](https://github.com/DeepLabCut/DeepLabCut-label/blob/ee71b0e15018228c98db3b88769e8a8f4e2c0454/dlclabel/layers.py#L9-L19))
- `Z`, to enable pan & zoom (which is achieved using the mouse wheel or finger scrolling on the Trackpad)
- `E`, to enable edge coloring (by default, if using this in refinement GUI mode, points with a confidence lower than 0.6 are marked
in red)
- `F`, to toggle between animal and bodypart color scheme. 
- `backspace` to delete a point.
- Check the box "display text" to show the label names on the canvas.
- To move to another folder, be sure to save (Ctrl+S), then delete the layers, and re-drag/drop the next folder.

**Mini Demo:**

<p align="center">
<img src="https://images.squarespace-cdn.com/content/v1/57f6d51c9f74566f55ecf271/1634122074646-E235DDG75MCO0BBZER95/dlclabeldemo.gif?format=1500w" width="55%">
</p>

To draw masks, simply add a `Shapes layer` and start drawing polygons over the images. Note, these would not currently be used within DeepLabCut, but could be useful for other applications.

**Save:**

Annotations and segmentations are saved with `File > Save Selected Layer(s)...`
(or its shortcut `Ctrl+S`). For convenience, the save file dialog opens automatically into the folder containing your images or your h5 data file. 
- As a reminder, DLC will only use the H5 file; so be sure if you open already labeled images you save/overwrite the H5. If you label from scratch, you should save the file as `CollectedData_YourName.h5`
- Note that when saving segmentation masks, data will be stored into
a folder bearing the name provided in the dialog window.
- Note,  before selecting `save layer` as as (or `ctrl-S`) make sure the key points layer is selected. If the user clicked on the image(s) layer first, does save as, then closes the window, any labeling work during that session will be lost!
