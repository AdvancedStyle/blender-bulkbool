# Blender Bulk Bool Tool

This tool allows you to union lots of objects together in the most efficient manner.

Booleans in Blender are inherently slow, but this addon tries to optimize the order in which operations occur to get the best performance and results.

# Installation

1) Download the bulkbool.py to your computer.

2) Go to Blender -> Edit -> Perference -> Addons -> Install and select the bulkbool.py

3) Check the box to Enable "Bulk Bool" addon

# Usage

1) Select at least 2 objects in 3D Viewport

2) Click the "Edit" tab in the "N" side panel

3) Under Bulk Union click the "Union Selected Objects"


# Performance

On my system with 1000 objects having about 50% of them interconnected run time was about 10 seconds.

As compared to Bool Tools tooks so long I gave up after about 10 minutes, plus made a bunch of errors in the booleans.
