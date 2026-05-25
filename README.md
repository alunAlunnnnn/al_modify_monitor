<div align="right">
  <strong>English</strong> | <a href="./README_CN.md">简体中文</a>
</div>


# AL Modify Monitor

**AL Modify Monitor** is a QGIS plugin designed to automatically track geometry modifications in vector data. When a feature's geometry (via translation, rotation, scaling, or vertex editing) is altered, the plugin automatically updates a designated status field to `1`. 



<br>

## Motivation

When validating, QA-ing, or correcting large-scale datasets, it's incredibly easy to lose track of which features have been modified and which haven't. Manually updating a status field after every single geometry tweak is tedious and error-prone. I built this "lazy" tool to reduce the manual overhead for GIS professionals who need to verify or correct massive amounts of spatial data. 

> **Note:** As of May 22, 2026, this is the initial release (v0.0.1). While it runs stably in my daily workflow, it hasn't undergone extensive long-term testing. Please remember to save your edits frequently. If you encounter bugs, feel free to open an issue or submit a PR. For urgent fixes, you can email me with detailed descriptions at [517308447@qq.com](mailto:517308447@qq.com) or alunzuishuai@gmail.com, and I will prioritize it when available.



<br>

## Core Features

* **Layer Selection:** Supports selecting single or multiple vector layers. Once tracking starts, the custom hotkeys configured in the "AL Modify Monitor" panel become active. Pressing the designated hotkey (number keys, numpad independent) will automatically populate the specified status field of the selected features with your custom value.
* **Status Field:** You can choose any existing field to record the status. If no field is selected, the plugin will automatically create a new numeric field named `al_check` with a default value of `0`.
* **Smart Symbology:** Upon clicking "Start Tracking", the plugin checks if the current layer is using a `Single Symbol` renderer. If so, it assumes you want visual feedback and automatically switches the symbology to `Categorized`. It then uses the active hotkey values to assign distinct colors/styles to modified features.



<br>

## Installation

**Method 1: QGIS Plugin Repository (Recommended)**
1. Open QGIS, go to `Plugins` > `Manage and Install Plugins...`
2. Search for **AL Modify Monitor** and click Install.

<img src="./README.assets/image-20260522170848120.png" alt="Plugin Repository Installation" style="zoom: 50%;" />

**Method 2: Manual Installation from Source**
1. Download the source code zip archive.
2. Extract the folder and place it into your QGIS plugins directory. 
   *(e.g., `C:\Users\alun\AppData\Roaming\QGIS\QGIS4\profiles\default\python\plugins\al_modify_monitor`)*

<img src="./README.assets/image-20260522171105391.png" alt="Manual Installation Path" style="zoom: 67%;" />



<br>

## Quick Start / Recommended Workflow

1. **Activate the Plugin:** Once installed and activated, the plugin icon will appear in your toolbar.
   
   <img src="./README.assets/image-20260522171524508.png" alt="Plugin Icon" style="zoom:50%;" />

   
   
2. **Load Data:** Add your target vector layer(s) into the current QGIS project.
   
   <img src="./README.assets/image-20260522172038041.png" alt="Load Data" style="zoom:50%;" />

   
   
3. **Initialize Tracking:** Select the layer and activate tracking. You don't need to manually select a status field, let the plugin create it automatically for the smoothest experience.
   
   <img src="./README.assets/image-20260522172342792.png" alt="Start Tracking" style="zoom: 50%;" />
   <img src="./README.assets/image-20260522172510217.png" alt="Tracking Active" style="zoom:33%;" />

   
   
4. **Edit Geometries:** Start editing. As you modify geometries, the affected features will automatically change color. By default, features with a status of `0` are red. Once edited, their status updates to `1` and they turn green.
   
   <img src="./README.assets/image-20260522172749237.png" alt="Geometry Editing Feedback" style="zoom:50%;" />

   
   
5. **Attribute-Only Updates via Hotkeys:** If you don't need to edit a feature's geometry but want to mark it as "checked" (changing its color), use your custom hotkeys. Select the feature(s) and press `1` to mark it as modified, or press `3` to assign a value of 3 (assuming you have activated hotkeys 1, 2, and 3 in the panel).
   
   <img src="./README.assets/image-20260522173658354.png" alt="Hotkey Usage" style="zoom:50%;" />
