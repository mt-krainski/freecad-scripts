#!/bin/bash
EXPORT_DIR=$1

# activate proper virtualenvironment
source $HOME/.local/bin/virtualenvwrapper.sh
workon freecad

# create stl export directory if does not exist
mkdir -p $EXPORT_DIR/stl

# create urdf export directory if does not exist
mkdir -p $EXPORT_DIR/urdf


for file in `ls $EXPORT_DIR`; do
  # ignore FCStd1 files, assembly files and directories
  if [[ $file == *"FCStd1"* ]] || [[ -d $file ]] || [[ $file == *"assembly"* ]]; then
    continue
  fi
  STL_FILE=stl/${file%.*}.stl
  URDF_FILE=urdf/${file%.*}.urdf
  if [[ $file -nt $EXPORT_DIR/$STL_FILE ]] || [[ $file -nt $EXPORT_DIR/$URDF_FILE ]]; then
    echo "---- Exporting $file ----"
    $FREECAD_SCRIPTS/export_stl.py -i $EXPORT_DIR/$file -o $EXPORT_DIR/$STL_FILE
    $FREECAD_SCRIPTS/get_inertia.py --density 2700 -i $EXPORT_DIR/$STL_FILE -o $EXPORT_DIR/$URDF_FILE
  fi
done
