# Building processes

## Building a Window .exe

*Until now it is mostly tested for Windows 10 and 11. But the post-installs, so getting additional data and compiling targets and meshes or even entering the desired user paths before starting the program first time is still missing.*

### Preparations (needed once):

A windows build is pretty easy. It should work for Linux and Windows.

An installation of pynsist and nsis is needed.

Required steps on Linux / Windows with Linux installed:

```bash
pip3 install pynsist
```

Then get a version of nsis and install it with e.g. (Linux):

```bash
apt-get install nsis
```

or download and install a version from:

[sourceforge.net](https://sourceforge.net page](https://sourceforge.net/projects/nsis)

for Windows.

### The build process

*Note: The build is done in the folder mentioned by python tempfile.gettempdir(). It is a platform-specific location:

* Windows, the directories C:\TEMP, C:\TMP, \TEMP, and \TMP, in that order.

* On all other platforms, the directories /tmp, /var/tmp, and /usr/tmp, in that order.*

After that works once, one only need to call winbuild.py (in this build folder):

```bash
python3 winbuild.py
```

Usually there is no need to do further manual actions.

* The program uses the configuration file build.json and version number, title and publisher from makehuman2\_version.json
* It copies all necessary files from the repo to the destination folder
* It leaves out directories and files mentioned in build.json
* It adds an icon, a starter script 'winstart.py' and a license file
* It creates pynsist.cfg for pynsist library call
* It gets the python version mentioned in build.json, packages and pypi\_wheels (python libraries)
* pynsist is started to create the "installer.nsi" for nsis
* It is started with "--no-makensis", because the "installer.nsi" will be changed to e.g. hold a desktop link.
* After that makensis itself is called. It creates the file:

```bash
/tmp/pynsist-work/build/nsis/MakeHuman_II_2.0.1.exe		# LINUX, on Windows temp path should be different
```

which is an self-extracting archive including all steps to create entries for registry etc. Also an uninstaller is supplied.
This usually takes some time.

### Result of installation

* The installation will put all files in the installation-directory, which the user has to enter in the dialog.
* A local python version is installed in that folder.
* License, starter program and icon are placed in that folder.
* A desktop link is created:

```bash
CreateShortCut "$DESKTOP\MakeHuman II.lnk" "$INSTDIR\Python\python.exe" '"$INSTDIR\winstart.py"' "$INSTDIR\makehuman2logo.ico"
```

* An uninstaller will also be placed in that folder. 
* Registry entries all starting with the name "Software\Microsoft\Windows\CurrentVersion\Uninstall\<MakeHumanName>" will be written to enanble uninstall command.

## Uninstall Windows Version

To uninstall the progran the uninstaller.exe in that installation folder must be called. It will delete the installation folder completely if no files are left in that folder. This will work even when makehuman2 creates mhbin files and compressed targets, because the makehuman2 system paths are ALWAYS deleted.

It will NOT delete the user folders, also the %APPDATA%/makehuman2/makehuman2.conf will stay. Normally this allows to install a new version.

Desktop link and registry entries are also deleted.


