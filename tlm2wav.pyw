#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт запуска GUI программы tlm2wav.
"""

import sys
from PyQt4 import QtGui, QtCore
import qt_gui

__author__ = 'Don D.S.'


def main():
    app = QtGui.QApplication(sys.argv)

    # Для локализации надписей на стандартных виджетах
    translator = QtCore.QTranslator()
    # скопировал qt_ru.qm себе в папку со своим скриптом в подпапку lib
    # В пути использовать прямые слэши!
    # qt_ru.qm брал из C:\Python27\Lib\site-packages\PyQt4\translations\
    translator.load(u'qt_ru', u'./forms/')
    # расширение файла (.qm) Qt сам добавит.
    app.installTranslator(translator)

    main_window = qt_gui.MainWindow()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
