# Napari + DeepLabCut Annotation Tool

Welcome! This is an **alpha** release of a napari-based GUI for fast and interactive annotation of images with DeepLabCut. 

It allows you to load images from a DLC project, annotate, and saves back into the proper spot in your DLC project folder. 

## News:

- The new napari-plugin is nearly ready for use; please see https://github.com/DeepLabCut/napari-deeplabcut for more information. Thank you to the alpha testers of this repo for feedback that helped guide the plugin development lead by [Jessy Lauer](https://github.com/jeylau), and CZI for funding the plugin work!

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

### Save Layers

Annotations and segmentations are saved with `File > Save Selected Layer(s)...`
(or its shortcut `Ctrl+S`). For convenience, the save file dialog opens automatically into the folder containing your images or your h5 data file. 
- As a reminder, DLC will only use the H5 file; so be sure if you open already labeled images you save/overwrite the H5. If you label from scratch, you should save the file as `CollectedData_YourName.h5`
- Note that when saving segmentation masks, data will be stored into
a folder bearing the name provided in the dialog window.
- Note,  before selecting `save layer` as as (or `Ctrl+S`) make sure the key points layer is selected. If the user clicked on the image(s) layer first, does save as, then closes the window, any labeling work during that session will be lost!

## Workflow

Suggested workflows, depending on the image folder contents:

1. **Labelling from scratch** – the image folder does not contain `CollectedData_<ScorerName>.h5` file.

    Open *napari* as described in [Open GUI & Usage](#open-gui--usage) and open an image folder together with the DeepLabCut project's `config.yaml`.
    The image folder creates an *image layer* with the images to label.
    Supported image formats are: `jpg`, `jpeg`, `png`.
    The `config.yaml` file creates a *keypoints layer*, which holds metadata (such as keypoints read from the config file) necessary for labelling.
    Select the *keypoints layer* in the layer list (lower left pane on the GUI) and click on the *+*-symbol in the layer controls menu (upper left pane) to start labelling.
    The current keypoint can be viewed/selected in the keypoints menu (bottom pane).
    The slider below the displayed image (right pane) allows selecting the image to label.

    To save the labelling progress refer to [Save Layers](#save-layers).
    If the console window does not display any errors, the image folder should now contain a `CollectedData_<ScorerName>.h5` file.
    (Note: For convenience, a CSV file with the same name is also saved.)

1. **Resuming labelling** – the image folder contains a `CollectedData_<ScorerName>.h5` file.

    Open *napari* and open an image folder (which needs to contain a `CollectedData_<ScorerName>.h5` file).
    In this case, it is not necessary to open the DLC project's `config.yaml` file, as all necessary metadata is read from the `h5` data file.

    Saving works as described in *1*.

1. **Refining labels** – the image folder contains a `machinelabels-iter<#>.h5` file.

    The process is analog to *2*.

### Labelling multiple image folders

Labelling multiple image folders has to be done in sequence, i.e., only one image folder can be opened at a time.
After labelling the images of a particular folder is done and the associated *keypoints layer* has been saved, *all* layers should be removed from the layers list (lower left pane on the GUI) by selecting them and clicking on the trashcan icon.
Now, another image folder can be labelled, following the process described in *1*, *2*, or *3*, depending on the particular image folder.

## Known Issues

### Cannot load image folder with single image file

The `pims` module fails to read images from a folder with only a single image.

The following error will be raised:

```python
ValueError: No plugin found capable of reading 'E:\\DLC-Project\\labeled-data\\label-from-scratch\\*.png'.
```

### Empty `CollectedData` file

If an image folder with an empty `CollectedData_<ScorerName>.h5` file gets opened, i.e.,
the file does not contain any annotation data, then the following error gets raised:

```python
ValueError: No plugin found capable of reading '/home/DLC-Project/labeled-data/image-folder/*.h5'.
```

### Saving keypoints layer without annotations

If none of the opened images has been annotated, the annotation data of the
keypoints layer is empty, causing the following error:

```python
TypeError: Cannot infer number of levels from empty list

The above exception was the direct cause of the following exception:
```
