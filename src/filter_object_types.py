# import xml.etree.ElementTree as et
# from xml.etree.ElementTree import Element as el, SubElement as sub
import argparse
from fileutils41cexch import replace_strings_in_file
from xml41cexh import *
from copy import deepcopy, copy

def get_types_list(filename):
    types_list = []
    with open(filename, 'r', encoding='utf-8-sig') as myfile:
        for line in myfile:
            line = line.strip()
            types_list.append(line)
    return types_list

def xml_element_from_string(s):
    parsr = et.XMLParser(encoding="utf-8")
    et.register_namespace('V8Exch', 'http://www.1c.ru/V8/1CV8DtUD/')
    et.register_namespace('v8', 'http://v8.1c.ru/data')
    et.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    return et.fromstring(s, parser=parsr)


def main():
    parser = argparse.ArgumentParser(description='List all top-level xml objects in file', prefix_chars='-/')
    parser.add_argument('xml_src', metavar='xml_src', type=str, help='actual xml to edit')
    parser.add_argument("-l", type=str, dest="types_list_file")
    parser.add_argument("-c", type=int, dest="obj_count")
    parser.add_argument("-o", type=str, dest="output_filename")
    args = parser.parse_args()

    tree_src = prepare_xml_tree(args.xml_src)
    if args.types_list_file and os.path.exists(args.types_list_file) and os.path.isfile(args.types_list_file):
        types_list = get_types_list(args.types_list_file)

    root = tree_src.getroot()[0]

    # tree_dst = et()
    # tree_dst
    tree_dst = prepare_xml_tree('empty_1c_tree.xml')
    root_dst = tree_dst.getroot()[0]

    counts = {}
    if args.obj_count:
        for xml_type in types_list:
            counts[xml_type] = 0

    for obj in root:
        if obj.tag in types_list:
            if args.obj_count:
                if counts.get(obj.tag, 0) < args.obj_count:
                    obj_dst = deepcopy(obj)
                    root_dst.append(obj_dst)
                    counts[obj.tag] = counts[obj.tag] + 1
            else:
                obj_dst = deepcopy(obj)
                root_dst.append(obj_dst)

    s = et.tostring(tree_src.getroot(), method='xml', encoding="utf-8")


    if args.output_filename:
        output_filename = args.output_filename
    else:
        output_filename = os.path.basename(args.xml_src) + '_filtered' + '.xml'
    tree_dst.write(output_filename, encoding='utf-8')
    replace_strings_in_file(output_filename, {'<v8:Types>': '<v8:Types xmlns="">'})

if __name__ == '__main__':
    main()