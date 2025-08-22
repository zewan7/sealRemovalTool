# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file '去印章.ui'
##
## Created by: Qt User Interface Compiler version 6.8.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QStatusBar, QTabWidget, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1175, 735)
        self.actionZ = QAction(MainWindow)
        self.actionZ.setObjectName(u"actionZ")
        self.actionZ.setCheckable(True)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        font = QFont()
        font.setPointSize(10)
        self.tab.setFont(font)
        self.tab.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.verticalLayout = QVBoxLayout(self.tab)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pushButton_7 = QPushButton(self.tab)
        self.pushButton_7.setObjectName(u"pushButton_7")

        self.horizontalLayout.addWidget(self.pushButton_7)

        self.spinBox = QSpinBox(self.tab)
        self.spinBox.setObjectName(u"spinBox")
        self.spinBox.setMaximum(255)
        self.spinBox.setValue(185)

        self.horizontalLayout.addWidget(self.spinBox)


        self.horizontalLayout_5.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(self.tab)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.label_2)

        self.comboBox = QComboBox(self.tab)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")
        self.comboBox.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.horizontalLayout_2.addWidget(self.comboBox)


        self.horizontalLayout_5.addLayout(self.horizontalLayout_2)

        self.checkBox = QCheckBox(self.tab)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.horizontalLayout_5.addWidget(self.checkBox)

        self.checkBox_2 = QCheckBox(self.tab)
        self.checkBox_2.setObjectName(u"checkBox_2")
        self.checkBox_2.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.horizontalLayout_5.addWidget(self.checkBox_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(self.tab)
        self.pushButton.setObjectName(u"pushButton")
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ZoomFitBest))
        self.pushButton.setIcon(icon)

        self.horizontalLayout_3.addWidget(self.pushButton)

        self.pushButton_2 = QPushButton(self.tab)
        self.pushButton_2.setObjectName(u"pushButton_2")
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart))
        self.pushButton_2.setIcon(icon1)

        self.horizontalLayout_3.addWidget(self.pushButton_2)

        self.pushButton_3 = QPushButton(self.tab)
        self.pushButton_3.setObjectName(u"pushButton_3")
        icon2 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave))
        self.pushButton_3.setIcon(icon2)

        self.horizontalLayout_3.addWidget(self.pushButton_3)


        self.horizontalLayout_5.addLayout(self.horizontalLayout_3)


        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_3 = QLabel(self.tab)
        self.label_3.setObjectName(u"label_3")
        font1 = QFont()
        font1.setPointSize(12)
        self.label_3.setFont(font1)

        self.horizontalLayout_4.addWidget(self.label_3)

        self.label_4 = QLabel(self.tab)
        self.label_4.setObjectName(u"label_4")
        font2 = QFont()
        font2.setFamilies([u"Microsoft Sans Serif"])
        font2.setPointSize(12)
        self.label_4.setFont(font2)

        self.horizontalLayout_4.addWidget(self.label_4)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.verticalLayout.setStretch(1, 1)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.tab_2.setFont(font)
        self.verticalLayout_4 = QVBoxLayout(self.tab_2)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.listWidget = QListWidget(self.tab_2)
        self.listWidget.setObjectName(u"listWidget")

        self.horizontalLayout_11.addWidget(self.listWidget)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.pushButton_4 = QPushButton(self.tab_2)
        self.pushButton_4.setObjectName(u"pushButton_4")

        self.horizontalLayout_6.addWidget(self.pushButton_4)

        self.spinBox_2 = QSpinBox(self.tab_2)
        self.spinBox_2.setObjectName(u"spinBox_2")
        self.spinBox_2.setMaximum(255)
        self.spinBox_2.setValue(185)

        self.horizontalLayout_6.addWidget(self.spinBox_2)

        self.label = QLabel(self.tab_2)
        self.label.setObjectName(u"label")

        self.horizontalLayout_6.addWidget(self.label)

        self.comboBox_2 = QComboBox(self.tab_2)
        self.comboBox_2.addItem("")
        self.comboBox_2.addItem("")
        self.comboBox_2.addItem("")
        self.comboBox_2.setObjectName(u"comboBox_2")

        self.horizontalLayout_6.addWidget(self.comboBox_2)

        self.checkBox_3 = QCheckBox(self.tab_2)
        self.checkBox_3.setObjectName(u"checkBox_3")

        self.horizontalLayout_6.addWidget(self.checkBox_3)

        self.checkBox_4 = QCheckBox(self.tab_2)
        self.checkBox_4.setObjectName(u"checkBox_4")

        self.horizontalLayout_6.addWidget(self.checkBox_4)


        self.horizontalLayout_9.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_2)

        self.pushButton_5 = QPushButton(self.tab_2)
        self.pushButton_5.setObjectName(u"pushButton_5")
        icon3 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MailAttachment))
        self.pushButton_5.setIcon(icon3)

        self.horizontalLayout_7.addWidget(self.pushButton_5)

        self.pushButton_6 = QPushButton(self.tab_2)
        self.pushButton_6.setObjectName(u"pushButton_6")
        self.pushButton_6.setIcon(icon1)

        self.horizontalLayout_7.addWidget(self.pushButton_6)

        self.pushButton_8 = QPushButton(self.tab_2)
        self.pushButton_8.setObjectName(u"pushButton_8")
        self.pushButton_8.setIcon(icon2)

        self.horizontalLayout_7.addWidget(self.pushButton_8)


        self.horizontalLayout_9.addLayout(self.horizontalLayout_7)


        self.verticalLayout_3.addLayout(self.horizontalLayout_9)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_5 = QLabel(self.tab_2)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_8.addWidget(self.label_5)

        self.label_6 = QLabel(self.tab_2)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_8.addWidget(self.label_6)


        self.verticalLayout_3.addLayout(self.horizontalLayout_8)

        self.verticalLayout_3.setStretch(1, 1)

        self.horizontalLayout_11.addLayout(self.verticalLayout_3)

        self.horizontalLayout_11.setStretch(0, 1)
        self.horizontalLayout_11.setStretch(1, 6)

        self.verticalLayout_4.addLayout(self.horizontalLayout_11)

        self.tabWidget.addTab(self.tab_2, "")

        self.verticalLayout_2.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionZ.setText(QCoreApplication.translate("MainWindow", u"Z", None))
        self.pushButton_7.setText(QCoreApplication.translate("MainWindow", u"\u56fe\u50cf\u9608\u503c(\u91cd\u7f6e):", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"  \u5370\u7ae0\u989c\u8272:", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("MainWindow", u"\u7ea2\u8272", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("MainWindow", u"\u7eff\u8272", None))
        self.comboBox.setItemText(2, QCoreApplication.translate("MainWindow", u"\u84dd\u8272", None))

        self.checkBox.setText(QCoreApplication.translate("MainWindow", u"\u589e\u5f3a\u5bf9\u6bd4\u5ea6", None))
        self.checkBox_2.setText(QCoreApplication.translate("MainWindow", u"\u589e\u5f3a\u6e05\u6670\u5ea6", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"\u9009\u62e9\u56fe\u50cf", None))
        self.pushButton_2.setText(QCoreApplication.translate("MainWindow", u"\u5f00\u59cb\u6267\u884c", None))
        self.pushButton_3.setText(QCoreApplication.translate("MainWindow", u"\u4fdd\u5b58\u5230\u672c\u5730", None))
        self.label_3.setText("")
        self.label_4.setText("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"\u5355\u56fe\u7247\u5904\u7406", None))
        self.pushButton_4.setText(QCoreApplication.translate("MainWindow", u"\u56fe\u50cf\u9608\u503c(\u91cd\u7f6e):", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"  \u5370\u7ae0\u989c\u8272:", None))
        self.comboBox_2.setItemText(0, QCoreApplication.translate("MainWindow", u"\u7ea2\u8272", None))
        self.comboBox_2.setItemText(1, QCoreApplication.translate("MainWindow", u"\u7eff\u8272", None))
        self.comboBox_2.setItemText(2, QCoreApplication.translate("MainWindow", u"\u84dd\u8272", None))

        self.checkBox_3.setText(QCoreApplication.translate("MainWindow", u"\u589e\u5f3a\u5bf9\u6bd4\u5ea6", None))
        self.checkBox_4.setText(QCoreApplication.translate("MainWindow", u"\u589e\u5f3a\u6e05\u6670\u5ea6", None))
        self.pushButton_5.setText(QCoreApplication.translate("MainWindow", u"\u9009\u62e9PDF", None))
        self.pushButton_6.setText(QCoreApplication.translate("MainWindow", u"\u5f00\u59cb\u6267\u884c", None))
        self.pushButton_8.setText(QCoreApplication.translate("MainWindow", u"\u4fdd\u5b58\u5230\u672c\u5730", None))
        self.label_5.setText("")
        self.label_6.setText("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"PDF\u6587\u4ef6\u5904\u7406", None))
    # retranslateUi

