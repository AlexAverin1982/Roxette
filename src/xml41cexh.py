# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
# from xml.dom.pulldom import parse
"""src - актуальные данные с неправильными идентификаторами - этот файл надо редактировать для загрузки
dst - неактуальные данные с правильными (целевыми) идентификаторами и ссылками - из этого файла они и берутся для замены"""
import xml.etree.ElementTree as et
from xml.etree.ElementTree import Element as el
from copy import deepcopy
from uuid import uuid4
import xml
import pickle

import os

def empty_UID():
    return '00000000-0000-0000-0000-000000000000'

def get_type_name_from_header(header: str, xml_1c_prefix: str):
    result = ''
    if header:
        l = len(xml_1c_prefix)
        line = header.strip()
        if line.startswith(xml_1c_prefix):
            result = line[l:]
            p = result.find('>')
            if p != -1:
                result = result[:p]
        elif ('<'+line).startswith(xml_1c_prefix):
            line = '<'+line
            result = line[l:]
            p = result.find('>')
            if p != -1:
                result = result[:p]

    return result

def prepare_xml_tree(xml_file: str):
    parsr = et.XMLParser(encoding="utf-8")
    et.register_namespace('V8Exch', 'http://www.1c.ru/V8/1CV8DtUD/')
    et.register_namespace('v8', 'http://v8.1c.ru/data')
    et.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    return et.parse(xml_file, parser=parsr)

def get_tag_value(obj, tag: str):
    result = None
    p = tag.find(' ')
    if (p != -1):
        tag = tag[:p]
        descr = list(obj.iter('Description'))[0].text
        tagid = list(obj.iter('Ref'))[0].text
        for attr in obj.iter():
            if attr.tag.lower() == tag.lower():
                result = attr.text
                if isinstance(attr.text, str):
                    result = attr.text
                elif isinstance(attr.text, tuple):
                    result = str(attr.text[0])
                else:
                    result = ''
                break
    else:
        descr = list(obj.iter('Description'))[0].text
        tagid = list(obj.iter('Ref'))[0].text

        for attr in obj.iter(tag):               #.iter(tag):
            # if attr.tag.lower() == tag.lower():
                if isinstance(attr.text, str):
                    result = attr.text
                elif isinstance(attr.text, tuple):
                    result = str(attr.text[0])
                else:
                    result = ''
                break
    return result

def has_tag(node, tag):
    result = False
    for d in node:
        if d.tag.lower() == tag.lower():
            result = True
            break
    return result

def is_empty(val, including_empty_UID: bool = True):
    return ((val == '00000000-0000-0000-0000-000000000000') and including_empty_UID) or (not val)

def replace_tag_values(obj_list: list, tag_to_edit, mapping: dict):
    non_processed = 0
    if hasattr(obj_list, '__iter__'):
        for obj in obj_list:
            if isinstance(tag_to_edit, dict):
                for key, val in tag_to_edit.items():
                    if val and isinstance(val, (dict, str)):
                        for attrib in obj.iter(key):
                            non_processed = non_processed + replace_tag_values(attrib, val, mapping)
            elif isinstance(tag_to_edit, str):
                for attrib in obj.iter(tag_to_edit):
                    key = attrib.text
                    non_processed = non_processed + 1
                    old_val = attrib.text

                    # if mapping.get('fa7fd4e1-2fa7-11e5-afc8-002590a6a5a7'):
                    #     del (mapping['fa7fd4e1-2fa7-11e5-afc8-002590a6a5a7'])

                    attrib.text = mapping.get(key, key)
                    if (attrib.text != old_val) or is_empty(old_val, True):
                        non_processed = non_processed - 1
    else:
        if isinstance(tag_to_edit, dict):
            for key, val in tag_to_edit.items():
                if val and isinstance(val, (dict, str, list)):
                    for attrib in obj_list:
                        non_processed = non_processed + replace_tag_values(attrib, val, mapping)

        elif isinstance(tag_to_edit, list):
            for tag in tag_to_edit:
                for attrib in obj_list.iter(tag):
                    key = attrib.text
                    non_processed = non_processed + 1
                    old_val = attrib.text
                    attrib.text = mapping.get(key, key)
                    if attrib.text != old_val:
                        non_processed = non_processed - 1

        elif isinstance(tag_to_edit, str):
            for attrib in obj_list.iter(tag_to_edit):
                non_processed = non_processed + 1
                key = attrib.text
                old_val = attrib.text
                attrib.text = mapping.get(key, key)
                if attrib.text != old_val:
                    non_processed = non_processed - 1

    return non_processed

def remove_tags_ex(obj_header: str, tree: et, tags_to_remove, iterations_count: int = 5):
    for _ in range(iterations_count):
        c = len(list(tree.iter(obj_header)))
        while True:
            delete_tags(tree.iter(obj_header), tags_to_remove)
            if c == len(list(tree.iter(obj_header))):
                break
            else:
                c = len(list(tree.iter(obj_header)))

def remove_tags_in_objects(objects: list, tags_to_remove, iterations_count: int = 5):
    delete_tags(objects, tags_to_remove)

    # for _ in range(iterations_count):
    #     c = len(objects)
    #     while True:
    #         delete_tags(objects, tags_to_remove)
    #         if c == len(objects):
    #             break
    #         else:
    #             c = len(objects)

def move_tag(obj_header: str, tree: et, tag_to_move: str, tag_insert_after: str):
    for obj in tree.iter(obj_header):
        for attrib in obj:
            if attrib.tag == tag_to_move:
                val = attrib.text
                delete_tags(obj, [tag_to_move])
                insert_attrib(obj, tag_to_move, val, tag_insert_after)

def move_tag_in_objects(object, tag_to_move: str, tag_insert_after: str):
    if hasattr(object, '__iter__'):
        for obj in object: move_tag_in_objects(obj, tag_to_move, tag_insert_after)
    else:
        for attrib in object.findall(tag_to_move):
            # if attrib.tag == :
                val = attrib.text
                delete_tags(object, [tag_to_move])
                insert_attrib(object, tag_to_move, val, tag_insert_after)

def get_tag_by_tag(obj_list, tag: str, tagval: str, ref_tag: str) -> tuple:
    result = ''
    if isinstance(obj_list, xml.etree.ElementTree.ElementTree):
        root = obj_list.getroot()
        if len(root):
            root = root[0]
        else:
            return None, None
        obj_list = list(root)


    if not tagval: return None, None
    for obj in obj_list:
        tag_val = get_tag_value(obj, tag)
        if tag_val and (tag_val.lower() == tagval.lower()):
            result = get_tag_value(obj, ref_tag)
            break
    else:
        obj = None

    if (not obj) and tag and tagval and (tag.lower() == 'number') and (tagval[:2] != '00'):
        tagval = '00'+tagval[2:]

    return (result, obj)

def set_tag_value(obj, tag, new_val):
    if hasattr(obj, '__iter__'):
        for ob in obj: set_tag_value(ob, tag, new_val)
    else:
        for tag_obj in obj.iter(tag):
            tag_obj.text = new_val

def replace_links(src_list: list, src_refs: list, dst_refs: list, ref_tag, descr_tag: str, target_tag: str, filter: dict = None, mapping: dict = None):
    """
src_list - объекты из этого списока правим
src_refs - по этому списку объектов мы определяем наименования по исходным ссылкам из src_list
dst_refs - в этом списке мы по наименованию определяем правильный идентификатор
ref_tag - имя тэга, значение которого нужно поправить в объектах из списка src_list
descr_tag - имя тэга, значение которого мы будем брать из второго списка, находя объект по ссылке ref_id
target_tag - имя тэга, значение которого мы ищем в списке dst_refs, используя для поиска значение тэга ref_name,
         это целевое значение, мы меняем значение ref_id на значение id_tag в списке src_list
    """
                                # кэш для ускоренного поиска...
    descr_mappings_cache = dict()               # ...наименования по идентификатору   Ref -> Name(or Description)

    if mapping:
        if isinstance(mapping, str) and os.path.isfile(mapping) and os.path.exists(mapping):
            with open('mapping_cache.dat', 'rb') as myfile:
                correct_id_mappings_cache = pickle.load(myfile)
        elif isinstance(mapping, dict):
            correct_id_mappings_cache = mapping
    else:
        correct_id_mappings_cache = dict()          # ...актуального идентификатора по исходному Ref_src -> Ref_dst

    if hasattr(src_list, '__iter__'):
        for src_obj in src_list:                       # просматриваем редактируемые объекты

            if filter and isinstance(ref_tag, str) and isinstance(filter, dict):
                valid_object = True
                for key, val in filter.items():
                    if get_tag_value(src_obj, key).lower() != str(val).lower():
                        valid_object = False
                        break
                if not valid_object: continue

            if isinstance(ref_tag, dict):
                for key, val in ref_tag.items():
                    if val and isinstance(val, (dict, str)):
                        for attrib in src_obj.iter(key):
                            replace_links(attrib, src_refs, dst_refs, val, descr_tag, target_tag, filter)
            elif isinstance(ref_tag, str):
                ref_val = get_tag_value(src_obj, ref_tag)            # находим в исходнике меняемое поле
                if is_empty(ref_val): continue
                search_descr_val = descr_mappings_cache.get(ref_val)
                if not search_descr_val:            # находим значение поля (наименование, имя), по которому будем искать объект с правильным значением идентификатора
                    search_descr_val = get_tag_by_tag(src_refs, target_tag, ref_val, descr_tag)[0]
                    if search_descr_val:
                        descr_mappings_cache[ref_val] = search_descr_val

                target_tag_val = correct_id_mappings_cache.get(ref_val)     # ищем правильное значение идентификатора сначала в кэше
                if not target_tag_val:
                    # if (not search_descr_val) or (not descr_tag):
                     #   target_tag_val = empty_UID()
                        # continue
                    target_tag_val = get_tag_by_tag(dst_refs, descr_tag, search_descr_val, target_tag)  # потом в объектах с правильными значениями
                    if target_tag_val and (len(target_tag_val) > 1) and target_tag_val[0] and target_tag_val[1]:
                        target_tag_val = target_tag_val[0]
                    elif descr_tag and search_descr_val and (descr_tag.lower() == 'number') and (search_descr_val[:2] != '00'):
                        search_descr_val = '00' + search_descr_val[2:]
                        target_tag_val = get_tag_by_tag(dst_refs, descr_tag, search_descr_val, target_tag)
                        if target_tag_val[0] and target_tag_val[1]:
                            target_tag_val = target_tag_val[0]
                        else:
                            target_tag_val = None
                    # else:
                    #     target_tag_val = empty_UID()

                    if target_tag_val:
                        correct_id_mappings_cache[ref_val] = target_tag_val
                        set_tag_value(src_obj, ref_tag, target_tag_val) # устанавливаем правильное значение идентификатора
    else:
        valid_object = True
        if filter and isinstance(ref_tag, str):
            valid_object = True
            for key, val in filter.items():
                if get_tag_value(src_list, key).lower() != str(val).lower():
                    valid_object = False
                    break
        if valid_object:
            if isinstance(ref_tag, dict):
                for key, val in ref_tag.items():
                    if val and isinstance(val, (dict, str)):
                        for attrib in src_list.iter(key):
                            replace_links(attrib, src_refs, dst_refs, val, descr_tag, target_tag, filter)
                    elif isinstance(val, list):
                        for attrib in src_list.iter(key):
                            for tag in val:
                                replace_links(attrib, src_refs, dst_refs, tag, descr_tag, target_tag, filter)
            elif isinstance(ref_tag, str):
                ref_val = get_tag_value(src_list, ref_tag)  # находим в банке ссылку на страну ( в исходнике - меняемое поле)
                if not is_empty(ref_val):
                    search_descr_val = descr_mappings_cache.get(ref_val)
                    if not search_descr_val:
                        search_descr_val = get_tag_by_tag(src_refs, target_tag, ref_val, descr_tag)[0]  # по ссылке находим название страны
                        descr_mappings_cache[ref_val] = search_descr_val

                    target_tag_val = correct_id_mappings_cache.get(ref_val)
                    if not target_tag_val:
                        target_tag_val = get_tag_by_tag(dst_refs, descr_tag, search_descr_val, target_tag)[0]  # по названию страны находим ее правильный идентификатор
                        if target_tag_val:
                            correct_id_mappings_cache[ref_val] = target_tag_val
                            set_tag_value(src_list, ref_tag, target_tag_val)

    return correct_id_mappings_cache

def filter_objects(obj_list: list, tag: str, filter_value: str):
    result = list()
    for obj in obj_list:
        name = get_tag_value(obj, 'Description')
        tag_val = get_tag_value(obj, tag)
        if tag_val.lower() == filter_value.lower():
            result.append(obj)
            # obj_list.remove(obj)
    return result

def filter_tree(tree: et, tag: str, filter_value: str, object_header: str = '') -> et:
    root = tree.getroot()[0]
    if object_header:
        for obj in root.iter(object_header):
            tag_val = get_tag_value(obj, tag)
            if tag_val.lower() != filter_value.lower():
                root.remove(obj)
    else:
        for obj in root:
            tag_val = get_tag_value(obj, tag)
            if tag_val.lower() != filter_value.lower():
                root.remove(obj)
    return tree

# def filter_objects_by_headers(root: el, headers: list):
#     if len(root):
#         if root[0].tag.startswith(xml_1c_prefix):
#             for attr in root:
#                 if attr.tag not in headers:
#                     root.remove(attr)
#         else:
#             filter_objects_by_headers(root[0], headers)

def delete_tags(obj, tags_to_delete):
    if hasattr(obj, '__iter__'):            # iterable
        for ob in obj: delete_tags(ob, tags_to_delete)
    else:
        if isinstance(tags_to_delete, dict):
            for key, val in tags_to_delete.items():
                for attr in obj.iter(key):
                    delete_tags(attr, val)
        elif isinstance(tags_to_delete, str):
            for attr in obj:
                if attr.tag == tags_to_delete:
                    obj.remove(attr)
        elif hasattr(tags_to_delete, '__iter__'):

            for tag in tags_to_delete:
                for attr in obj.findall(tag):
                    obj.remove(attr)

            # for attr in obj:
            #
            #     if attr.tag in tags_to_delete:
            #         obj.remove(attr)

            for tag in tags_to_delete:
                if isinstance(tag, dict):
                    for key, val in tag.items():
                        for attr in obj.iter(key):
                            delete_tags(attr, val)

def replace_links_in_objects_of_type(object_type_header: str,
                                     objects_to_edit: list,
                                     tree_src: et,
                                     tree_dst: et,
                                     tag_to_edit: str,
                                     tag_to_identify: str,
                                     correct_value_tag: str,
                                     mapping: dict = None,
                                     filter: dict = None,
                                     reference_obj_type_header: str = None):
    obj_list_src = objects_to_edit

    if isinstance(tree_src, xml.etree.ElementTree.ElementTree):
        root_src = tree_src.getroot()
        if len(root_src):
            root_src = root_src[0]
            # список объектов одного типа, из которых будем брать правильные значения идентификаторов
            if reference_obj_type_header:
                reference_obj_list = list(root_src.iter(object_type_header))
            else:
                reference_obj_list = obj_list_src  # doublecheck this!
            if not reference_obj_list:
                reference_obj_list = list(root_src.iter(reference_obj_type_header))
        else:
            return
    #     obj_list_src = list(tree_src.iter(object_type_header))
    #     if not obj_list_src:
    #         obj_list_src = list(tree_src.iter(reference_obj_type_header))
    # elif isinstance(tree_src, list):
    #     obj_list_src = tree_src
    # else:
    #     return

    if isinstance(tree_dst, xml.etree.ElementTree.ElementTree):
        root_dst = tree_dst.getroot()
        if len(root_dst):
            root_dst = root_dst[0]
            obj_list_dst = list(root_dst.iter(object_type_header))
            if not obj_list_dst:
                obj_list_dst = list(root_dst.iter(reference_obj_type_header))
        else:
            return

    elif isinstance(tree_dst, list):
        obj_list_dst = tree_dst
    else:
        return


    if mapping:
        all_replaced = (replace_tag_values(obj_list_src, tag_to_edit, mapping) == 0)
    else:
        all_replaced = False
        """
            obj_list_src - список объектов одного типа, в которых мы будем менять ссылки
            reference_obj_list
            obj_list_dst - список объектов того же типа, откуда будем брать корректные значения
            tag_to_edit - имя тэга, значание которого будем менять
            tag_to_identify - имя тэга, по которому будем искать тот же объект с правильным значением изменяемого тэга 
            correct_value_tag - имя тэга, содержащего правильное значение изменяемого тэга
            filter - 
        """
    if all_replaced:
        return mapping
    else:
        return replace_links(obj_list_src, reference_obj_list, obj_list_dst, tag_to_edit, tag_to_identify, correct_value_tag, filter=filter, mapping=mapping)



def list_used_xml_object_types(tree_data, file_to_save: str = None):
    types_list = []
    if isinstance(tree_data, str) and os.path.exists(tree_data) and os.path.isfile(tree_data):
        tree = prepare_xml_tree(tree_data)
    elif isinstance(tree_data, xml.etree.ElementTree.ElementTree):
        tree = tree_data

    root = tree.getroot()
    if len(root):
        root = root[0]
    else:
        return types_list

    for obj in root:
        if obj.tag not in types_list: types_list.append(obj.tag)
    types_list.sort()

    if file_to_save:
        with open(file_to_save, 'w', encoding='utf-8-sig') as myfile:
            for t in types_list:
                myfile.write(str(t) + '\n')
    return types_list

def insert_attrib(obj, tag: str, val: str, insert_after_tag: str, attribute: str = ''):
    if hasattr(obj, '__iter__'):            # iterable
        for ob in obj: insert_attrib(ob, tag, val, insert_after_tag, attribute)
    else:
        new_attrib = el(tag)
        new_attrib.text = val
        # if attribute:
        #     new_attrib.attrib = attribute     # error comes here
        if not len(list(obj.iter(tag))):
            if insert_after_tag:
                for ind, attr in enumerate(obj):

                    if attr.tag == insert_after_tag:
                        new_attrib.tail = attr.tail
                        obj.insert(ind+1, new_attrib)
                        # obj.set(tag, val)
                        break
            else:
                obj.insert(0, new_attrib)       # !!! строки двух записей слипаются

def get_obj_by_ref(tree: et, xml_object_header: str, ref_tag: str, ref_tag_val: str) -> el:
    result = None
    root = tree.getroot()
    if len(root):
        root = root[0]
    else:
        return

    for obj in root.findall(xml_object_header):
        for ref_attr in obj.findall(ref_tag):
            if ref_attr.text == ref_tag_val:
                    result = obj
                    break
        if result: break
    return result

def copy_attrib_from_source(tree_src: et, tree_dst: et, xml_object_header: str, tag: str, insert_after_tag: str, descr_tag: str = 'Description', default_val: str = ''):
    obj_src_list = list(tree_src.iter(xml_object_header))
    obj_dst_list = list(tree_dst.iter(xml_object_header))

    for obj_src in obj_src_list:
        descr = get_tag_value(obj_src, descr_tag)
        val = get_tag_by_tag(obj_dst_list, descr_tag, descr, tag)[0]
        if not val: val = default_val
        insert_attrib(obj_src, tag, val, insert_after_tag)

def get_exchange_scheme_value(exchange_scheme_source, xml_type_header, tag_to_search) -> str:
    result = ''
    if isinstance(exchange_scheme_source, str) and os.path.exists(exchange_scheme_source) and os.path.isfile(exchange_scheme_source):
        with open(exchange_scheme_source, 'r') as f:
            exchange_scheme = f.readlines()
    elif isinstance(exchange_scheme_source, list) or isinstance(exchange_scheme_source, dict):
        exchange_scheme = exchange_scheme_source
    else:
        exchange_scheme = []

    if isinstance(exchange_scheme, dict):
        exchange_scheme = exchange_scheme.get(xml_type_header)
        if exchange_scheme:
            result = exchange_scheme.get(tag_to_search,'')
    elif isinstance(exchange_scheme, list):
        type_section_found = False
        for line in exchange_scheme:
            line = line.strip()
            if line.find(xml_type_header) != -1:
                type_section_found = True

            if type_section_found:
                if line.startswith(tag_to_search):
                    result = line[:line.find('=')+1]
                    break
    return result

def xor(a: bool, b: bool) -> bool:
    return (a and not b) or (not a and b)

def salvage_nonempty_old_values(parameters: dict):
    tree_src = parameters.get('tree_src')
    if not tree_src: return
    tree_dst = parameters.get('tree_dst')
    if not tree_dst: return
    key_tags = parameters.get('key_tags', [])
    obj_ref_mapping = parameters.get('mappings', {})
    exchange_scheme = parameters.get('exchange_scheme', {})

    object_types_list = list_used_xml_object_types(tree_src)

    root = tree_src.getroot()
    if len(root):
        root = root[0]
    else:
        return

    # obj_src_list = list(tree_src.iter(xml_object_header))
    # obj_dst_list = list(tree_dst.iter(xml_object_header))

    for xml_type in object_types_list:
        ref_mapping = obj_ref_mapping.get(xml_type)
        for ind, obj_src in enumerate(root.findall(xml_type)):
            ref_id = None
            dst_ref_id = None
            dst_obj = None
            for attr in obj_src:
                if not ref_id:
                    ref_id = get_tag_value(obj_src, 'Ref')
                if attr.tag in key_tags: continue
                old_val = None

                if not dst_ref_id:
                    if ref_mapping:
                        dst_ref_id = ref_mapping.get(ref_id)

                    if not dst_ref_id:
                        dst_obj = get_obj_by_ref(tree_dst, xml_type, 'Ref', ref_id)
                        if dst_obj: dst_ref_id = ref_id
                    if not dst_ref_id:
                        id_tag = get_exchange_scheme_value(exchange_scheme, xml_type, 'id_description_tag')
                        # descr = get_tag_value(obj_src, 'Description')
                        if id_tag:
                            id_tag_src_val = get_tag_value(obj_src, id_tag)
                        else:
                            continue
                        if id_tag_src_val:
                            dst_ref_id, dst_obj = get_tag_by_tag(tree_dst, id_tag, id_tag_src_val, 'Ref')
                        if dst_ref_id:
                            if obj_ref_mapping:
                                obj_ref_mapping[ref_id] = dst_ref_id
                        else:
                            continue

                if not dst_obj:
                    dst_obj = get_obj_by_ref(tree_dst, xml_type, 'Ref', dst_ref_id)

                if dst_obj:
                    old_val = get_tag_value(dst_obj, attr.tag)
                    obj_ref_mapping[ref_id] = dst_ref_id

                if xor(is_empty(old_val, False), is_empty(attr.text, False)):
                    if old_val:
                        set_tag_value(obj_src, attr.tag, old_val)
                        # tail = attr.tail
                        # attr.text = old_val
                        # attr.tail = tail

def compare_objects_attribute_content(attr_src: el, attr_dst: el):
    comparison_result = []
    if attr_src.text != attr_dst.text:
        if not attr_src.text:
            comparison_result.append(
                'Атрибут ' + attr_src.tag + ' не хранит значение в целевом объекте и имеет значение ' + attr_dst.text + ' в исходном')
        elif not attr_dst.text:
            comparison_result.append(
                'Атрибут ' + attr_src.tag + ' не хранит значение в исходном объекте и имеет значение ' + attr_src.text + ' в целевом')
        else:
            comparison_result.append(
                'Атрибут ' + attr_src.tag + ' имеет значение ' + attr_src.text + ' в целевом объекте и значение ' + attr_dst.text + ' в исходном')
    else:
        if len(attr_src) and not len(attr_dst):
            comparison_result.append('Атрибут ' + attr_src.tag +  ' целевого объекта содержит дочерние элементы, в то время, как исходный - нет.')
    if len(attr_src) and not len(attr_dst):
        comparison_result.append(
            'Атрибут ' + attr_src.tag + ' целевого объекта содержит дочерние элементы, в то время, как исходный - нет.')
    elif not len(attr_src) and len(attr_dst):
        comparison_result.append(
            'Атрибут ' + attr_src.tag + ' исходного объекта содержит дочерние элементы, в то время, как целевой - нет.')
    return comparison_result

def compare_objects(src_data, dst_data, ref_id_src: str = None, ref_id_dst: str = None, extra_params: dict = {}):
    def save_comparison_result_to_file(data: list, filename: str):
        if not filename: return
        with open(filename, 'w', encoding='utf-8-sig') as f:
            for line in data: f.writelines(line + '\n')

    comparison_result = []
    result_filename = extra_params.get('result_filename', 'comparison_result.txt')

    if isinstance(src_data, str) and os.path.exists(src_data) and os.path.isfile(src_data):
        tree_src = prepare_xml_tree(src_data)
        file_src = src_data
    elif isinstance(src_data, xml.etree.ElementTree.ElementTree):
        tree_src = src_data
    else:
        comparison_result.append('Данные целевого дерева имеют неподходящий тип, сравнение отменено.')
        save_comparison_result_to_file(result_filename)
        terminate_execution = True
    
    if isinstance(dst_data, str) and os.path.exists(dst_data) and os.path.isfile(dst_data):
        tree_dst = prepare_xml_tree(dst_data)
        file_dst = dst_data
    elif isinstance(dst_data, xml.etree.ElementTree.ElementTree):
        tree_dst = dst_data
    else:
        comparison_result.append('Данные конечного дерева имеют неподходящий тип, сравнение отменено.')
        save_comparison_result_to_file(result_filename)
        return

    root_src = tree_src.getroot()
    root_dst = tree_dst.getroot()
    if len(root_src):
        root_src = root_src[0]
    else:
        comparison_result.append('Исходное дерево пустое или имеет некорректую структуру, сравнение отменено.')
        save_comparison_result_to_file(result_filename)
        return

    if len(root_dst):
        root_dst = root_dst[0]
    else:
        comparison_result.append('Конечное дерево пустое или имеет некорректую структуру, сравнение отменено.')
        save_comparison_result_to_file(result_filename)
        return

    stop_at_first = extra_params.get('stop_at_first', False)    # завершать сравнение, при первом же несоответствии

    line_number_src = extra_params.get('line_number_src', -1)   # номер строки в целевом файле, где обнаружена ошибка
    line_number_dst = extra_params.get('line_number_dst', -1)   # номер строки в конечном файле, где обнаружена ошибка
    if not file_src: file_src = extra_params.get('file_src')
    if not file_dst: file_dst = extra_params.get('file_dst')

    src_xml_types = list_used_xml_object_types(tree_src)
    dst_xml_types = list_used_xml_object_types(tree_dst)
    if not ref_id_dst: ref_id_dst = ref_id_src


    if (line_number_src != -1) and file_src and os.path.exists(file_src) and os.path.isfile(file_src):

        with open(file_src, 'r', encoding='utf-8-sig') as f_src:      # ищем в загружаемом файле,
            lines = f_src.readlines()
            # начиная с указанной строчки (место ошибки) и двигаясь вверх, идентификатор искомого объекта
            for i in range(line_number_src, 0, -1):
                line = lines[i].strip().strip('<>')
                if line in src_xml_types:               # нашли заголовок объекта
                    xml_object_type = line
                    for j in range(i+1, line_number_src):   # ищем идентификатор
                        line_ref = lines[j].strip()
                        p = line_ref.find('<Ref>')
                        if p != -1:                            # нашли
                            ref_id_src = line_ref[p+5:]
                            p = ref_id_src.find('</Ref>')
                            ref_id_src = ref_id_src[:p]         # извлекаем
                            break
                    else:
                        ref_id_src = None
                    break
            else:
                comparison_result.append('Исходный объект с указанным идентификатором не найден: не был обнаружен заголовок объекта')
                save_comparison_result_to_file(result_filename)
                return
        if ref_id_src:  
            line_number_dst = -1        # в конечном файле искать уже не надо
            obj_src = get_obj_by_ref(tree_src, xml_object_type, 'Ref', ref_id_src)
            if not ref_id_dst: ref_id_dst = ref_id_src
            obj_dst = get_obj_by_ref(tree_dst, xml_object_type, 'Ref', ref_id_dst)
            if not obj_dst:
                # проверить наличие схемы обмена, если она есть - выяснить альтернативный тэг идентификации
                # использовать get_tag_by_tag для получения obj_dst
                ...

    elif (line_number_dst != -1) and file_dst and os.path.exists(file_dst) and os.path.isfile(file_dst):
        src_xml_types = list_used_xml_object_types(tree_src)
        with open(file_dst, 'r') as f_dst:      # ищем в конечном файле,
            lines = f_dst.readlines()
            for i in range(line_number_dst, 0, -1):     # начиная с указанной строчки и двигаясь вверх, идентификатор искомого объекта
                line = lines[i].strip().strip('<>')
                if line in dst_xml_types:               # нашли заголовок объекта
                    xml_object_type = line
                    for j in range(i+1, line_number_dst):   # ищем идентификатор
                        line_ref = lines[j].strip
                        p = line_ref.find('<Ref>')
                        if p != -1:     # нашли
                            ref_id_dst = line_ref[p+6:]
                            p = ref_id_dst.find('</Ref>')
                            ref_id_dst = ref_id_dst[:p]
                            break
                    else:
                        ref_id_dst = None
                    break
            if ref_id_dst: 
                obj_dst = get_obj_by_ref(tree_dst, xml_object_type, 'Ref', ref_id_dst)
                if not ref_id_src: ref_id_src = ref_id_dst
            else:
                obj_dst = None

    else:
        for obj in root_src:
            ref = get_tag_value(obj, 'Ref')
            if ref == ref_id_src:
                obj_src = obj
                break
        else:
            obj_src = None
    if not obj_src:
        comparison_result.append('Исходный объект с указанным идентификатором не найден')
        save_comparison_result_to_file(result_filename)
        return
    if not obj_dst:
        for obj in root_dst:
            ref = get_tag_value(obj, 'Ref')
            if ref == ref_id_dst:
                obj_dst = obj
                break
        else:
            obj_dst = None
    if not obj_dst:
        comparison_result.append('Конечный объект с указанным идентификатором не найден')
        save_comparison_result_to_file(result_filename)
        return

    for ind_src, attr in enumerate(obj_src):        # начинаем искать различия
        ind_dst = get_index(obj_dst, attr.tag)
        if ind_dst == -1:
            comparison_result.append('В конечном объекте отсутствует атрибут ' + attr.tag)
            if stop_at_first:
                save_comparison_result_to_file(comparison_result, result_filename)
                break
        elif ind_src != ind_dst:
            comparison_result.append('Атрибут ' + attr.tag + ' находится на '+str(ind_src) + ' месте в целевом объекте и на '+str(ind_dst) + ' месте в исходном объекте.')
            if stop_at_first:
                save_comparison_result_to_file(comparison_result, result_filename)
                break
        else:
            attr_dst = root_dst.findall(attr.tag)[0]
            attributes_comparison = compare_objects_attribute_content(attr, attr_dst)
            val_src = get_tag_value(obj_src, attr.tag)
            val_dst = get_tag_value(obj_dst, attr.tag)
            if val_src != val_dst:
                if not val_src:
                    comparison_result.append('Атрибут ' + attr.tag + ' не хранит значение в целевом объекте и имеет значение ' + val_dst + ' в исходном')
                elif not val_dst:
                    comparison_result.append('Атрибут ' + attr.tag + ' не хранит значение в исходном объекте и имеет значение ' + val_src + ' в целевом')
                else:
                    comparison_result.append(
                        'Атрибут ' + attr.tag + ' имеет значение ' + val_src + ' в целевом объекте и значение ' + val_dst + ' в исходном')
                if stop_at_first:
                    save_comparison_result_to_file(comparison_result, result_filename)
                    break
    if len(comparison_result): save_comparison_result_to_file(comparison_result, result_filename)

def obj_type_has_references(xml_obj_header: str, tree: et):
    # найти первый объект типа
    # просмотреть все его атрибуты
    # проверить их значение на соответствие шаблону
    #
    pass

def get_attributes_as_template(obj: el, prefix: str = ''):        # non-recursive! single-level only
    header = prefix + str(obj.tag).strip()
    xml_template = list()

    if get_tag_value(obj, 'IsFolder') == 'true': header = header + '_group'
    xml_template.append(['Header', header])

    i = 0
    for attr in obj:
        xml_template.append(['tag_'+str(i), attr.tag])
        if attr.tag == 'Row': break
        i = i + 1
    xml_template.append([header+'_end', '\n'])
    return xml_template

def get_xml_object_template(obj: el, including_subobjects: bool = True, prefix: str = ''):
    if not len(obj): return []
    xml_template = get_attributes_as_template(obj, prefix)
    if including_subobjects:
        attr_templates = list()
        for attr in obj:
            if len(attr):
                attr_template = get_xml_object_template(attr, True, prefix + obj.tag.strip() + '_')
                # attr_template = get_attributes_as_template(attr)
                attr_templates.extend(attr_template)
                if attr.tag == 'Row': break
        if len(attr_templates):
            xml_template.extend(attr_templates)
    return xml_template

def save_xml_template_to_file(template: list, filename: str):
    with open(filename, 'a', encoding='utf-8-sig') as myfile:
            for (key, val) in template:
                if key == 'attribute_templates':
                    save_xml_template_to_file(val, filename)
                else:
                    myfile.write(str(key) + '=' + str(val) + '\n')

            myfile.write(' \n')

def get_types_to_exclude(list_src: list, list_dst: list):
    return list(set(list_src) - set(list_dst))

def load_1c_xml_exchange_scheme(scheme_file: str, prefixes: list):
    if (not os.path.exists(scheme_file)) or (not os.path.isfile(scheme_file)): return None
    result = dict()
    # l = len(xml_1c_prefix)
    # type_name = get_type_name_from_header(type_header)
    obj_type = ''
    type_scheme = {}
    with open(scheme_file, 'r', encoding='utf-8-sig') as myfile:
        for line in myfile:
            line = line.strip()
            if not line: continue
            if obj_type:
                if line.startswith('end_' + obj_type):
                    obj_type = ''
                    type_scheme = {}
                elif line.find('=') == -1:
                    continue
                else:
                    key, val = (line.split('=', 1))
                    if key and val: type_scheme[key] = val
            else:
                for _, prefix in prefixes:
                    if line.startswith(prefix):
                        obj_type = line
                        result[line] = type_scheme
                        break

        return result

def get_xml_prefixes(tree: et):
    root = tree.getroot()
    if len(root):
        root = root[0]
    else:
        return []

    prefixes = [['Header', 'Object_prefixes']]
    prefixes_set = set()

    i = 0
    for obj in root:
        prefix = obj.tag.strip()
        prefix = prefix[:prefix.find('.')]
        if prefix not in prefixes_set:
            prefixes.append(['prefix' + str(i), prefix])
            i = i + 1
            prefixes_set.add(prefix)
    prefixes.append(['Object_prefixes_end', ''])
    return prefixes

def save_templates(tree, file):
    root = tree.getroot()
    if len(root):
        root = root[0]
    else:
        return

    templates_processed = {}

    for obj in root:
        header = obj.tag.strip()
        new_template = get_xml_object_template(obj)

        if len(new_template):
            header = new_template[0][1]
            # выясняем, не записывали ли этот шаблон раньше,
            # Если записывали, выясняем, какой шаблон имеет больше элементов описания,
            # и сохраняем его в качестве рабочего варианта в файл
        old_template = templates_processed.get(header)

        old_count = len(old_template) if old_template else 0

        if len(new_template) > old_count: templates_processed[header] = new_template

    # with open(file, 'w', encoding='utf-8-sig') as myfile: ...

    for header, template in templates_processed.items():
        save_xml_template_to_file(template, file)

def load_1c_xml_templates_from_file(filename):
    result = {}
    with open(filename, 'r', encoding='utf-8-sig') as myfile:
        header = ''
        template = []
        for line in myfile:
            if line.find('=') == -1: continue
            key, val = line.split('=', 1)
            if (not key) or (not val): continue
            if key.lower() == 'header':
                header = val[:-1]

            elif key.lower().endswith('_end'):
                result[header] = template
                header = ''
                template = []
            else:
                template.append(val[:-1])
    return result

def get_index(obj, att_tag):
    result = -1
    for ind, attr in enumerate(obj):
        if attr.tag == att_tag:
            result = ind
            break
    return result

def make_attribute_copy(obj, copy_what_tag, copy_to_tag, insert_after_tag):
    if hasattr(obj, '__iter__'):
        for ob in obj: make_attribute_copy(ob, copy_what_tag, copy_to_tag, insert_after_tag)
    else:
        ind = get_index(obj, insert_after_tag)
        if ind == -1: return
        for attr in obj.findall(copy_what_tag):
            new_attr = deepcopy(attr)
            new_attr.tag = copy_to_tag
            obj.insert(ind+1, new_attr)
            break

def subtract_lists(a, b):
    fsb = frozenset(b)
    result = [item for item in a if item not in fsb]
    return result

def rename_tags(obj, rename_data):
    if hasattr(obj, '__iter__'):
        for ob in obj: rename_tags(ob, rename_data)
    else:
        if isinstance(rename_data, tuple):
            for rename_tag, rename_to_tag in rename_data:
                for attr in obj.findall(rename_tag):
                    attr.tag = rename_to_tag
        elif isinstance(rename_data, dict):
            for rename_tag, rename_to_tag in rename_data.items():
                for attr in obj.findall(rename_tag):
                    attr.tag = rename_to_tag

def reorder_tags_in_object(xml_object: list, template: dict, extra_parameters: dict = {}):
    if not xml_object or not template: return
    tree_src = extra_parameters.get('tree_src')
    tree_dst = extra_parameters.get('tree_dst')
    dst_type = extra_parameters.get('target_type')
    tags_to_keep = extra_parameters.get('force_keep', [])
    tags_to_rename = extra_parameters.get('tags_to_rename', [])
    copy_instructions = extra_parameters.get('copy', [])

    changes_done = False

    if len(xml_object):
        if tags_to_rename:
            job_is_done = True
            for src_tag, dst_tag in tags_to_rename.items():
                if not has_tag(xml_object, dst_tag):
                    job_is_done = False
                    break
            if not job_is_done:
                rename_tags(xml_object, tags_to_rename)
                changes_done = True

        differs = object_differs_from_template(xml_object, template)

    if differs:
        tags_to_remove = differs.get('tags_to_remove', [])
        tags_to_move = differs.get('tags_to_move', [])
        tags_to_insert = differs.get('tags_to_insert', [])
    else:
        tags_to_remove = []
        tags_to_move = []
        tags_to_insert = []

    if len(tags_to_remove):
        # tags_to_remove = tags_to_remove - tags_to_keep
        tags_to_remove = subtract_lists(tags_to_remove, tags_to_keep)
        remove_tags_in_objects(xml_object, tags_to_remove)
        changes_done = True

    if len(tags_to_move):
        for tags in tags_to_move:
            if len(tags) % 2: continue
            if tags[0] in tags_to_keep:
                if tags[1] in tags_to_keep:
                    continue

            i = get_index(xml_object, tags[0])
            j = get_index(xml_object, tags[1])
            if i == -1 or j == -1: continue
            if i == j+1: continue
            move_tag_in_objects(xml_object, tags[0], tags[1])
            changes_done = True

    if changes_done: return changes_done

    if copy_instructions:
        for instruction in copy_instructions:
            if len(instruction) == 3:
                i = get_index(xml_object, instruction[0])
                j = get_index(xml_object, instruction[1])
                k = get_index(xml_object, instruction[2])
                if (i == -1) or (k == -1): continue
                if j == k + 1: continue
                make_attribute_copy(xml_object, instruction[0], instruction[1], instruction[2])
                changes_done = True
                # tree_src.write('transformed.xml', encoding='utf-8')


    if len(tags_to_insert) and tree_dst:
        if not dst_type: dst_type = xml_object[0].tag
        for tti in tags_to_insert:
            if len(tti) % 2: continue
            if tti[0] in tags_to_keep: continue
            if has_tag(xml_object, tti[0]): continue

            get_value = extra_parameters.get(tti[0]+ '_insert_data', '')
            if get_value == 'GUID':
                val = str(uuid4())
            else:
                for obj_dst in tree_dst.iter(dst_type):
                    val = get_tag_value(obj_dst, tti[0])
                    if val: break
                else: val = ''
            insert_attrib(xml_object, tti[0], val, tti[1])
            changes_done = True
    return changes_done

def reorder_tags_in_rows(row_object: list, row_number: int, parent_ind: int, template: dict, extra_parameters, aux_values):
    tags_to_keep = extra_parameters.get('force_keep', [])
    tags_to_rename = extra_parameters.get('tags_to_rename', [])
    copy_instructions = extra_parameters.get('copy', [])
    tree_dst = extra_parameters.get('tree_dst')
    tree_src = extra_parameters.get('tree_src')
    rows_count = extra_parameters.get('rows_count')
    src_type = extra_parameters.get('src_type')
    target_type = extra_parameters.get('target_type')
    inject_data = extra_parameters.get('attributes_to_inject')

    changes_done = False

    if len(row_object):
        if tags_to_rename:
            job_is_done = True
            for src_tag, dst_tag in tags_to_rename.items():
                if not has_tag(row_object, dst_tag):
                    job_is_done = False
                    break
            if not job_is_done:
                rename_tags(row_object, tags_to_rename)
                changes_done = True
                # extra_parameters['tags_to_rename'] = None

        if inject_data:
            # updated_data = []
            for src_tag, val, dst_tag, insert_after_tag in inject_data:
                i = get_index(row_object, dst_tag)
                j = get_index(row_object, insert_after_tag)
                if j == -1:
                    continue
                    # updated_data.append((src_tag, val, dst_tag, insert_after_tag))
                elif (i == -1) and (j == -1):
                    continue
                    # updated_data.append((src_tag, val, dst_tag, insert_after_tag))
                elif i == (j+1):
                    test_val = get_tag_value(row_object, dst_tag)
                    if test_val != val:
                        for attr in row_object.iter(dst_tag): attr.text = val
                        changes_done = True
                else:
                    insert_attrib(row_object, dst_tag, val, insert_after_tag)
                    changes_done = True

            # extra_parameters['attributes_to_inject'] = updated_data

        differs = object_differs_from_template(row_object, template)
    else:
        return

    if differs:
        tags_to_remove = differs.get('tags_to_remove', [])
        tags_to_move = differs.get('tags_to_move', [])
        tags_to_insert = differs.get('tags_to_insert', [])
    else:
        tags_to_remove = []
        tags_to_move = []
        tags_to_insert = []

    if len(tags_to_remove):
        # tags_to_remove = tags_to_remove - tags_to_keep
        tags_to_remove = subtract_lists(tags_to_remove, tags_to_keep)
        remove_tags_in_objects(row_object, tags_to_remove)
        changes_done = True

    if copy_instructions:
        for instruction in copy_instructions:
            if len(instruction) == 3:
                make_attribute_copy(row_object, instruction[0], instruction[1], instruction[2])
                changes_done = True

    if len(tags_to_move) and (len(row_object) > 1):
        for tags in tags_to_move:
            if len(tags) % 2: continue
            if tags[0] in tags_to_keep:
                if tags[1] in tags_to_keep:
                    continue
                else:
                    ...
            else:
                i = get_index(row_object, tags[0])
                j = get_index(row_object, tags[1])
                if i == -1 or j == -1: continue
                if i == j+1: continue
                move_tag_in_objects(row_object, tags[0], tags[1])
                changes_done = True

    if changes_done: return changes_done

    if len(tags_to_insert) and tree_dst:
        if not target_type: target_type = row_object[0].tag

        root = tree_dst.getroot()
        if len(root): root = root[0]    # to search data absent in src object to be transformed

        row_ids = aux_values.get('row_ids')
        if not row_ids: row_ids = [''] * rows_count

        for tti in tags_to_insert:
            if len(tti) % 2: continue
            if tti[0] in tags_to_keep: continue

            get_value = extra_parameters.get(tti[0] + '_insert_data', '')
            if isinstance(get_value, dict):
                val = get_value.get('val')
                attr = get_value.get('attr')
            elif isinstance(get_value, str):
                attr = ''
                val = ''
                if get_value == 'GUID_set':
                    val = str(uuid4())
                    row_ids[row_number] = val
                elif get_value == 'GUID_get':
                    val = row_ids[row_number]
                elif get_value == 'GUID_empty':
                    val = empty_UID()
                elif get_value == '_':
                    val = ''
                elif get_value.lower().startswith('readas_'):
                    retrieval = get_value.split('_')
                    if len(retrieval) > 1:
                        target_tag = retrieval[1]
                    else:
                        continue

                    if len(retrieval) > 2:
                        target_xml_type = retrieval[2]
                    else:
                        continue

                    if len(retrieval) > 3:
                        search_tag = retrieval[3]
                    else:
                        continue

                    if len(retrieval) > 4:
                        src_obj_attr = retrieval[4]
                        if src_obj_attr:
                            root_src = tree_src.getroot()[0]
                            for ind, par_obj in enumerate(root_src.iter(target_type)):
                                if ind == parent_ind:
                                    parent_object = par_obj
                                    break
                            else:
                                parent_object = None
                            if parent_object:
                                val_we_have = get_tag_value(parent_object, src_obj_attr)
                            else:
                                val_we_have =   ''
                    else:
                        src_obj_attr = None
                        val_we_have = get_tag_value(row_object, search_tag)

                    if val_we_have:
                        val = get_tag_by_tag(root.findall(target_xml_type), search_tag, val_we_have, target_tag)
                        if val and isinstance(val, tuple): val = val[0]
                        if (not val) and tree_src:
                            root_src = tree_src.getroot()[0]
                            val = get_tag_by_tag(root_src.findall(target_xml_type), search_tag, val_we_have, target_tag)
                            if val and isinstance(val, tuple): val = val[0]
                else:
                    for obj_dst in tree_dst.iter(target_type):
                        val = get_tag_value(obj_dst, tti[0])
                        if val: break
                    else: val = ''

            if val == '_': val = ''
            insert_attrib(row_object, tti[0], val, tti[1], attr)
            changes_done = True
        aux_values['row_ids'] = row_ids
    return changes_done

def object_differs_from_template(obj: el, template: list):

    tags_to_remove = []
    tags_to_move = []
    tags_to_insert = []

    if not obj or not template: return None

    for ind, attr in enumerate(obj):
        val = get_tag_value(obj, attr.tag)
        if attr.tag not in template:
            tags_to_remove.append(attr.tag)
        else:
            i = template.index(attr.tag)
            if i != ind:
                tags_to_move.append([attr.tag, template[i-1]])

    for ind, attr in enumerate(template):
        if not has_tag(obj, attr):
            if ind:
                tags_to_insert.append([attr, template[ind-1]])
            else:
                tags_to_insert.append([attr, ''])


    return {'tags_to_remove': tags_to_remove, 'tags_to_move': tags_to_move, 'tags_to_insert': tags_to_insert}

def object_complies_template(obj: el, template: list, exchange_scheme: dict = None):
    differs = object_differs_from_template(obj, template)
    if differs:
        tags_to_remove = differs.get('tags_to_remove')
        tags_to_move = differs.get('tags_to_move')
        tags_to_insert = differs.get('tags_to_insert')
    else:
        tags_to_remove = []
        tags_to_move = []
        tags_to_insert = []

    return not (len(tags_to_remove) and len(tags_to_move) and len(tags_to_insert))

def transform_subobjects(subobjects, parent_ind, part_names: list, template_header: str, transform_instructions: dict, stored_aux_values: dict):
    xml_templates = transform_instructions.get('xml_templates', {})

    if len(part_names) == 1:                    # если в именах подобъектов остался последний элемент - исследуем subojects на изменения прямо щас!!!
        transform_instructions['rows_count'] = len(subobjects)
        template_header = template_header + '_' + part_names[0]
        for ind, row in enumerate(subobjects):
            while True:
                changes_done = reorder_tags_in_rows(row, ind, parent_ind, xml_templates[template_header], transform_instructions, stored_aux_values)
                if not changes_done: break

    elif len(part_names) > 1:
        part_name = part_names[0]
        for subj in subobjects.findall(part_name):
            transform_subobjects(subj, parent_ind, part_names[1:], template_header + '_' + part_name, transform_instructions, stored_aux_values)

def transform_type(parameters: dict):
    src_file = parameters.get('xml_src_file')
    dst_file = parameters.get('xml_dst_file')
    templates_file = parameters.get('templates_file')
    target_type = parameters.get('target_xml_type')
    src_type = parameters.get('src_xml_type')
    result_file = parameters.get('result_file')
    transform_instructions = parameters.get('transform_instructions')

    if src_file and (not os.path.exists(src_file)) or (not os.path.isfile(src_file)): return
    if templates_file and (not os.path.exists(templates_file)) or (not os.path.isfile(templates_file)): return

    tree_src = prepare_xml_tree(src_file)
    root = tree_src.getroot()
    if len(root):
        root = root[0]
    else: return

    xml_templates = load_1c_xml_templates_from_file(templates_file)
    template = xml_templates.get(target_type)
    if not template: return

    if dst_file and os.path.exists(dst_file) and os.path.isfile(dst_file):
        tree_dst = prepare_xml_tree(dst_file)
    else:
        tree_dst = None

    keep_tags = {'force_keep': transform_instructions.get('force_keep')}

    transform_instructions['xml_templates'] = xml_templates
    transform_instructions['target_type'] = target_type
    transform_instructions['src_type'] = src_type
    transform_instructions['tree_dst'] = tree_dst
    transform_instructions['tree_src'] = tree_src

    for xml_object in root.findall(src_type):
        while True:
            # changes_done = reorder_tags_in_objects(list(root.findall(src_type)), template, tree_src=tree_src, tree_dst=tree_dst, extra_parameters=keep_tags, dst_type=target_type)
            changes_done = reorder_tags_in_object(xml_object, template, transform_instructions)
            if not changes_done: break

        xml_object.tag = target_type
    # reorder_tags_in_objects(list(root.findall(src_type)), template, tree_src=tree_src, tree_dst=tree_dst, extra_parameters=transform_instructions, dst_type=target_type)

    i = 0
    stored_aux_values = {}
    while True:
        sub_transform_instructions = transform_instructions.get('transform_sub' + str(i))

        if not sub_transform_instructions: break
        sub_transform_instructions['xml_templates'] = xml_templates
        sub_transform_instructions['target_type'] = target_type
        sub_transform_instructions['src_type'] = src_type
        sub_transform_instructions['tree_dst'] = tree_dst
        sub_transform_instructions['tree_src'] = tree_src
        attributes_to_inject = sub_transform_instructions.get('attributes_to_inject')

        for ind, obj in enumerate(root.iter(target_type)):
            if sub_transform_instructions.get('attributes_to_inject'):
                attributes_to_inject = transform_instructions.get('attributes_to_inject')

                if attributes_to_inject:  # retrieving data for attributes to inject and repacking sub_transform_instructions
                    updated_data = []
                    for src_tag, val, dst_tag, insert_after_tag in attributes_to_inject:
                        val = get_tag_value(obj, src_tag)
                        updated_data.append((src_tag, val, dst_tag, insert_after_tag))
                    sub_transform_instructions['attributes_to_inject'] = updated_data

            transform_subobjects(obj, ind, sub_transform_instructions.get('headers', '').split('_'), target_type, sub_transform_instructions, stored_aux_values)

        i = i + 1

    return tree_src
