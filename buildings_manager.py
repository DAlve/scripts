import math
from math import sqrt, pow
import random

import maya.cmds as cmds




def _create_height_ctrl(radius = 10000, height=10000):
    """
    creates a height controller circle
    """

    height_ctrls = '_height_ctrls'

    if not cmds.ls(height_ctrls):
        cmds.group(empty=True, n=height_ctrls)


    # create our height control
    height_ctrl = cmds.circle()
    for i in ['x', 'y', 'z']:
        cmds.setAttr('{}.s{}'.format(height_ctrl[0], i), radius)

    cmds.addAttr(height_ctrl[0], ln='height', dv=height)

    cmds.parent(height_ctrl[0], height_ctrls)



def extrude_building(building=None, height=None):
    """
    Given an object will extrude it upwards
    """

    building_face = '{}.f[0]'.format(building)

    if not height:
        building_scale = math.ceil(cmds.polyEvaluate(building_face, worldArea=True)/1000000)
        if building_scale > 12:
            building_scale = 12

        num_stories = math.floor(random.uniform(1, 3))*building_scale

        height = 450 * num_stories

    cmds.polyExtrudeFacet(building_face, kft=True, ltz=height, sma=0)
    cmds.polyNormalPerVertex(building, ufn=True)


def build():
    """
    Builds the current scene
    """

    ctrls = []

    # get the height control and buildings group
    height_ctrl_grp = cmds.ls('_height_ctrls')
    buildings_grp = cmds.ls('_buildings')

    if not height_ctrl_grp:
        print "Couldn't find height control group!"
        return
    else:
        height_ctrl_grp = height_ctrl_grp[0]

    if not buildings_grp:
        print "Couldn't find buildings group!"
        return
    else:
        buildings_grp = buildings_grp[0]


    # go through the objects in our height ctrls group and get the data that we need from them
    for i in cmds.listRelatives(height_ctrl_grp, children=True):

        data = {}

        data['ctrl_pos'] = cmds.getAttr('{}.translate'.format(i))[0]
        data['ctrl_radius'] = cmds.getAttr('{}.sx'.format(i))
        data['ctrl_height'] = cmds.getAttr('{}.height'.format(i))
        data['ctrl_name'] = i

        ctrls.append(data)

    buildings = []

    # go through each building and see if it is in range of the ctrl
    for bld in cmds.listRelatives(buildings_grp, children=True):
        bld_pos = cmds.xform(bld, q=True, rp=True, ws=True)

        heights = []

        for ctrl in ctrls:
            ctrl_pos = ctrl['ctrl_pos']
            ctrl_radius = ctrl['ctrl_radius']
            ctrl_height = ctrl['ctrl_height']

            mag = get_mag(ctrl_pos, bld_pos)
            mag_ratio = 1 - (mag / ctrl_radius)

            #if mag_ratio < 1 and> 0:
            if 0 <= mag_ratio <= 1:
                height = ctrl_height * mag_ratio
                heights.append(height)

        if heights:

            bld_height = sum(heights) / len(heights)

            print '{} in radius! Extrude {}'.format(bld, bld_height)

            extrude_building(bld, bld_height)

            buildings.append(bld)





    cmds.select(buildings)




def get_mag(objA, objB):
    """
    Takes 2 vectors and gets the magnitude between them
    """
    return sqrt(
        pow(objA[0] - objB[0], 2) + pow(objA[1] - objB[1], 2) +
        pow(objA[2] - objB[2], 2))
