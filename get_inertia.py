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
BOUNDING_BOX_TAGS = ['x', 'y', 'z']
BOUNDING_BOX_MIN_RE = meshlab_re_template('Mesh Bounding Box min', BOUNDING_BOX_TAGS)
BOUNDING_BOX_MAX_RE = meshlab_re_template('Mesh Bounding Box max', BOUNDING_BOX_TAGS)
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
    parser.add_argument('-c', '--collision-file',
        help='Export bounding box as collision element (only for URDF).',
        metavar='FILE'
    )
    args = parser.parse_args()

    input_file = args.input_file
    units = args.units
    density = args.density
    mass = args.mass
    format = args.format
    collision_file = args.collision_file
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

    bounding_box_min =dict([
        (tag, float(item)*scale_factor)
        for tag, item in
        zip(
            BOUNDING_BOX_TAGS,
            re.search(BOUNDING_BOX_MIN_RE, text).group(*BOUNDING_BOX_TAGS)
        )
    ])

    bounding_box_max =dict([
        (tag, float(item)*scale_factor)
        for tag, item in
        zip(
            BOUNDING_BOX_TAGS,
            re.search(BOUNDING_BOX_MAX_RE, text).group(*BOUNDING_BOX_TAGS)
        )
    ])

    bounding_box_offset = dict([
        (key, (bounding_box_min[key]+bounding_box_max[key])/2)
        for key in bounding_box_min
    ])

    properties['collision'] = {
        'x': bounding_box_max['x'] - bounding_box_min['x'],
        'y': bounding_box_max['y'] - bounding_box_min['y'],
        'z': bounding_box_max['z'] - bounding_box_min['z'],
        'offset-x': bounding_box_offset['x'],
        'offset-y': bounding_box_offset['y'],
        'offset-z': bounding_box_offset['z'],
    }


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

    if format == FORMAT_SDF:
        if collision_file:
            raise ValueError('Currently can\'t export collision for sdf!')
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

        with open(output_file, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True))

    elif format == FORMAT_URDF:
        root = etree.Element('root')
        inertia = etree.SubElement(root, 'inertial')
        inertia.append(etree.Element(
            'origin',
            rpy='0 0 0',
            xyz='{x} {y} {z}'.format(**properties['center-of-mass'])
        ))
        inertia.append(etree.Element(
            'mass',
            value='{}'.format(properties['mass'])
        ))

        attr = {}
        for tag, value in tag_value:
            attr[tag] = '{}'.format(properties['inertia-tensor'][value])

        inertia.append(etree.Element(
            'inertia',
            **attr
        ))
        if collision_file:
            collision_root = etree.SubElement(root, 'collision')
            geometry = etree.SubElement(collision_root, 'geometry')
            geometry.append(etree.Element(
                'box',
                size='{x} {y} {z}'.format(**properties['collision'])
            ))
            collision_root.append(etree.Element(
                'origin',
                xyz='{offset-x} {offset-y} {offset-z}'.format(**properties['collision'])
            ))

        with open(output_file, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True))
    else:
        raise ValueError('Improper type defined!')
