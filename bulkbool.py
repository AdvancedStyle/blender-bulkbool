# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Bulk Bool",
    "author": "David B",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Edit Tab",
    "description": "Bulk Bool allows you to union lots of objects together, even if some are intersecting and others are not",
    "doc_url": "https://github.com/AdvancedStyle/blender-bulkbool",
    "category": "Object",
}

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import bmesh
import time


def BoundingsToMesh( obj, scene ):
    name = obj.name + "_bounds"
    meshData = bpy.data.meshes.new( name )
    meshObj = bpy.data.objects.new( name, meshData )
    meshObj.matrix_world = obj.matrix_world.copy()

    meshObj.data.from_pydata( *BoundingsGeometry( obj ) )

    scene.objects.link( meshObj )

    return meshObj

#Create bounding geometry from an object
def BoundingsGeometry( obj ):
    verts = [Vector(co) for co in obj.bound_box]
    edges = []
    faces = [ (0,1,2,3), (4,5,1,0), (7,6,5,4), (3,2,6,7), (6,2,1,5), (7,4,0,3) ]
    return verts, edges, faces

#Translates bounding geometry in world coordinates
def BoundingsGeometryInWorld( obj ):
    verts, edges, faces = BoundingsGeometry( obj )
    return [obj.matrix_world @ v for v in verts], edges, faces

#Get vertices and polygons from an object in world coordinates
def MeshGeometryInWorld( obj ):
    return [obj.matrix_world @ v.co for v in obj.data.vertices], [], [p.vertices for p in obj.data.polygons]

#Create a BVH tree from bounding (world co)
def BVHFromBoundings( obj ):
    verts, edges, faces = BoundingsGeometryInWorld( obj )
    return BVHTree.FromPolygons( verts, faces )

#Create a BVH tree from mesh (world co)
def BVHFromMesh( obj ):
    verts, edges, faces = MeshGeometryInWorld( obj )
    return BVHTree.FromPolygons( verts, faces )

#Create a BVH tree from bmesh (world co)
def BVHFromBMesh( obj ):
    bm = bmesh.new()
    bm.from_mesh( obj.data )
    bm.transform( obj.matrix_world )
    result = BVHTree.FromBMesh( bm )
    del bm
    return result

#Test if a bvh tree overlap an object
def IntersectBVHObj( bvh, obj, toBvh ):
    objBvh = toBvh( obj )
    result = bvh.overlap( objBvh )
    del objBvh
    return result

#Test if two objects overlap
def IntersectObjObj( obj, others, toBvh ):
    objBvh = toBvh( obj )
    result = [other for other in others if IntersectBVHObj( objBvh, other, toBvh )]
    del objBvh
    return result

#Test if two objects overlap using boundings method
def IntersectBoundings( obj, others ):
    return IntersectObjObj( obj, others, BVHFromBoundings )

#Test if two objects overlap using mesh method
def IntersectMesh( obj, others ):
    return IntersectObjObj( obj, others, BVHFromMesh )

#Test if two objects overlap using bmesh method
def IntersectBMesh( obj, others ):
    return IntersectObjObj( obj, others, BVHFromBMesh )

#Select objects which overlap another one
def SelectIntersect( obj, scene, others, intersectBounding = False ):
    result = IntersectBoundings( obj, others )

    if intersectBounding == False:
        #startTime = time.time()
        #for i in range( 1000 ):
            result = IntersectBMesh( obj, result )
        #print( "elapsed", time.time() - startTime )

    return result

class BULKBOOL_PT_panel(bpy.types.Panel):
    bl_label = "Bulk Union"
    bl_idname = "BULKBOOL_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_category = 'Edit'
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.operator('object.bulkbool_auto_union')

class Auto_Boolean:

    def objects_prepare(self):
        objects = bpy.context.selected_objects
        print('Preparing Objects: '+str(len(objects)))
        for ob in bpy.context.selected_objects:
            #print(ob.type)
            if ob.type != "MESH":
                ob.select_set(False)
            else:
                ob.data = ob.data.copy()

    def mesh_selection(self, ob, select_action):
        obj = bpy.context.active_object

        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")

        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action=select_action)

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.objects.active = obj

    def boolean_operation(self, obs):
        joins_tracker = dict()
        for ob in obs:
            joins_tracker[ob.name] = len(ob.data.vertices)

        while len(joins_tracker) > 1:
            # Get our objects with 
            list = iter(sorted(joins_tracker.items(), key=lambda x: x[1]))
            obj1_name = next(list)[0]
            obj2_name = next(list)[0]
            
            obj1 = bpy.context.scene.objects[obj1_name]
            obj2 = bpy.context.scene.objects[obj2_name]
            
            print(obj1_name)
            print(obj2_name)
            
            self.boolean_mod(obj1, obj2, self.mode)
            
            del joins_tracker[obj2_name]
            
            joins_tracker[obj1_name] = len(obj1.data.vertices)
            
            
        obj1.select_set(True)

    def boolean_mod(self, obj, ob, mode, ob_delete=True):
        object_materials = []
        for material in obj.data.materials:
            object_materials.append(material.name)
        
        # Handle Materials
        for material in ob.data.materials:
            if material.name not in object_materials:
                # We need to add this material to the main object
                obj.data.materials.append(material)
        
        
        md = obj.modifiers.new("Auto Boolean", "BOOLEAN")
        md.show_viewport = False
        md.operation = mode
        md.object = ob

        override = {"object": obj}
        bpy.ops.object.modifier_apply(override, modifier=md.name)

        if ob_delete:
            bpy.data.objects.remove(ob)
            
    def get_touching_group(self):
        all_objects = bpy.context.selected_objects.copy()
        
        # Remove the untouching items
        try_objects = []
        for obj in all_objects:
            if obj.name not in self.untouching_list:
                try_objects.append(obj)
        
        
        n=0
        for obj in try_objects:
            list = try_objects.copy()
            
            # Remove itself from the list
            del list[n]
            
            result = SelectIntersect( obj, self.context.scene, list)
            n += 1
            if len(result) == 0:
                # put this object in the no touching list
                self.untouching_list.append(obj.name)
            else:
                store = [obj]
                for r in result:
                    store.append(r)
                    
                return store
                
        return False
        

    def execute(self, context):
        
        self.untouching_list = []
        self.context = context
        self.objects_prepare()
        
        touching = self.get_touching_group()
        while touching != False:
            print('Found touching objects')
            self.boolean_operation(touching)
            touching = self.get_touching_group()
        
        print('Done with touching do join');
        #All touching stuff has been unioned, so now just join the rest instead of Union

        # Make sure we have one of the objects set as active
        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        bpy.ops.object.join()

        return {"FINISHED"}

    def invoke(self, context, event):
        #if len(context.selected_objects) < 2:
        #    self.report({"ERROR"}, "At least two objects must be selected")
         #   return {"CANCELLED"}

        return self.execute(context)
    
class OBJECT_OT_bulkbool_Auto_Union(bpy.types.Operator, Auto_Boolean):
    bl_idname = "object.bulkbool_auto_union"
    bl_label = "Union Selected Objects"
    bl_description = "Combine selected objects"

    mode = "UNION"

        
def register():
    bpy.utils.register_class(BULKBOOL_PT_panel)
    bpy.utils.register_class(OBJECT_OT_bulkbool_Auto_Union)
    
def unregister():
    bpy.utils.unregister_class(BULKBOOL_PT_panel)
    bpy.utils.unregister_class(OBJECT_OT_bulkbool_Auto_Union)
    
    
if __name__ == "__main__":
    register()
