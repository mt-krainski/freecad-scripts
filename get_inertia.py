#!/usr/bin/env python

import argparse
from lxml import etree
import os
import re
import subprocess

VALID_MESH_EXTENSIONS = [
    '.stl',
]

UNIT_MM = 'mm'
UNIT_M = 'm'
FORMAT_SDF = 'sdf'
FORMAT_URDF = 'urdf'

FLOAT_RE = '(?P<{}>[+-]?\d+\.\d+)[^0-9\-]+'
def meshlab_re_template(label, tags):
    return '[^0-9\-]*'.join([label] + [FLOAT_RE.format(id) for id in tags])

MESHLAB = 'meshlab.meshlabserver'
VOLUME_TAGS = ['value']
VOLUME_RE = meshlab_re_template('Mesh Volume', VOLUME_TAGS)
COM_TAGS = ['x', 'y', 'z']
COM_RE = meshlab_re_template('Center of Mass', COM_TAGS)
INERTIA_TENSOR_TAGS = ['xx', 'xy', 'xz', 'yx', 'yy', 'yz', 'zx', 'zy', 'zz']
INERTIA_TENSOR_RE = meshlab_re_template('Inertia Tensor', INERTIA_TENSOR_TAGS)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def is_mesh_file(arg):
    if not os.path.exists(arg):
        raise argparse.ArgumentTypeError(
            'The file "%s" does not exist!' % arg)

    if not any(ext in arg for ext in VALID_MESH_EXTENSIONS):
        raise argparse.ArgumentTypeError(
            'The file "%s" does not have a recognized mesh extension!' % arg)

    return arg

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate an URDF config containing inertial parameters '\
                    'calculated for a given stl file.'
    )
    parser.add_argument('-i', '--input-file',
        help='Input file.',
        required=True,
        metavar='FILE',
        type=is_mesh_file,
    )
    parser.add_argument('-o', '--output-file',
        help='Output file. Defaults to the same filename as input ' \
             'with sdf or urdf extension',
        metavar='FILE'
    )
    parser.add_argument('-u', '--units',
        help='Define the units in which the input file is specified',
        choices=[UNIT_M, UNIT_MM],
        default=UNIT_MM,
    )
    parser.add_argument('-d', '--density',
        help='Assume this material density for inertia ' \
             'and mass calculations [kg/m3]',
        type=float
    )
    parser.add_argument('-m', '--mass',
        help='Assume this mass for inertia calculations [kg]',
        type=float
    )
    parser.add_argument('-f', '--format',
        help='Chose output format',
        choices=[FORMAT_URDF, FORMAT_SDF],
        type=str.lower,
        default=FORMAT_URDF
    )
    args = parser.parse_args()

    input_file = args.input_file
    units = args.units
    density = args.density
    mass = args.mass
    format = args.format
    output_file = args.output_file or input_file.split('.')[0]+'.'+format

    if density is not None and mass is not None:
        print 'Error! You can only specify one - mass or density!'
        exit(-1)

    script = SCRIPT_DIR+'/cgm.mlx' if units == UNIT_MM else SCRIPT_DIR+'/cgm_scale100.mlx'
    scale_factor = 1e-3 if units == UNIT_MM else 1e-2

    result = subprocess.Popen(
        [
            MESHLAB,
            '-i', input_file,
            '-s', script
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    result.wait()

    properties = {}

    text = result.stdout.read()

    properties['volume']=float(
        re.search(VOLUME_RE, text).group(*VOLUME_TAGS)
    )*(scale_factor**3)

    if mass is None:
        if density is not None:
            properties['mass'] = density * properties['volume']
        else:
            properties['mass'] = 1.0
    else:
        properties['mass'] = mass

    properties['center-of-mass']=dict([
        (tag, float(item)*scale_factor)
        for tag, item in zip(COM_TAGS, re.search(COM_RE, text).group(*COM_TAGS))
    ])

    # meshlab assumes density=1, so mass=volume. To properly calculate inertia
    # first we need to rescale to mass=1 and then to proper mass
    properties['inertia-tensor']=dict([
        (tag, float(item)*(scale_factor**5)/properties['volume']*properties['mass'])
        for tag, item
        in zip(
            INERTIA_TENSOR_TAGS,
            re.search(INERTIA_TENSOR_RE, text).group(*INERTIA_TENSOR_TAGS)
        )
    ])

    tag_value = [
        ('ixx', 'xx'),
        ('ixy', 'xy'),
        ('ixz', 'xz'),
        ('iyy', 'yy'),
        ('iyz', 'yz'),
        ('izz', 'zz'),
    ]

    root = None

    if format == FORMAT_SDF:
        root = etree.Element('inertial')
        root.append(etree.Comment('  Volume: {}  '.format(properties['volume'])))
        xml_mass = etree.SubElement(root, 'mass')
        xml_mass.text = ' {: e} '.format(properties['mass'])
        xml_pose = etree.SubElement(root, 'pose')
        xml_pose.text = ' {x: e} {y: e} {z: e} '.format(**properties['center-of-mass'])
        xml_inertia = etree.SubElement(root, 'inertia')
        for tag, value in tag_value:
            attr = etree.SubElement(xml_inertia, tag)
            attr.text = ' {: e} '.format(properties['inertia-tensor'][value])

    elif format == FORMAT_URDF:
        root = etree.Element('inertial')
        root.append(etree.Element(
            'origin',
            rpy='0 0 0',
            xyz='{x} {y} {z}'.format(**properties['center-of-mass'])
        ))
        root.append(etree.Element(
            'mass',
            value='{}'.format(properties['mass'])
        ))

        attr = {}
        for tag, value in tag_value:
            attr[tag] = '{}'.format(properties['inertia-tensor'][value])

        root.append(etree.Element(
            'inertia',
            **attr
        ))
    else:
        raise ValueError('Improper type defined!')

    if root is None:
        raise ValueError('Improper root node!')

    with open(output_file, 'w') as f:
        f.write(etree.tostring(root, pretty_print=True))
