"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * DownLoadImport
"""
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel,
    QMessageBox, QRadioButton, QCheckBox, QComboBox
    )

from PySide6.QtCore import Qt
from gui.tablewindow import MHSelectAssetWindow
from gui.common import ErrorBox, WorkerThread, MHBusyWindow, IconButton, MHFileRequest
from opengl.texture import MH_Thumb
from core.importfiles import AssetPack

import os

class DownLoadImport(QVBoxLayout):
    def __init__(self, parent, view, displaytitle):
        self.parent = parent
        self.glob = parent.glob
        self.env = parent.env
        self.view = view
        self.displaytitle = displaytitle
        self.bckproc = None     # will contain process running in parallel
        self.error   = None     # will contain possible error text
        self.zipfile = None     # last loaded zipfile
        self.assetlistpath = None
        self.assetjson = None
        self.assetpacklistpath = None
        self.assetpackjson = None
        self.packitems = []
        self.packurls = []
        self.use_userpath = True
        self.assets = AssetPack()

        dl = os.path.join(self.env.path_userdata, "downloads", self.env.basename)
        assetname = os.path.split(self.env.release_info["url_assetlist"])[1]
        assetpackname = os.path.split(self.env.release_info["url_assetpacklist"])[1]
        self.assetlistpath = os.path.join(dl, assetname)
        self.assetpacklistpath = os.path.join(dl, assetpackname)
        self.getAssetPackList()

        super().__init__()

        self.latest = self.assets.testAssetList(self.assetlistpath)
        if self.latest is None:
            self.asdlbutton=QPushButton("Download Asset and Assetpack list")
        else:
            self.asdlbutton=QPushButton("Replace Current Asset Lists [" + self.latest + "]")
        self.asdlbutton.clicked.connect(self.listDownLoad)
        self.asdlbutton.setToolTip("Asset list are needed to load single assets or assetpacks.<br>This must be done once.<br>Usually you only need to reload lists if new assets are available.")
        self.addWidget(self.asdlbutton)

        gb = QGroupBox("Single Asset")
        gb.setObjectName("subwindow")
        vlayout = QVBoxLayout()

        vlayout.addWidget(QLabel("\nBrowse in list to find your asset."))
        self.browsebutton=QPushButton("Asset Browser")
        self.browsebutton.setEnabled(self.latest is not None)
        self.browsebutton.clicked.connect(self.selectfromList)
        self.browsebutton.setToolTip("Browse downloaded asset list.")
        vlayout.addWidget(self.browsebutton)


        gb.setLayout(vlayout)
        self.addWidget(gb)

        gb = QGroupBox("Asset Pack")
        gb.setObjectName("subwindow")

        # name and link
        #
        ilayout = QVBoxLayout()
        ilayout.addWidget(QLabel("Select asset pack:"))

        self.combo = QComboBox()
        self.combo.addItems(self.packitems)
        self.combo.setToolTip("An asset pack is a zip file,\nDownload of the standard assets can be done here.\nThey also can be downloaded manually\nand extracted with extract button below")
        self.combo.currentIndexChanged.connect(self.packNameChanged)

        ilayout.addWidget(self.combo)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("or select and copy an URL from:"))
        linklabel = QLabel()
        ltext = "<a href='" + self.env.release_info["url_assetpacks"] + "'>Asset Packs</a>"
        linklabel.setToolTip("Opens browser to search for asset packs.\nAn asset pack usually ends with .zip")
        linklabel.setText(ltext)
        linklabel.setOpenExternalLinks(True)
        hlayout.addWidget(linklabel)
        ilayout.addLayout(hlayout)

        self.packname = QLineEdit("")
        self.packname.editingFinished.connect(self.packinserted)
        ilayout.addWidget(self.packname)

        self.dlbutton=QPushButton("Download Asset Pack")
        self.dlbutton.clicked.connect(self.downLoad)
        ilayout.addWidget(self.dlbutton)

        userpath = QLabel("Destination user path for base: "  + self.env.basename + "\n"+ self.env.path_userdata)
        userpath.setToolTip("Files will be extracted to " + self.env.basename + " folders in "  + self.env.path_userdata)
        ilayout.addWidget(userpath)

        if self.env.admin:
            syspath = QLabel("Destination system path for base: " + self.env.basename + "\n"+ self.env.path_sysdata)
            syspath.setToolTip("Files will be extracted to " + self.env.basename + " folders in "  + self.env.path_sysdata)
            ilayout.addWidget(syspath)

            self.userbutton = QRadioButton("Install in your user path")
            self.userbutton.setChecked(True)
            self.systembutton = QRadioButton("Install in system path")
            self.userbutton.toggled.connect(self.setMethod)
            self.systembutton.toggled.connect(self.setMethod)
            ilayout.addWidget(self.userbutton)
            ilayout.addWidget(self.systembutton)


        ilayout.addWidget(QLabel("\nAfter download use the filename inserted by\nprogram or type in a name of an already\ndownloaded asset pack and press extract:"))
        self.filename = QLineEdit("")
        self.filename.editingFinished.connect(self.fnameinserted)
        self.filename.setText(self.parent.glob.lastdownload)
        ilayout.addWidget(self.filename)

        self.savebutton=QPushButton("Extract")
        self.savebutton.clicked.connect(self.extractZip)
        ilayout.addWidget(self.savebutton)

        ilayout.addWidget(QLabel("\nIf the downloaded file is no longer needed,\npress cleanup to delete the temporary folder"))
        self.clbutton=QPushButton("Clean Up")
        self.clbutton.clicked.connect(self.cleanUp)
        ilayout.addWidget(self.clbutton)
        gb.setLayout(ilayout)
        self.addWidget(gb)
        self.packinserted()
        self.fnameinserted()

    def defaultList(self):
        self.packitems= ["", "Standard Asset Pack", "Additional Makehuman2 Asset Pack"]
        self.packurls= [
            "",
            self.env.release_info["url_fileserver"] + "/" + self.env.release_info["url_systemassets"],
            self.env.release_info["url_fileserver"] +  "/" +self.env.release_info["url_systemassets2"]
        ]

    def formList(self, packs):
        self.packitems= []
        self.packurls= []
        for key, elem in packs.items():
            if "url" in elem:
                if "descr" in elem:
                    text = elem["descr"]
                else:
                    text = key
                if "license" in elem:
                    text += ", " + elem["license"]
                if "size" in elem:
                    text += " (" + str(elem["size"]) + " mb)"
                self.packitems.append(text)
                self.packurls.append(elem["url"])

    def getAssetPackList(self):
        self.assetpackjson = self.env.readJSON(self.assetpacklistpath)
        if self.assetpackjson is not None and "packs" in self.assetpackjson:
            self.formList(self.assetpackjson["packs"])   
        else:
            self.defaultList()

    def packNameChanged(self, index):
        f = self.env.release_info["url_fileserver"] + "/" + self.packurls[index]
        self.packname.setText(f)
        self.packinserted()

    def setMethod(self, value):
        if self.userbutton.isChecked():
            self.use_userpath = True
        else:
            self.use_userpath = False

    def packinserted(self):
        self.dlbutton.setEnabled(len(self.packname.text()) > 0)

    def fnameinserted(self):
        self.savebutton.setEnabled(len(self.filename.text()) > 0)

    def selectfromList(self):
        if self.assetjson is None:
            self.assetjson =  self.assets.alistReadJSON(self.env, self.assetlistpath)
        w = self.glob.showSubwindow("loadasset", self, MHSelectAssetWindow, self.assetjson)

    def par_unzip(self, bckproc, *args):
        tempdir = self.assets.unZip(self.filename.text())
        destpath = self.env.path_sysdata if self.use_userpath is False else self.env.path_userdata
        self.env.logLine(1, "Unzip into: " + tempdir + " >" + destpath + " Mesh: " + self.env.basename)
        self.assets.copyAssets(tempdir, destpath, self.env.basename)

    def finishUnzip(self):
        self.assets.cleanupUnzip()
        if self.prog_window is not None:
            self.prog_window.progress.close()
            self.prog_window = None

        # recreate internal repos to avoid a new start
        #
        self.glob.MainWindow.redoImageSelectionRepos()

        QMessageBox.information(self.parent, "Done!", self.bckproc.finishmsg)
        self.bckproc = None

    def extractZip(self):
        fname = self.filename.text()
        if not fname.endswith(".zip"):
            ErrorBox(self.parent, "Filename should have the suffix .zip")
            return

        self.env.logLine(1, "Extract zip: " + fname)
        if self.bckproc == None:
            self.prog_window = MHBusyWindow("Extract ZIP file", "extracting ...")
            self.prog_window.progress.forceShow()
            self.bckproc = WorkerThread(self.par_unzip, None)
            self.bckproc.start()
            self.bckproc.finishmsg = "Zip file has been imported"
            self.bckproc.finished.connect(self.finishUnzip)

    def par_download(self, bckproc, *args):
        tempdir = args[0][0]
        filename = args[0][1]
        self.error = None
        self.env.logLine(1, "Download " + filename + " to " + tempdir)
        (err, text) = self.assets.getAssetPack(self.packname.text(), tempdir, filename)
        self.error = text

    def finishLoad(self):
        if self.prog_window is not None:
            self.prog_window.progress.close()
            self.prog_window = None
        if self.error:
            ErrorBox(self.parent, self.error)
        else:
            QMessageBox.information(self.parent, "Done!", self.bckproc.finishmsg)
        self.bckproc = None

    def finishListLoad(self):
        if self.prog_window is not None:
            self.prog_window.progress.close()
            self.prog_window = None
        if self.error:
            ErrorBox(self.parent, self.error)
        else:
            QMessageBox.information(self.parent, "Done!", self.bckproc.finishmsg)
        self.bckproc = None
        self.latest = self.assets.testAssetList(self.assetlistpath)
        self.browsebutton.setEnabled(self.latest is not None)

        # add the new items to combobox
        #
        self.getAssetPackList()
        self.combo.clear()
        self.combo.addItems(self.packitems)


    def downLoad(self):
        url = self.packname.text()
        if not (url.startswith("ftp:") or url.startswith("http:") or url.startswith("https:")):
            ErrorBox(self.parent, "URL must start with a known protocol [http, https, ftp]")
            return
        filename = os.path.split(url)[1]

        if self.bckproc == None:
            tempdir = self.assets.tempDir()
            self.parent.glob.lastdownload = os.path.join(tempdir, filename)
            self.filename.setText(self.parent.glob.lastdownload)
            self.fnameinserted()
            self.prog_window = MHBusyWindow("Download pack to " + tempdir, "loading ...")
            self.prog_window.progress.forceShow()
            self.bckproc = WorkerThread(self.par_download, tempdir, filename)
            self.bckproc.start()
            self.bckproc.finishmsg = "Download finished"
            self.bckproc.finished.connect(self.finishLoad)

    def par_listdownload(self, bckproc, *args):
        destination = args[0][0]
        destination2 = args[0][1]
        self.error = None
        (err, text) = self.assets.getUrlFile(self.env.release_info["url_assetlist"], destination)
        self.error = text
        if err is False:
            return
        (err, text) = self.assets.getUrlFile(self.env.release_info["url_assetpacklist"], destination2)
        self.error = text

    def listDownLoad(self):
        if self.bckproc == None:
            self.assetjson = None       # reset this
            self.prog_window = MHBusyWindow("Download list to " + self.assetlistpath, "loading ...")
            self.prog_window.progress.forceShow()
            self.bckproc = WorkerThread(self.par_listdownload, self.assetlistpath, self.assetpacklistpath)
            self.bckproc.start()
            self.bckproc.finishmsg = "Download finished"
            self.bckproc.finished.connect(self.finishListLoad)

    def par_filesdownload(self, bckproc, *args):
        destination = args[0][0]
        files = args[0][1]
        self.error = None
        for elem in files:
            dest = os.path.split(elem)[1]
            self.env.logLine(8, "Get: " + elem + " >" + destination)
            self.prog_window.setLabelText("Loading: " + elem)
            destpath = os.path.join(destination, dest)
            (loaded, text) = self.assets.getUrlFile(elem, destpath)
            if loaded is False:
                self.error = text
                return
            #
            # resize thumbfile if needed or recreate targetlist
            #
            if destpath.endswith(".thumb"):
                thumb = MH_Thumb()
                thumb.rescale(destpath)
            elif destpath.endswith(".target"):
                self.glob.Targets.categories.newUserCategories()
                tname, t = self.glob.Targets.categories.findUserAsset(dest)
                if tname is not None:
                    self.glob.Targets.createTarget(tname, t)
                else:
                    self.error = "target not found, please restart makehuman"

        self.error = text

    def parentAsset(self, key):
        """
        calculate path of parent asset or return a path to type if possible
        """
        pobj = self.assetjson[key]["belongs_to"]
        if pobj["belonging_is_assigned"] is False:
            #
            # asset missing return User-data path
            return False, self.env.path_userdata
        else:
            if "belongs_to_core_asset" in pobj:
                #
                # core assets must be recalculated (basename added).
                # eyes will always go into a common folder

                (mtype, folder) = pobj["belongs_to_core_asset"].split("/", 2)
                if mtype == "eyes":
                    path = self.env.existDataDir(mtype, self.env.basename)
                else:
                    path = self.env.existDataDir(mtype, self.env.basename, folder)
                if path is None:
                    self.env.last_error = "core assets not found: " + pobj["belongs_to_core_asset"]
                    return False, None

                return True, path

            parentkey = str(pobj["belongs_to_id"])
            mtype = self.assetjson[parentkey]["type"]        # changed type includes hair, cannot use belongs_to_type
            folder = self.assets.titleToFileName(pobj["belongs_to_title"])

            path = self.env.existDataDir(mtype, self.env.basename, folder)
            if path is None:
                return False, self.env.existDataDir(mtype, self.env.basename)
            return True, path

    def singleDownLoad(self, assetname):

        supportedclasses = ["clothes", "hair", "eyes", "teeth", "eyebrows", "eyelashes", "expression",
                "pose", "skin", "rig", "proxy", "model", "target", "material" ]

        # if not loaded, load json now
        if self.assetjson is None:
            self.assetjson = self.assets.alistReadJSON(self.env, self.assetlistpath)

        # if still None, error in JSON file
        if self.assetjson is None:
            ErrorBox(self.parent, self.env.last_error)
            return

        if assetname in self.assetjson:
            item = self.assetjson[assetname]
            folder = item.get("folder")
        else:
            ErrorBox(self.parent, "Asset '" + assetname + "' not found in list.")
            return

        mtype, flist = self.assets.alistGetFiles(self.assetjson, assetname)

        if mtype not in supportedclasses:
            ErrorBox(self.parent, "Supported classes until now: " + str(supportedclasses))
            return

        self.env.logLine(8, "Assets of type " + mtype + " >" + folder)
        for elem in flist:
            self.env.logLine(8, " " + elem)

        if mtype == "material":
            #
            # for materials the parent asset is needed and the path should be calculated

            okay, path = self.parentAsset(assetname)
            if okay is False:
                if path is None:
                    ErrorBox(self.parent, self.env.last_error)
                    return
                #
                # part of the path is known, create a file request box

                freq = MHFileRequest(self.glob, "Select a directory to save additional materials", None, path, save=".")
                path = freq.request()
                if path is None:
                    return              # cancel

                print ("Working with path: ", path)


            folder, err = self.assets.createMaterialsFolder(path)
        else:
            folder, err = self.assets.alistCreateFolderFromTitle(self.env.path_userdata, self.env.basename, mtype, folder)

        if folder is None:
            ErrorBox(self.parent, err)
            return

        if self.bckproc == None:
            self.prog_window = MHBusyWindow("Download files to " + folder, "loading ...")
            self.prog_window.progress.forceShow()
            self.bckproc = WorkerThread(self.par_filesdownload, folder, flist)
            self.bckproc.start()
            self.bckproc.finishmsg = "Download finished"
            self.bckproc.finished.connect(self.finishLoad)

    def cleanUp(self):
        fullpath = self.parent.glob.lastdownload
        if fullpath is not None:
            (fpath, fname ) = os.path.split(fullpath)
            if os.path.isfile(fullpath):
                os.remove(fullpath)
            os.rmdir(fpath)
            self.parent.glob.lastdownload = None
            self.filename.setText(self.parent.glob.lastdownload)
