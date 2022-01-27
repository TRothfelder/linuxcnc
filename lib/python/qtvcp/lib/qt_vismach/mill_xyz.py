#!/usr/bin/env python3

# Rolf Redford, Nov 2018
# modded for qtvcp Chris Morley 2020

import sys
import hal
from .qt_vismach import *

# ---------------------------------------------------------------------------------------------------------------------------------- Starting and defining

# model is built in metric
# if using a imperial config need to scale movement
METRIC = 1
IMPERIAL = 25.4
MODEL_SCALING = IMPERIAL

# used for diameter for versions less than 2.8.
# it gives us way to access variable values from vismach script.
# import linuxcnc
# s = linuxcnc.stat()
# s.poll()

# Here is where we define pins that linuxcnc will send
# data to, in order to make movements.
# We will need 5 pins, 3 for motion and 2 for tool stats.
# tooldiameter isn't really used but if you are using 2.8 you can make couple changes
# in this file, and uncomment last line in HAL file.
# add joints. Mill has 3.
# c = hal.component("3axis-tutorial-test")
# tells loadusr pins is ready
# c.ready()

# we are not using a component but the original code requires a variable
c = None

# Used for tool cylinder
# it will be updated in shape and length by function below.
toolshape = CylinderZ(0)
toolshape = Color([1, .5, .5, .5], [toolshape])


# updates tool cylinder shape.
class HalToolCylinder(CylinderZ):
    def __init__(self, comp, *args):
        # get machine access so it can
        # change itself as it runs
        # specifically tool cylinder in this case.
        CylinderZ.__init__(self, *args)
        self.comp = c

    def coords(self):
        # update data -  not needed if using 2.8 and self.comp["tooldiameter"]
        # 2.7 does not have direct pin for diameter so this is workaround. commented out code is direct way to do it.
        # s.poll() # 2.8 don't need this, comment out if using 2.8.
        # get diameter and divide by 2 to get radius.
        # rad = ( s.tool_table[s.tool_in_spindle].diameter ) # 2.7 workaround
        try:
            dia = (hal.get_value('halui.tool.diameter') * MODEL_SCALING)
        except:
            dia = 0
        rad = dia / 2  # change to rad
        # this instantly updates tool model but tooltip doesn't move till -
        # tooltip, the drawing point will NOT move till g43h(tool number) is called, however.
        # Tool will "crash" if h and tool length does not match.
        try:
            leng = hal.get_value('motion.tooloffset.z') * MODEL_SCALING
        except:
            leng = 0
        # Update tool length when g43h(toolnumber) is called, otherwise stays at 0 or previous size.
        # commented out as I prefer machine to show actual tool size right away.
        # leng = self.comp["toollength"]
        return (-leng, rad, 0, rad)


# ----------------------------------------------------------------------------------------------------------------------------------
# Concept of machine design

# The model follows logical tree design - picture the tree, with branch and smaller branches off it
# if you move the larger branch, smaller branches will move with it, but if you move smaller branch larger will not.
#
# Machine design follows that conceptal design, so for example if you move X, it can move on its own, but if you move Y,
# it will also move X assembly, as it is attached to Y assembly.
# so for this machine, tree looks like this:

# model
#   |
#   |---frame
#   |     |
#   |     |---base
#   |     |
#   |     |---column
#   |     |
#   |     |---top
#   |
#   |
#   |---yassembly
#   |      |
#   |      |
#   |      |---xassembly
#   |      |      |
#   |      |      |
#   |      |      |---xbase
#   |      |      |
#   |      |      |---work
#   |      |
#   |      |
#   |      |---ybase
#   |
#   |
#   |---zassembly
#           |
#           |
#           |---zframe
#           |     |
#           |     |---zbody
#           |     |
#           |     |---spindle
#           |
#           |
#           |---toolassembly
#                     |
#                     |---cat30
#                     |
#                     |---tool
#                          |
#                          |---tooltip
#                          |
#                          |---(tool cylinder function)

# As you can see, lowest parts must exist first before it can be grouped with others into assembly.
# So you build upwards from lowest point in tree and assembly them together.
# Same is applicable for any design of machine. Look at machine arm example and you will see that it starts
# with tip and adds to larger part of arm then it finally groups with base.


# ----------------------------------------------------------------------------------------------------------------------------------
# Starting with fixed frame

# start creating base itself, floor and column for z. box is centered on 0,0,0
base = BoxCentered(200, 560, 20)
# translate it so top of base is at zero
base = Translate([base], 0, 0, -10)

# column, attached to base on side. 
# Box() accepts extents
# ie -100 to 100 is 200 wide, and rightmost is at -100 on coord.
#        Box(x rightmost, y futherest, z lowest, x leftmost, y nearest, z highest)
column = Box(-60, -260, 0, 60, -200, 400)

# add block on top
# not really needed, but I like how it looks with it.
# bare column looks little bit strange for some reason.
top = Box(-80, -280, 400, 80, -160, 440)

# now fuse it into "frame"
frame = Collection([base, column, top])
# color it grayish
frame = Color([.8, .8, .8, 1], [frame])

# ----------------------------------------------------------------------------------------------------------------------------------
# Moving parts section

# Start with X, Y then finally Z with tool and spindle.

# X table addition
xbase = BoxCentered(1000, 200, 30)
# let's color it blue
xbase = Color([0, 0, 1, 1], [xbase])
# Move table so top is at zero for now,
# so work (default 0,0,0) is on top of table.
xbase = Translate([xbase], 0, 0, -15)

# now create work which would be defined by Linuxcnc.
# I suspect we would need to define shape but not enough is known.
# for now just create an point that would be bottom center of stock.
work = Capture()

# group work and xbase together so they move together.
xassembly = Collection([xbase, work])
# work is now defined and grouped, and default at 0,0,0, or
# currently on top of x part table.
# so we move table group upwards, taking work with it.
xassembly = Translate([xassembly], 0, 0, 35)

# Must define part motion before it becomes part of collection.
# Must have arguments, object itself, c (defined above), then finally scale from the pin to x y z.
# since this moves solely on X axis, only x is 1, rest is zero.
# you could use fractions for say axis that moves in compound like arm for example
# but this machine is very simple, so all axis will be purely full on axis and zero on other axis.
xassembly = HalTranslate([xassembly], c, "joint.0.pos-fb", MODEL_SCALING, 0, 0, direct=1)

# Y assembly creation
ybase = BoxCentered(200, 200, 10)
# colorize it green so we can see it separate from frame.
ybase = Color([0, 1, 0, 1], [ybase])
# don't define translation for this one, as y also moves X table.
# translating this would move itself alone. You want it to move X parts also.

# X table is moved by Y base, so we have to make X child of Y.
# now define collection of ybase and xassembly.
yassembly = Collection([ybase, xassembly])
# define its motion first before translate.
yassembly = HalTranslate([yassembly], c, "joint.1.pos-fb", 0, MODEL_SCALING, 0, direct=1)
# Now that translate is locked with part, 
# move it upwards so its on frame base.
yassembly = Translate([yassembly], 0, 0, 5)

# spindle head
# define small cylinder where tool will be attached to.
# It is shallow, basically exposed end of "cat30" toolholder.
# let's pretend machine uses cat30.
cat30 = CylinderZ(0, 30, 20, 40)  # cone wider top smaller bottom
# color it red, as in danger, tool!
cat30 = Color([1, 0, 0, 1], [cat30])

# Define tool and grab such model information from linuxcnc
# tooltip is initially in vismach "world" 0,0,0. 
# what it does is place where line drawing is in world, so
# you can see where machine think tip of tool is.
# first capture it, so we can use it and move it to where
# defined end of tool is.
tooltip = Capture()

# Now that we have tooltip, let's attach it to cylinder function (see above)
# it creates cylinder then translates tooltip to end of it.
tool = Collection([
    Translate([HalTranslate([tooltip], c, "motion.tooloffset.z", 0, 0, -MODEL_SCALING, direct=1)], 0, 0, 0),
    HalToolCylinder(toolshape)
])

# Since tool is defined, lets attach it to cat30
# Group cat30 and tooltip
toolassembly = Collection([cat30, tool])
# now that tool is properly attached, we can move it
# and tool will "move" with it now.
# BUT we need to build rest of head in such way that TOP of head is defined as Z zero.
# Move it so it attaches to bottom of spindle body.
toolassembly = Translate([toolassembly], 0, 0, -120)

# Start building Z assembly head, including spindle and support
# top is at zero as I want top to be defined as Z home top.
spindle = CylinderZ(-100, 60, 0, 60)  # top is at zero
# define rest of head using Box
zbody = Box(-30, -200, 0, 30, 0, -100)

# fuse into z assembly
zframe = Collection([zbody, spindle])
# color it yellow
zframe = Color([1, 1, 0, 1], [zframe])

# Now that all parts are created, let's group it and finally make Z motion
zassembly = Collection([zframe, toolassembly])
# define Z motion
zassembly = HalTranslate([zassembly], c, "joint.2.pos-fb", 0, 0, MODEL_SCALING, direct=1)
# Now that motion is defined,
# we can now move it to Z home position.
zassembly = Translate([zassembly], 0, 0, 400)

# ----------------------------------------------------------------------------------------------------------------------------------
# Getting it all together and finishing model

# Assembly everything into single model.
# xassembly is already included into yassembly so don't need to include it.
model = Collection([frame, yassembly, zassembly])


# Finally, call main() with parameter to let linuxcnc know.
# parameter list:
# final model name must include all parts you want to use
# tooltip (special for tool tip inclusuion)
# work (special for work part inclusion)
# size of screen (bigger means more zoomed out to show more of machine)
# last 2 is where view point source is.
# main(model, tooltip, work, 600, lat=-75, lon=215)

# we want to embed with qtvcp so build a window to display
# the model
class Window(QWidget):

    def __init__(self):
        super(Window, self).__init__()
        self.glWidget = GLWidget()
        v = self.glWidget
        v.set_latitudelimits(-180, 180)

        world = Capture()

        v.model = Collection([model, world])
        size = 600
        v.distance = size * 3
        v.near = size * 0.01
        v.far = size * 10.0
        v.tool2view = tooltip
        v.world2view = world
        v.work2view = work

        mainLayout = QHBoxLayout()
        mainLayout.addWidget(self.glWidget)
        self.setLayout(mainLayout)


# but it you call this directly it should work too

if __name__ == '__main__':
    from PyQt5.QtWidgets import (QApplication, QWidget)

    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
