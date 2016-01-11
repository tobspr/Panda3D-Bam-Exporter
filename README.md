# Panda3D BAM Exporter

This is a Blender plugin to export models to the `.bam` format, which can be loaded
into the <a href="https://github.com/panda3d/panda3d" target="_blank">Panda3D</a> engine.

It provides several advantages over <a target="_blank" href="https://github.com/09th/YABEE">YABEE</a> (which
is an exporter for the `.egg` format), mainly speed and smaller exported files.


### Installation

You need to clone the repositority, since it uses a submodule which will not be 
included when you use the `Download ZIP` button.

After cloning, make sure to execute `git submodule init` and then `git submodule update`.

If you want the preview to work, you need to adjust the path to the render pipeline
in `rp/generate.py`.


### Usage

After you installed the plugin, you should have an entry `File > Export > Panda3D (.bam)`.
You can also use the quick search, press `space` and then type `bam`.

If you click that entry, a standard exporter window will open, with several options
in the lower left. 

**TODO:** Write wiki entry about export options.


### Whats not working (yet)

- Animations
- Bones & Deforms

