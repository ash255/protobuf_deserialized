from google.protobuf import descriptor_pb2
from google.protobuf import unknown_fields
from google.protobuf.descriptor import FieldDescriptor
import os

LabelString = {
    FieldDescriptor.LABEL_OPTIONAL: 'optional',
    FieldDescriptor.LABEL_REQUIRED: 'required',
    FieldDescriptor.LABEL_REPEATED: 'repeated'
}

TypeString = {
    FieldDescriptor.TYPE_DOUBLE: 'double',      #1
    FieldDescriptor.TYPE_FLOAT: 'float',        #2
    FieldDescriptor.TYPE_INT64: 'int64',        #3
    FieldDescriptor.TYPE_UINT64: 'uint64',      #4
    FieldDescriptor.TYPE_INT32: 'int32',        #5
    FieldDescriptor.TYPE_FIXED64: 'fixed64',    #6
    FieldDescriptor.TYPE_FIXED32: 'fixed32',    #7
    FieldDescriptor.TYPE_BOOL: 'bool',          #8
    FieldDescriptor.TYPE_STRING: 'string',      #9
    FieldDescriptor.TYPE_GROUP: 'group',        #10
    FieldDescriptor.TYPE_MESSAGE: 'message',    #11
    FieldDescriptor.TYPE_BYTES: 'bytes',        #12
    FieldDescriptor.TYPE_UINT32: 'uint32',      #13
    FieldDescriptor.TYPE_ENUM: 'enum',          #14
    FieldDescriptor.TYPE_SFIXED32: 'sfixed32',  #15
    FieldDescriptor.TYPE_SFIXED64: 'sfixed64',  #16
    FieldDescriptor.TYPE_SINT32: 'sint32',      #17
    FieldDescriptor.TYPE_SINT64: 'sint64'       #18
}

def HasField(obj, field_name):
    try:
        return obj.HasField(field_name)
    except ValueError:
        return False

class decoder(object):
    def __init__(self, as_utf8=False):
        self.as_utf8 = as_utf8
        self.indent = 0
        self.descriptor_options = ''
        self.descriptor_message = ''
        self.descriptor_package = ''
        self.descriptor_dependency = ''
        self.descriptor_service = ''
        self.descriptor_comment = ''
        self.extension = {}
        self.out_name = ''
        self.syntax = 'proto2'
        self.nested_type = {}
    
    def Output(self):
        out = ''
        out += 'syntax = \"%s\";\n\n' % self.syntax
        if(self.descriptor_package != ''):
            out += 'package %s;\n\n' % self.descriptor_package
        if(self.descriptor_options != ''):
            out += self.descriptor_options + '\n'
        if(self.descriptor_dependency != ''):
            out += self.descriptor_dependency + '\n'
        if(self.descriptor_message != ''):
            out += self.descriptor_message + '\n'
        if(self.descriptor_service != ''):
            out += self.descriptor_service + '\n'
        if(len(self.extension) > 0):
            out += self.PrintExtension()
        if(self.descriptor_comment != ''):
            out += self.descriptor_comment
        return out
    
    def WriteMessage(self, message, dirs='.'):
        descriptor_def = self.PrintMessage(message)
        if(self.out_name == ''):
            self.out_name = input('save file')
        if(self.out_name != ''):
            full_path = os.path.join(dirs, self.out_name)
            dir_path = os.path.dirname(full_path)
            if(os.path.exists(dir_path) == False):
                os.makedirs(dir_path)
            fd = open(full_path, 'w')
            fd.write(descriptor_def)
            fd.close()
            return full_path
        return None
        
    def PrintMessage(self, message):
        #message: FileDescriptorProto
        #fields: name, package, dependency, public_dependency, weak_dependency, message_type, 
        #       enum_type, service, extension, options, source_code_info, syntax

        #对repeated的key使用HasField函数将报异常而不是返回False，需要用ListFields才能取得repeated类型成员
        all_fields = ['name', 'package', 'dependency', 'public_dependency', 'weak_dependency', 'message_type', 
                      'enum_type', 'service', 'extension', 'options', 'source_code_info', 'syntax']

        used_fields = []
        #优先设置protobuf syntax
        try:
            if(message.HasField('syntax')):
                self.syntax = message.syntax
        except Exception:
            pass
            
        for field, value in message.ListFields():
            if(field.name in all_fields):
                used_fields.append(field.name)
                if(field.name == 'name'):
                    self.out_name = message.name
                elif(field.name == 'package'):
                    self.descriptor_package = message.package
                elif(field.name == 'dependency'):
                    self.descriptor_dependency += self.PrintDescriptorDependency(message)
                elif(field.name == 'public_dependency'):
                    pass    #由PrintDescriptorDependency处理
                elif(field.name == 'weak_dependency'):
                    pass    ##由PrintDescriptorDependency处理
                elif(field.name == 'message_type'):
                    for element in message.message_type:
                        self.descriptor_message += self.PrintDescriptorMessageType(element)
                elif(field.name == 'enum_type'):
                    for element in message.enum_type:
                        self.descriptor_message += self.PrintDescriptorMessageEnumType(element) 
                elif(field.name == 'service'):
                    for element in message.service:
                        self.descriptor_service += self.PrintDescriptorService(element)
                elif(field.name == 'extension'):
                    for element in message.extension:
                        self.AddExtension(element)
                elif(field.name == 'options'):
                    self.descriptor_options += self.PrintDescriptorOptions(message.options)
                elif(field.name == 'source_code_info'):
                    pass
                elif(field.name == 'syntax'):
                    self.syntax = message.syntax
            else:
                self.descriptor_comment += '/*Unprocessed type, full_name=%s*/\n' % field.full_name
                print('Unprocessed type, full_name=%s' % field.full_name)
        self.descriptor_comment += self.PrintUnusedField(message.ListFields(), used_fields)
        self.descriptor_comment += self.PrintUnknownField(message)
        return self.Output()

    def __GetTypeNameFromStr(self, type_name):
        if(type_name != '' and self.descriptor_package != ''):
            package = '.' + self.descriptor_package + '.'
            if(type_name.startswith(package)):
                pos = type_name.rfind('.')
                if(pos != -1):
                    name = type_name[pos+1:]
                    if(name in self.nested_type):
                        return self.nested_type[name]
                return type_name.replace(package, '')
        return type_name[1:]
        
    def __GetTypeNameFromId(self, type_id):
        if(type_id in TypeString):
            return TypeString[type_id]
        return ''
        
    def __GetTypeName(self, member):
        type_name = self.__GetTypeNameFromStr(member.type_name)
        if(type_name == ''):
            type_name = self.__GetTypeNameFromId(member.type)
        return type_name
    
    def PrintUnusedField(self, all_fields, used_fields):
        out = ''
        for field, value in all_fields:
            if(field.name not in used_fields):
                out += self.indent * ' '
                if(field.type == FieldDescriptor.TYPE_ENUM or field.type == FieldDescriptor.TYPE_MESSAGE):
                    if(field.label == FieldDescriptor.LABEL_REPEATED):
                        for element in value:
                            out += self.PrintUnusedField(element.ListFields(), [])
                    else:
                        out += self.PrintUnusedField(value.ListFields(), [])
                else:
                    #todo: 需要根据field类型打印
                    out += '/*%s = %s*/' % (field.full_name, str(value))
        return out
    
    def PrintDescriptorMessageMember(self, member):
        #member: FieldDescriptorProto
        #fields: name, number, label, type, type_name, extendee, default_value, 
        #       oneof_index, json_name, options, proto3_optional
        used_fields = ['name', 'number', 'label', 'type', 'type_name', 'oneof_index', 'extendee']
        out = self.indent * ' '
        if(self.syntax == 'proto3' and member.label == FieldDescriptor.LABEL_REPEATED):
            if(member.HasField('oneof_index') == False and self.__GetTypeName(member).startswith('map<') == False):
                out += '%s ' % LabelString[member.label]
        elif(self.syntax == 'proto2' and member.HasField('label') and member.label in LabelString):
            if(member.HasField('oneof_index') == False and self.__GetTypeName(member).startswith('map<') == False):
                out += '%s ' % LabelString[member.label]
        out += '%s ' % self.__GetTypeName(member)
        out += '%s = %d' % (member.name, member.number)
        options_str = ''
        if(member.HasField('default_value')):
            used_fields.append('default_value')
            options_str += 'default=%s,' % (member.default_value)
        if(member.HasField('json_name')):
            used_fields.append('json_name')
            options_str += 'json_name=\"%s\",' % (member.json_name)
        if(member.HasField('options')):
            used_fields.append('options')
            options_str += self.PrintPropertyOptions(member.options)
        if(options_str != ''):
            if(options_str.endswith(',')):
                options_str = options_str[0:-1]
            out += ' [%s];\n' % options_str
        else:
            out += ';\n'
        out += self.PrintUnusedField(member.ListFields(), used_fields)
        out += self.PrintUnknownField(member)
        return out
    
    def PrintDescriptorMessageEnumType(self, enum):
        #enum: EnumDescriptorProto
        #fields: name, value, options, reserved_range, reserved_name
        used_fields = ['name', 'value']
        out = self.indent * ' '
        out += 'enum %s {\n' % (enum.name)
        self.indent += 2
        for member in enum.value:
            out += self.indent * ' '
            out += '%s = %d' % (member.name, member.number)
            if(member.options.HasField('deprecated')):
                out += ' [deprecated = %s]' % str(member.options.deprecated).lower()
            out += ';\n'
        if(enum.HasField('options')):
            used_fields.append('options')
            out += self.PrintCommonOptions(enum.options)
        
        if(len(enum.reserved_range) > 0):
            used_fields.append('reserved_range')
            out += self.indent * ' '
            out += 'reserved '
            for reserved_range in enum.reserved_range:
                if((reserved_range.end - reserved_range.start) == 0):
                    out += '%d,' % reserved_range.start
                else:
                    out += '%d to %d,' % (reserved_range.start, reserved_range.end)
            if(out.endswith(',')):
                out = out[0:-1]
            out += ';\n'
        if(len(enum.reserved_name) > 0):
            used_fields.append('reserved_name')
            out += self.indent * ' '
            out += 'reserved '
            for reserved_name in enum.reserved_name:
                out += '\"%s\",' % reserved_name
            if(out.endswith(',')):
                out = out[0:-1]
            out += ';\n'
        self.indent -= 2
        out += self.indent * ' '
        out += '}\n'
        return out
    
    def PrintDescriptorMssageMemberAndOneof(self, msg_type):
        #msg_type.oneof_decl: OneofDescriptorProto[]
        #OneofDescriptorProto fields: name, options
        out = ''
        oneof_maps = {}
        oneof_index = -1
        for member in msg_type.field:
            if(member.HasField('oneof_index')):
                if(member.oneof_index >= len(msg_type.oneof_decl)):
                    print('member.oneof_index=%d overflow' % member.oneof_index)
                    out += '\*member.oneof_index=%d overflow*/' % member.oneof_index
                else:
                    if(oneof_index != member.oneof_index):
                        out += '%s'
                        oneof_index = member.oneof_index
                        if(oneof_index not in oneof_maps):
                            oneof_maps[oneof_index] = []
                        oneof_maps[oneof_index].append(member)
                    else:
                        oneof_maps[oneof_index].append(member)                        
            else:
                out += self.PrintDescriptorMessageMember(member)
        
        if(len(msg_type.oneof_decl) > 0):
            oneof_def = [''] * len(msg_type.oneof_decl)
            for idx in range(len(msg_type.oneof_decl)):
                if(idx in oneof_maps):
                    oneof_def[idx] += self.indent * ' '
                    oneof_def[idx] += 'oneof %s {\n' % (msg_type.oneof_decl[idx].name)
                    self.indent += 2
                    for member in oneof_maps[idx]:
                        oneof_def[idx] += self.PrintDescriptorMessageMember(member)
                    oneof_def[idx] += self.indent * ' ' + '}\n'
                    self.indent -= 2
            out = out % tuple(oneof_def)
        return out
    
    def PrintUnknownField(self, message):
        out = ''
        unknown_field_set = unknown_fields.UnknownFieldSet(message)
        if(len(unknown_field_set) > 0):
            out += '/*[Unknown Field]\n' + str(unknown_field_set) + '*/'
        return out
        
    def PrintDescriptorMessageType(self, msg_type):
        #msg_type: DescriptorProto
        #fields: name, field, extension, nested_type, enum_type, extension_range, oneof_decl, options, reserved_range, reserved_name
        used_fields = ['name']
        out = ''
        if(msg_type.HasField('options') and msg_type.options.HasField('map_entry')):
            self.nested_type[msg_type.name] = 'map<%s, %s>' % (self.__GetTypeName(msg_type.field[0]), self.__GetTypeName(msg_type.field[1]))
        else:
            out += self.indent * ' '
            out += 'message %s {\n' % (msg_type.name)
            self.indent += 2
            if(len(msg_type.enum_type) > 0):
                used_fields.append('enum_type')
                for enum in msg_type.enum_type:
                    out += self.PrintDescriptorMessageEnumType(enum)
            if(len(msg_type.nested_type) > 0):   
                used_fields.append('nested_type')
                for nested_type in msg_type.nested_type:
                    out += self.PrintDescriptorMessageType(nested_type)
            if(len(msg_type.field) > 0):
                used_fields.append('oneof_decl')
                used_fields.append('field')
                out += self.PrintDescriptorMssageMemberAndOneof(msg_type)     
            if(len(msg_type.reserved_range) > 0):
                used_fields.append('reserved_range')
                out += self.indent * ' '
                out += 'reserved '
                for reserved_range in msg_type.reserved_range:
                    if((reserved_range.end - 1 - reserved_range.start) == 0):
                        out += '%d,' % reserved_range.start
                    else:
                        out += '%d to %d,' % (reserved_range.start, reserved_range.end - 1)
                if(out.endswith(',')):
                    out = out[0:-1]
                out += ';\n'
            if(len(msg_type.reserved_name) > 0):
                used_fields.append('reserved_name')
                out += self.indent * ' '
                out += 'reserved '
                for reserved_name in msg_type.reserved_name:
                    out += '\"%s\",' % reserved_name
                if(out.endswith(',')):
                    out = out[0:-1]
                out += ';\n'
            if(len(msg_type.extension_range) > 0):
                used_fields.append('extension_range')
                for extension_range in msg_type.extension_range:
                    out += self.indent * ' '
                    if((extension_range.end - 1 - extension_range.start) == 0):
                        out += 'extensions %d;\n' % extension_range.start
                    else:
                        if(extension_range.end - 1 == 536870911):
                            out += 'extensions %d to max;\n' % (extension_range.start)
                        else:
                            out += 'extensions %d to %d;\n' % (extension_range.start, extension_range.end - 1)
            if(msg_type.HasField('options')):
                used_fields.append('options')
                out += self.PrintCommonOptions(msg_type.options)
            out += self.PrintUnusedField(msg_type.ListFields(), used_fields)
            out += self.PrintUnknownField(msg_type)
            self.indent -= 2
            out += self.indent * ' '
            out += '}\n'
        return out
        
    def PrintDescriptorDependency(self, message):
        #message.dependency: string[]
        #message.public_dependency: int[]
        #message.weak_dependency: int[]
        out = ''
        dep_cnt = 0
        for dep in message.dependency:
            if(dep_cnt in message.public_dependency):
                out += 'import public \"%s\";\n' % dep
            elif(dep_cnt in message.weak_dependency):
                out += 'import weak \"%s\";\n' % dep
            else:
                out += 'import \"%s\";\n' % dep
            dep_cnt += 1
        return out
    
    def PrintCommonOptions(self, options, lead_str='option '):
        #根据option的类型打印，每个option一行
        out = ''
        for field, value in options.ListFields():
            #cpp_type比type类型少一点，利于判断
            if(field.cpp_type == FieldDescriptor.CPPTYPE_STRING):
                out += '%s%s%s = \"%s\";\n' % (self.indent*' ', lead_str, field.name, value)
            elif(field.cpp_type == FieldDescriptor.CPPTYPE_BOOL):
                out += '%s%s%s = %s;\n' % (self.indent*' ', lead_str, field.name, str(value).lower())
            elif(field.cpp_type in [FieldDescriptor.CPPTYPE_INT32, FieldDescriptor.CPPTYPE_INT64, 
                                    FieldDescriptor.CPPTYPE_UINT32, FieldDescriptor.CPPTYPE_UINT64]): 
                out += '%s%s%s = %d;\n' % (self.indent*' ', lead_str, field.name, value)
            elif(field.cpp_type in [FieldDescriptor.CPPTYPE_DOUBLE, FieldDescriptor.CPPTYPE_FLOAT]): 
                out += '%s%s%s = %f;\n' % (self.indent*' ', lead_str, field.name, value)
            elif(field.cpp_type == FieldDescriptor.CPPTYPE_ENUM):
                out += '%s%s%s = %s;\n' % (self.indent*' ', lead_str, field.name, field.enum_type.values_by_number[value].name)
            else:
                out += '%s//unknown type, name=%s, value=%s, type(value)=%s' % (self.indent*' ', field.name, str(value), type(value))
                print('unknown type, name=%s, value=%s, type(value)=%s' % (field.name, str(value), type(value)))
        return out
        
    def PrintPropertyOptions(self, options):
        #根据option的类型打印，所有option位于一行内
        out = ''
        comment = ''
        for field, value in options.ListFields():
            #cpp_type比type类型少一点，利于判断
            if(field.cpp_type == FieldDescriptor.CPPTYPE_STRING):
                out += '%s=\"%s\",' % (field.name, value)
            elif(field.cpp_type == FieldDescriptor.CPPTYPE_BOOL):
                out += '%s=%s,' % (field.name, str(value).lower())
            elif(field.cpp_type in [FieldDescriptor.CPPTYPE_INT32, FieldDescriptor.CPPTYPE_INT64, 
                                    FieldDescriptor.CPPTYPE_UINT32, FieldDescriptor.CPPTYPE_UINT64]): 
                out += '%s=%d,' % (field.name, value)
            elif(field.cpp_type in [FieldDescriptor.CPPTYPE_DOUBLE, FieldDescriptor.CPPTYPE_FLOAT]): 
                out += '%s=%f,' % (field.name, value)
            elif(field.cpp_type == FieldDescriptor.CPPTYPE_ENUM):
                out += '%s=%s,' % (field.name, field.enum_type.values_by_number[value].name)
            else:
                comment += '/*unknown type, name=%s, value=%s, type(value)=%s*/' % (field.name, str(value), type(value))
                print('unknown type, name=%s, value=%s, type(value)=%s' % (field.name, str(value), type(value)))
        if(out.endswith(',')):
            out = out[0:-1]
        return out + comment
    
    def PrintDescriptorOptions(self, options):
        #options: FileOptions
        #fields: java_package, java_outer_classname, java_multiple_files, java_generate_equals_and_hash, 
        #        java_string_check_utf8, optimize_for, go_package, cc_generic_services, java_generic_services, 
        #        py_generic_services, php_generic_services, deprecated, cc_enable_arenas, objc_class_prefix, 
        #        csharp_namespace, swift_prefix, php_class_prefix, php_namespace, php_metadata_namespace, ruby_package
        return self.PrintCommonOptions(options)
    
    def PrintDescriptorServiceMethod(self, method):
        #method: MethodDescriptorProto
        #field: name, input_type, output_type, options, client_streaming, server_streaming
        used_fields = ['name', 'input_type', 'output_type']
        option_str = ''
        out = self.indent * ' '
        out += 'rpc %s(' % method.name
        if(method.HasField('client_streaming')):
            used_fields.append('client_streaming')
            out += 'stream '
        out += self.__GetTypeNameFromStr(method.input_type)
        out += ') returns('
        if(method.HasField('server_streaming')):
            used_fields.append('server_streaming')
            out += 'stream '
        out += self.__GetTypeNameFromStr(method.output_type)
        if(method.HasField('options')):
            used_fields.append('options')
            option_str = self.PrintPropertyOptions(method.options)
        if(option_str == ''):
            out += ');'
        else:
            out += ') [%s];' % option_str
        out += self.PrintUnusedField(method.ListFields(), used_fields)
        out += self.PrintUnknownField(method)
        out += '\n'
        return out
    
    def PrintDescriptorService(self, service):
        #service: ServiceDescriptorProto
        #fields: name, method, option
        used_fields = ['name', 'method']
        out = ''
        out += self.indent * ' '
        out += 'service %s {\n' % (service.name)
        self.indent += 2
        for method in service.method:
            out += self.PrintDescriptorServiceMethod(method)
        if(service.HasField('options')):
            used_fields.append('options')
            out += self.PrintCommonOptions(service.options)
        out += self.PrintUnusedField(service.ListFields(), used_fields)
        out += self.PrintUnknownField(service)
        self.indent -= 2
        out += self.indent * ' '
        out += '}\n'
        return out
    
    def PrintExtension(self):
        out = ''
        for type_name, extension in self.extension.items():
            out += self.indent * ' '
            out += 'extend %s {\n' % (type_name)
            self.indent += 2
            for extend in extension:
                out += self.PrintDescriptorMessageMember(extend)
            self.indent -= 2
            out += self.indent * ' '
            out += '}\n'
        return out 
    
    def AddExtension(self, values):
        type_name = self.__GetTypeNameFromStr(values.extendee)
        if(type_name not in self.extension):
            self.extension[type_name] = []
        self.extension[type_name].append(values)

def deserialized(file, dirs=''):
    fd_r = open(file, 'rb')
    data = fd_r.read()
    fd_r.close()
    file_desc_proto = descriptor_pb2.FileDescriptorProto.FromString(data)
    if(dirs == ''):
        # print(file_desc_proto)
        return decoder().PrintMessage(file_desc_proto)
    else:
        return decoder().WriteMessage(file_desc_proto, dirs)


from google.protobuf import text_format
def main():
    for root, dirs, files in os.walk('protobin'):
        for name in files:
            path = os.path.join(root, name)
            print('proc: %s' % path)
            deserialized(path, 'protodef')
    # print(deserialized(''))

if __name__ == '__main__':
    main()
        