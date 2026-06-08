# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QSizePolicy, QSpacerItem,
    QTextBrowser, QVBoxLayout, QWidget)

from ui.widgets.video_widget import VideoWidget

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(480, 320)
        MainWindow.setMinimumSize(QSize(0, 320))
        MainWindow.setMaximumSize(QSize(480, 320))
        MainWindow.setStyleSheet(u"background-color: rgb(11, 19, 43);")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_3 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setSpacing(10)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(9, 5, 9, 15)
        self.top_bar = QFrame(self.centralwidget)
        self.top_bar.setObjectName(u"top_bar")
        self.top_bar.setMinimumSize(QSize(480, 30))
        self.top_bar.setMaximumSize(QSize(480, 30))
        self.top_bar.setFrameShape(QFrame.StyledPanel)
        self.top_bar.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.top_bar)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(50, 3, -1, -1)
        self.lbl_tittle = QLabel(self.top_bar)
        self.lbl_tittle.setObjectName(u"lbl_tittle")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_tittle.sizePolicy().hasHeightForWidth())
        self.lbl_tittle.setSizePolicy(sizePolicy)
        self.lbl_tittle.setMinimumSize(QSize(200, 15))
        self.lbl_tittle.setMaximumSize(QSize(350, 50))
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.lbl_tittle.setFont(font)
        self.lbl_tittle.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"background-color: transparent;")
        self.lbl_tittle.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_5.addWidget(self.lbl_tittle)

        self.btn_minimizar = QPushButton(self.top_bar)
        self.btn_minimizar.setObjectName(u"btn_minimizar")
        sizePolicy.setHeightForWidth(self.btn_minimizar.sizePolicy().hasHeightForWidth())
        self.btn_minimizar.setSizePolicy(sizePolicy)
        self.btn_minimizar.setMinimumSize(QSize(15, 15))
        self.btn_minimizar.setMaximumSize(QSize(25, 25))
        self.btn_minimizar.setStyleSheet(u"background-color: rgb(58, 80, 107);\n"
"border: none;\n"
"color: #EAEAEA;\n"
"font-size: 16px;\n"
"padding: 5px 10px;\n"
"background-color: rgb(28, 37, 65);")

        self.horizontalLayout_5.addWidget(self.btn_minimizar)

        self.btn_cerrar = QPushButton(self.top_bar)
        self.btn_cerrar.setObjectName(u"btn_cerrar")
        sizePolicy.setHeightForWidth(self.btn_cerrar.sizePolicy().hasHeightForWidth())
        self.btn_cerrar.setSizePolicy(sizePolicy)
        self.btn_cerrar.setMinimumSize(QSize(15, 15))
        self.btn_cerrar.setMaximumSize(QSize(25, 25))
        self.btn_cerrar.setStyleSheet(u"border: none;\n"
"color: #EAEAEA;\n"
"background-color: rgb(28, 37, 65);\n"
"background-color: rgb(255, 77, 79);")

        self.horizontalLayout_5.addWidget(self.btn_cerrar)


        self.verticalLayout_3.addWidget(self.top_bar)

        self.central_panel = QHBoxLayout()
        self.central_panel.setObjectName(u"central_panel")
        self.left_panel = QVBoxLayout()
        self.left_panel.setSpacing(10)
        self.left_panel.setObjectName(u"left_panel")
        self.left_panel.setContentsMargins(5, 0, 5, 10)
        self.lbl_cam = QLabel(self.centralwidget)
        self.lbl_cam.setObjectName(u"lbl_cam")
        self.lbl_cam.setMinimumSize(QSize(200, 20))
        self.lbl_cam.setMaximumSize(QSize(300, 20))
        self.lbl_cam.setFont(font)
        self.lbl_cam.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"background-color: transparent;")
        self.lbl_cam.setAlignment(Qt.AlignCenter)

        self.left_panel.addWidget(self.lbl_cam)

        self.video_layaout = QHBoxLayout()
        self.video_layaout.setObjectName(u"video_layaout")
        self.lbl_video = VideoWidget(self.centralwidget)
        self.lbl_video.setObjectName(u"lbl_video")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.lbl_video.sizePolicy().hasHeightForWidth())
        self.lbl_video.setSizePolicy(sizePolicy1)
        self.lbl_video.setMinimumSize(QSize(180, 160))
        self.lbl_video.setMaximumSize(QSize(230, 180))
        self.lbl_video.setSizeIncrement(QSize(0, 0))
        self.lbl_video.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"background-color: rgb(15, 27, 61);\n"
"border-color: rgb(94, 192, 190);\n"
"")
        self.lbl_video.setAlignment(Qt.AlignCenter)

        self.video_layaout.addWidget(self.lbl_video)


        self.left_panel.addLayout(self.video_layaout)


        self.central_panel.addLayout(self.left_panel)

        self.right_panel = QVBoxLayout()
        self.right_panel.setSpacing(5)
        self.right_panel.setObjectName(u"right_panel")
        self.right_panel.setContentsMargins(15, 5, 5, 5)
        self.verticalSpacer = QSpacerItem(100, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)

        self.right_panel.addItem(self.verticalSpacer)

        self.lbl_model = QLabel(self.centralwidget)
        self.lbl_model.setObjectName(u"lbl_model")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.lbl_model.sizePolicy().hasHeightForWidth())
        self.lbl_model.setSizePolicy(sizePolicy2)
        self.lbl_model.setMinimumSize(QSize(180, 30))
        self.lbl_model.setMaximumSize(QSize(180, 30))
        font1 = QFont()
        font1.setBold(True)
        self.lbl_model.setFont(font1)
        self.lbl_model.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 10px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")
        self.lbl_model.setAlignment(Qt.AlignCenter)

        self.right_panel.addWidget(self.lbl_model)

        self.btn_config = QPushButton(self.centralwidget)
        self.btn_config.setObjectName(u"btn_config")
        sizePolicy2.setHeightForWidth(self.btn_config.sizePolicy().hasHeightForWidth())
        self.btn_config.setSizePolicy(sizePolicy2)
        self.btn_config.setMinimumSize(QSize(180, 30))
        self.btn_config.setMaximumSize(QSize(180, 30))
        self.btn_config.setFont(font1)
        self.btn_config.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 10px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.right_panel.addWidget(self.btn_config)

        self.status_1 = QHBoxLayout()
        self.status_1.setSpacing(5)
        self.status_1.setObjectName(u"status_1")
        self.status_1.setContentsMargins(0, -1, -1, -1)
        self.indicator_1 = QPushButton(self.centralwidget)
        self.indicator_1.setObjectName(u"indicator_1")
        self.indicator_1.setEnabled(True)
        sizePolicy.setHeightForWidth(self.indicator_1.sizePolicy().hasHeightForWidth())
        self.indicator_1.setSizePolicy(sizePolicy)
        self.indicator_1.setMinimumSize(QSize(35, 35))
        self.indicator_1.setMaximumSize(QSize(35, 35))
        self.indicator_1.setStyleSheet(u"border: 2px solid;\n"
"font-size: 16px;\n"
"border-radius: 17px;\n"
"border-color: rgb(46, 196, 182);\n"
"color: rgb(46, 196, 182);\n"
"background-color: rgb(15, 27, 61);")

        self.status_1.addWidget(self.indicator_1)

        self.lbl_indicator_1 = QLabel(self.centralwidget)
        self.lbl_indicator_1.setObjectName(u"lbl_indicator_1")
        self.lbl_indicator_1.setMinimumSize(QSize(100, 20))
        self.lbl_indicator_1.setMaximumSize(QSize(110, 50))
        self.lbl_indicator_1.setFont(font1)
        self.lbl_indicator_1.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"background-color: transparent;")

        self.status_1.addWidget(self.lbl_indicator_1)


        self.right_panel.addLayout(self.status_1)

        self.verticalSpacer_2 = QSpacerItem(100, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)

        self.right_panel.addItem(self.verticalSpacer_2)


        self.central_panel.addLayout(self.right_panel)


        self.verticalLayout_3.addLayout(self.central_panel)

        self.bttm_bar = QFrame(self.centralwidget)
        self.bttm_bar.setObjectName(u"bttm_bar")
        sizePolicy1.setHeightForWidth(self.bttm_bar.sizePolicy().hasHeightForWidth())
        self.bttm_bar.setSizePolicy(sizePolicy1)
        self.bttm_bar.setMinimumSize(QSize(450, 30))
        self.bttm_bar.setMaximumSize(QSize(700, 30))
        self.bttm_bar.setStyleSheet(u"background-color: rgb(28, 37, 65);\n"
"border-radius: 10px;")
        self.bttm_bar.setFrameShape(QFrame.StyledPanel)
        self.bttm_bar.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.bttm_bar)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(30, -1, -1, -1)
        self.txt_log = QTextBrowser(self.bttm_bar)
        self.txt_log.setObjectName(u"txt_log")

        self.horizontalLayout_3.addWidget(self.txt_log)


        self.verticalLayout_3.addWidget(self.bttm_bar)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.lbl_tittle.setText(QCoreApplication.translate("MainWindow", u"SISTEMA DE VISI\u00d3N - WORKSURFACE", None))
        self.btn_minimizar.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.btn_cerrar.setText(QCoreApplication.translate("MainWindow", u"X", None))
        self.lbl_cam.setText(QCoreApplication.translate("MainWindow", u"CAMARA", None))
        self.lbl_video.setText("")
        self.lbl_model.setText(QCoreApplication.translate("MainWindow", u"MODELO A", None))
        self.btn_config.setText(QCoreApplication.translate("MainWindow", u"CONFIGURACI\u00d3N", None))
        self.indicator_1.setText(QCoreApplication.translate("MainWindow", u"\u2714", None))
        self.lbl_indicator_1.setText(QCoreApplication.translate("MainWindow", u"INSPECCI\u00d3N OK/NG", None))
    # retranslateUi

