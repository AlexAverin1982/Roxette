"""
Runtime
One-s
XML
Exchange and
Transform
Tool
Engine

    Designed specificly to meet the needs of exchanging XML-formatted data between
1C products (usually, databases with a random structure)

    The current class is based on the formerly designed procedure-level tools in 1c_catalogs project.
Both projects use the ElementTree python facilities to extend the XML-handling python functionality.

    Roxette implies data, processing algorithms and instructions, adjusting and configuring those algorithms
and scrips should and could be kept just in plain text files.

Basic concept:

    ad means actual data containing references (links, pointers, ids, etc), "wrong", non-compatible with the target base,
where we want to transfer that data to. ad data is issued from the source database, containg useful and actual data we need
to be in target database, but with "wrong" markers that make it impossible just to load this data in a straighforward way.

    This data should be converted in a way of replacing the wrong references with the correct ones, stored in the target database.
Here comes the notion of ci data - outdated, but containg correct identifiers, compatible (originating from)
with the target (destination) database.

    The Mechanism of matching comes like this:
we can match records from ad and ci dbs by finding the field in the record, that has the same unique value in ad and ci,
that doesn't serve as an identifer of the record, but nevertheless can identify it, e.g. full name of a person
or description of an entity. Thus, we take a source record, search the record with the same unique value of a field,
known as an alternative identifer, in the destination db, and, being successful in finding the relevant record in ci db,
retrieve the correct value of the real identifier (e.g., Ref in 1C databases) and replace it in the source record.
We repeat this procedure with all the reference-looking fields, until we have the record, fully compatible with the
destination db and ready to be loaded there.

    The instructions of where to look for those alternative identifers and what fields are necessary to be replaced in the way
just described, reside in the plain-text files in some deliberately regular, brief and comprehencible format (not XML-like).
So, parts of such instructions could be written directly amici the script, implementing the algorithm,
or loaded from some file, written aside the current task.
"""

import os
import xml.etree.ElementTree as et
import xml
from xml.etree.ElementTree import Element as el
from copy import deepcopy
from uuid import uuid4
import re
from binarytree import Node as bt_node
import pickle
from text_cursor import set_cursor_pos

def is_guid(val: str) -> bool:
    return re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', val, re.IGNORECASE)

def xor(a: bool, b: bool) -> bool:
    return (a and not b) or (not a and b)

def empty_1C_XML():
    return '<V8Exch:_1CV8DtUD xmlns:V8Exch="http://www.1c.ru/V8/1CV8DtUD/" xmlns:v8="http://v8.1c.ru/data" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n' + \
           '\t<V8Exch:Data>\n' + '\t</V8Exch:Data>\n' + '</V8Exch:_1CV8DtUD>'

def is_empty(val, including_empty_UID: bool = True):
    return ((val == '00000000-0000-0000-0000-000000000000') and including_empty_UID) or (not val)

def lists_diff(list1: list, list2: list):
    return list(set(list1) - set(list2))

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

def load_1c_xml_exchange_scheme(scheme_file: str, prefixes: list):
    result = dict()
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

def get_tag_value(obj, tag: str):
    result = None
    if isinstance(tag, str):
        p = tag.find(' ')
    else:
        return ''
    if p != -1:
        tag = tag[:p]
        # descr = list(obj.iter('Description'))[0].text
        # tagid = list(obj.iter('Ref'))[0].text
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
        # descr = list(obj.iter('Description'))[0].text
        # tagid = list(obj.iter('Ref'))[0].text
        for attr in obj.iter(tag):
            if isinstance(attr.text, str):
                result = attr.text
            elif isinstance(attr.text, tuple):
                result = str(attr.text[0])
            else:
                result = ''
            break
    return result

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

    return result, obj

def get_obj_by_ref(tree: et, xml_object_header: str, ref_tag: str, ref_tag_val: str) -> el:
    result = None
    root = tree.getroot()
    if len(root):
        root = root[0]
    else:
        return
    if xml_object_header:
        for obj in root.findall(xml_object_header):
            for ref_attr in obj.findall(ref_tag):
                if ref_attr.text == ref_tag_val:
                        result = obj
                        break
            if result: break
    else:
        for obj in root.iter():
            for ref_attr in obj.findall(ref_tag):
                if ref_attr.text == ref_tag_val:
                        result = obj
                        break
            if result: break
    return result

def prepare_xml_tree(xml_source: str):
    parsr = et.XMLParser(encoding="utf-8")
    et.register_namespace('V8Exch', 'http://www.1c.ru/V8/1CV8DtUD/')
    et.register_namespace('v8', 'http://v8.1c.ru/data')
    et.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

    if xml_source:
        if is_valid_filename(xml_source):
            return et.parse(xml_source, parser=parsr)
        elif isinstance(xml_source, str):
            root = et.fromstring(xml_source)
            return et.ElementTree(root)

def prepare_empty_1C_xml_tree(source_tree = None):
    parsr = et.XMLParser(encoding="utf-8")
    et.register_namespace('V8Exch', 'http://www.1c.ru/V8/1CV8DtUD/')
    et.register_namespace('v8', 'http://v8.1c.ru/data')
    et.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

    if source_tree and isinstance(source_tree, et):
        tree = deepcopy(source_tree)
        res_root = tree.getroot()
        if len(res_root):
            res_root = res_root[0]
            while len(res_root): res_root.remove(res_root[0])
    else:
        root = et.fromstring(empty_1C_XML(), parser=parsr)
        tree = et.ElementTree(root)
        # root.attrib['xmlns:V8Exch'] = "http://www.1c.ru/V8/1CV8DtUD/"
        # root.attrib['xmlns:v8'] = "http://v8.1c.ru/data"
        # root.attrib['xmlns:xsi'] = "http://www.w3.org/2001/XMLSchema-instance"
        tree.write('empty_1c.xml', encoding='utf-8-sig')
    return tree

def is_valid_filename(s: str) -> bool:
    return s and isinstance(s, str) and os.path.exists(s) and os.path.isfile(s)

def has_tag(obj, tag):
    return len(list(obj.iter(tag))) != 0

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

def delete_tags(obj, tags_to_delete):
    if hasattr(obj, '__iter__'):            # iterable
        for ob in obj: delete_tags(ob, tags_to_delete)
    else:
        if isinstance(tags_to_delete, dict):
            for key, val in tags_to_delete.items():
                for attr in obj.iter(key):
                    delete_tags(attr, val)
        elif isinstance(tags_to_delete, str):
            if tags_to_delete == '*':
                for attr in obj:
                    while len(attr):
                        del attr[-1]
                    obj.remove(attr)
                    # if attr.tag == obj.tag: continue
                    # if len(list(attr.iter())):
                    #     delete_tags(attr, '*')
                    # obj.remove(attr)
            else:
                for attr in obj.iter(tags_to_delete):
                    obj.remove(attr)
        elif hasattr(tags_to_delete, '__iter__'):
            for tag in tags_to_delete:
                i = len(obj)-1
                while i:
                    if obj[i].tag == tag:
                        del obj[i]
                    i -= 1
                    # obj.remove(attr)
            for tag in tags_to_delete:
                if isinstance(tag, dict):
                    for key, val in tag.items():
                        for attr in obj.iter(key):
                            delete_tags(attr, val)

def get_index(obj, att_tag):
    result = -1
    for ind, attr in enumerate(obj):
        if attr.tag == att_tag:
            result = ind
            break
    return result

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

def move_tag_in_objects(object, tag_to_move: str, tag_insert_after: str):
    if hasattr(object, '__iter__'):
        for obj in object: move_tag_in_objects(obj, tag_to_move, tag_insert_after)
    else:
        for attrib in object.findall(tag_to_move):
                delete_tags(object, [tag_to_move])
                insert_attrib(object, tag_to_move, attrib.text, tag_insert_after)

def set_tag_value(obj, tag, new_val):
    if hasattr(obj, '__iter__'):
        for ob in obj: set_tag_value(ob, tag, new_val)
    else:
        for tag_obj in obj.iter(tag):
            tag_obj.text = new_val

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


def list_referred_types(type_data, data_tree: et, group_tags: list, search_cache, loop_resolution_data) -> list:
    """
    анализируем дерево xml-данных и выясняем, какие типы ссылаются на какие, создаем список данных вида (тип, типы, накотоные он ссылается)
    и сортируем нужным образом - по количеству внешних ссылок.

    :param type_data: список строк, либо строка, содержащая xml-тип
    :param data_tree: xml-дерево, откуда будут извлекаться данные о том, какие типы ссылаются на какие
    :param group_tags: список тэгов, хранящих признак того, что объект является группой и, соотвтетственно,
    может содержать меньше тэгов, чем нужно, и потому игнорируется при анализе
    :param search_cache: словарь данных, помогающий быстро определить, на какой тип ссылается тот или иной guid
    :return: список двумерных кортежей:
        первый элемент - имя xmL типа;
        второй элемент - список типов, на которые ссылается объект типа, указанного в первом элементе.
        Список упорядочен по длине второго элемента: сначала идут типы, не имеющие внешних ссылок,
        затем типы, ссылающиеся только на те типы, которые идут перед ними, и т.д.
    """
    def place_val_in_tree(root: bt_node, node: bt_node, index: int, depth: int) -> bt_node:
        """
        формируем бинарное дерево для сортировки результирующего списка кортежей
        :param depth: глубина вложенности рекурсивных вызовов, нужна для оптимизации
        :param root: корень дерева
        :param node: текущий узел дерева, просматриваемый на предмет, можно ли в него поместить новые данные
        :param index: индекс элемента из списка сортируемых кортежей
        type_name: имя типа, данные о котором нужно разместить

        :param types_pool: множество всех типов, использвемых в исходных данных
        :param fixed_types: множество типов, данные о которых уже размещены в дереве
        :return: корень обновленного дерева
        """
        type_name: str = unsorted[index][0]
        referred_types: list = unsorted[index][1]
        referred_types_set: set = set(referred_types)

        if type_name in fixed_types:
            return root

        type_is_from_loop = type_name in types_in_loop
        if not depth:
            all_types_fixed = True

            types_to_ignore = []
            # type_is_from_loop = (type_name in loop_primary_types)
            if type_is_from_loop:
                loop_resolve_dict = loop_resolution_data.get(type_name)
                if loop_resolve_dict:
                    types_to_ignore = loop_resolve_dict.get('types_to_ignore')
                    if types_to_ignore:
                        for type1 in types_to_ignore:
                            fixed_types.add(type1)

            for referred_type in referred_types_set:
                all_types_fixed &= (referred_type in fixed_types)
                if not all_types_fixed: break

            for type1 in types_to_ignore:
                fixed_types.remove(type1)

            if not all_types_fixed:
                return root

        if node:
            if type_is_from_loop:
                type_weight = len(list(fixed_types)) + 1
            else:
                type_weight = len(referred_types)

            weights[ind] = type_weight

            if type_weight <= weights[node.val]:
                if node.left:
                    place_val_in_tree(root, node.left, index, depth+1)
                else:
                    node.left = bt_node(index)
                    fixed_types.add(type_name)
                    types_pool.remove(type_name)
            else:
                if node.right:
                    place_val_in_tree(root, node.right, index, depth+1)
                else:
                    node.right = bt_node(index)
                    fixed_types.add(type_name)
                    types_pool.remove(type_name)
        else:
            node = bt_node(index)
            fixed_types.add(type_name)
            types_pool.remove(type_name)
            if not root: root = node
        return root

    def get_sorted_list(node: bt_node, unsorted: list, sorted: list):
        if not node: exit
        if node.left:
            get_sorted_list(node.left, unsorted, sorted)

        sorted.append(unsorted[node.val])

        if node.right:
            get_sorted_list(node.right, unsorted, sorted)



    if isinstance(type_data, list):
        result = []
        unsorted = []
        bt_root = None
        for type_item in type_data:
            """ формируем список кортежей (тип, список типов в ссылках) для всех типов в дереве"""
            unsorted.append(list_referred_types(type_item, data_tree, group_tags, search_cache, loop_resolution_data))


        weights = [None] * len(unsorted)   # weights: длины списков типов внешних ссылок
        types_pool = set(type_data)         # все типы, которые надо рассмотреть
        fixed_types = set([])               # типы, место которых в отсортированном списке найдено

        loop_primary_types = []
        for xml_type in loop_resolution_data.keys():
            loop_primary_types.append(xml_type)

        types_in_loop = []
        while types_pool:
            old_pool_len = len(types_pool)  # будем проверять, изменилось ли число обработанных типов

            for ind, (header, ref_types_list) in enumerate(unsorted):
                """помещаем данные о кортежах в неотсортированном списке в бинарное дерево"""
                weights[ind] = len(ref_types_list)
                bt_root = place_val_in_tree(bt_root, bt_root, ind, 0)

            cyclic_refs_detected = old_pool_len == len(types_pool)  # ничего не поменялось, нашли зацикленные ссылки
            if cyclic_refs_detected:
                types_in_loop = list(types_pool)

        get_sorted_list(bt_root, unsorted, result)
        return result
    else:               # type_data - имя xml типа, заголовок
        root = data_tree.getroot()
        if len(root):
            root = root[0]
        ref_types_list = []
        # if self.verbous_ouput:
        n = len(list(root.findall(type_data)))
        count = 0
        print('Analysing type ', type_data)
        guid_empty_tags = set()
        detected_tags = set()
        objects_found = 0
        # ищем тэги, содержащие непустые guid-ссылки, определяем тип объектов, на которые они ссылаются
        for obj in root.findall(type_data):
            print('Analysing %s %s, %d of %d ' % (type_data, obj[0].text, count, n))
            count += 1

            for ind, attr in enumerate(obj.iter()):
                if ind == 0:
                    continue
                if ind == 1:
                    search_cache[attr.text.lower()] = type_data
                    continue
                if (attr.tag in group_tags) and (attr.text.lower() == 'true'):
                    break    # groups usually have less tags than objects
                else:
                    objects_found += 1
                if attr.tag in detected_tags: continue
                if attr.text and is_guid(attr.text):
                    if is_empty(attr.text, True) and (attr.tag not in detected_tags):
                        guid_empty_tags.add(attr.tag)
                    else:
                        if attr.tag in guid_empty_tags: guid_empty_tags.remove(attr.tag)
                        ref_obj_type = search_cache.get(attr.text)
                    if not ref_obj_type:
                        ref_obj = get_obj_by_ref(data_tree, None, 'Ref', attr.text)
                        if ref_obj:
                            search_cache[attr.text] = ref_obj.tag
                            ref_obj_type = ref_obj.tag
                    if ref_obj_type:
                        detected_tags.add(attr.tag)
                        if ref_obj_type != obj.tag: ref_types_list.append(ref_obj_type)
            if (len(guid_empty_tags) == 0) and (objects_found != 0): break   # all outer links in this type have been detected

        ref_types_list = list(set(ref_types_list))
        return type_data, ref_types_list 



class Roxette:
    empty_UID: str = '00000000-0000-0000-0000-000000000000'

    def __init__(self, args=None):
        self.id_mappings = None
        self.tree_ad = None
        self.tree_ci = None
        self.xml_templates = None
        self.xml_exchange_scheme = None
        self.root_ad = None
        self.root_ci = None
        self.result_tree = None

        if not args:
            return

        self.verbous_ouput = args.verbous_output
        self.types_list_ad = []
        if args.xml_ad and is_valid_filename(args.xml_ad):
            self.tree_ad = prepare_xml_tree(args.xml_ad)
            if self.tree_ad:
                self.root_ad = self.tree_ad.getroot()
                if len(self.root_ad):
                    self.root_ad = self.root_ad[0]
                else:
                    self.tree_ad = None
                    self.root_ad = None
                    return

        self.types_list_ad = list_used_xml_object_types(self.tree_ad)

        types_list_ci = []
        if args.xml_ci and is_valid_filename(args.xml_ci):
            self.tree_ci = prepare_xml_tree(args.xml_ci)
            if self.tree_ci:
                types_list_ci = list_used_xml_object_types(self.tree_ci)
                self.root_ci = self.tree_ci.getroot()
                if len(self.root_ci):
                    self.root_ci = self.root_ci[0]
                else:
                    self.tree_ci = None
                    self.root_ci = None
                    return

        self.types_list_ci = types_list_ci
        types_to_ignore = lists_diff(self.types_list_ad, self.types_list_ci)
        for type_to_ignore in types_to_ignore:
            c = len(self.root_ad)
            while True:
                for obj in self.root_ad.iter(type_to_ignore):
                    self.root_ad.remove(obj)
                if c == len(self.root_ad):
                    break
                else:
                    c = len(self.root_ad)

        if args.templates and is_valid_filename(args.templates):
            self.xml_templates = load_1c_xml_templates_from_file(args.templates)

        if args.exchange_scheme and is_valid_filename(args.exchange_scheme) and self.tree_ci:
            self.xml_exchange_scheme = load_1c_xml_exchange_scheme(args.exchange_scheme, get_xml_prefixes(self.tree_ci)[1:])

        if is_valid_filename(args.id_mappings_filename):
            cache_file = open(args.id_mappings_filename, 'rb')
            self.id_mappings = pickle.load(cache_file)
        else:

            if self.root_ad and self.xml_exchange_scheme:
                self.prepare_id_mappings(args.xml_ad)

            if self.root_ci and self.id_mappings:
                self.complete_id_mappings()
                if args.id_mappings_filename and isinstance(args.id_mappings_filename, str):
                    cache_file = open(args.id_mappings_filename, 'wb')
                    pickle.dump(self.id_mappings, cache_file)

    def prepare_id_mappings(self, xml_ad_filename: str):
        def is_obj_header(s: str) -> bool:
            result = False
            for obj_type in self.types_list_ci:
                if '<' + obj_type + '>' == s.strip():
                    result = True
                    break
            return result
        
        def extract_tag_value(s: str, tag: str) -> str:
            s = s.strip()
            result = ''
            p1 = s.find('<' + tag + '>')
            if p1 != -1:
                p2 = s.find('</' + tag + '>')
                if p2 == -1:
                    p2 = len(s)
                result = s[p1 + len(tag) + 2: p2]
            return result

        """we read xml data from file line by line and form a dictionary containig key data about xml objects we find"""
        self.id_mappings = {}
        with open(xml_ad_filename, 'r', encoding='utf-8-sig') as myfile:
            lines = myfile.readlines()
            id_val = ''
            header = ''
            description_tag = ''
            obj_data = {}
            for line in lines:
                if description_tag:
                    description_tag_value = extract_tag_value(line, description_tag)
                    if description_tag_value:
                        obj_data[description_tag] = description_tag_value
                        id_val = ''
                        header = ''
                        description_tag = ''
                        obj_data = {}           # we got all the info about xml object we wanted
                elif header:
                    id_val = extract_tag_value(line, 'Ref')     # we've found another object header
                    if id_val:                                  # now retrieving its key info
                        self.id_mappings[id_val] = obj_data
                        e_scheme = self.xml_exchange_scheme.get(header)
                        if e_scheme:
                            description_tag = e_scheme.get('id_description_tag')
                            obj_data['description_tag'] = description_tag
                        else:
                            id_val = ''
                            header = ''
                            description_tag = ''
                            obj_data = {}
                elif not id_val:
                    if is_obj_header(line):     # we've found another object header
                        obj_data = {'type': line.strip()[1:-1]}
                        header = obj_data.get('type')

    def complete_id_mappings(self):
        for ad_id, mapping_data in self.id_mappings.items():
            xml_type = mapping_data.get('type')

            descr_tag = mapping_data.get('description_tag')
            if descr_tag:
                descr_tag_val = mapping_data.get(descr_tag)
                if descr_tag_val:
                    target_id = get_tag_by_tag(self.root_ci.iter(xml_type), descr_tag, descr_tag_val, 'Ref')
                    if target_id:
                        mapping_data['correct_id'] = target_id[0]

    def invalidate_data(self):
        self.tree_ad = None
        self.tree_ci = None
        self.root_ad = None
        self.root_ci = None

    def split_into_groups_and_objects(self, type_header: str, scheme: dict):
        objects = []
        groups = []
        result = [objects, groups]
        filter_tag = scheme.get('filter_key0')

        for obj in self.tree_ad.iter(type_header):
            if filter_tag:
                if get_tag_value(obj, filter_tag) == 'true':
                    groups.append(obj)
                else:
                    objects.append(obj)
            else:
                objects.append(obj)
        return result

    def reorder_tags_in_objects(self, xml_object: list, template: dict, extra_parameters=None) -> bool:
        if extra_parameters is None:
            extra_parameters = {}
        if not xml_object or not template: return False
        dst_type = extra_parameters.get('target_type')
        tags_to_keep = extra_parameters.get('force_keep', [])
        tags_to_rename = extra_parameters.get('tags_to_rename', [])
        copy_instructions = extra_parameters.get('copy', [])

        changes_done = False

        if len(xml_object):
            if tags_to_rename and isinstance(tags_to_rename, dict):
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
            tags_to_remove = lists_diff(tags_to_remove, tags_to_keep)
            delete_tags(xml_object, tags_to_remove)
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
                if i == j + 1: continue
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

        if len(tags_to_insert) and self.tree_ci:
            if not dst_type: dst_type = xml_object[0].tag
            for tti in tags_to_insert:
                if len(tti) % 2: continue
                if tti[0] in tags_to_keep: continue
                if has_tag(xml_object, tti[0]): continue

                get_value = extra_parameters.get(tti[0] + '_insert_data', '')
                if get_value == 'GUID':
                    val = str(uuid4())
                else:
                    for obj_dst in self.tree_ci.iter(dst_type):
                        val = get_tag_value(obj_dst, tti[0])
                        if val: break
                    else:
                        val = ''
                insert_attrib(xml_object, tti[0], val, tti[1])
                changes_done = True
        return changes_done

    def replace_links(self, src_list: list, src_refs: list, dst_refs: list, ref_tag, descr_tag: str, target_tag: str,
                      filter: dict = None, mapping: dict = None):
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
        descr_mappings_cache = dict()  # ...наименования по идентификатору   Ref -> Name(or Description)

        if mapping:
            # if isinstance(mapping, str) and os.path.isfile(mapping) and os.path.exists(mapping):
            #     with open('mapping_cache.dat', 'rb') as myfile:
            #         correct_id_mappings_cache = pickle.load(myfile)
            # elif isinstance(mapping, dict):
            correct_id_mappings_cache = mapping
        else:
            correct_id_mappings_cache = dict()  # ...актуального идентификатора по исходному Ref_src -> Ref_dst

        if hasattr(src_list, '__iter__'):
            for src_obj in src_list:  # просматриваем редактируемые объекты

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
                                self.replace_links(attrib, src_refs, dst_refs, val, descr_tag, target_tag, filter)
                elif isinstance(ref_tag, str):
                    ref_val = get_tag_value(src_obj, ref_tag)  # находим в исходнике меняемое поле
                    if is_empty(ref_val): continue
                    search_descr_val = descr_mappings_cache.get(ref_val)
                    if not search_descr_val:  # находим значение поля (наименование, имя), по которому будем искать объект с правильным значением идентификатора
                        search_descr_val = get_tag_by_tag(src_refs, target_tag, ref_val, descr_tag)[0]
                        if search_descr_val:
                            descr_mappings_cache[ref_val] = search_descr_val

                    target_tag_val = correct_id_mappings_cache.get(
                        ref_val)  # ищем правильное значение идентификатора сначала в кэше
                    if not target_tag_val:
                        # if (not search_descr_val) or (not descr_tag):
                        #   target_tag_val = empty_UID()
                        # continue
                        target_tag_val = get_tag_by_tag(dst_refs, descr_tag, search_descr_val,
                                                        target_tag)  # потом в объектах с правильными значениями
                        if target_tag_val and (len(target_tag_val) > 1) and target_tag_val[0] and target_tag_val[1]:
                            target_tag_val = target_tag_val[0]
                        elif descr_tag and search_descr_val and (descr_tag.lower() == 'number') and (
                                search_descr_val[:2] != '00'):
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
                            set_tag_value(src_obj, ref_tag,
                                          target_tag_val)  # устанавливаем правильное значение идентификатора
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
                                self.replace_links(attrib, src_refs, dst_refs, val, descr_tag, target_tag, filter)
                        elif isinstance(val, list):
                            for attrib in src_list.iter(key):
                                for tag in val:
                                    self.replace_links(attrib, src_refs, dst_refs, tag, descr_tag, target_tag, filter)
                elif isinstance(ref_tag, str):
                    ref_val = get_tag_value(src_list,
                                            ref_tag)  # находим в банке ссылку на страну ( в исходнике - меняемое поле)
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


    def replace_links_in_objects_of_type(self, object_type_header: str,
                                         objects_to_edit: list,
                                         tag_to_edit: str,
                                         tag_to_identify: str,
                                         correct_value_tag: str,
                                         filter: dict = None,
                                         reference_obj_type_header: str = None):
        obj_list_src = objects_to_edit

        if self.id_mappings:
            all_replaced = (replace_tag_values(obj_list_src, tag_to_edit, self.id_mappings) == 0)
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
        if not all_replaced:

            if reference_obj_type_header:
                reference_obj_list = list(self.root_ad.iter(object_type_header))
            else:
                reference_obj_list = objects_to_edit  # doublecheck this!
            if not reference_obj_list:
                reference_obj_list = list(self.root_ad.iter(reference_obj_type_header))

            obj_list_dst = list(self.root_ci.iter(object_type_header))
            if not obj_list_dst:
                obj_list_dst = list(self.root_ci.iter(reference_obj_type_header))

            self.replace_links(objects_to_edit, reference_obj_list, obj_list_dst, tag_to_edit, tag_to_identify, correct_value_tag, filter=filter, mapping=self.id_mappings)

    def process_tags_by_scheme_in_objects(self, obj_list, template, parameters):

        type_header = parameters.get('type_header')
        if not type_header: return

        if not self.xml_exchange_scheme: return
        exchange_scheme = self.xml_exchange_scheme.get(type_header)
        if not exchange_scheme: return

        if not self.id_mappings:
            self.id_mappings = {}
        if not self.tree_ad: return
        if not self.tree_ci: return
        if not self.root_ad:
            self.root_ad = self.tree_ad.getroot()
            if len(self.root_ad):
                self.root_ad = self.root_ad[0]
            else:
                return
        i = 0
        description_tag = exchange_scheme.get('id_description_tag')

        objects_to_edit = parameters.get('objects_to_edit')

        while True:
            ref_tag = exchange_scheme.get('ref_tag' + str(i))
            ref_tag_type = exchange_scheme.get('ref_tag_type' + str(i))
            if ref_tag and ref_tag_type:
                subobject_type_header = parameters.get('subobject_type_header')
                if subobject_type_header:
                    ref_tag_header = subobject_type_header
                else:
                    ref_tag_header = ref_tag_type

                if not objects_to_edit:
                    objects_to_edit = list(self.root_ad[0].iter(ref_tag_header))

                if self.verbous_ouput:
                    set_cursor_pos(1, 11)
                    print('Replacing links...')


                mappings = self.replace_links_in_objects_of_type(type_header, objects_to_edit, ref_tag, description_tag, 'Ref', reference_obj_type_header=ref_tag_header)
                i = i + 1
            else:
                break

        if self.verbous_ouput:
            set_cursor_pos(1, 11)
            print('Applying exchange scheme ... in ',type_header, type(obj_list))


        i = 0
        while True:
            tag = exchange_scheme.get('empty_val_tag' + str(i))
            if tag:
                set_tag_value(obj_list, tag, '')
                i = i + 1
            else:
                break

        i = 0
        while True:
            tag = exchange_scheme.get('remove_tag' + str(i))
            if tag:
                for obj in obj_list:
                    for attr in obj.findall(tag): obj.remove(attr)
                i = i + 1
            else:
                break

        i = 0
        while True:
            remove_where = exchange_scheme.get('remove_in_subitem' + str(i))
            if remove_where:
                remove_what = exchange_scheme.get('remove_subitem' + str(i))
                if remove_what:
                    for obj in self.root_ad.findall('./' + type_header + remove_where):
                        for attr in obj.findall(remove_what):
                            obj.remove(attr)
                i = i + 1
            else:
                break

        i = 0
        while True:
            tag = exchange_scheme.get('insert_tag' + str(i))
            if tag:
                insert_after = exchange_scheme.get('insert_after' + str(i))
                insert_val = exchange_scheme.get('insert_val' + str(i))

                if insert_after and insert_val:
                    insert_attrib(obj_list, tag, insert_val, insert_after)
                i = i + 1
            else:
                break

        i = 0
        while True:
            tag = exchange_scheme.get('enforce_value_tag' + str(i))
            if tag:
                insert_val = exchange_scheme.get('enforce_value' + str(i))

                if insert_val:
                    set_tag_value(obj_list, tag, insert_val)
                i = i + 1
            else:
                break

        i = 0
        while True:
            tag = exchange_scheme.get('crop_value_tag' + str(i))
            if tag:
                crop_value_to = exchange_scheme.get('crop_value_to' + str(i))
                if crop_value_to == 'guid':
                    for obj in obj_list:
                        for attr in obj.findall(tag):
                            regexp = re.compile(r"(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})")
                            result = regexp.search(str(attr.text))
                            if result:
                                attr.text = result.group('guid')
                            else:
                                attr.text = self.empty_UID

                i = i + 1
            else:
                break


        i = 0
        while True:
            tag = exchange_scheme.get('ref_subobject' + str(i))

            if tag:
                subobject_type = exchange_scheme.get('ref_subobject_type' + str(i))
                for obj in obj_list:
                    sub_obj_list = list(obj.iter(tag))
                    if sub_obj_list:
                        extra_parameters: dict = {'objects_to_edit': sub_obj_list,
                                                  'type_header': type_header + '_' + tag,
                                                  'subobject_type_header': subobject_type}
                        self.process_tags_by_scheme_in_objects(sub_obj_list, template, extra_parameters)
                i = i + 1
            else:
                break

        i = 0
        while True:
            tag = exchange_scheme.get('first_phase_tag' + str(i))

            if tag:
                # subobject_type = exchange_scheme.get('ref_subobject_type' + str(i))
                for obj in obj_list:
                    for attr in obj.iter():
                        if attr.tag != tag: continue
                        action = exchange_scheme.get('first_phase_action' + str(i))
                        if  action == 'set_empty_guid':
                            attr.text = self.empty_UID
                        elif action == 'set_empty':
                            while len(attr):
                                delete_tags(attr, '*')
                            attr.text=''
                i = i + 1
            else:
                break


    def replace_links_in_objects_of_type(self, object_type_header: str,
                                         objects_to_edit: list,
                                         tag_to_edit: str,
                                         tag_to_identify: str,
                                         correct_value_tag: str,
                                         filter: dict = None,
                                         reference_obj_type_header: str = None):

        if not len(self.root_ad): return
        # список объектов одного типа, из которых будем брать правильные значения идентификаторов
        if reference_obj_type_header:
            reference_obj_list = list(self.root_ad.iter(object_type_header))
        else:
            reference_obj_list = objects_to_edit  # doublecheck this!
        if not reference_obj_list:
            reference_obj_list = list(self.root_ad.iter(reference_obj_type_header))

        #     objects_to_edit = list(self.tree_ad.iter(object_type_header))
        #     if not objects_to_edit:
        #         objects_to_edit = list(self.tree_ad.iter(reference_obj_type_header))
        # elif isinstance(self.tree_ad, list):
        #     objects_to_edit = self.tree_ad
        # else:
        #     return

        if not self.root_ci: return
        obj_list_ci = list(self.root_ci.iter(object_type_header))
        if not obj_list_ci:
            obj_list_ci = list(self.root_ci.iter(reference_obj_type_header))
        else:
            return

        if self.id_mappings:
            all_replaced = (replace_tag_values(objects_to_edit, tag_to_edit, mapping=self.id_mappings) == 0)
        else:
            all_replaced = False
            """
                objects_to_edit - список объектов одного типа, в которых мы будем менять ссылки
                reference_obj_list
                obj_list_ci - список объектов того же типа, откуда будем брать корректные значения
                tag_to_edit - имя тэга, значание которого будем менять
                tag_to_identify - имя тэга, по которому будем искать тот же объект с правильным значением изменяемого тэга 
                correct_value_tag - имя тэга, содержащего правильное значение изменяемого тэга
                filter - 
            """
        if not all_replaced:
            self.replace_links(objects_to_edit, reference_obj_list, obj_list_ci, tag_to_edit, tag_to_identify, correct_value_tag, filter=filter, mapping=self.id_mappings)

    def salvage_nonempty_old_values(self, parameters: dict):
        """сохраняем значения, которые в устаревших объектах непустые, а в актуальных - пустые"""
        key_tags = parameters.get('key_tags', [])            # список тэгов, которые не надо анализировать
        obj_ref_mapping = parameters.get('mappings', {})     # кэш (база знаний) сопоставления идентификаторов
        exchange_scheme = parameters.get('exchange_scheme', {})
        referred_types_data = parameters.get('referred_types_data')

        object_types_list = list_used_xml_object_types(self.tree_ad) # список типов xml объектов с актуальными данными и неправильными ид

        # for xml_type in object_types_list:
        for xml_type, referred_types_list in referred_types_data:
            if self.verbous_ouput:
                print('Processing ', xml_type)
            ref_mapping = obj_ref_mapping.get(xml_type)
            count = len(self.root_ad.findall(xml_type))
            for ind, obj_src in enumerate(self.root_ad.findall(xml_type)):  # перебираем все объекты с актуальными данными и неправильными ид
                if self.verbous_ouput:
                    print('Processing %s %s %d / %d' % (xml_type, obj_src[0].text, ind+1, count))
                ref_id = None
                dst_ref_id = None
                dst_obj = None
                for attr in obj_src:            # просматриваем аттрибуты очередного объекта
                    if not ref_id:                  # ищем идентификатор
                        ref_id = get_tag_value(obj_src, 'Ref')
                    if attr.tag in key_tags: continue
                    old_val = None

                    if not dst_ref_id:          # пытаемся найти правильный идентификатор
                        if ref_mapping:             # ... в кэше
                            dst_ref_id = ref_mapping.get(ref_id)

                        if not dst_ref_id:     # не нашли в кэше - раньше этот объект нигде не встречали, попытаемся найти в дереве с правильными идентификаторами по описанию
                            # предположим, что актуальный и исходный правильный идентификаторы совпадают
                            dst_obj = get_obj_by_ref(self.tree_ci, xml_type, 'Ref', ref_id)
                            if dst_obj: dst_ref_id = ref_id
                        # неа, не совпадают, ищем по описанию
                        if not dst_ref_id:
                            # определяем название тэга описания для текущего типа, например Description или Code
                            id_tag = exchange_scheme.get('id_description_tag')
                            # descr = get_tag_value(obj_src, 'Description')
                            if id_tag:         # находим описание объекта
                                id_tag_src_val = get_tag_value(obj_src, id_tag)
                            else:            # схема обмена неполна / повреждена / ошибочна -
                                             # идентфикатор не будет скорректирован, что может привести к ошибке
                                             # это нужно зафиксировать в журнале ошибок
                                continue
                            if id_tag_src_val:    # описание объекта известно, находим его идентификатор и его самого среди устаревших объектов с правильными ид
                                dst_ref_id, dst_obj = get_tag_by_tag(self.tree_ci, id_tag, id_tag_src_val, 'Ref')
                            if dst_ref_id:      # нужный идентификатор найден - фиксируем его в кэше сопоставлений
                                if obj_ref_mapping:
                                    obj_ref_mapping[ref_id] = dst_ref_id
                            else:              # нужный идентификатор не найден - скорее всего, это новый объект
                                # либо объект существует, но его описание сильно отличается, сопоставлять надо вручную
                                # это нужно зафиксировать в журнале предупреждений
                                continue

                    if not dst_obj:  # объект с таким описанием не найден среди устаревших объектов
                        dst_obj = get_obj_by_ref(self.tree_ci, xml_type, 'Ref', dst_ref_id)

                    if dst_obj:     # устаревший объект найден
                        old_val = get_tag_value(dst_obj, attr.tag)  # пробуем получить значение тэга, которое нужно сохранить
                        obj_ref_mapping[ref_id] = dst_ref_id # нужный идентификатор найден - фиксируем его в кэше сопоставлений

                    if xor(is_empty(old_val, False), is_empty(attr.text, False)):
                        if old_val:             # сохраняем старое значение - то, для чего вся эта подпрограмма нужна
                            set_tag_value(obj_src, attr.tag, old_val)
                            # tail = attr.tail
                            # attr.text = old_val
                            # attr.tail = tail

    def process_ad_tree(self, mappings_filename):
        # просматриваем все нужные для импорта типы объектов
        # формируем для импорта дерево объектов, отсортированных по количеству ссылок на другие объекты, начиная с простых справочников

        self.result_tree = prepare_empty_1C_xml_tree()
        res_root = self.result_tree.getroot()
        if len(res_root):
            res_root = res_root[0]

        search_cache = {}

        if self.verbous_ouput:
            print('Getting referred types data...')


        loop_resolution_data = {'CatalogObject.Контрагенты': {'types_to_ignore': ['CatalogObject.БанковскиеСчета']},
                                'CatalogObject.Организации': {'types_to_ignore': ['CatalogObject.РегистрацииВНалоговомОргане']}}

        referred_types_data = list_referred_types(self.types_list_ci, self.tree_ad, ['IsFolder'], search_cache, loop_resolution_data)



        # получить список типов данных, отсортированный по количеству ссылок на другие объекты
        # по списку типов формируем список кортежей вида (имя_типа, [список типов, на которые он ссылается])
        # сортируем его по возрастанию длины списка используемых типов


        for type_header, referred_types_list in referred_types_data:
            if self.verbous_ouput:
                print('Processing objects of type ', type_header)

            template = self.xml_templates.get(type_header)
            exchange_scheme = self.xml_exchange_scheme.get(type_header)

            if not template or not exchange_scheme: continue

            obj_list, group_list = self.split_into_groups_and_objects(type_header, exchange_scheme)

            extra_parameters: dict = {'type_header': type_header}

            for xml_object in obj_list:
                if self.verbous_ouput:
                    set_cursor_pos(1, 10)
                    print('Processing object: ', xml_object[3].text)

                i = 0
                while True:
                    changes_done = self.reorder_tags_in_objects(xml_object, template, extra_parameters)
                    # if self.verbous_ouput:
                    #     set_cursor_pos(1, 11)
                    #     print('Reordering tags, step %d' % i)
                    i += 1

                    if (not changes_done) and object_complies_template(xml_object, template):
                        break

            for xml_object in group_list:
                if self.verbous_ouput:
                    set_cursor_pos(1, 10)
                    print('Processing group: ', xml_object[3].text)
                template = self.xml_templates.get(type_header + '_group')
                i = 0
                while True:
                    # if self.verbous_ouput:
                    #     set_cursor_pos(1, 11)
                    #     print('Reordering tags, step %d' % i)

                    changes_done = self.reorder_tags_in_objects(xml_object, template, extra_parameters)
                    i += 1
                    if (not changes_done) and object_complies_template(xml_object, template):
                        break

            if group_list:
                self.process_tags_by_scheme_in_objects(group_list, self.xml_templates.get(type_header + '_group'), extra_parameters)
                for obj in group_list:
                    res_root.append(deepcopy(obj))
            if obj_list:
                self.process_tags_by_scheme_in_objects(obj_list, self.xml_templates.get(type_header), extra_parameters)
                for obj in obj_list:
                    res_root.append(deepcopy(obj))

        key_tags = ['Ref', 'IsFolder', 'DeletionMark', 'Description', 'PredefinedDataName']

        id_mappings_cache = {}

        if is_valid_filename(mappings_filename):
            with open(mappings_filename, 'r', encoding='utf-8-sig') as myfile:
                lines = myfile.readlines()
                for line in lines:
                    if not line.strip(): continue
                    ad_id, ci_id = line.split(':', 1)
                    id_mappings_cache[ad_id] = ci_id

        for ad_id, mapping_data in self.id_mappings.items():
            ci_id = mapping_data.get('correct_id')
            if ci_id and ad_id: id_mappings_cache[ad_id] = ci_id

        parameters = {'key_tags': key_tags, 'exchange_scheme': exchange_scheme, 'mappings': id_mappings_cache, 'referred_types_data':referred_types_data}

        if self.verbous_ouput:
            print('Salvaging non-empty old values...')
        self.salvage_nonempty_old_values(parameters)

        if mappings_filename and isinstance(mappings_filename, str):
            with open(mappings_filename, 'w', encoding='utf-8-sig') as myfile:
                for ad_id, ci_id in id_mappings_cache.items():
                    myfile.write(str(ad_id) + ':' + str(ci_id) + '\n')

            with open(mappings_filename, 'r', encoding='utf-8-sig') as myfile:
                lines = myfile.readlines()

            with open(mappings_filename, 'w', encoding='utf-8-sig') as myfile:
                for line in lines:
                    if not line.strip(): continue
                    myfile.write(line)
