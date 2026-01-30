## Script Created by Scot McPherson:
## https://www.youtube.com/channel/UCNDREeLwXewcJzyiMYF9kMA
##
## Original Script Created by MissingLinkDev:
## https://www.youtube.com/channel/UCnPYqCSU-CFppoufb7BKuAg
##
## You can buy explosive.ws animations for godot here:
## https://www.explosive.ws/products/rpg-animation-fbx-for-godot-blender



## Todo:
##  List of animation libraries that need to have their Rotation X set to 0 and Rotation Applied
##  2h Crossbow
##  2h Spear
##  2h Sword
##  Armed_Shield
##  Climbing-Ladder
##  Climbing-Ledge
##  Crawl
##  Swimming

## explosive version 0.0.6 and earlier, this is already fixed in future versions
##  Crouch Walk Left - Delete Pelvis X Motion

import bpy
import os
import math
from bpy_extras import anim_utils


# linux example path
folder_path = "/home/scot/godot/Assets/Animations/ExplosiveLLC/RPG Animation FBX-0.0.6/Relax"

# windows example path
#folder_path =  "C:\\Users\\Scot\\Animations\\ExplosiveLLC\\RPG Animation FBX-0.0.0\\Relax"


# Setup some variables
rotate_z = True # rotate the animation by 180 on Z
remove_root_motion = True # remove the root motion location fcurves from animations, root rotation and root scale fcurves are not removed.

remove_mesh = False # Experimental: remove the final mesh inside the armature that causes warnings in Godot
weapon = "Crossbow"  # Name of weapon in case it exists in anim (it shouldn't)

# Setup the environment
collection = bpy.data.collections.get("Collection") # Starting Cube and it's Collection
#bpy.ops.wm.read_factory_settings(use_empty=True) # Reset to default startup environment


if not os.path.isdir(folder_path):
    print(f"Error: '{folder_path}' is not a valid directory.")

else:

    # Delete the starting cube and collection
    if collection is not None:
        # Iterate over all objects in the collection and unlink them
        for obj in collection.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        
        # Remove the collection itself
        bpy.data.collections.remove(collection)
        
    main_armature = None

    # Search Folder for FBX files.
    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith(".FBX"):
            continue

        file_path = os.path.join(folder_path, filename)
        print(f"Importing: {file_path}")

        # Snapshot state before import so we can find what was added
        actions_before = set(bpy.data.actions.keys())
        objects_before = set(bpy.data.objects.keys())

        # Import the file
        bpy.ops.wm.fbx_import(filepath=file_path)

        # Find newly created objects and actions
        new_object_names = set(bpy.data.objects.keys()) - objects_before
        new_action_names = set(bpy.data.actions.keys()) - actions_before

        # Look for weapon name and remove it
        if weapon in new_object_names:
            bpy.data.objects.remove(bpy.data.objects[weapon])
            new_object_names.discard(weapon)
            # Remove any weapon-related actions
            weapon_actions = [n for n in new_action_names if weapon in n]
            for wa in weapon_actions:
                bpy.data.actions.remove(bpy.data.actions[wa])
                new_action_names.discard(wa)

        # Find the action created by this import
        action = None
        action_slot = None
        for name in new_action_names:
            action = bpy.data.actions[name]
            break

        if not action:
            print(f"  Warning: '{filename}' didn't create any animation action.")
            for obj_name in new_object_names:
                if obj_name in bpy.data.objects:
                    bpy.data.objects.remove(bpy.data.objects[obj_name])
            continue

        # Remove root motion fcurves
        if remove_root_motion:
            for slot in action.slots:
                channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                if channelbag:
                    fcurves_to_remove = [
                        fc for fc in channelbag.fcurves
                        if "Motion" in fc.data_path and "location" in fc.data_path
                    ]
                    for fc in fcurves_to_remove:
                        channelbag.fcurves.remove(fc)

        # Rename the action
        action.name = os.path.splitext(filename)[0].replace("RPG-Character@", "").replace("-", "")
        action.use_fake_user = True

        # Identify the main armature on first import, delete duplicates on subsequent imports
        new_armature = None
        new_meshes = []
        for obj_name in new_object_names:
            if obj_name not in bpy.data.objects:
                continue
            obj = bpy.data.objects[obj_name]
            if obj.type == 'ARMATURE':
                new_armature = obj
            elif obj.type == 'MESH':
                new_meshes.append(obj)

        if main_armature is None:
            # First import — keep this armature, slot is already correctly bound
            main_armature = new_armature
            if remove_mesh:
                for m in new_meshes:
                    bpy.data.objects.remove(m)
        else:
            # Subsequent imports — rebind the action's slot to main_armature
            # The importer bound the slot to the new (duplicate) armature, so the
            # Action Editor can't resolve bone channels unless we rebind it.
            old_slot = action.slots[0] if action.slots else None
            if old_slot:
                old_cb = anim_utils.action_get_channelbag_for_slot(action, old_slot)
                new_slot = action.slots.new(id_type='OBJECT', name=main_armature.name)
                new_cb = anim_utils.action_ensure_channelbag_for_slot(action, new_slot)
                if old_cb:
                    for old_fc in list(old_cb.fcurves):
                        new_fc = new_cb.fcurves.new(old_fc.data_path, index=old_fc.array_index)
                        kp_count = len(old_fc.keyframe_points)
                        if kp_count > 0:
                            new_fc.keyframe_points.add(kp_count)
                            co = [0.0] * (kp_count * 2)
                            old_fc.keyframe_points.foreach_get('co', co)
                            new_fc.keyframe_points.foreach_set('co', co)
                            new_fc.update()
                action.slots.remove(old_slot)

            # Delete the duplicate armature and meshes
            if new_armature is not None:
                bpy.data.objects.remove(new_armature)
            for m in new_meshes:
                bpy.data.objects.remove(m)

        # Assign the action to the main armature
        if main_armature:
            if main_armature.animation_data is None:
                main_armature.animation_data_create()
            main_armature.animation_data.action = action
            # Find the slot bound to main_armature
            for slot in action.slots:
                if slot.target_id_type == 'OBJECT':
                    main_armature.animation_data.action_slot = slot
                    break

        print(f"  Imported animation: '{action.name}'")

    # Rotate the armature to face forward in Godot
    if rotate_z and main_armature:
        main_armature.rotation_euler = [math.radians(90), 0.0, math.radians(180)]
        bpy.context.view_layer.update()

    # Export File
    #bpy.ops.export_scene.glb(filepath=export_file_path, export_selected=False)

print("Done!")
