import maya.mel as mel
import maya.cmds as cmds
import maya.OpenMaya as om
import maya.OpenMayaFX as omfx

def set_goals():
    
    sel = cmds.ls(sl=True, l=True)
    
    # make sure we have at least two items 
    if len(sel) < 2:
        print 'Please select a nParticle system followed by the objects to set as goals'
        return
    
    elif len(sel) > 2:
        print 'For inital goal we want one particle system and one object to goal!'
        print 'Try again :)'
        return
    
    print sel
    
    # from the list make sure the first object is a nparticle system, get a handle on this
    # then remove from the list
    if not cmds.objectType(sel[0]) == 'nParticle':
        
        shape = cmds.listRelatives(sel[0])[0]
        
        if not cmds.objectType(shape) == 'nParticle':
            print 'Please select a nParticle system followed by objects to goal to!'
            return
        
        else:
            npSystem = sel.pop(0)
            npShape = shape 
    
    else:
        npShape = sel.pop(0)
        npSystem = cmds.listRelatives(npShape, parent=True, f=True)
        
    obj = sel[0]
        
    
    selList = om.MSelectionList()
    selList.add(npShape)
    
    npDag = om.MDagPath()
    npMObj = om.MObject()
    
    selList.getDependNode(0, npMObj)
    selList.getDagPath(0, npDag)
    
    npNode = om.MFnDependencyNode(npMObj)
    npFnPart = omfx.MFnParticleSystem(npDag)
    
    
    if _get_goal(npDag):
        print 'Particle system already has goal. For now we are only supporting one goal!'
        return
    
    cmds.goal(npSystem, g=obj, w=1)
    
    
    set_initial_state(npNode, npFnPart)
    
    print '#------------------------------#'
    
    creation_dynExpression = ('.goalV = 0;\n'
                              '.goalU = 0;\n'
                              '.goalWeight0PP = .2;\n'
                              '.verticalSpeedPP = rand(0.01, 0.1);\n'
                              '.rotationRatePP = rand(0.03, 0.05);\n'
                              '.jitterIntervalPP = 0;\n'
                              '.jitterStepPP = 0;\n'
                              '.jitterRangePP = 0;\n'
                              '.lifespanPP = 5;'
                              )
    runtime_dynExpression = ('.goalV += .verticalSpeedPP;\n'
                             '.goalU += .rotationRatePP;\n\n'
                             'if (.jitterIntervalPP > .jitterStepPP)\n'
                             '{\n'
                             '\t.jitterStepPP ++;\n'
                             '}\n'
                             'else\n' 
                             '{\n'
                             '\t.goalU += .jitterValuePP;\n'
                             '\t$hiRange = rand(0, .jitterRangePP);\n'
                             '\t$loRange = $hiRange * -1;\n'
                             '\t.jitterValuePP = rand($loRange, $hiRange);\n'
                             '\t.jitterStepPP = 0;\n'
                             '}\n\n'
                             'if (.goalU > 1)\n'
                             '{\n'
                             '\t.goalU -= 1;\n'
                             '}\n'
                             'else if(.goalU < 0)\n'
                             '{\n'
                             '\t.goalU += 1;\n'
                             '}')

    cmds.dynExpression(npShape, creation=True, string=creation_dynExpression)                            
    cmds.dynExpression(npShape, rbd=True,  string=runtime_dynExpression)
    
    # now we want to make our goal object a passive rigid body so that
    # the particles don't go through it
    cmds.select(obj)
    
    print 'Selection is: %s' % cmds.ls(sl=True)
    
    # make our goal object a passive rigid body so the particles 
    # can collide with it
    cmd = 'makeCollideNCloth'
    rigidShape = mel.eval(cmd)
    
    # rigid shape is not created if it already exists!
    if rigidShape:
        # parent the rigid body to keep things tidy
        nRigid = cmds.listRelatives(rigidShape[0], parent=True, f=True)
        #cmds.parent(nRigid, dynamics_grp)
    
    # select our particle system to tidy things up
    cmds.select(npSystem)


def _get_goal(dg):
    """
    Gets the mObjects that are attached to the goalGeometry of an 
    nParticleSystem
    :param dg: dagPath of object we are looking for goals for
    :return: returns the first goal that we find or none if we can't find one
    """    
    
    print '#---------------------#'
    print 'Getting goal'
    
    if not dg:
        print '###Error: Either a dependency node or dagPath needs to be passed in to get goal!'
        return
        
    dg.extendToShape()
    mObj = dg.node()
    
    npNode = om.MFnDependencyNode(mObj)
    
    print npNode.name()
    
    # get the goalGeometry plug. this can tell us what our
    # particle is goaled to
    goalGeo_plug = npNode.findPlug('goalGeometry')
    
    # if we don't find the plug return empty
    if not goalGeo_plug:
        print 'Could not find goalGeometry attribute!'
        return
    
    # check the number of connections we have
    connections = goalGeo_plug.numConnectedElements()
    
    # if not connections return empty
    if connections == 0:
        print 'No goals are attached to this node!'
        return
    
    # if we have more than one connection tell user that we are 
    # going to return first goal
    elif connections > 1:
        print 'Found more than one goal. Looking for first goal!'
    
    
    # get the element plug that is connected to something
    goal_plug = goalGeo_plug.elementByPhysicalIndex(0)
    
    # find all plugs that are comming into this plug
    mPlugArray = om.MPlugArray()
    goal_plug.connectedTo(mPlugArray, True, False)
    
    # if we have more than one plug connected through weird error!
    if mPlugArray.length() > 1:
        print '###Error :More than one object is connected to this goal plug. Weird!'
        return
    
    goal_obj = mPlugArray[0].node()
    
    return goal_obj

def set_initial_state(npNode=None, npFnPart=None):
    """
    Given a particle dependency node calculate the start goalU and and goalV values
    :param npNode: Particle dependency node to get goal data from
    :param npFnPart: particle function set we can get the points from and set data
    """
    print '#----------------------------#'
    print 'Setting initial state'
    
    # before we start set the time back to the first frame
    tMin = int(cmds.playbackOptions(q=True, minTime=True))
    cmds.currentTime(tMin, e=True)
    
    # a dict of all the base attributes we want to make sure exist!
    attrs = {'goalU': {'longName': 'goalU',
                       'shortName': 'goalU',
                       'initialState':True,  
                       'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                       'data': om.MDoubleArray()},
             'goalV': {'longName': 'goalV',
                       'shortName': 'goalV',
                       'initialState':True,
                       'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                       'data': om.MDoubleArray()},
             'verticalSpeedPP': {'longName': 'verticalSpeedPP',
                                 'shortName': 'vSpePP',
                                 'initialState':True,
                                 'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                                 'data': om.MDoubleArray()},
             'rotationRatePP': {'longName': 'rotationRatePP',
                                  'shortName': 'rotRtPP',
                                  'initialState':True,
                                  'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                                  'data': om.MDoubleArray()},
             'jitterIntervalPP': {'longName': 'jitterIntervalPP',
                                  'shortName': 'jtrIntPP',
                                  'initialState':True,
                                  'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                                  'data': om.MDoubleArray()},
             'jitterStepPP': {'longName': 'jitterStepPP',
                              'shortName': 'jtrStpPP',
                              'initialState':True,
                              'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                              'data': om.MDoubleArray()},
             'jitterRangePP': {'longName': 'jitterRangePP',
                               'shortName': 'jtrRngPP',
                               'initialState': True,
                               'type': om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                               'data': om.MDoubleArray()},
             'jitterValuePP': {'longName': 'jitterValuePP',
                               'shortName': 'jtrValPP',
                               'initialState':True,
                               'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                               'data': om.MDoubleArray()},
             'isDonePP': {'longName': 'isDonePP',
                               'shortName': 'isDonePP',
                               'initialState':True,
                               'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                               'data': om.MDoubleArray()},
             'lifespanPP': {'longName': 'lifespanPP',
                               'shortName': 'lifespanPP',
                               'initialState':True,
                               'type':om.MFnNumericData.kDoubleArray,  # @UndefinedVariable
                               'data': om.MDoubleArray()}}
    
    
    
    # if nothing passed in we assume we are updating intial state
    # so need to setup npNode and npFnPart from selection
    if not npNode:
        sel = cmds.ls(sl=True, l=True)
    
        if len(sel) == 0:
            print 'Please select a nParticle system to update initial state on!'
            return
        
        # from the list make sure the first object is a nparticle system, get a handle on this
        # then remove from the list
        if not cmds.objectType(sel[0]) == 'nParticle':
            
            shape = cmds.listRelatives(sel[0])[0]
            
            if not cmds.objectType(shape) == 'nParticle':
                print 'Please select a nParticle system followed by objects to goal to!'
                return
            
            else:
                npShape = shape 
        
        else:
            npShape = sel.pop(0)
            
        # now we have our particle system we need to get the 
        # dependency node and particle system function set        
        selList = om.MSelectionList()
        selList.add(npShape)
        
        npDag = om.MDagPath()
        npMObj = om.MObject()
        
        selList.getDependNode(0, npMObj)
        selList.getDagPath(0, npDag)
        
        npNode = om.MFnDependencyNode(npMObj)
        npFnPart = omfx.MFnParticleSystem(npDag)
    
    # make sure that we have a valid function set
    if npFnPart == None:
        print '###Error: Please make sure you pass in both a dependency node and function set or neither!'
        return
    
    
    # get the goalGeometry plug. this can tell us what our
    # particle is goaled to
    goalGeo_plug = npNode.findPlug('goalGeometry')

    # get the first item that is connected as a goal (this will be our initial goal)
    goal_plug = goalGeo_plug.elementByPhysicalIndex(0)
    attrName = goal_plug.name()
    
    # get the goal index number (this may not be 0)
    goalIndex = attrName.split('[')[-1].split(']')[0]
    
    # create the goal weight attribute
    attrs['goalWeight{}PP'.format(goalIndex)] = {'longName': 'goalWeight%sPP' % goalIndex,
                                                 'shortName': 'goalWeight%sPP' % goalIndex,
                                                 'initialState': True, 
                                                 'type':om.MFnNumericData.kDoubleArray,
                                                 'data': om.MDoubleArray()}
    
    # make sure that all the attributes we need exist
    _create_attributes(npNode, attrs)
    
    # get all the objects connected to our goal array plug (should only be 1!)
    mPlugArray = om.MPlugArray()
    goal_plug.connectedTo(mPlugArray, True, False)
    
    if mPlugArray.length() > 1:
        print '###Error :More than one object is connected to this goal plug. Weird!'
        return
    
    goalMeshFn = om.MFnMesh()
    
    # get the node that is connected the plug and get a mesh function set
    goal_obj = mPlugArray[0].node()
    goal_dagpath = om.MDagPath().getAPathTo(goal_obj)
    goalMeshFn.setObject(goal_dagpath)
    
    
    # get user defined variables
    verticalOffset = 0
    goalWeight_min = 0.2
    goalWeight_max = 0.4
    verticleSpeed_min = 0.005
    verticleSpeed_max = 0.0075
    rotationSpeed = 0.1
    jitterInterval = 10
    jitterRange = 0.01
    
    # setup a bunch of arrays we are about to calculate
    # then get a list of all the points in our particle system and iterate through them
    partPosArray = om.MVectorArray()
    
    npFnPart.position(partPosArray)
    
    # for each particle we want to calculate information on the intial state
    # for all of our pp attributes we want to set
    for i in range(partPosArray.length()):
        
        # get our particle point as a vector
        partPoint = partPosArray[i]
        
        # get the goal uvs closest to our point
        uvArray = [0,0]
        scriptUtil = om.MScriptUtil()
        scriptUtil.createFromList(uvArray, 2)
        uvPoint = scriptUtil.asFloat2Ptr()
        
        goalMeshFn.getUVAtPoint(om.MPoint(partPoint), uvPoint, om.MSpace.kWorld)
            
        uPoint = om.MScriptUtil.getFloat2ArrayItem(uvPoint, 0, 0)
        #vPoint = om.MScriptUtil.getFloat2ArrayItem(uvPoint, 0, 1)
        
        # append to our goalU and goalV array 
        attrs['goalU']['data'].append(uPoint%1)
        attrs['goalV']['data'].append(random.uniform(0, verticalOffset))
        
        goalWeight = random.uniform(goalWeight_min, goalWeight_max)
        
        # give this particle a random goal weight
        attrs['goalWeight%sPP' % goalIndex]['data'].append(goalWeight)
        #goal_weights.append(1)
        
        # set a bunch of attributes used to control motion of particles
        attrs['verticalSpeedPP']['data'].append(random.uniform(verticleSpeed_min, verticleSpeed_max))
        
        adjustedRot = rotationSpeed * (1.1 - goalWeight)
        
        attrs['rotationRatePP']['data'].append(random.uniform(0, adjustedRot))
        attrs['jitterIntervalPP']['data'].append(random.randint(1, jitterInterval))
        attrs['jitterStepPP']['data'].append(0)
        attrs['jitterRangePP']['data'].append(jitterRange)
        attrs['jitterValuePP']['data'].append(random.uniform((-1 * jitterRange), jitterRange))
        
        attrs['isDonePP']['data'].append(0)
        
        attrs['lifespanPP']['data'].append(100000000000000000)
    
    # for each item in our attrs dictionary we want to set the attribute data
    for i in attrs:
        print 'Setting: %s' % i
        if npFnPart.hasAttribute(i):
            npFnPart.setPerParticleAttribute(i, attrs[i]['data'])
    
    
    # save our intial state (NB: if the particle sim has moved on from particle start it 
    # will overwrite their positions. Write a check in at the start of function)
    npFnPart.saveInitialState()  

def _create_attributes(npNode, attrs):
    """
    Given a dependency node will create a number of different attributes
    required
    :param npNode: dependency node that we want to add attributes to
    :param attrs: dictionary containing data needed to add attr
                        -longName
                        -shortName
                        -type
                        -initialState
    """
    
    
    ### NB: Currently only create typed attributes!
    print '#---------#'
    print 'creating new attributes!'
    mFnAttr = om.MFnTypedAttribute()
    
    for attr in attrs:
        # make sure that the attribute doesn't already exist
        if not npNode.hasAttribute(attrs[attr]['longName']):
            # create the attribute and then add it
            customAttr = mFnAttr.create(attrs[attr]['longName'],
                                        attrs[attr]['shortName'],
                                        attrs[attr]['type'])
            npNode.addAttribute(customAttr)
            
            # if the attribute requires an intial state then add that one to
            if attrs[attr]['initialState']:
                custom0Attr = mFnAttr.create('%s0' % attrs[attr]['longName'],
                                              '%s0' % attrs[attr]['shortName'],
                                              attrs[attr]['type'])
                npNode.addAttribute(custom0Attr)
