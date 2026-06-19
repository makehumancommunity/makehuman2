"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * MHLogWindow
"""


from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QListWidgetItem, QRadioButton,
        QGroupBox, QCheckBox, QLineEdit, QGridLayout
        )
from PySide6.QtGui import QColor

import sys
import re

class MHLogWindow(QWidget):
    """
    Message window for logfiles and errors
    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.env = parent.env
        self.redispdata = True
        self.f_displayed = self.env.path_stdout
        self.f_match = re.compile(r"^\[(\d+)\]\s+")
        self.setWindowTitle("Messages")
        self.resize (500, 600)
        layout = QVBoxLayout()

        self.error_view = QListWidget()
        layout.addWidget(self.error_view)

        self.f_stdout = QRadioButton("Messages")
        self.f_stdout.setChecked(True)
        self.f_stdout.toggled.connect(self.change_file)
        self.f_stderr = QRadioButton("Errors")
        self.f_stderr.toggled.connect(self.change_file)

        hlayout = QHBoxLayout()

        fdisp = QGroupBox("Modes")
        fdisp.setObjectName("subwindow")
        me_layout = QVBoxLayout()

        self.cb_redisp = QCheckBox("Automatic redisplay\n(5 seconds)")
        self.cb_redisp.setLayoutDirection(Qt.LeftToRight)
        self.cb_redisp.setChecked(self.redispdata)
        self.cb_redisp.stateChanged.connect(self.handleTimer)

        me_layout.addWidget(self.cb_redisp)
        me_layout.addWidget(self.f_stdout)
        me_layout.addWidget(self.f_stderr)
        fdisp.setLayout(me_layout)
        hlayout.addWidget(fdisp)

        rbutton = QPushButton("Manual Redisplay")
        rbutton.clicked.connect(self.redisplay_call)
        hlayout.addWidget(rbutton)
        button = QPushButton("Close")
        button.clicked.connect(self.close_call)
        hlayout.addWidget(button)

        layout.addLayout(hlayout)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.redisplay_call)
        self.timer.start(5000) 

    def handleTimer(self, value):
        state = Qt.CheckState(value)
        if state == Qt.CheckState.Checked:
            self.timer.start()
        elif state == Qt.CheckState.Unchecked:
            self.timer.stop()

    def fillListWidget(self):
        """
        inserts lines of logfile, just a crude hack
        """
        col = ["#202020", "#600000", "#606000", "#402080",  "#002080", "#408020", "#008020", "#804080", "#004080" ]
        self.error_view.clear()

        # in case of no redirection
        #
        if self.f_displayed is None:
            l = QListWidgetItem("No redirection, nothing to display")
            l.setBackground( QColor(col[1]) )
            self.error_view.addItem(l)
            return
        with open(self.f_displayed) as f:
            for line in f:
                color = 0
                m = self.f_match.match(line)
                if m:
                    color = int(m.group(1))
                    if color > 8:
                        color=0
                l = QListWidgetItem(line.rstrip())
                l.setBackground( QColor(col[color]) )
                self.error_view.addItem(l)
        self.error_view.scrollToBottom()
                

    def change_file(self):
        """
        change between stderr and stdout
        """
        if self.f_stdout.isChecked():
            if self.f_displayed != self.env.path_stdout:
                sys.stdout.flush()
                self.f_displayed = self.env.path_stdout
                self.fillListWidget()
        else:
            if self.f_displayed != self.env.path_stderr:
                sys.stderr.flush()
                self.f_displayed = self.env.path_stderr
                self.fillListWidget()

    def show(self):
        """
        normal show + flush to get the newest entries
        """
        sys.stdout.flush()
        sys.stderr.flush()
        self.fillListWidget()
        super().show()

    def redisplay_call(self):
        """
        to get more lines of logfiles uses redisplay
        """
        sys.stdout.flush()
        sys.stderr.flush()
        self.fillListWidget()

    def close_call(self):
        self.close()

