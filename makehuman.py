#!/usr/bin/python3
"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck
"""
import argparse, textwrap
import os
import sys
from time import sleep

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop

sys.path.insert(0, ".") # used for windows

from core.globenv import programInfo, globalObjects
from gui.mainwindow import  MHMainWindow
from gui.infowindow import  MHInfoWindow
from gui.application import  MHApplication
from core.baseobj import baseClass

def main():
    """
    main simply
    * parses arguments
    * calls environment
    * sets theme
    * starts application itself
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    # optional arguments
    parser.add_argument("model", type=str, nargs='?', help="name of an mhm model file (use with base mesh)")
    parser.add_argument('-V', '--version', action='store_true',  help="Show version and License")
    parser.add_argument("--nomultisampling", action="store_true", help=textwrap.dedent('''\
        disable multisampling (used to display multi transparent layers)
        without multisampling normal blend function is used'''))
    parser.add_argument("-l", action="store_true", help="force to write to log file")
    parser.add_argument("-b", "--base", type=str, help="preselect base mesh use 'none' for no preselection")
    parser.add_argument("-r", "--repository", action="store_true", help=textwrap.dedent('''\
        create a new database repository. It is needed when repository seems to have
        missing entries or when user space was moved to a new location. The manually
        entered data (new tags for categorization) is not deleted.'''))
    parser.add_argument("-A", '--admin', action="store_true", help="Support administrative tasks ('Admin'). Command will write into program folder, where makehuman is installed.")
    parser.add_argument("-v", "--verbose",  type=int, default = 1, help= textwrap.dedent('''\
            bitwise verbose option (add values)
            1 low log level (standard)
            2 mid log level
            4 memory management
            8 file access
            16 enable numpy runtime error messages
            32 JSON for e.g glTF or to get lines for face or body poses when loading bvh file'''))

    args = parser.parse_args()

    frozen = getattr(sys, 'frozen', False) # frozen means, no source download
    if frozen:
        syspath = os.path.dirname(sys.executable)
    else:
        syspath = os.path.dirname(os.path.realpath(__file__))
    
    os.chdir(syspath)

    # get programInfo as environment (only for strings to be printed in JSON)
    # and globalObjects for non-printable objects

    env = programInfo(frozen, syspath, args)
    if not env.environment():
        print (env.last_error)
        exit (20)

    if args.version:
        env.showVersion()
        exit(0)

    glob = globalObjects(env)
    if not glob.readShaderInitJSON():
        print (env.last_error)
        exit (21)

    if args.verbose & 2:
        print (env)

    theme = env.existDataFile("themes", env.config["theme"])

    app = MHApplication(glob, sys.argv)
    glob.setApplication(app)

    if app.setStyles(theme) is False:
        env.logLine(1, env.last_error)

    if args.base:
        if args.base == "none":
            env.basename = None
        else:
            env.basename = args.base

    if env.basename is not None:
        dirnames  = env.getDataDirs("base", env.basename)
        if len(dirnames) == 0:
            print("Base mesh " + env.basename + " does not exist")
            exit(22)

    modelfile = None
    if args.model is not None:
        if env.basename is None:
            print("Cannot load a model with undefined base mesh")
            exit(23)
        if not args.model.endswith(".mhm"):
            args.model += ".mhm"

        modelpath = env.stdUserPath("models")
        modelfile  = env.existDataFile("models", env.basename, args.model)
        if modelfile is None:
            print("File '" + args.model + "' does not exist in: " + str(modelpath))
            exit(24)


    # splash screen
    #
    loading = MHInfoWindow(glob)
    loading.show()
    sleep(0.5)
    app.processEvents(QEventLoop.AllEvents)

    if env.basename is not None:
        base = baseClass(glob, env.basename)
        base.prepareClass(modelfile)

    mainwin = MHMainWindow(glob)
    mainwin.show()
    mainwin.move(app.topLeftCentered(mainwin))
    loading.close()
    #
    # all we need from openGL is now existent (get initial values)
    #
    mainwin.initParams()
    app.exec()
    

if __name__ == '__main__':
    main()
