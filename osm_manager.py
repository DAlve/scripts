import re
import math
import random

import xml.etree.cElementTree as ET
from math import sin, cos, sqrt, atan2, radians

import maya.cmds as cmds


osmFile = "F:\Maya\map.osm"

R = 637300.0


def latlong_distance(lat_long_1, lat_long_2):
    
    lat1 = radians(lat_long_1[0])
    lon1 = radians(lat_long_1[1])
    lat2 = radians(lat_long_2[0])
    lon2 = radians(lat_long_2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R *c
    return distance * 1000


class OSMNode(object):

    def __init__(self):
        self.id = 0
        self.lat = 0
        self.lon = 0
        self.tags = {}
    
    @classmethod
    def from_xml(cls, xml_node):
        self = cls()

        self.id = xml_node.attrib['id']
        self.lat = xml_node.attrib['lat']
        self.lon = xml_node.attrib['lon']

        for child in xml_node:
            if child.tag == 'tag':
                clean_tag = re.sub('[^a-zA-Z0-9]', '_', child.attrib['k'])
                self.tags[clean_tag] = child.attrib['v']
        
        return self


class OSMWay(object):

    def __init__(self):
        self.id = 0
        self.tags = {}
        self.nodes = []
    
    @classmethod
    def from_xml(cls, xml_node):
        self = cls()

        self.id = xml_node.attrib["id"]
        for child in xml_node:
            if child.tag == "tag" and "k" in child.attrib:
                clean_tag = re.sub('[^a-zA-Z0-9\n]', '_', child.attrib['k'])
                self.tags[clean_tag] = child.attrib['v']
            
            if child.tag == 'nd' and 'ref' in child.attrib:
                self.nodes.append(child.attrib['ref'])

        return self


class OSMParser(object):
    """
    Class to work with osm file
    """

    def __init__(self, osm_file):

        print 'Initialising'
        self.osm_file = osm_file
        
        self.min_lat = 0
        self.max_lat = 0
        
        self.min_long = 0
        self.max_long = 0
        
        self.length = 0
        self.height = 0
        
        self.ways = []
        self.nodes = {}
        self.tagged_nodes = []
        self.tags = []


    def get_size(self):
        """
        Get the length and height of the region for the osm
        """

        self.length = latlong_distance([self.min_lat, self.min_long], [self.max_lat, self.min_long])
        self.height = latlong_distance([self.min_lat, self.min_long], [self.min_lat, self.max_long])


    def get_relative_coordinates(self, lat_long):
        """
        Get the points relative coordinates
        """

        rel_lat = (lat_long[0] - self.min_lat) / (self.max_lat - self.min_lat) * self.length
        rel_lon = (lat_long[1] - self.min_long) / (self.max_long - self.min_long) * self.height

        return rel_lat, rel_lon


    def get_centre_pos(self, positions):
        """
        Get the centre point of a list of positions
        """

        # get the length of the positions array
        dims = len(positions)

        # create empty arrays for each dimension
        x_array = []
        y_array = []
        z_array = []

        # for each position we want to split the axis into their arrays
        for i in positions:
            x_array.append(i[0])
            y_array.append(i[1])
            z_array.append(i[2])
        
        # find the average of each array
        x = sum(x_array) / dims
        y = sum(y_array) / dims
        z = sum(z_array) / dims

        return (x, y, z)


    def build(self):
        """
        Build the osm file
        """
        print 'Building'


        # first get a group to put everything in
        bld_group = '_buildings'

        if not cmds.ls(bld_group):
            cmds.group(empty=True, n=bld_group)

        # create a something to store the number of the building we are on
        num_buildings = 0

        # go through our ways and find the buildings
        for way in self.ways:
            if 'building' in way.tags:
                
                positions = []

                for node_id in way.nodes:
                    node = self.nodes[node_id]
                    pos_xy = self.get_relative_coordinates([float(node.lat), float(node.lon)])
                    positions.append((pos_xy[0], pos_xy[1], 0))

                building = cmds.polyCreateFacet(p=positions)

                centre_pos = self.get_centre_pos(positions)
                cmds.xform( building[0], ws=True, piv=centre_pos )

                # make sure all the vertices have the correct normals
                for i in range(cmds.polyEvaluate(building[0], vertex=True)):
                    cmds.select('{}.vtx[{}]'.format(building[0], i))
                    cmds.polyNormalPerVertex(xyz=(0,0,1))


                new_building = cmds.rename(building[0], 'building_{0:03d}'.format(num_buildings+1))
                cmds.parent(new_building, bld_group)

                num_buildings += 1
        
        print 'Build {} buildings!'.format(num_buildings)
                    
            

    
    def parse(self):
        """
        Read in the osm file and get all the data from it
        """

        print 'parsing'
        tags = []
        
        
        for _, child in ET.iterparse(self.osm_file):
            if child.tag == 'bounds':
                #this is the extents of the mapping data
                self.min_lat = float(child.attrib['minlat'])
                self.max_lat = float(child.attrib['maxlat'])
                self.min_long = float(child.attrib['minlon'])
                self.max_long = float(child.attrib['maxlon'])
                
                self.get_size()
                child.clear()
            
            if child.tag == "way":
                way = OSMWay.from_xml(child)
                tags.extend(way.tags.keys())
                self.ways.append(way)
                child.clear()
            
            if child.tag == 'node':

                node = OSMNode.from_xml(child)
                tags.extend(node.tags.keys())
                self.nodes[node.id] = node

                if node.tags.keys():
                    self.tagged_nodes.append(node)

                child.clear()
        
        

parser = OSMParser(osmFile)
parser.parse()
parser.build()


