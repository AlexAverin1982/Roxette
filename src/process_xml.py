import argparse
import os.path
import xml.etree.ElementTree as et

from Roxette import Roxette, prepare_empty_1C_xml_tree

def main():
    parser = argparse.ArgumentParser(description='Processes the source (actual, but improper) xml in accordance with the correct data from the outdated ci xml', prefix_chars='-/')
    parser.add_argument('xml_ad', metavar='xml_ad', type=str, help='actual xml data (ad) to edit')
    parser.add_argument('xml_ci', metavar='xml_ci', type=str, help='outdated xml with from destination base containig correct ids (ci)')
    parser.add_argument("-t", type=str, dest="templates", help='file containg templates for xml objects to process')
    parser.add_argument("-e", type=str, dest="exchange_scheme", help='file containg the exchange process details')
    parser.add_argument("-m", type=str, dest="mappings_filename", help='a file conting ids mappings in format source_id:correct_id')
    parser.add_argument("-o", type=str, dest="output_filename", help='the name of a file to write processed xml into')
    parser.add_argument("-c", type=str, dest="id_mappings_filename", help='the name of a file to read/write cache')
    parser.add_argument("-v", dest="verbous_output", action="store_true", help='verbous debugging output of all ongoing processes')
    args = parser.parse_args()

    if args.verbous_output:
        print('Init...')

    xml_proc = Roxette(args)

    if args.verbous_output:
        print('Processing trees...')
    xml_proc.process_ad_tree(args.mappings_filename)

    if not args.output_filename:
        args.output_filename = os.path.basename(args.xml_ad) + '_processd.xml'

    #
    # # перечислить типы объектов в обоих файлах
    # # если такой-то тип отсутствует в конечном файле, тип не обрабатывается, данные передаются как есть, если в них нет ссылок на другие типы объектов
    # remove_obsolete_ad_objects(args.xml_ad, args.xml_ci, tree_ad)
    # object_types_list = list_used_xml_object_types(args.xml_ad)
    # # save_templates(tree_ci, object_types_list, '1c_xml_templates.txt', '1c_xml_exchange_scheme.txt')
    # process_ad_data(args.xml_ad, args.xml_ci, args.templates, args.exchange_scheme, tree_ad, tree_ci, object_types_list, args.mappings)
    #
    #
    # target_filename = os.path.basename(args.xml_ad) + '_processed.xml'
    xml_proc.result_tree.write(args.output_filename, encoding='utf-8')
    # xml_proc.tree_ad.write(args.output_filename, encoding='utf-8')
    # replace_strings_in_file(target_filename, {'<v8:Types>': '<v8:Types xmlns="">', '<Predefined>true</Predefined>': '<Predefined>false</Predefined>', ' />': '/>'})
    # remove_strings_in_file(target_filename, ['<v8:Type>DocumentRef.ОперацияСБилетом</v8:Type>', '<v8:Type>DocumentRef.ПутевойЛист</v8:Type>'])
if __name__ == '__main__':
    main()
