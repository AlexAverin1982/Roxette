# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
# from xml.dom.pulldom import parse
"""src - актуальные данные с неправильными идентификаторами - этот файл надо редактировать для загрузки
dst - неактуальные данные с правильными (целевыми) идентификаторами и ссылками - из этого файла они и берутся для замены"""
import xml.etree.ElementTree as et
from xml.etree.ElementTree import Element as el
import argparse
import os
from xml41cexh import *

def main():
    parser = argparse.ArgumentParser(description='Create templates for xml object types from specified file', prefix_chars='-/')
    # parser.add_argument('xml_src', metavar='xml_src', type=str, help='actual xml to edit')
    parser.add_argument('xml_dst', metavar='xml_dst', type=str, help='xml file with objects to describe')
    parser.add_argument("-o", type=str, dest="output_filename", help='filename where resulting templates are to be stored')

    args = parser.parse_args()

    f = args.xml_dst
    if (not os.path.exists(f)) or (not os.path.isfile(f)): return

    if not args.output_filename:
        args.output_filename = args.xml_dst + '_templates.txt'

    # tree_src = prepare_xml_tree(args.xml_src)
    tree_dst = prepare_xml_tree(args.xml_dst)

    save_templates(tree_dst, args.output_filename)

if __name__ == '__main__':
    main()
