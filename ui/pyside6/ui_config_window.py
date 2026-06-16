# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'config_window.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(800, 480)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(480, 0))
        Form.setMaximumSize(QSize(800, 480))
        Form.setStyleSheet(u"background-color: rgb(11, 19, 43);")
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.top_bar = QFrame(Form)
        self.top_bar.setObjectName(u"top_bar")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.top_bar.sizePolicy().hasHeightForWidth())
        self.top_bar.setSizePolicy(sizePolicy1)
        self.top_bar.setMinimumSize(QSize(0, 40))
        self.top_bar.setMaximumSize(QSize(780, 40))
        font = QFont()
        font.setPointSize(11)
        self.top_bar.setFont(font)
        self.top_bar.setStyleSheet(u"")
        self.top_bar.setFrameShape(QFrame.StyledPanel)
        self.top_bar.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.top_bar)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.lbl_tittle = QLabel(self.top_bar)
        self.lbl_tittle.setObjectName(u"lbl_tittle")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.lbl_tittle.sizePolicy().hasHeightForWidth())
        self.lbl_tittle.setSizePolicy(sizePolicy2)
        self.lbl_tittle.setMinimumSize(QSize(300, 15))
        self.lbl_tittle.setMaximumSize(QSize(500, 80))
        font1 = QFont()
        font1.setPointSize(15)
        font1.setBold(True)
        self.lbl_tittle.setFont(font1)
        self.lbl_tittle.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"background-color: transparent;")
        self.lbl_tittle.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_4.addWidget(self.lbl_tittle)


        self.verticalLayout.addWidget(self.top_bar)

        self.central_layout = QHBoxLayout()
        self.central_layout.setSpacing(10)
        self.central_layout.setObjectName(u"central_layout")
        self.left_panel = QVBoxLayout()
        self.left_panel.setObjectName(u"left_panel")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.lbl_recipes = QLabel(Form)
        self.lbl_recipes.setObjectName(u"lbl_recipes")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.lbl_recipes.sizePolicy().hasHeightForWidth())
        self.lbl_recipes.setSizePolicy(sizePolicy3)
        self.lbl_recipes.setMaximumSize(QSize(200, 20))
        font2 = QFont()
        font2.setPointSize(10)
        font2.setBold(True)
        self.lbl_recipes.setFont(font2)
        self.lbl_recipes.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"background-color: transparent;")
        self.lbl_recipes.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_6.addWidget(self.lbl_recipes)


        self.left_panel.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.cmb_recipes = QComboBox(Form)
        self.cmb_recipes.setObjectName(u"cmb_recipes")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.cmb_recipes.sizePolicy().hasHeightForWidth())
        self.cmb_recipes.setSizePolicy(sizePolicy4)
        self.cmb_recipes.setMaximumSize(QSize(280, 30))
        self.cmb_recipes.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 3px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")
        self.cmb_recipes.setEditable(False)

        self.horizontalLayout_7.addWidget(self.cmb_recipes)


        self.left_panel.addLayout(self.horizontalLayout_7)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btn_add_r = QPushButton(Form)
        self.btn_add_r.setObjectName(u"btn_add_r")
        sizePolicy4.setHeightForWidth(self.btn_add_r.sizePolicy().hasHeightForWidth())
        self.btn_add_r.setSizePolicy(sizePolicy4)
        self.btn_add_r.setMinimumSize(QSize(0, 30))
        self.btn_add_r.setMaximumSize(QSize(130, 30))
        self.btn_add_r.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.horizontalLayout.addWidget(self.btn_add_r)

        self.btn_del_r = QPushButton(Form)
        self.btn_del_r.setObjectName(u"btn_del_r")
        sizePolicy4.setHeightForWidth(self.btn_del_r.sizePolicy().hasHeightForWidth())
        self.btn_del_r.setSizePolicy(sizePolicy4)
        self.btn_del_r.setMinimumSize(QSize(0, 30))
        self.btn_del_r.setMaximumSize(QSize(130, 30))
        self.btn_del_r.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.horizontalLayout.addWidget(self.btn_del_r)


        self.left_panel.addLayout(self.horizontalLayout)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.btn_select_r = QPushButton(Form)
        self.btn_select_r.setObjectName(u"btn_select_r")
        sizePolicy4.setHeightForWidth(self.btn_select_r.sizePolicy().hasHeightForWidth())
        self.btn_select_r.setSizePolicy(sizePolicy4)
        self.btn_select_r.setMinimumSize(QSize(0, 30))
        self.btn_select_r.setMaximumSize(QSize(160, 30))
        self.btn_select_r.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.horizontalLayout_5.addWidget(self.btn_select_r)


        self.left_panel.addLayout(self.horizontalLayout_5)

        self.horizontalSpacer_3 = QSpacerItem(380, 30, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.left_panel.addItem(self.horizontalSpacer_3)


        self.central_layout.addLayout(self.left_panel)

        self.line = QFrame(Form)
        self.line.setObjectName(u"line")
        self.line.setMinimumSize(QSize(3, 300))
        self.line.setMaximumSize(QSize(16777215, 500))
        self.line.setStyleSheet(u"background-color: rgb(15, 27, 61);")
        self.line.setFrameShape(QFrame.Shape.VLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.central_layout.addWidget(self.line)

        self.right_panel = QVBoxLayout()
        self.right_panel.setSpacing(5)
        self.right_panel.setObjectName(u"right_panel")
        self.right_panel.setContentsMargins(8, -1, 8, -1)
        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.lbl_tools = QLabel(Form)
        self.lbl_tools.setObjectName(u"lbl_tools")
        sizePolicy3.setHeightForWidth(self.lbl_tools.sizePolicy().hasHeightForWidth())
        self.lbl_tools.setSizePolicy(sizePolicy3)
        self.lbl_tools.setMaximumSize(QSize(200, 20))
        self.lbl_tools.setFont(font2)
        self.lbl_tools.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"background-color: transparent;")
        self.lbl_tools.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_9.addWidget(self.lbl_tools)


        self.right_panel.addLayout(self.horizontalLayout_9)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.cmb_tools = QComboBox(Form)
        self.cmb_tools.setObjectName(u"cmb_tools")
        sizePolicy4.setHeightForWidth(self.cmb_tools.sizePolicy().hasHeightForWidth())
        self.cmb_tools.setSizePolicy(sizePolicy4)
        self.cmb_tools.setMinimumSize(QSize(0, 25))
        self.cmb_tools.setMaximumSize(QSize(280, 30))
        self.cmb_tools.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 3px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.horizontalLayout_8.addWidget(self.cmb_tools)


        self.right_panel.addLayout(self.horizontalLayout_8)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.btn_edit_t = QPushButton(Form)
        self.btn_edit_t.setObjectName(u"btn_edit_t")
        sizePolicy4.setHeightForWidth(self.btn_edit_t.sizePolicy().hasHeightForWidth())
        self.btn_edit_t.setSizePolicy(sizePolicy4)
        self.btn_edit_t.setMinimumSize(QSize(0, 30))
        self.btn_edit_t.setMaximumSize(QSize(150, 30))
        self.btn_edit_t.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.horizontalLayout_3.addWidget(self.btn_edit_t)


        self.right_panel.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_add_t = QPushButton(Form)
        self.btn_add_t.setObjectName(u"btn_add_t")
        sizePolicy4.setHeightForWidth(self.btn_add_t.sizePolicy().hasHeightForWidth())
        self.btn_add_t.setSizePolicy(sizePolicy4)
        self.btn_add_t.setMinimumSize(QSize(0, 30))
        self.btn_add_t.setMaximumSize(QSize(120, 30))
        self.btn_add_t.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.horizontalLayout_2.addWidget(self.btn_add_t)

        self.btn_del_t = QPushButton(Form)
        self.btn_del_t.setObjectName(u"btn_del_t")
        sizePolicy4.setHeightForWidth(self.btn_del_t.sizePolicy().hasHeightForWidth())
        self.btn_del_t.setSizePolicy(sizePolicy4)
        self.btn_del_t.setMinimumSize(QSize(0, 30))
        self.btn_del_t.setMaximumSize(QSize(120, 30))
        self.btn_del_t.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.horizontalLayout_2.addWidget(self.btn_del_t)


        self.right_panel.addLayout(self.horizontalLayout_2)

        self.line_2 = QFrame(Form)
        self.line_2.setObjectName(u"line_2")
        sizePolicy.setHeightForWidth(self.line_2.sizePolicy().hasHeightForWidth())
        self.line_2.setSizePolicy(sizePolicy)
        self.line_2.setMinimumSize(QSize(355, 0))
        self.line_2.setMaximumSize(QSize(355, 3))
        self.line_2.setStyleSheet(u"background-color: rgb(15, 27, 61);")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.right_panel.addWidget(self.line_2)

        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.lbl_focus = QLabel(Form)
        self.lbl_focus.setObjectName(u"lbl_focus")
        sizePolicy3.setHeightForWidth(self.lbl_focus.sizePolicy().hasHeightForWidth())
        self.lbl_focus.setSizePolicy(sizePolicy3)
        self.lbl_focus.setMaximumSize(QSize(200, 30))
        self.lbl_focus.setFont(font2)
        self.lbl_focus.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"background-color: transparent;")
        self.lbl_focus.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_11.addWidget(self.lbl_focus)


        self.right_panel.addLayout(self.horizontalLayout_11)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.btn_focus_config = QPushButton(Form)
        self.btn_focus_config.setObjectName(u"btn_focus_config")
        sizePolicy4.setHeightForWidth(self.btn_focus_config.sizePolicy().hasHeightForWidth())
        self.btn_focus_config.setSizePolicy(sizePolicy4)
        self.btn_focus_config.setMinimumSize(QSize(0, 30))
        self.btn_focus_config.setMaximumSize(QSize(160, 30))
        self.btn_focus_config.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.horizontalLayout_10.addWidget(self.btn_focus_config)


        self.right_panel.addLayout(self.horizontalLayout_10)


        self.central_layout.addLayout(self.right_panel)


        self.verticalLayout.addLayout(self.central_layout)

        self.bttm_layout = QHBoxLayout()
        self.bttm_layout.setSpacing(30)
        self.bttm_layout.setObjectName(u"bttm_layout")
        self.bttm_layout.setContentsMargins(-1, 10, -1, 10)
        self.horizontalSpacer = QSpacerItem(30, 30, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bttm_layout.addItem(self.horizontalSpacer)

        self.btn_save = QPushButton(Form)
        self.btn_save.setObjectName(u"btn_save")
        sizePolicy4.setHeightForWidth(self.btn_save.sizePolicy().hasHeightForWidth())
        self.btn_save.setSizePolicy(sizePolicy4)
        self.btn_save.setMinimumSize(QSize(0, 30))
        self.btn_save.setMaximumSize(QSize(160, 35))
        self.btn_save.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")

        self.bttm_layout.addWidget(self.btn_save)

        self.btn_out = QPushButton(Form)
        self.btn_out.setObjectName(u"btn_out")
        sizePolicy4.setHeightForWidth(self.btn_out.sizePolicy().hasHeightForWidth())
        self.btn_out.setSizePolicy(sizePolicy4)
        self.btn_out.setMinimumSize(QSize(0, 30))
        self.btn_out.setMaximumSize(QSize(160, 35))
        self.btn_out.setStyleSheet(u"color: rgb(234, 234, 234);\n"
"border-radius: 15px;\n"
"border: 2px solid;\n"
"border-color: rgb(91, 192, 190);\n"
"background-color: rgb(15, 27, 61);")
        self.btn_out.setCheckable(False)
        self.btn_out.setChecked(False)
        self.btn_out.setAutoDefault(True)

        self.bttm_layout.addWidget(self.btn_out)

        self.horizontalSpacer_2 = QSpacerItem(30, 30, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bttm_layout.addItem(self.horizontalSpacer_2)


        self.verticalLayout.addLayout(self.bttm_layout)

        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        sizePolicy3.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy3)
        self.frame.setMinimumSize(QSize(780, 45))
        self.frame.setMaximumSize(QSize(800, 45))
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_12 = QHBoxLayout(self.frame)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.list_log_config = QListWidget(self.frame)
        self.list_log_config.setObjectName(u"list_log_config")
        self.list_log_config.setMaximumSize(QSize(800, 35))
        self.list_log_config.setFont(font)
        self.list_log_config.setStyleSheet(u"border: none;")

        self.horizontalLayout_12.addWidget(self.list_log_config)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(Form)

        self.btn_out.setDefault(True)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.lbl_tittle.setText(QCoreApplication.translate("Form", u"SISTEMA DE VISI\u00d3N - CONFIGURACI\u00d3N", None))
        self.lbl_recipes.setText(QCoreApplication.translate("Form", u"RECETAS", None))
        self.btn_add_r.setText(QCoreApplication.translate("Form", u"AGREGAR", None))
        self.btn_del_r.setText(QCoreApplication.translate("Form", u"ELIMINAR", None))
        self.btn_select_r.setText(QCoreApplication.translate("Form", u"SELECCIONAR", None))
        self.lbl_tools.setText(QCoreApplication.translate("Form", u"HERRAMIENTAS", None))
        self.btn_edit_t.setText(QCoreApplication.translate("Form", u"EDITAR", None))
        self.btn_add_t.setText(QCoreApplication.translate("Form", u"AGREGAR", None))
        self.btn_del_t.setText(QCoreApplication.translate("Form", u"ELIMINAR", None))
        self.lbl_focus.setText(QCoreApplication.translate("Form", u"ENFOQUE DE CAMARA", None))
        self.btn_focus_config.setText(QCoreApplication.translate("Form", u"FOCUS CONFIG", None))
        self.btn_save.setText(QCoreApplication.translate("Form", u"GUARDAR", None))
        self.btn_out.setText(QCoreApplication.translate("Form", u"SALIR", None))
    # retranslateUi

