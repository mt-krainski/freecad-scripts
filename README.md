## FreeCAD Scripts

This repository contains a few handy FreeCAD automation scripts I've written over time.

If you see something useful - feel Free to use it!

### Getting started

> This assumes that you're using FreeCAD 0.18

> Those notes are for Ubuntu. If you're using a different system, feel free to let me know - let's figure out the steps together!

Install FreeCAD:
```
apt install FreeCAD
```

Find your FreeCAD libraries:
```
locate FreeCAD.so
```

That library in my case was in `/usr/lib/freecad-python2/lib`. After adding it to path, and trying to `import FreeCAD` (as suggested by the [offical docs](https://www.freecadweb.org/wiki/Embedding_FreeCAD)), a message was being printed out that `No modules found in /usr/lib/freecad-python2/Mod`. And this later caused an error. After inspection, I've found the `Mod` directory in `/usr/lib/freecad/` and I've made a symlink from that directory to `/usr/lib/freecad-python2/lib`:

```
cd /usr/lib/freecad-python2/lib
ln --symbolic ../freecad/Mod Mod
```

I'm usually working with [`virtualenvwrapper`](https://virtualenvwrapper.readthedocs.io/en/latest/), so in this case you can make a virtualenv with (FreeCAD now is using Python2):

```
mkvirtualenv freecad -p `which python2`
```

and then add this to the `postactivate` script:

```
export PYTHONPATH=$PYTHONPATH:/usr/lib/freecad/lib
```

Some of the scripts are using [MeshLab](http://www.meshlab.net/), so feel free to install it as well:
```
snap install meshlab
```


### Features

- Auto export `.FCStd` files to `.stl` (Currently only single-object files)
- Auto-generate [URDF](http://wiki.ros.org/urdf) config for an `.stl` object using `meshlabserver`.
