import argparse
import os

import FreeCAD
import Mesh

VALID_FREECAD_EXTENSIONS = [
    '.FCStd',
]

def is_freecad_file(arg):
    if not os.path.exists(arg):
        raise argparse.ArgumentTypeError(
            'The file "%s" does not exist!' % arg)
    if not any(ext in arg for ext in VALID_FREECAD_EXTENSIONS):
        raise argparse.ArgumentTypeError(
            'The file "%s" is not a recognized FreeCAD extension!' % arg)
    return arg

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_file',
        help='File to convert to stl.',
        required=True,
        metavar='FILE',
        type=is_freecad_file
    )
    parser.add_argument('-o', '--output',
        help='Output filename. Default is the same as the original'
             'file with .stl extension.',
    )
    # todo: make this accept a list
    parser.add_argument('-e', '--exported-body',
        help='Name of the exported body',
        default='Body',
    )
    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output or input_file.split('.')[0]+'.stl'
    body = args.exported_body

    doc = FreeCAD.open(input_file)
    App.setActiveDocument(doc.Name)
    App.ActiveDocument = App.getDocument(doc.Name)
    exported_objs = [
        FreeCAD.getDocument(doc.Name).getObject(body)
    ]
    Mesh.export(exported_objs, output_file)
