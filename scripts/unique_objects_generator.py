#!/usr/bin/python3 -i
#
# Copyright (c) 2015-2016 The Khronos Group Inc.
# Copyright (c) 2015-2016 Valve Corporation
# Copyright (c) 2015-2016 LunarG, Inc.
# Copyright (c) 2015-2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Tobin Ehlis <tobine@google.com>
# Author: Mark Lobodzinski <mark@lunarg.com>

import os,re,sys
import xml.etree.ElementTree as etree
from generator import *
from collections import namedtuple

# UniqueObjectsGeneratorOptions - subclass of GeneratorOptions.
#
# Adds options used by UniqueObjectsOutputGenerator objects during
# unique objects layer generation.
#
# Additional members
#   prefixText - list of strings to prefix generated header with
#     (usually a copyright statement + calling convention macros).
#   protectFile - True if multiple inclusion protection should be
#     generated (based on the filename) around the entire header.
#   protectFeature - True if #ifndef..#endif protection should be
#     generated around a feature interface in the header file.
#   genFuncPointers - True if function pointer typedefs should be
#     generated
#   protectProto - If conditional protection should be generated
#     around prototype declarations, set to either '#ifdef'
#     to require opt-in (#ifdef protectProtoStr) or '#ifndef'
#     to require opt-out (#ifndef protectProtoStr). Otherwise
#     set to None.
#   protectProtoStr - #ifdef/#ifndef symbol to use around prototype
#     declarations, if protectProto is set
#   apicall - string to use for the function declaration prefix,
#     such as APICALL on Windows.
#   apientry - string to use for the calling convention macro,
#     in typedefs, such as APIENTRY.
#   apientryp - string to use for the calling convention macro
#     in function pointer typedefs, such as APIENTRYP.
#   indentFuncProto - True if prototype declarations should put each
#     parameter on a separate line
#   indentFuncPointer - True if typedefed function pointers should put each
#     parameter on a separate line
#   alignFuncParam - if nonzero and parameters are being put on a
#     separate line, align parameter names at the specified column
class UniqueObjectsGeneratorOptions(GeneratorOptions):
    def __init__(self,
                 filename = None,
                 directory = '.',
                 apiname = None,
                 profile = None,
                 versions = '.*',
                 emitversions = '.*',
                 defaultExtensions = None,
                 addExtensions = None,
                 removeExtensions = None,
                 sortProcedure = regSortFeatures,
                 prefixText = "",
                 genFuncPointers = True,
                 protectFile = True,
                 protectFeature = True,
                 protectProto = None,
                 protectProtoStr = None,
                 apicall = '',
                 apientry = '',
                 apientryp = '',
                 indentFuncProto = True,
                 indentFuncPointer = False,
                 alignFuncParam = 0):
        GeneratorOptions.__init__(self, filename, directory, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions, sortProcedure)
        self.prefixText      = prefixText
        self.genFuncPointers = genFuncPointers
        self.protectFile     = protectFile
        self.protectFeature  = protectFeature
        self.protectProto    = protectProto
        self.protectProtoStr = protectProtoStr
        self.apicall         = apicall
        self.apientry        = apientry
        self.apientryp       = apientryp
        self.indentFuncProto = indentFuncProto
        self.indentFuncPointer = indentFuncPointer
        self.alignFuncParam  = alignFuncParam

# UniqueObjectsOutputGenerator - subclass of OutputGenerator.
# Generates unique objects layer non-dispatchable handle-wrapping code.
#
# ---- methods ----
# UniqueObjectsOutputGenerator(errFile, warnFile, diagFile) - args as for OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# beginFeature(interface, emit)
# endFeature()
# genCmd(cmdinfo)
# genStruct()
# genType()
class UniqueObjectsOutputGenerator(OutputGenerator):
    """Generate UniqueObjects code based on XML element attributes"""
    # This is an ordered list of sections in the header file.
    ALL_SECTIONS = ['command']
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
        self.INDENT_SPACES = 4
        self.intercepts = []
        self.instance_extensions = []
        self.device_extensions = []
        # Commands which are not autogenerated but still intercepted
        self.no_autogen_list = [
            'vkGetDeviceProcAddr',
            'vkGetInstanceProcAddr',
            'vkCreateInstance',
            'vkDestroyInstance',
            'vkCreateDevice',
            'vkDestroyDevice',
            'vkCreateComputePipelines',
            'vkCreateGraphicsPipelines',
            'vkCreateSwapchainKHR',
            'vkCreateSharedSwapchainsKHR',
            'vkGetSwapchainImagesKHR',
            'vkQueuePresentKHR',
            'vkEnumerateInstanceLayerProperties',
            'vkEnumerateDeviceLayerProperties',
            'vkEnumerateInstanceExtensionProperties',
            'vkCreateDescriptorUpdateTemplateKHR',
            'vkDestroyDescriptorUpdateTemplateKHR',
            'vkUpdateDescriptorSetWithTemplateKHR',
            'vkCmdPushDescriptorSetWithTemplateKHR',
            'vkDebugMarkerSetObjectTagEXT',
            'vkDebugMarkerSetObjectNameEXT',
            'vkGetPhysicalDeviceDisplayProperties2KHR',
            'vkGetPhysicalDeviceDisplayPlaneProperties2KHR',
            'vkGetDisplayModeProperties2KHR',
            'vkCreateRenderPass',
            'vkDestroyRenderPass',
            ]
        # Commands shadowed by interface functions and are not implemented
        self.interface_functions = [
            'vkGetPhysicalDeviceDisplayPropertiesKHR',
            'vkGetPhysicalDeviceDisplayPlanePropertiesKHR',
            'vkGetDisplayPlaneSupportedDisplaysKHR',
            'vkGetDisplayModePropertiesKHR',
            'vkGetDisplayPlaneCapabilitiesKHR',
            # DebugReport APIs are hooked, but handled separately in the source file
            'vkCreateDebugReportCallbackEXT',
            'vkDestroyDebugReportCallbackEXT',
            'vkDebugReportMessageEXT',
            ]
        self.headerVersion = None
        # Internal state - accumulators for different inner block text
        self.sections = dict([(section, []) for section in self.ALL_SECTIONS])

        self.cmdMembers = []
        self.cmd_feature_protect = []  # Save ifdef's for each command
        self.cmd_info_data = []        # Save the cmdinfo data for wrapping the handles when processing is complete
        self.structMembers = []        # List of StructMemberData records for all Vulkan structs
        self.extension_structs = []    # List of all structs or sister-structs containing handles
                                       # A sister-struct may contain no handles but shares a structextends attribute with one that does
        self.structTypes = dict()      # Map of Vulkan struct typename to required VkStructureType
        self.struct_member_dict = dict()
        # Named tuples to store struct and command data
        self.StructType = namedtuple('StructType', ['name', 'value'])
        self.CmdMemberData = namedtuple('CmdMemberData', ['name', 'members'])
        self.CmdInfoData = namedtuple('CmdInfoData', ['name', 'cmdinfo'])
        self.CmdExtraProtect = namedtuple('CmdExtraProtect', ['name', 'extra_protect'])

        self.CommandParam = namedtuple('CommandParam', ['type', 'name', 'ispointer', 'isconst', 'iscount', 'len', 'extstructs', 'cdecl', 'islocal', 'iscreate', 'isdestroy', 'feature_protect'])
        self.StructMemberData = namedtuple('StructMemberData', ['name', 'members'])
    #
    def incIndent(self, indent):
        inc = ' ' * self.INDENT_SPACES
        if indent:
            return indent + inc
        return inc
    #
    def decIndent(self, indent):
        if indent and (len(indent) > self.INDENT_SPACES):
            return indent[:-self.INDENT_SPACES]
        return ''
    #
    # Override makeProtoName to drop the "vk" prefix
    def makeProtoName(self, name, tail):
        return self.genOpts.apientry + name[2:] + tail
    #
    # Check if the parameter passed in is a pointer to an array
    def paramIsArray(self, param):
        return param.attrib.get('len') is not None
    #
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        # User-supplied prefix text, if any (list of strings)
        if (genOpts.prefixText):
            for s in genOpts.prefixText:
                write(s, file=self.outFile)
        # Namespace
        self.newline()
        write('namespace unique_objects {', file = self.outFile)
    # Now that the data is all collected and complete, generate and output the wrapping/unwrapping routines
    def endFile(self):

        self.struct_member_dict = dict(self.structMembers)

        # Generate the list of APIs that might need to handle wrapped extension structs
        self.GenerateCommandWrapExtensionList()
        # Write out wrapping/unwrapping functions
        self.WrapCommands()
        # Build and write out pNext processing function
        extension_proc = self.build_extension_processing_func()
        self.newline()
        write('// Unique Objects pNext extension handling function', file=self.outFile)
        write('%s' % extension_proc, file=self.outFile)

        # Actually write the interface to the output file.
        if (self.emit):
            self.newline()
            if (self.featureExtraProtect != None):
                write('#ifdef', self.featureExtraProtect, file=self.outFile)
            # Write the unique_objects code to the file
            if (self.sections['command']):
                if (self.genOpts.protectProto):
                    write(self.genOpts.protectProto,
                          self.genOpts.protectProtoStr, file=self.outFile)
                write('\n'.join(self.sections['command']), end=u'', file=self.outFile)
            if (self.featureExtraProtect != None):
                write('\n#endif //', self.featureExtraProtect, file=self.outFile)
            else:
                self.newline()

        # Record intercepted procedures
        write('// Map of all APIs to be intercepted by this layer', file=self.outFile)
        write('static const std::unordered_map<std::string, void*> name_to_funcptr_map = {', file=self.outFile)
        write('\n'.join(self.intercepts), file=self.outFile)
        write('};\n', file=self.outFile)
        self.newline()
        write('} // namespace unique_objects', file=self.outFile)
        # Finish processing in superclass
        OutputGenerator.endFile(self)
    #
    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)
        self.headerVersion = None

        if self.featureName != 'VK_VERSION_1_0':
            white_list_entry = []
            if (self.featureExtraProtect != None):
                white_list_entry += [ '#ifdef %s' % self.featureExtraProtect ]
            white_list_entry += [ '"%s"' % self.featureName ]
            if (self.featureExtraProtect != None):
                white_list_entry += [ '#endif' ]
            featureType = interface.get('type')
            if featureType == 'instance':
                self.instance_extensions += white_list_entry
            elif featureType == 'device':
                self.device_extensions += white_list_entry
    #
    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)
    #
    def genType(self, typeinfo, name):
        OutputGenerator.genType(self, typeinfo, name)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the imbedded <member> tags generating a structure.
        # Otherwise, emit the tag text.
        category = typeElem.get('category')
        if (category == 'struct' or category == 'union'):
            self.genStruct(typeinfo, name)
    #
    # Append a definition to the specified section
    def appendSection(self, section, text):
        # self.sections[section].append('SECTION: ' + section + '\n')
        self.sections[section].append(text)
    #
    # Check if the parameter passed in is a pointer
    def paramIsPointer(self, param):
        ispointer = False
        for elem in param:
            if ((elem.tag is not 'type') and (elem.tail is not None)) and '*' in elem.tail:
                ispointer = True
        return ispointer
    #
    # Get the category of a type
    def getTypeCategory(self, typename):
        types = self.registry.tree.findall("types/type")
        for elem in types:
            if (elem.find("name") is not None and elem.find('name').text == typename) or elem.attrib.get('name') == typename:
                return elem.attrib.get('category')
    #
    # Check if a parent object is dispatchable or not
    def isHandleTypeNonDispatchable(self, handletype):
        handle = self.registry.tree.find("types/type/[name='" + handletype + "'][@category='handle']")
        if handle is not None and handle.find('type').text == 'VK_DEFINE_NON_DISPATCHABLE_HANDLE':
            return True
        else:
            return False
    #
    # Retrieve the type and name for a parameter
    def getTypeNameTuple(self, param):
        type = ''
        name = ''
        for elem in param:
            if elem.tag == 'type':
                type = noneStr(elem.text)
            elif elem.tag == 'name':
                name = noneStr(elem.text)
        return (type, name)
    #
    # Retrieve the value of the len tag
    def getLen(self, param):
        result = None
        len = param.attrib.get('len')
        if len and len != 'null-terminated':
            # For string arrays, 'len' can look like 'count,null-terminated', indicating that we
            # have a null terminated array of strings.  We strip the null-terminated from the
            # 'len' field and only return the parameter specifying the string count
            if 'null-terminated' in len:
                result = len.split(',')[0]
            else:
                result = len
            # Spec has now notation for len attributes, using :: instead of platform specific pointer symbol
            result = str(result).replace('::', '->')
        return result
    #
    # Generate a VkStructureType based on a structure typename
    def genVkStructureType(self, typename):
        # Add underscore between lowercase then uppercase
        value = re.sub('([a-z0-9])([A-Z])', r'\1_\2', typename)
        # Change to uppercase
        value = value.upper()
        # Add STRUCTURE_TYPE_
        return re.sub('VK_', 'VK_STRUCTURE_TYPE_', value)
    #
    # Struct parameter check generation.
    # This is a special case of the <type> tag where the contents are interpreted as a set of
    # <member> tags instead of freeform C type declarations. The <member> tags are just like
    # <param> tags - they are a declaration of a struct or union member. Only simple member
    # declarations are supported (no nested structs etc.)
    def genStruct(self, typeinfo, typeName):
        OutputGenerator.genStruct(self, typeinfo, typeName)
        members = typeinfo.elem.findall('.//member')
        # Iterate over members once to get length parameters for arrays
        lens = set()
        for member in members:
            len = self.getLen(member)
            if len:
                lens.add(len)
        # Generate member info
        membersInfo = []
        for member in members:
            # Get the member's type and name
            info = self.getTypeNameTuple(member)
            type = info[0]
            name = info[1]
            cdecl = self.makeCParamDecl(member, 0)
            # Process VkStructureType
            if type == 'VkStructureType':
                # Extract the required struct type value from the comments
                # embedded in the original text defining the 'typeinfo' element
                rawXml = etree.tostring(typeinfo.elem).decode('ascii')
                result = re.search(r'VK_STRUCTURE_TYPE_\w+', rawXml)
                if result:
                    value = result.group(0)
                else:
                    value = self.genVkStructureType(typeName)
                # Store the required type value
                self.structTypes[typeName] = self.StructType(name=name, value=value)
            # Store pointer/array/string info
            extstructs = self.registry.validextensionstructs[typeName] if name == 'pNext' else None
            membersInfo.append(self.CommandParam(type=type,
                                                 name=name,
                                                 ispointer=self.paramIsPointer(member),
                                                 isconst=True if 'const' in cdecl else False,
                                                 iscount=True if name in lens else False,
                                                 len=self.getLen(member),
                                                 extstructs=extstructs,
                                                 cdecl=cdecl,
                                                 islocal=False,
                                                 iscreate=False,
                                                 isdestroy=False,
                                                 feature_protect=self.featureExtraProtect))
        self.structMembers.append(self.StructMemberData(name=typeName, members=membersInfo))

    #
    # Insert a lock_guard line
    def lock_guard(self, indent):
        return '%sstd::lock_guard<std::mutex> lock(global_lock);\n' % indent
    #
    # Determine if a struct has an NDO as a member or an embedded member
    def struct_contains_ndo(self, struct_item):
        struct_member_dict = dict(self.structMembers)
        struct_members = struct_member_dict[struct_item]

        for member in struct_members:
            if self.isHandleTypeNonDispatchable(member.type):
                return True
            elif member.type in struct_member_dict:
                if self.struct_contains_ndo(member.type) == True:
                    return True
        return False
    #
    # Return list of struct members which contain, or which sub-structures contain
    # an NDO in a given list of parameters or members
    def getParmeterStructsWithNdos(self, item_list):
        struct_list = set()
        for item in item_list:
            paramtype = item.find('type')
            typecategory = self.getTypeCategory(paramtype.text)
            if typecategory == 'struct':
                if self.struct_contains_ndo(paramtype.text) == True:
                    struct_list.add(item)
        return struct_list
    #
    # Return list of non-dispatchable objects from a given list of parameters or members
    def getNdosInParameterList(self, item_list, create_func):
        ndo_list = set()
        if create_func == True:
            member_list = item_list[0:-1]
        else:
            member_list = item_list
        for item in member_list:
            if self.isHandleTypeNonDispatchable(paramtype.text):
                ndo_list.add(item)
        return ndo_list
    #
    # Construct list of extension structs containing handles, or extension structs that share a structextends attribute
    # WITH an extension struct containing handles. All extension structs in any pNext chain will have to be copied.
    # TODO: make this recursive -- structs buried three or more levels deep are not searched for extensions
    def GenerateCommandWrapExtensionList(self):
        for struct in self.structMembers:
            if (len(struct.members) > 1) and struct.members[1].extstructs is not None:
                found = False;
                for item in struct.members[1].extstructs:
                    if item != '' and self.struct_contains_ndo(item) == True:
                        found = True
                if found == True:
                    for item in struct.members[1].extstructs:
                        if item != '' and item not in self.extension_structs:
                            self.extension_structs.append(item)
    #
    # Returns True if a struct may have a pNext chain containing an NDO
    def StructWithExtensions(self, struct_type):
        if struct_type in self.struct_member_dict:
            param_info = self.struct_member_dict[struct_type]
            if (len(param_info) > 1) and param_info[1].extstructs is not None:
                for item in param_info[1].extstructs:
                    if item in self.extension_structs:
                        return True
        return False
    #
    # Generate pNext handling function
    def build_extension_processing_func(self):
        # Construct helper functions to build and free pNext extension chains
        pnext_proc = ''
        pnext_proc += 'void *CreateUnwrappedExtensionStructs(layer_data *dev_data, const void *pNext) {\n'
        pnext_proc += '    void *cur_pnext = const_cast<void *>(pNext);\n'
        pnext_proc += '    void *head_pnext = NULL;\n'
        pnext_proc += '    void *prev_ext_struct = NULL;\n'
        pnext_proc += '    void *cur_ext_struct = NULL;\n\n'
        pnext_proc += '    while (cur_pnext != NULL) {\n'
        pnext_proc += '        GenericHeader *header = reinterpret_cast<GenericHeader *>(cur_pnext);\n\n'
        pnext_proc += '        switch (header->sType) {\n'
        for item in self.extension_structs:
            struct_info = self.struct_member_dict[item]
            if struct_info[0].feature_protect is not None:
                pnext_proc += '#ifdef %s \n' % struct_info[0].feature_protect
            pnext_proc += '            case %s: {\n' % self.structTypes[item].value
            pnext_proc += '                    safe_%s *safe_struct = new safe_%s;\n' % (item, item)
            pnext_proc += '                    safe_struct->initialize(reinterpret_cast<const %s *>(cur_pnext));\n' % item
            # Generate code to unwrap the handles
            indent = '                '
            (tmp_decl, tmp_pre, tmp_post) = self.uniquify_members(struct_info, indent, 'safe_struct->', 0, False, False, False, False)
            pnext_proc += tmp_pre
            pnext_proc += '                    cur_ext_struct = reinterpret_cast<void *>(safe_struct);\n'
            pnext_proc += '                } break;\n'
            if struct_info[0].feature_protect is not None:
                pnext_proc += '#endif // %s \n' % struct_info[0].feature_protect
            pnext_proc += '\n'
        pnext_proc += '            default:\n'
        pnext_proc += '                break;\n'
        pnext_proc += '        }\n\n'
        pnext_proc += '        // Save pointer to the first structure in the pNext chain\n'
        pnext_proc += '        head_pnext = (head_pnext ? head_pnext : cur_ext_struct);\n\n'
        pnext_proc += '        // For any extension structure but the first, link the last struct\'s pNext to the current ext struct\n'
        pnext_proc += '        if (prev_ext_struct) {\n'
        pnext_proc += '            (reinterpret_cast<GenericHeader *>(prev_ext_struct))->pNext = cur_ext_struct;\n'
        pnext_proc += '        }\n'
        pnext_proc += '        prev_ext_struct = cur_ext_struct;\n\n'
        pnext_proc += '        // Process the next structure in the chain\n'
        pnext_proc += '        cur_pnext = const_cast<void *>(header->pNext);\n'
        pnext_proc += '    }\n'
        pnext_proc += '    return head_pnext;\n'
        pnext_proc += '}\n\n'
        pnext_proc += '// Free a pNext extension chain\n'
        pnext_proc += 'void FreeUnwrappedExtensionStructs(void *head) {\n'
        pnext_proc += '    void * curr_ptr = head;\n'
        pnext_proc += '    while (curr_ptr) {\n'
        pnext_proc += '        GenericHeader *header = reinterpret_cast<GenericHeader *>(curr_ptr);\n'
        pnext_proc += '        void *temp = curr_ptr;\n'
        pnext_proc += '        curr_ptr = header->pNext;\n'
        pnext_proc += '        free(temp);\n'
        pnext_proc += '    }\n'
        pnext_proc += '}\n'
        return pnext_proc

    #
    # Generate source for creating a non-dispatchable object
    def generate_create_ndo_code(self, indent, proto, params, cmd_info):
        create_ndo_code = ''
        handle_type = params[-1].find('type')
        if self.isHandleTypeNonDispatchable(handle_type.text):
            # Check for special case where multiple handles are returned
            ndo_array = False
            if cmd_info[-1].len is not None:
                ndo_array = True;
            handle_name = params[-1].find('name')
            create_ndo_code += '%sif (VK_SUCCESS == result) {\n' % (indent)
            indent = self.incIndent(indent)
            create_ndo_code += '%sstd::lock_guard<std::mutex> lock(global_lock);\n' % (indent)
            ndo_dest = '*%s' % handle_name.text
            if ndo_array == True:
                create_ndo_code += '%sfor (uint32_t index0 = 0; index0 < %s; index0++) {\n' % (indent, cmd_info[-1].len)
                indent = self.incIndent(indent)
                ndo_dest = '%s[index0]' % cmd_info[-1].name
            create_ndo_code += '%s%s = WrapNew(dev_data, %s);\n' % (indent, ndo_dest, ndo_dest)
            if ndo_array == True:
                indent = self.decIndent(indent)
                create_ndo_code += '%s}\n' % indent
            indent = self.decIndent(indent)
            create_ndo_code += '%s}\n' % (indent)
        return create_ndo_code
    #
    # Generate source for destroying a non-dispatchable object
    def generate_destroy_ndo_code(self, indent, proto, cmd_info):
        destroy_ndo_code = ''
        ndo_array = False
        if True in [destroy_txt in proto.text for destroy_txt in ['Destroy', 'Free']]:
            # Check for special case where multiple handles are returned
            if cmd_info[-1].len is not None:
                ndo_array = True;
                param = -1
            else:
                param = -2
            if self.isHandleTypeNonDispatchable(cmd_info[param].type) == True:
                if ndo_array == True:
                    # This API is freeing an array of handles.  Remove them from the unique_id map.
                    destroy_ndo_code += '%sif ((VK_SUCCESS == result) && (%s)) {\n' % (indent, cmd_info[param].name)
                    indent = self.incIndent(indent)
                    destroy_ndo_code += '%sstd::unique_lock<std::mutex> lock(global_lock);\n' % (indent)
                    destroy_ndo_code += '%sfor (uint32_t index0 = 0; index0 < %s; index0++) {\n' % (indent, cmd_info[param].len)
                    indent = self.incIndent(indent)
                    destroy_ndo_code += '%s%s handle = %s[index0];\n' % (indent, cmd_info[param].type, cmd_info[param].name)
                    destroy_ndo_code += '%suint64_t unique_id = reinterpret_cast<uint64_t &>(handle);\n' % (indent)
                    destroy_ndo_code += '%sdev_data->unique_id_mapping.erase(unique_id);\n' % (indent)
                    indent = self.decIndent(indent);
                    destroy_ndo_code += '%s}\n' % indent
                    indent = self.decIndent(indent);
                    destroy_ndo_code += '%s}\n' % indent
                else:
                    # Remove a single handle from the map
                    destroy_ndo_code += '%sstd::unique_lock<std::mutex> lock(global_lock);\n' % (indent)
                    destroy_ndo_code += '%suint64_t %s_id = reinterpret_cast<uint64_t &>(%s);\n' % (indent, cmd_info[param].name, cmd_info[param].name)
                    destroy_ndo_code += '%s%s = (%s)dev_data->unique_id_mapping[%s_id];\n' % (indent, cmd_info[param].name, cmd_info[param].type, cmd_info[param].name)
                    destroy_ndo_code += '%sdev_data->unique_id_mapping.erase(%s_id);\n' % (indent, cmd_info[param].name)
                    destroy_ndo_code += '%slock.unlock();\n' % (indent)
        return ndo_array, destroy_ndo_code

    #
    # Clean up local declarations
    def cleanUpLocalDeclarations(self, indent, prefix, name, len, index, process_pnext):
        cleanup = '%sif (local_%s%s) {\n' % (indent, prefix, name)
        if len is not None:
            if process_pnext:
                cleanup += '%s    for (uint32_t %s = 0; %s < %s%s; ++%s) {\n' % (indent, index, index, prefix, len, index)
                cleanup += '%s        FreeUnwrappedExtensionStructs(const_cast<void *>(local_%s%s[%s].pNext));\n' % (indent, prefix, name, index)
                cleanup += '%s    }\n' % indent
            cleanup += '%s    delete[] local_%s%s;\n' % (indent, prefix, name)
        else:
            if process_pnext:
                cleanup += '%s    FreeUnwrappedExtensionStructs(const_cast<void *>(local_%s%s->pNext));\n' % (indent, prefix, name)
            cleanup += '%s    delete local_%s%s;\n' % (indent, prefix, name)
        cleanup += "%s}\n" % (indent)
        return cleanup
    #
    # Output UO code for a single NDO (ndo_count is NULL) or a counted list of NDOs
    def outputNDOs(self, ndo_type, ndo_name, ndo_count, prefix, index, indent, destroy_func, destroy_array, top_level):
        decl_code = ''
        pre_call_code = ''
        post_call_code = ''
        if ndo_count is not None:
            if top_level == True:
                decl_code += '%s%s *local_%s%s = NULL;\n' % (indent, ndo_type, prefix, ndo_name)
            pre_call_code += '%s    if (%s%s) {\n' % (indent, prefix, ndo_name)
            indent = self.incIndent(indent)
            if top_level == True:
                pre_call_code += '%s    local_%s%s = new %s[%s];\n' % (indent, prefix, ndo_name, ndo_type, ndo_count)
                pre_call_code += '%s    for (uint32_t %s = 0; %s < %s; ++%s) {\n' % (indent, index, index, ndo_count, index)
                indent = self.incIndent(indent)
                pre_call_code += '%s    local_%s%s[%s] = Unwrap(dev_data, %s[%s]);\n' % (indent, prefix, ndo_name, index, ndo_name, index)
            else:
                pre_call_code += '%s    for (uint32_t %s = 0; %s < %s; ++%s) {\n' % (indent, index, index, ndo_count, index)
                indent = self.incIndent(indent)
                pre_call_code += '%s    %s%s[%s] = Unwrap(dev_data, %s%s[%s]);\n' % (indent, prefix, ndo_name, index, prefix, ndo_name, index)
            indent = self.decIndent(indent)
            pre_call_code += '%s    }\n' % indent
            indent = self.decIndent(indent)
            pre_call_code += '%s    }\n' % indent
            if top_level == True:
                post_call_code += '%sif (local_%s%s)\n' % (indent, prefix, ndo_name)
                indent = self.incIndent(indent)
                post_call_code += '%sdelete[] local_%s;\n' % (indent, ndo_name)
        else:
            if top_level == True:
                if (destroy_func == False) or (destroy_array == True):
                    pre_call_code += '%s    %s = Unwrap(dev_data, %s);\n' % (indent, ndo_name, ndo_name)
            else:
                # Make temp copy of this var with the 'local' removed. It may be better to not pass in 'local_'
                # as part of the string and explicitly print it
                fix = str(prefix).strip('local_');
                pre_call_code += '%s    if (%s%s) {\n' % (indent, fix, ndo_name)
                indent = self.incIndent(indent)
                pre_call_code += '%s    %s%s = Unwrap(dev_data, %s%s);\n' % (indent, prefix, ndo_name, fix, ndo_name)
                indent = self.decIndent(indent)
                pre_call_code += '%s    }\n' % indent
        return decl_code, pre_call_code, post_call_code
    #
    # first_level_param indicates if elements are passed directly into the function else they're below a ptr/struct
    # create_func means that this is API creates or allocates NDOs
    # destroy_func indicates that this API destroys or frees NDOs
    # destroy_array means that the destroy_func operated on an array of NDOs
    def uniquify_members(self, members, indent, prefix, array_index, create_func, destroy_func, destroy_array, first_level_param):
        decls = ''
        pre_code = ''
        post_code = ''
        index = 'index%s' % str(array_index)
        array_index += 1
        # Process any NDOs in this structure and recurse for any sub-structs in this struct
        for member in members:
            process_pnext = self.StructWithExtensions(member.type)
            # Handle NDOs
            if self.isHandleTypeNonDispatchable(member.type) == True:
                count_name = member.len
                if (count_name is not None):
                    if first_level_param == False:
                        count_name = '%s%s' % (prefix, member.len)

                if (first_level_param == False) or (create_func == False):
                    (tmp_decl, tmp_pre, tmp_post) = self.outputNDOs(member.type, member.name, count_name, prefix, index, indent, destroy_func, destroy_array, first_level_param)
                    decls += tmp_decl
                    pre_code += tmp_pre
                    post_code += tmp_post
            # Handle Structs that contain NDOs at some level
            elif member.type in self.struct_member_dict:
                # Structs at first level will have an NDO, OR, we need a safe_struct for the pnext chain
                if self.struct_contains_ndo(member.type) == True or process_pnext:
                    struct_info = self.struct_member_dict[member.type]
                    # Struct Array
                    if member.len is not None:
                        # Update struct prefix
                        if first_level_param == True:
                            new_prefix = 'local_%s' % member.name
                            # Declare safe_VarType for struct
                            decls += '%ssafe_%s *%s = NULL;\n' % (indent, member.type, new_prefix)
                        else:
                            new_prefix = '%s%s' % (prefix, member.name)
                        pre_code += '%s    if (%s%s) {\n' % (indent, prefix, member.name)
                        indent = self.incIndent(indent)
                        if first_level_param == True:
                            pre_code += '%s    %s = new safe_%s[%s];\n' % (indent, new_prefix, member.type, member.len)
                        pre_code += '%s    for (uint32_t %s = 0; %s < %s%s; ++%s) {\n' % (indent, index, index, prefix, member.len, index)
                        indent = self.incIndent(indent)
                        if first_level_param == True:
                            pre_code += '%s    %s[%s].initialize(&%s[%s]);\n' % (indent, new_prefix, index, member.name, index)
                            if process_pnext:
                                pre_code += '%s    %s[%s].pNext = CreateUnwrappedExtensionStructs(dev_data, %s[%s].pNext);\n' % (indent, new_prefix, index, new_prefix, index)
                        local_prefix = '%s[%s].' % (new_prefix, index)
                        # Process sub-structs in this struct
                        (tmp_decl, tmp_pre, tmp_post) = self.uniquify_members(struct_info, indent, local_prefix, array_index, create_func, destroy_func, destroy_array, False)
                        decls += tmp_decl
                        pre_code += tmp_pre
                        post_code += tmp_post
                        indent = self.decIndent(indent)
                        pre_code += '%s    }\n' % indent
                        indent = self.decIndent(indent)
                        pre_code += '%s    }\n' % indent
                        if first_level_param == True:
                            post_code += self.cleanUpLocalDeclarations(indent, prefix, member.name, member.len, index, process_pnext)
                    # Single Struct
                    else:
                        # Update struct prefix
                        if first_level_param == True:
                            new_prefix = 'local_%s->' % member.name
                            decls += '%ssafe_%s *local_%s%s = NULL;\n' % (indent, member.type, prefix, member.name)
                        else:
                            new_prefix = '%s%s->' % (prefix, member.name)
                        # Declare safe_VarType for struct
                        pre_code += '%s    if (%s%s) {\n' % (indent, prefix, member.name)
                        indent = self.incIndent(indent)
                        if first_level_param == True:
                            pre_code += '%s    local_%s%s = new safe_%s(%s);\n' % (indent, prefix, member.name, member.type, member.name)
                        # Process sub-structs in this struct
                        (tmp_decl, tmp_pre, tmp_post) = self.uniquify_members(struct_info, indent, new_prefix, array_index, create_func, destroy_func, destroy_array, False)
                        decls += tmp_decl
                        pre_code += tmp_pre
                        post_code += tmp_post
                        if process_pnext:
                            pre_code += '%s    local_%s%s->pNext = CreateUnwrappedExtensionStructs(dev_data, local_%s%s->pNext);\n' % (indent, prefix, member.name, prefix, member.name)
                        indent = self.decIndent(indent)
                        pre_code += '%s    }\n' % indent
                        if first_level_param == True:
                            post_code += self.cleanUpLocalDeclarations(indent, prefix, member.name, member.len, index, process_pnext)
        return decls, pre_code, post_code
    #
    # For a particular API, generate the non-dispatchable-object wrapping/unwrapping code
    def generate_wrapping_code(self, cmd):
        indent = '    '
        proto = cmd.find('proto/name')
        params = cmd.findall('param')

        if proto.text is not None:
            cmd_member_dict = dict(self.cmdMembers)
            cmd_info = cmd_member_dict[proto.text]
            # Handle ndo create/allocate operations
            if cmd_info[0].iscreate:
                create_ndo_code = self.generate_create_ndo_code(indent, proto, params, cmd_info)
            else:
                create_ndo_code = ''
            # Handle ndo destroy/free operations
            if cmd_info[0].isdestroy:
                (destroy_array, destroy_ndo_code) = self.generate_destroy_ndo_code(indent, proto, cmd_info)
            else:
                destroy_array = False
                destroy_ndo_code = ''
            paramdecl = ''
            param_pre_code = ''
            param_post_code = ''
            create_func = True if create_ndo_code else False
            destroy_func = True if destroy_ndo_code else False
            (paramdecl, param_pre_code, param_post_code) = self.uniquify_members(cmd_info, indent, '', 0, create_func, destroy_func, destroy_array, True)
            param_post_code += create_ndo_code
            if destroy_ndo_code:
                if destroy_array == True:
                    param_post_code += destroy_ndo_code
                else:
                    param_pre_code += destroy_ndo_code
            if param_pre_code:
                if (not destroy_func) or (destroy_array):
                    param_pre_code = '%s{\n%s%s%s%s}\n' % ('    ', indent, self.lock_guard(indent), param_pre_code, indent)
        return paramdecl, param_pre_code, param_post_code
    #
    # Capture command parameter info needed to wrap NDOs as well as handling some boilerplate code
    def genCmd(self, cmdinfo, cmdname):

        # Add struct-member type information to command parameter information
        OutputGenerator.genCmd(self, cmdinfo, cmdname)
        members = cmdinfo.elem.findall('.//param')
        # Iterate over members once to get length parameters for arrays
        lens = set()
        for member in members:
            len = self.getLen(member)
            if len:
                lens.add(len)
        struct_member_dict = dict(self.structMembers)
        # Generate member info
        membersInfo = []
        constains_extension_structs = False
        for member in members:
            # Get type and name of member
            info = self.getTypeNameTuple(member)
            type = info[0]
            name = info[1]
            cdecl = self.makeCParamDecl(member, 0)
            # Check for parameter name in lens set
            iscount = True if name in lens else False
            len = self.getLen(member)
            isconst = True if 'const' in cdecl else False
            ispointer = self.paramIsPointer(member)
            # Mark param as local if it is an array of NDOs
            islocal = False;
            if self.isHandleTypeNonDispatchable(type) == True:
                if (len is not None) and (isconst == True):
                    islocal = True
            # Or if it's a struct that contains an NDO
            elif type in struct_member_dict:
                if self.struct_contains_ndo(type) == True:
                    islocal = True
            isdestroy = True if True in [destroy_txt in cmdname for destroy_txt in ['Destroy', 'Free']] else False
            iscreate = True if True in [create_txt in cmdname for create_txt in ['Create', 'Allocate', 'Import', 'GetRandROutputDisplayEXT', 'RegisterDeviceEvent', 'RegisterDisplayEvent']] else False
            extstructs = self.registry.validextensionstructs[type] if name == 'pNext' else None
            membersInfo.append(self.CommandParam(type=type,
                                                 name=name,
                                                 ispointer=ispointer,
                                                 isconst=isconst,
                                                 iscount=iscount,
                                                 len=len,
                                                 extstructs=extstructs,
                                                 cdecl=cdecl,
                                                 islocal=islocal,
                                                 iscreate=iscreate,
                                                 isdestroy=isdestroy,
                                                 feature_protect=self.featureExtraProtect))
        self.cmdMembers.append(self.CmdMemberData(name=cmdname, members=membersInfo))
        self.cmd_info_data.append(self.CmdInfoData(name=cmdname, cmdinfo=cmdinfo))
        self.cmd_feature_protect.append(self.CmdExtraProtect(name=cmdname, extra_protect=self.featureExtraProtect))
    #
    # Create code to wrap NDOs as well as handling some boilerplate code
    def WrapCommands(self):
        cmd_member_dict = dict(self.cmdMembers)
        cmd_info_dict = dict(self.cmd_info_data)
        cmd_protect_dict = dict(self.cmd_feature_protect)

        for api_call in self.cmdMembers:
            cmdname = api_call.name
            cmdinfo = cmd_info_dict[api_call.name]
            if cmdname in self.interface_functions:
                continue
            if cmdname in self.no_autogen_list:
                decls = self.makeCDecls(cmdinfo.elem)
                self.appendSection('command', '')
                self.appendSection('command', '// Declare only')
                self.appendSection('command', decls[0])
                self.intercepts += [ '    {"%s", (void *)%s},' % (cmdname,cmdname[2:]) ]
                continue
            # Generate NDO wrapping/unwrapping code for all parameters
            (api_decls, api_pre, api_post) = self.generate_wrapping_code(cmdinfo.elem)
            # If API doesn't contain an NDO's, don't fool with it
            if not api_decls and not api_pre and not api_post:
                continue
            feature_extra_protect = cmd_protect_dict[api_call.name]
            if (feature_extra_protect != None):
                self.appendSection('command', '')
                self.appendSection('command', '#ifdef '+ feature_extra_protect)
                self.intercepts += [ '#ifdef %s' % feature_extra_protect ]
            # Add intercept to procmap
            self.intercepts += [ '    {"%s", (void*)%s},' % (cmdname,cmdname[2:]) ]
            decls = self.makeCDecls(cmdinfo.elem)
            self.appendSection('command', '')
            self.appendSection('command', decls[0][:-1])
            self.appendSection('command', '{')
            # Setup common to call wrappers, first parameter is always dispatchable
            dispatchable_type = cmdinfo.elem.find('param/type').text
            dispatchable_name = cmdinfo.elem.find('param/name').text
            # Generate local instance/pdev/device data lookup
            if dispatchable_type in ["VkPhysicalDevice", "VkInstance"]:
                self.appendSection('command', '    instance_layer_data *dev_data = GetLayerDataPtr(get_dispatch_key('+dispatchable_name+'), instance_layer_data_map);')
            else:
                self.appendSection('command', '    layer_data *dev_data = GetLayerDataPtr(get_dispatch_key('+dispatchable_name+'), layer_data_map);')
            # Handle return values, if any
            resulttype = cmdinfo.elem.find('proto/type')
            if (resulttype != None and resulttype.text == 'void'):
              resulttype = None
            if (resulttype != None):
                assignresult = resulttype.text + ' result = '
            else:
                assignresult = ''
            # Pre-pend declarations and pre-api-call codegen
            if api_decls:
                self.appendSection('command', "\n".join(str(api_decls).rstrip().split("\n")))
            if api_pre:
                self.appendSection('command', "\n".join(str(api_pre).rstrip().split("\n")))
            # Generate the API call itself
            # Gather the parameter items
            params = cmdinfo.elem.findall('param/name')
            # Pull out the text for each of the parameters, separate them by commas in a list
            paramstext = ', '.join([str(param.text) for param in params])
            # If any of these paramters has been replaced by a local var, fix up the list
            params = cmd_member_dict[cmdname]
            for param in params:
                if param.islocal == True or self.StructWithExtensions(param.type):
                    if param.ispointer == True:
                        paramstext = paramstext.replace(param.name, '(%s %s*)local_%s' % ('const', param.type, param.name))
                    else:
                        paramstext = paramstext.replace(param.name, '(%s %s)local_%s' % ('const', param.type, param.name))
            # Use correct dispatch table
            API = cmdinfo.elem.attrib.get('name').replace('vk','dev_data->dispatch_table.',1)
            # Put all this together for the final down-chain call
            self.appendSection('command', '    ' + assignresult + API + '(' + paramstext + ');')
            # And add the post-API-call codegen
            self.appendSection('command', "\n".join(str(api_post).rstrip().split("\n")))
            # Handle the return result variable, if any
            if (resulttype != None):
                self.appendSection('command', '    return result;')
            self.appendSection('command', '}')
            if (feature_extra_protect != None):
                self.appendSection('command', '#endif // '+ feature_extra_protect)
                self.intercepts += [ '#endif' ]
