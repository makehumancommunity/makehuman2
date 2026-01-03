"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * KeyPrefFilter
    * MHPrefWindow
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QAbstractItemView, QRadioButton,
    QGroupBox, QCheckBox, QLineEdit, QGridLayout, QTabWidget, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QIntValidator, QKeySequence
from gui.common import ErrorBox

class KeyPrefFilter(QObject):
    def eventFilter(self, widget, event):
        if event.type() == QEvent.ShortcutOverride:
            key = QKeySequence(event.keyCombination()).toString()
            widget.keylabel.setText(key)
        return False

class MHPrefWindow(QWidget):
    """
    preferences window
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        env = parent.env

        self.localKeys = self.genLocalKeys(self.parent.glob.keyDict)
        self.old_homepath = env.path_home

        self.setWindowTitle("Preferences")
        self.resize (500, 600)

        self.apihost = env.config["apihost"] if "apihost" in env.config else "127.0.0.1"
        self.apiport = str(env.config["apiport"] if "apiport" in env.config else 12345)

        self.redirect_bool = env.config["redirect_messages"]
        self.redirect_path = env.path_error

        layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.maintab = QWidget()
        self.keytab  = QWidget()
        self.tab_widget.addTab(self.maintab, "Main")
        self.tab_widget.addTab(self.keytab, "Input")
        layout.addWidget(self.tab_widget)
        self.initMainTab(self.maintab)
        self.initKeyTab(self.keytab)

        # buttons for cancel and save
        #
        hLayout = QHBoxLayout()
        button1 = QPushButton("Cancel")
        button1.clicked.connect(self.cancel_call)
        hLayout.addWidget(button1)

        button2 = QPushButton("Save")
        button2.clicked.connect(self.save_call)
        hLayout.addWidget(button2)
        layout.addLayout(hLayout)

        self.setLayout(layout)

    def genLocalKeys(self, keys):
        """
        create a copy of given key-dictionary with only lists with 3 elements
        """
        localKeys = {}
        for key, item in keys.items():
            if isinstance(item, str):
                localKeys[key] = [item, "", "" ]
            elif isinstance(item, list):
                nitem = []
                for s in item:
                    nitem.append(s)
                while len(nitem) < 3:
                    nitem.append("")
                localKeys[key] = nitem

        return localKeys

    def genNewKeyDict(self):
        """
        the key dictionary is the optimized version of the localKeys to handle keys using strings and lists
        """
        keydict = {}
        for key, item in self.localKeys.items():
            nitem = []
            for i in item:
                if i != '':
                    nitem.append(i)
            l = len(nitem)
            if l == 1:
                keydict[key] = nitem[0]
            elif l > 1:
                keydict[key] = nitem

        return keydict

    def show(self):
        #
        # is called when displaying the menu, in case of "cancel" before, it should be display again
        #
        for row in range(self.keyTable.rowCount()):
            key = self.keyTable.item(row,0).text()
            pos = 1
            for text in self.localKeys[key]:
                self.keyTable.item(row,pos).setText(text)
                pos +=1
        self.keylabel.setText('')
        self.textlabel.setText('')
        self.keyTable.clearSelection()
        super().show()

    def initMainTab(self, maintab):
        """
        main preferences: folder, themes, preselected mesh, units, API, session
        """
        env = self.parent.env
        layout = QVBoxLayout(maintab)
        folders = QGroupBox("Folders")
        folders.setObjectName("subwindow")
        fo_layout = QGridLayout()
        fo_layout.addWidget(QLabel("MakeHuman user home"), 0, 0, 1, 2)
        self.ql_path_home = QLineEdit(env.path_home)
        self.ql_path_home.setToolTip('must be different to ' + env.path_sys + '\nif you change this, be aware to move existent data to new folder')
        self.ql_path_home.editingFinished.connect(self.test_homepath)
        fo_layout.addWidget(self.ql_path_home, 1, 0, 1, 2)
        fo_layout.addWidget(QLabel("Errors and logging"), 2, 0)
        self.cb_redirect = QCheckBox("Redirect")
        self.cb_redirect.setLayoutDirection(Qt.RightToLeft)
        if self.redirect_bool is True:
            self.cb_redirect.setChecked(True)
        self.cb_redirect.setToolTip('if not checked, messages will be sent to CLI')
        fo_layout.addWidget(self.cb_redirect, 2, 1)
        self.ql_path_error  = QLineEdit(env.path_error)
        fo_layout.addWidget(self.ql_path_error, 3, 0, 1, 2)
        folders.setLayout(fo_layout)
        layout.addWidget(folders)

        # themes
        #
        themes = QGroupBox("Themes")
        themes.setObjectName("subwindow")
        th_layout = QVBoxLayout()
        self.themelist = env.getDataFileList("qss", "themes")
        self.listwidget = QListWidget()
        self.listwidget.addItems(self.themelist.keys())
        self.listwidget.setSelectionMode(QAbstractItemView.SingleSelection)
        items = self.listwidget.findItems(env.config["theme"],Qt.MatchExactly)
        if len(items) > 0:
            self.listwidget.setCurrentItem(items[0])

        th_layout.addWidget(self.listwidget)
        themes.setLayout(th_layout)
        layout.addWidget(themes)

        # prefered mesh
        #
        meshes = QGroupBox("Base mesh")
        meshes.setObjectName("subwindow")
        me_layout = QVBoxLayout()
        baselist = env.getDataDirList("base.obj", "base")
        self.basewidget = QListWidget()
        self.basewidget.addItems(baselist.keys())
        self.basewidget.setSelectionMode(QAbstractItemView.SingleSelection)
        if env.basename is not None:
            items = self.basewidget.findItems(env.basename,Qt.MatchExactly)
            if len(items) > 0:
                self.basewidget.setCurrentItem(items[0])
        me_layout.addWidget(self.basewidget)
        meshes.setLayout(me_layout)
        layout.addWidget(meshes)

        # units
        #
        self.u_metric =   QRadioButton("Metric")
        self.u_imperial = QRadioButton("Imperial")
        if env.config["units"] == "imperial":
            self.u_imperial.setChecked(True)
        else:
            self.u_metric.setChecked(True)
        units = QGroupBox("Units")
        units.setObjectName("subwindow")
        me_layout = QVBoxLayout()
        me_layout.addWidget(self.u_metric)
        me_layout.addWidget(self.u_imperial)
        units.setLayout(me_layout)
        layout.addWidget(units)

        # API
        #
        apigr = QGroupBox("API (socket communication)")
        apigr.setObjectName("subwindow")
        ap_layout = QGridLayout()
        ap_layout.addWidget(QLabel("Host"), 0, 0)
        ap_layout.addWidget(QLabel("Port"), 1, 0)
        self.ql_host = QLineEdit(self.apihost)
        self.ql_port = QLineEdit(self.apiport)
        self.ql_port.setToolTip('socket port number, range is 1024 to 49151')
        self.ql_port.setValidator(QIntValidator())
        ap_layout.addWidget(self.ql_host, 0, 1)
        ap_layout.addWidget(self.ql_port, 1, 1)
        apigr.setLayout(ap_layout)
        layout.addWidget(apigr)

        # session
        #
        sess = QGroupBox("Session")
        sess.setObjectName("subwindow")
        se_layout = QVBoxLayout()

        self.cb_keep = QCheckBox("remember window size")
        if env.config["remember_session"] is True:
            self.cb_keep.setChecked(True)
        se_layout.addWidget(self.cb_keep)
        sess.setLayout(se_layout)
        layout.addWidget(sess)


    def initKeyTab(self, keytab):
        layout = QVBoxLayout(keytab)
        rows = len(self.localKeys)
        self.keyTable = QTableWidget(rows, 4)
        self.keyTable.setHorizontalHeaderLabels(["Feature", "Key", "Key2", "Key3"])
        self.keyTable.verticalHeader().setVisible(False)
        self.keyTable.horizontalHeader().setMinimumSectionSize((keytab.width() - 200) // 4)
        self.keyTable.itemClicked.connect(self.key_selected)
        i = 0
        #
        # create columns using localKeys
        #
        for key, item in self.localKeys.items():
            q =  QTableWidgetItem(key)
            q.setFlags(q.flags() ^ (Qt.ItemFlag.ItemIsEditable|Qt.ItemFlag.ItemIsSelectable))
            self.keyTable.setItem(i, 0, q)
            pos = 1
            for col in item:
                q =  QTableWidgetItem(col)
                q.setFlags(q.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.keyTable.setItem(i, pos, q)
                pos += 1
            i += 1
        layout.addWidget(self.keyTable)

        chgkey = QGroupBox("Change key")
        chgkey.setObjectName("subwindow")
        explain = QLabel("Select a key in table above, then press a key,<br>To use new key, push change button")

        # set style to make the input fields visible
        #
        self.textlabel = QLabel("", self)
        self.textlabel.setObjectName("groupbox")
        self.keylabel  = QLabel("", self)
        self.keylabel.setObjectName("groupbox")

        self.eventFilter = KeyPrefFilter(parent=self)
        self.installEventFilter(self.eventFilter)
        vlayout = QVBoxLayout()
        vlayout.addWidget(explain)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.textlabel)
        hlayout.addWidget(self.keylabel)
        self.changeButton = QPushButton("Change")
        self.changeButton.clicked.connect(self.changekey_call)
        hlayout.addWidget(self.changeButton)
        self.deleteButton = QPushButton("Delete")
        self.deleteButton.clicked.connect(self.deletekey_call)
        hlayout.addWidget(self.deleteButton)
        vlayout.addLayout(hlayout)
        chgkey.setLayout(vlayout)
        layout.addWidget(chgkey)


    def key_selected(self):
        """
        write feature to change into textlabel
        """
        row = self.keyTable.currentRow()
        if row < 0:
            return
        self.textlabel.setText(self.keyTable.item(row,0).text())
        self.keylabel.setText('')

    def test_homepath(self):
        """
        test the pathname, it should not be equal to installation path and longer than 3
        """
        up = self.parent.env.fullPath(self.ql_path_home.text())
        sp = self.parent.env.fullPath(self.parent.env.path_sys)
        if sp == up or len(up) < 3:
            up = self.old_homepath
        self.ql_path_home.setText(up)

    def changekey_call(self):
        row = self.keyTable.currentRow()
        col = self.keyTable.currentColumn()
        if row < 0 or col < 1:
            return
        name = self.textlabel.text()
        key  = self.keylabel.text()
        self.localKeys[name][col-1] = key
        self.keyTable.item(row,col).setText(key)

    def deletekey_call(self):
        row = self.keyTable.currentRow()
        col = self.keyTable.currentColumn()
        if row < 0 or col < 1:
            return
        name = self.textlabel.text()
        self.localKeys[name][col-1] = ''
        self.keyTable.item(row,col).setText('')

    def cancel_call(self):
        # reset keys
        self.localKeys = self.genLocalKeys(self.parent.glob.keyDict)
        self.close()

    def save_call(self):
        """
        does all the work to save configuration
        """
        env =  self.parent.env
        glob=  self.parent.glob

        # first save new keys and apply it to graphical window
        #
        glob.keyDict = self.genNewKeyDict()
        glob.midColumn.generateKeyDict()

        apiport = int(self.ql_port.text())
        if apiport < 1024 or apiport > 49152:
            ErrorBox(self.parent.central_widget, "Port must be in range 1024 to 49151.")
            return

        env.config["keys"] = glob.keyDict
        env.config["apiport"] = apiport
        env.config["apihost"] = self.ql_host.text()

        sel = self.listwidget.selectedItems()
        if len(sel) > 0:
            theme = sel[0].text()
            self.parent.glob.app.setStyles(self.themelist[theme])
        else:
            theme = "makehuman.qss"
        env.config["theme"] = theme

        sel = self.basewidget.selectedItems()
        if len(sel) > 0:
            basename = sel[0].text()
        else:
            basename = None
        env.config["basename"] = basename

        env.config["units"] = self.u_metric.text().lower() if self.u_metric.isChecked() else self.u_imperial.text().lower()
        env.config["remember_session"] = self.cb_keep.isChecked()

        env.path_home = env.config["path_home"] = self.ql_path_home.text()
        #
        env.config["redirect_messages"] = self.cb_redirect.isChecked()
        env.path_error = env.config["path_error"] = self.ql_path_error.text()
        env.generateFolders()

        if self.redirect_bool != env.config["redirect_messages"] or self.redirect_path != env.path_error:
            env.reDirect()

        env.logLine(2, "Save preferences in " + env.path_userconf)
        if env.writeJSON(env.path_userconf, env.config) is False:
            env.logLine(1, env.last_error)
        self.close()
