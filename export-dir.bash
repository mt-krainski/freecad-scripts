#!/bin/bash
EXPORT_DIR=$1

# activate proper virtualenvironment
source $HOME/.local/bin/virtualenvwrapper.sh
workon freecad

# create export directory if does not exist
mkdir -p $EXPORT_DIR/stl


for file in `ls $EXPORT_DIR`; do
  # ignore FCStd1 files, assembly files and directories
  if [[ $file == *"FCStd1"* ]] || [[ -d $file ]] || [[ $file == *"assembly"* ]]; then
    continue
  fi
  if [[ $file -nt $EXPORT_DIR/stl/${file%.*}.stl ]]; then
    echo "---- Exporting $file ----"
    $FREECAD_SCRIPTS/export_stl.py -i $EXPORT_DIR/$file -o $EXPORT_DIR/stl/${file%.*}.stl
  fi
done
