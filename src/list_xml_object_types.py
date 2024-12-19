import os
import argparse
from xml41cexh import list_used_xml_object_types

def main():
    parser = argparse.ArgumentParser(description='List all top-level xml objects in file', prefix_chars='-/')
    parser.add_argument('xml_file', metavar='xml_file', type=str, help='file to analyze')
    parser.add_argument("-o", type=str, dest="output_filename", help='filename for the resulting list of xml types')

    args = parser.parse_args()

    f = args.xml_file
    if (not os.path.exists(f)) or (not os.path.isfile(f)): return

    if not args.output_filename:
        args.output_filename = 'used_xml_object_types_for_'+os.path.basename(f)+'.txt'

    list_used_xml_object_types(f, args.output_filename)

if __name__ == '__main__':
    main()
