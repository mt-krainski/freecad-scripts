import argparse
import os
import subprocess

VALID_MESH_EXTENSIONS = [
    '.stl',
]

MESHLAB = 'meshlab.meshlabserver'

def is_mesh_file(arg):
    if not os.path.exists(arg):
        raise argparse.ArgumentTypeError(
            'The file "%s" does not exist!' % arg)

    if not any(ext in arg for ext in VALID_MESH_EXTENSIONS):
        raise argparse.ArgumentTypeError(
            'The file "%s" does not have a recognized mesh extension!' % arg)

    return arg

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_file',
        help='Input file.',
        required=True,
        metavar='FILE',
        type=is_mesh_file,
    )
    parser.add_argument('-u', '--units',
        help='Define the units in which the input file is specified',
        choices=['m', 'mm'],
        default='mm',
    )
    parser.add_argument('-d', '--density',
        help='Assume this material density for inertia and mass calculations',
    )
    parser.add_argument('-m', '--mass',
        help='Assume this mass for inertia calculations',
    )
    args = parser.parse_args()

    input_file = args.input_file
    units = args.units
    density = args.density
    mass = args.mass

    if density is not None and mass is not None:
        print 'Error! You can only specify one - mass or density!'
        exit(-1)

    script = 'cgm_scale100.mlx' if units=='mm' else 'cgm.mlx'

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
    print "Completed"
    for line in result.stdout.readlines():
        #todo: parse result
        print line
