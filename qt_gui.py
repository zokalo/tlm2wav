#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Графическая оболочка PyQt4 для программы tlm2wav
"""

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT
import matplotlib.pyplot as plt
from matplotlib.widgets import SpanSelector
import matplotlib
import matplotlib.patches
import wave
import struct
import numpy as np
import shutil
import os
import time
from PyQt4 import QtGui, QtCore
from tlm2wav import Telemetry, LEFT, RIGHT, META, CALIB, TIME
import pyaudio
import threading
import enum

__author__ = 'Don D.S.'


class MainWindow(QtGui.QWidget):
    """Главное окно программы
    """
    def __init__(self):
        # Инициализировать:
        # - родительский класс
        QtGui.QWidget.__init__(self)

        # Имя аудиофайла по умолчанию
        self._tmp_outfile = 'tmp_output.wav'
        # Размер иконок на кнопках
        btn_iconsize = 24
        # Высота progress-bar'а
        progressbar_height = 24

        # Аналог документа - телеметрия
        self._telemetry = None
        # Путь к последнему файлу
        self.lastfile = '.'  # os.path.expanduser('~')
        # Дочернее окно
        self.calib_window = None

        # Поток создания аудиофайла
        # --------------------------------------------
        self.make_sound_thread = MakeSoundThread(
            get_tlm=lambda: self.telemetry,
            get_sens_left=lambda: self.sens_left,
            get_sens_right=lambda: self.sens_right,
            get_mode=lambda: self.mode,
            get_multiplier=lambda: self.multiplier,
            get_framerate=lambda: self.framerate,
            get_sampwidth=lambda: self.sampwidth,
            get_outfile=lambda: self.tmp_outfile)
        # Соединить сигналы завершения потока с обработкой
        self.connect(self.make_sound_thread,
                     QtCore.SIGNAL("finished()"), self._make_sound_finished)
        self.connect(self.make_sound_thread,
                     QtCore.SIGNAL("started()"), self._make_sound_start)
        self.connect(self.make_sound_thread,
                     QtCore.SIGNAL("progress(int)"), self.set_progress)
        self.connect(self.make_sound_thread,
                     QtCore.SIGNAL("progress(QString)"), self.set_progress)

        # Установить параметры основного окна
        # ----------------------------------------------------------
        self.setFixedSize(450, 400)  # вместо resize - чтобы запретить
        #  изменение размера окна
        self.setWindowTitle('Конвертер телеметрии')
        self.setWindowIcon(QtGui.QIcon('icons/Icon_34.ico'))

        # КНОПКИ
        # -----------------------------------------------------------
        # Кнопка открытия файла телеметрии
        self.btn_file = QtGui.QPushButton('Файл', self)
        self.btn_file.setShortcut('Ctrl+O')
        self.btn_file.setToolTip('Указать файл телеметрии')
        self.connect(self.btn_file, QtCore.SIGNAL('clicked()'), self.dlg_open)
        # - калибровка
        self.btn_calib = QtGui.QPushButton('График / Калибровка', self)
        self.btn_calib.setToolTip(
            'Отобразить график, указать калибровочные периоды')
        self.btn_calib.setDisabled(True)
        self.connect(self.btn_calib,
                     QtCore.SIGNAL('clicked()'),
                     self.show_calib_window)
        # - создать аудиофайл (перекрывает прервать)
        self.btn_make_snd = QtGui.QPushButton('', self)
        self.btn_make_snd.setIcon(QtGui.QIcon(
            "icons/appbar.check.rest.png"))
        self.btn_make_snd.setIconSize(QtCore.QSize(btn_iconsize, btn_iconsize))
        self.btn_make_snd.setToolTip('Создать аудиофайл из телеметрической информации')
        self.btn_make_snd.setDisabled(True)
        self.connect(self.btn_make_snd,
                     QtCore.SIGNAL('clicked()'), self.make_sound_thread.start)
        # - прервать создание (перекрывает создать)
        self.btn_abort = QtGui.QPushButton('', self)
        self.btn_abort.setIcon(QtGui.QIcon(
            "icons/appbar.close.rest.png"))
        self.btn_abort.setIconSize(QtCore.QSize(btn_iconsize, btn_iconsize))
        self.btn_abort.setToolTip('Прервать')
        self.btn_abort.setVisible(False)
        self.connect(self.btn_abort,
                     QtCore.SIGNAL('clicked()'), self.make_sound_thread.abort)
        # - сохранить
        self.btn_save = QtGui.QPushButton('', self)
        self.btn_save.setIcon(QtGui.QIcon("icons/appbar.save.rest.png"))
        self.btn_save.setIconSize(QtCore.QSize(btn_iconsize, btn_iconsize))
        self.btn_save.setShortcut('Ctrl+S')
        self.btn_save.setToolTip('Сохранить аудиофайл')
        self.btn_save.setDisabled(True)
        self.connect(self.btn_save, QtCore.SIGNAL('clicked()'), self.dlg_save)

        # Поля ввода:
        # ------------------------------
        # - отображение текущего файла
        self.txt_file = QtGui.QLineEdit('')
        self.txt_file_default = 'Выберите файл телеметрии'
        self.txt_file.setText(self.txt_file_default)
        self.txt_file.setReadOnly(True)
        # - скорость проигрывания телеметрии
        self.txt_multiplier = QtGui.QLineEdit('')
        self.txt_multiplier.setValidator(QtGui.QIntValidator(1, 9999))
        self.txt_multiplier.setText('200')

        # Выпадающие списки:
        # ------------------------------
        self.lst_left = QtGui.QComboBox(self)
        self.lst_left.addItem('Угловой пр-ль 1', 1)  # строка и связанные данные
        self.lst_left.addItem('Угловой пр-ль 2', 2)
        self.lst_left.addItem('Угловой пр-ль 3', 3)
        self.lst_left.setCurrentIndex(2-1)
        self.lst_right = QtGui.QComboBox(self)
        self.lst_right.addItem('Угловой пр-ль 1', 1)
        self.lst_right.addItem('Угловой пр-ль 2', 2)
        self.lst_right.addItem('Угловой пр-ль 3', 3)
        self.lst_right.setCurrentIndex(1-1)
        self.lst_mode = QtGui.QComboBox(self)
        self.lst_mode.addItem('Усреднение', LEFT | RIGHT)
        self.lst_mode.addItem('По левой рамке', LEFT)
        self.lst_mode.addItem('По правой рамке', RIGHT)
        # - частота дискретизации
        self.lst_framerate = QtGui.QComboBox(self)
        self.lst_framerate.addItem('8000 Гц (телефон)', 8000)
        self.lst_framerate.addItem('11025 Гц', 11025)
        self.lst_framerate.addItem('16000 Гц', 16000)
        self.lst_framerate.addItem('22050 Гц (радио)', 22050)
        self.lst_framerate.addItem('44100 Гц (audio CD)', 44100)
        self.lst_framerate.addItem('48000 Гц (DVD, DAT)', 48000)
        self.lst_framerate.addItem('96000 Гц (DVD-Audio (MLP 5.1))', 96000)
        self.lst_framerate.setCurrentIndex(3)
        # - глубина звучания (бит в сэмпле)
        self.lst_sampwidth = QtGui.QComboBox(self)
        self.lst_sampwidth.addItem('8 бит', 1)
        self.lst_sampwidth.addItem('16 бит', 2)
        self.lst_sampwidth.addItem('32 бит', 4)
        self.lst_sampwidth.setCurrentIndex(1)

        # Текст:
        # ------------------------------
        self.lbl_left = QtGui.QLabel('Датчик левой рамки:')
        self.lbl_left.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_right = QtGui.QLabel('Датчик правой рамки:')
        self.lbl_right.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_mode = QtGui.QLabel('Режим:')
        self.lbl_mode.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_speed = QtGui.QLabel('Множитель скорости:')
        self.lbl_speed.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_framerate = QtGui.QLabel('Частота дискретизации:')
        self.lbl_framerate.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_sampwidth = QtGui.QLabel('Глубина звучания:')
        self.lbl_sampwidth.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.progressbar = QtGui.QProgressBar(self)
        self.progressbar.setMaximum(99)
        self.progressbar.setMinimum(0)
        self.progressbar.setTextVisible(True)

        # Создать компоновочную сетку и добавить в неё элементы управления
        # ----------------------------------------------------------------
        self.grid = QtGui.QGridLayout()
        self.grid.setSpacing(10)
        # 1 линия: файл ...
        self.grid.addWidget(self.btn_file, 1, 0)
        self.grid.addWidget(self.txt_file, 1, 1, 1, 3)
        # 2 линия: датчик левой рамки
        self.grid.addWidget(self.lbl_left, 2, 0, 1, 2)
        self.grid.addWidget(self.lst_left, 2, 2, 1, 2)
        # 3 линия: датчик правой рамки
        self.grid.addWidget(self.lbl_right, 3, 0, 1, 2)
        self.grid.addWidget(self.lst_right, 3, 2, 1, 2)
        # 4 линия: режим
        self.grid.addWidget(self.lbl_mode, 4, 0, 1, 2)
        self.grid.addWidget(self.lst_mode, 4, 2, 1, 2)
        # 5 линия: калибровка!
        self.grid.addWidget(self.btn_calib, 5, 1, 1, 2)
        # 6 линия: скорость ...
        self.grid.addWidget(self.lbl_speed, 6, 0, 1, 2)
        self.grid.addWidget(self.txt_multiplier, 6, 2, 1, 2)
        # частота дискретизации
        line = 7
        self.grid.addWidget(self.lbl_framerate, line, 0, 1, 2)
        self.grid.addWidget(self.lst_framerate, line, 2, 1, 2)
        # глубина звучания
        line += 1
        self.grid.addWidget(self.lbl_sampwidth, line, 0, 1, 2)
        self.grid.addWidget(self.lst_sampwidth, line, 2, 1, 2)
        # Ползунок воспроизведения /    progress-bar
        line += 1
        self.grid.addWidget(self.progressbar, line, 0, 1, 4)
        # play pause stop save
        line += 1
        # self.grid.addWidget(self.make_or_terminate, line, 0)
        self.grid.addWidget(self.btn_abort, line, 0)
        self.grid.addWidget(self.btn_make_snd, line, 0)
        self.grid.addWidget(self.btn_save, line, 3)

        self.setLayout(self.grid)

    @property
    def telemetry(self):
        """ True если инициализирован/прочитан успешно
        """
        return self._telemetry

    @telemetry.setter
    def telemetry(self, tlm):
        self._telemetry = tlm
        if tlm:
            self.btn_calib.setEnabled(True)
            self.btn_make_snd.setEnabled(True)

    @property
    def sens_left(self):
        return self.lst_left.itemData(self.lst_left.currentIndex())

    @property
    def sens_right(self):
        return self.lst_right.itemData(self.lst_right.currentIndex())

    @property
    def mode(self):
        return self.lst_mode.itemData(self.lst_mode.currentIndex())

    @property
    def multiplier(self):
        return int(self.txt_multiplier.text())

    @property
    def framerate(self):
        return self.lst_framerate.itemData(self.lst_framerate.currentIndex())

    @property
    def sampwidth(self):
        return self.lst_sampwidth.itemData(self.lst_sampwidth.currentIndex())

    @property
    def tmp_outfile(self):
        return self._tmp_outfile

    @property
    def _str_playposition(self):
        ms = self.slider.value()
        min = int(ms/1000/60)
        sec = ms/1000-60*min
        return "{0:0=2}:{1:06.3f}".format(min, sec)

    def dlg_open(self):
        """ Открыть файл телеметрии
        """
        # Получить файлов для открытия
        filename = QtGui.QFileDialog.getOpenFileName(
            self,
            "Выберите файл телеметрии...",
            self.lastfile,
            "Text files (*.txt);;All Files (*)")
        if not filename:
            return

        try:
            self.telemetry = Telemetry(filename)
        except Exception as err:
            flags = QtGui.QMessageBox.Retry
            flags |= QtGui.QMessageBox.Cancel
            msg = "Не удалось открыть файл:\n" + str(err)
            response = QtGui.QMessageBox.warning(self, "Ошибка",
                                                 msg, flags)
            if response == QtGui.QMessageBox.Retry:
                self.dlg_open()

        if self.telemetry:
            self.txt_file.setText(filename)
            # Сохранить путь к последнему открытому файлу
            self.lastfile = os.path.dirname(filename)

        # Если открыто окно графика - обновить его
        if self.calib_window:
            if self.calib_window.isVisible():
                self.calib_window.update()

    def dlg_save(self):
        """ Открыть файл телеметрии
        """
        # Получить имя файла для сохранения
        filename = QtGui.QFileDialog.getSaveFileName(
            self,
            "Сохранить аудиофайл",
            '.',
            "WAV (*.wav)")
        # Если не указан файл - пользователь отменил сохранение
        if not filename:
            return
        # Если указан временный файл - ничего не делать
        if filename == self._tmp_outfile:
            return
        # Copy file to choosen destination
        shutil.copyfile(self._tmp_outfile, filename)

    def show_calib_window(self):
        if not self.calib_window:
            # Показать новое если не показано
            self.calib_window = CalibWindow(self)
            self.calib_window.show()
        else:
            self.calib_window.show()
            # # Перевести фокус, если показано
            # self.calib_window.activateWindow()

    def _make_sound_start(self):
        # Действия, выполняемые с началом создания аудиофайла

        # Скрыть кнопку создания аудио / показать кнопку прерывание
        self.btn_make_snd.setVisible(False)
        self.btn_abort.setVisible(True)

    def _make_sound_finished(self):
        # Действия, выполняемые по окончании потока создания аудиофайла

        # Показать кнопку создания аудио / скрыть кнопку прерывание
        self.btn_make_snd.setVisible(True)
        self.btn_abort.setVisible(False)
        # Изменить иконку и надпись     с 'создать' на 'пересоздать'
        self.btn_make_snd.setIcon(QtGui.QIcon('icons/appbar.sync.rest.png'))
        self.btn_make_snd.setToolTip('Пересоздать аудиофайл')

        # Обновить состояние кнопок управления воспроизведением
        # (в зависимости от успешности завершения потока создания)
        self._audio_btns_set_enabled(not self.make_sound_thread.isaborted)

    def _audio_btns_set_enabled(self, tf):
        # Активировать/деактивировать кнопки
        self.btn_save.setEnabled(tf)

    def set_progress(self, value):
        """ Установить текущее значение прогресса (от 0 до 100) или текстовый
        статус
        """
        if isinstance(value, int):
            # Set default percent-format
            self.progressbar.setFormat('%p %')
            self.progressbar.setValue(value)
        elif isinstance(value, str):

            self.progressbar.setFormat(value)
        else:
            raise TypeError(
                "Неожиданный тип аргумента-значения текущего прогресса")


class MakeSoundThread(QtCore.QThread):
    """ Поток создания аудиофайла из телеметрии
    """
    def __init__(self, get_tlm, get_sens_left, get_sens_right, get_mode,
                 get_multiplier, get_framerate, get_sampwidth, get_outfile):
        """ Инициализация экземпляра потока

        Поля инициализируются функциями возвращающими ....
        :param get_tlm:        ...объект телеметрии
        :param get_sens_left:  ...номер "левого" датчика
        :param get_sens_right: ...номер "правого" датчика
        :param get_mode:       ...режим расчёта. По лев.,прав, по среднему
                           {LEFT, RIGHT, LEFT | RIGHT}
        :param get_multiplier: ...скорость воспроизведения
        :param get_framerate:  ...частота фреймов ауиофайла
        :param get_sampwidth:  ...глубина звука аудиофайла
        :param get_outfile:    ...имя выходного аудиофайла
        """

        QtCore.QThread.__init__(self)
        self.get_tlm = get_tlm
        self.get_sens_left = get_sens_left
        self.get_sens_right = get_sens_right
        self.get_mode = get_mode
        self.get_multiplier = get_multiplier
        self.get_framerate = get_framerate
        self.get_sampwidth = get_sampwidth
        self.get_outfile = get_outfile
        self.isaborted = False

    def __del__(self):
        """ Уничтожение экземпляра потока

        Вызывается сборщиком мусора (например при выходе переменной, которой
        присвоена ссылка на экземпляр потока, из области видимости). Ожидает
        завершения выполнения задачи потока перед уничтожением экземпляра.
        """
        self.wait()

    def abort(self):
        # Безопасно прервать выполнение процесса
        self.exit(1)

    def exit(self, int_returnCode=0):
        # Добавлена пометка процесса прерванным,
        # если возвращаемое значение отлично от 0
        if int_returnCode != 0:
            self.isaborted = True
        QtCore.QThread.exit(self, int_returnCode)

    def run(self):
        """ Создать аудиофайл
        Запускает процесс создания аудиофайла из телеметрии
        """
        # Сбросить флаг прерывания потока
        self.isaborted = False
        # Вызвать функцию создания аудиофайла
        self.make_sound()

    def make_sound(self):

        self.emit(QtCore.SIGNAL('progress(QString)'), "Подготовка данных")
        nchannels = 1  # MONO=1; STEREO=2
        # Получить парамеры
        sens_left = self.get_sens_left()
        sens_right = self.get_sens_right()
        mode = self.get_mode()
        multiplier = self.get_multiplier()
        framerate = self.get_framerate()
        sampwidth = self.get_sampwidth()
        outfile = self.get_outfile()
        tlm = self.get_tlm()
        self.emit(QtCore.SIGNAL('progress(QString)'),
                  "Преобразование телеметрии")
        # Получить телеметрию
        times = tlm.get_tlm(TIME).copy()
        if mode == LEFT | RIGHT:
            # Среднее по правой и левой
            values = 0.5*(tlm.get_tlm(LEFT, sens_left, sens_right)
                          + tlm.get_tlm(RIGHT, sens_left, sens_right)).copy()
        else:
            values = tlm.get_tlm(mode, sens_left, sens_right).copy()

        # Максимальная громкость - максимальное число со знаком,
        # которое может быть записано в сэмпл / в заданном числе байт 0x7F...FFF
        max_vol = 2**(sampwidth*8-1)-1
        # Исключение - 8битный сэмпл, который использует беззнаковые целые числа
        if sampwidth == 1:
            max_vol = 2**8-1
            sample_fmt = struct.Struct('B')
        # 16-битный
        elif sampwidth == 2:
            sample_fmt = struct.Struct('<h')
        # 24-битный
        elif sampwidth == 3:
            raise NotImplementedError(
                'Не реализована запись 24-битовых целых со знаком')
        # 32-битный
        elif sampwidth == 4:
            sample_fmt = struct.Struct('<i')
        else:
            raise Exception(
                'Некорректная длина сэмпла: должна быть 1, 2, 3, 4 Байта')

        # Нормировать абсолютный максимум амплитуды к максимальной громкости
        values = values/np.max(np.abs(values))*max_vol
        # Привести массив времени к ускоренному виду
        # - сжав в указанное число раз
        times /= multiplier
        # Создать функцию интерполирующую амплитуду телеметрии
        # по заданному моменту времени
        # interp = np.interp(times, values)

        # Определить длительность и число фреймов
        duration = np.max(times)  # длительность в секундах (после умножения)
        nframes = int(duration*framerate)

        # Создать аудио-файл
        with wave.open(outfile, 'wb') as wav:
            # Установить параметры
            wav.setnchannels(nchannels)
            wav.setsampwidth(sampwidth)
            wav.setframerate(framerate)
            # Записать фреймы звука
            for frame in range(nframes):
                # Сигнал о текущем прогрессе
                # Подавать каждый 100-й фрейм
                if frame % 100 == 0:
                    self.emit(QtCore.SIGNAL('progress(int)'),
                              int(frame/nframes*100))
                # Прервать работу безопасно, если запрошена остановка
                if self.isaborted:
                    break
                # Момент, соответствующий текущему фрейму
                time = frame/framerate
                # Амплитуда для этого фрейма
                value = np.interp(time, times, values)
                # Если 8-битный - амплитуда от 0 до 255,
                if sampwidth == 1:
                    # отрицательные инвертировать.
                    value = np.abs(value)
                # write the audio frames to file
                wav.writeframesraw(sample_fmt.pack(int(value)))


class CalibWindow(QtGui.QDialog):
    """ Окно построения графика и калибровки
    """
    def __init__(self, parent):
        # Инициализировать:
        # - родительский класс
        QtGui.QDialog.__init__(self, parent)
        # сделать окно разворачиваемым
        self.setWindowFlags(self.windowFlags() |
                            QtCore.Qt.WindowSystemMenuHint |
                            QtCore.Qt.WindowMinMaxButtonsHint)

        # Графики
        self.ax = None
        self.tmp = None
        # Прямоуголники калибровочных интервалов
        self.tint_rects = []

        # Установить параметры окна
        # ----------------------------------------------------------
        self.resize(800, 600)
        self.setWindowTitle('Калибровка')
        self.setWindowIcon(QtGui.QIcon('icons/appbar.edit.rest.png'))

        # Заголовок списка временных интервалов
        self.lbl_tints = QtGui.QLabel('Калибровочные интервалы:')
        # Список временных интервалов
        self.tbl_tints = TintsTable(self.calib_tints)

        # Check-box'ы отображения кривых
        self.chk_left = QtGui.QCheckBox('Левая рамка')
        self.chk_left.setChecked(True)
        self.chk_left.setStyleSheet("color: red")
        self.chk_right = QtGui.QCheckBox('Правая рамка')
        self.chk_right.setChecked(True)
        self.chk_right.setStyleSheet("color: blue")
        self.chk_meta = QtGui.QCheckBox('Метки')
        self.chk_meta.setChecked(False)
        self.chk_meta.setStyleSheet("color: green")

        # Кнопки
        # - Перестроить
        self.btn_refresh = QtGui.QPushButton('Обновить', self)
        self.btn_refresh.setToolTip('Перестроить график с учётом калибровки')
        self.connect(self.btn_refresh, QtCore.SIGNAL('clicked()'), self.plot)
        # - сброс
        self.btn_reset = QtGui.QPushButton('Сброс', self)
        self.btn_reset.setToolTip('Сбросить калибровку')
        self.connect(self.btn_reset,
                     QtCore.SIGNAL('clicked()'), self.reset_calib)
        # - ок
        self.btn_ok = QtGui.QPushButton('OK', self)
        self.btn_ok.setToolTip('Принять калибровку')
        self.connect(self.btn_ok,
                     QtCore.SIGNAL('clicked()'),  QtCore.SLOT('close()'))

        # График
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumWidth(200)
        self.canvas.setMinimumHeight(200)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        # Построить график
        self.plot()

        # Соединить сигнал обновления набора временных интервалов
        # - с перерисовкой графиков
        self.connect(self.calib_tints,
                     QtCore.SIGNAL('tints_changed()'),
                     self.plot_tint_rects)
        # - с перерисовкой таблицы
        self.connect(self.calib_tints,
                     QtCore.SIGNAL('tints_changed()'),
                     self.tbl_tints.update_items)

        # Упаковать элементы интерфейса в сетку/макет
        # ---------------------------------------------------------------------
        # Строка из областей: левая группа элементов управления и график
        design = QtGui.QHBoxLayout()

        # Столбец элементов от заголовка таблицы интервалов до чекбоксов
        left_panel = QtGui.QVBoxLayout()
        # left_panel.addStretch(1)
        left_panel.addWidget(self.lbl_tints, 0, QtCore.Qt.AlignLeft)
        left_panel.addWidget(self.tbl_tints, 1)
        left_panel.addWidget(self.chk_left, 0)
        left_panel.addWidget(self.chk_right, 0)
        left_panel.addWidget(self.chk_meta, 0)

        # Строка 3-х нижних кнопок
        btns_group = QtGui.QHBoxLayout()
        # btns_group.addStretch(1)
        btns_group.addWidget(self.btn_refresh)
        btns_group.addWidget(self.btn_reset)
        btns_group.addWidget(self.btn_ok)

        # Добавить в левую группу строку кнопок
        left_panel.addLayout(btns_group, 0)

        # Поместить в главный макет левую группу элементов управления
        #  и столбец тулбар+правый график
        design.addLayout(left_panel, 0)

        right_plot = QtGui.QVBoxLayout()
        right_plot.addWidget(self.toolbar, 0)
        right_plot.addWidget(self.canvas, 1)
        design.addLayout(right_plot, 1)

        self.setLayout(design)

    @property
    def calib_tints(self):
        return self.parentWidget().telemetry.observs[CALIB]

    def reset_calib(self):
        # Очистить список калибровочных интервалов
        self.calib_tints.clear()
        # (таблица и интервалы на графике обновляются сами по сигналу из класса)
        # Обновить кривые на графике
        self.plot()

    def show(self):
        QtGui.QDialog.show(self)
        # Дополнительно обновить график
        self.update()

    def update(self, *__args):
        QtGui.QDialog.update(self, *__args)
        # Дополнительно обновить график
        self.plot()

    def plot(self):
        # Получить текущие установки соответствтия датчиков левой и правой рамки
        sens_left = self.parent().lst_left.itemData(
            self.parentWidget().lst_left.currentIndex())
        sens_right = self.parentWidget().lst_right.itemData(
            self.parentWidget().lst_right.currentIndex())

        time = self.parentWidget().telemetry.get_tlm(TIME)

        matplotlib.rcParams['font.size'] = 14
        matplotlib.rcParams['font.family'] = 'Times New Roman'
        matplotlib.rcParams["axes.grid"] = True

        if self.ax is None:
            # create an axis
            self.ax = self.figure.add_subplot(111)
            # set useblit True on gtkagg for enhanced performance
            SpanSelector(self.ax, self.new_tint, 'horizontal',
                         useblit=True,
                         rectprops=dict(alpha=0.5, facecolor='red'))

        self.ax.cla()
        self.ax.hold(True)
        # Настройка осей
        self.ax.set_xlabel('Время, с')
        self.ax.set_ylabel('Угол поворота, \xB0')
        if len(self.calib_tints) > 0:
            self.ax.axis([0, time[-1], -180, +180])
        else:
            self.ax.axis([0, time[-1], 0, 360])

        # plot telemetry data
        if self.chk_left.isChecked():
            left = self.parentWidget().telemetry.get_tlm(LEFT,
                                                         sens_left=sens_left,
                                                         sens_right=sens_right,
                                                         calib=True)
            self.ax.plot(time, left, 'r-', linewidth=2.0, label='Левая')

        if self.chk_right.isChecked():
            right = self.parentWidget().telemetry.get_tlm(RIGHT,
                                                          sens_left=sens_left,
                                                          sens_right=sens_right,
                                                          calib=True)
            self.ax.plot(time, right, 'b-', linewidth=2.0, label='Правая')

        if self.chk_meta.isChecked():
            meta = self.parentWidget().telemetry.get_tlm(META)
            self.ax.plot(time, meta, 'g-', linewidth=2.0, label='Маркер')

        # plot CALIB-tints rectangles
        self.plot_tint_rects(refresh=False)
        # make layout tight
        self.figure.tight_layout()
        # refresh canvas manually
        self.canvas.draw()

    def plot_tint_rects(self, refresh=True):
        """ Добавление на график прямоугольников временных интервалов
        Обновляет график, если не указано иное
        :param refresh: обновлять график
        :return:
        """
        # Удалить прежние прямоугольники с графика
        for rect in self.tint_rects:
            try:
                rect.remove()
            except ValueError:
                pass
            # rect.set_visible(False)
        self.tint_rects.clear()

        # Создать новые прямоугольники
        for tint in self.calib_tints:
            x = tint[0]
            y = -360
            w = tint[1] - tint[0]
            h = 720
            # add a rectangle
            rect = matplotlib.patches.Rectangle((x, y), w, h,
                                                edgecolor="g",
                                                alpha=0.5,
                                                facecolor="y")
            self.tint_rects.append(rect)
            self.ax.add_patch(rect)

        if refresh:
            # refresh canvas
            self.canvas.draw()

    def new_tint(self, xmin, xmax):
        # Вызывается в результате графического добавления временных интрвалов
        self.calib_tints.append([xmin, xmax])


class TintsTable(QtGui.QTableWidget):
    def __init__(self, tints, *args):
        QtGui.QTableWidget.__init__(self, *args)
        # Для растягивания задать
        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Начало', 'Конец'])
        self.itemChanged.connect(self._item_changed_handler)
        self._tints = tints
        self.update_items()
        # Флаг редактирования ячейки вручную.
        # Снимается на время вызова обновления таблицы update_items()
        # Таким образом update_items() изменяет таблицу, а ручное
        # редактирование сначала изменяет исходные данные, а затем
        # вызывает update_items()
        self.is_manual_edited = True

    @property
    def tints(self):
        return self._tints

    def update_items(self):
        # Пометить, что предстоящие изменения в таблице выполняются
        # не пользователем
        self.is_manual_edited = False
        self.clearContents()
        self.setRowCount(len(self.tints)+1)
        for line, tint in enumerate(self.tints):
            for col, time in enumerate(self.tints[line]):
                newitem = QtGui.QTableWidgetItem(str(time))
                self.setItem(line, col, newitem)
        self.is_manual_edited = True

    def _item_changed_handler(self, item):
        # Вызывается при любом изменении элемента в таблице
        if self.is_manual_edited:
            # Это редактирование вручную.
            # Такое редактирование должно быть произведено только в
            # источнике данных
            # Изменения в источнике данных автоматически подадут сигнал на
            # обновление табличных данных
            value_new = item.text()
            num_row = item.row()    # номер строки  - индекс наблюдения
            num_col = item.column()   # номер колонки - индекс времени
            if self.columnCount() != 2:
                raise Exception("Логика поиска соседнего значения опирается "
                                "на то, что в таблице 2 колонки. "
                                "Но в таблице не 2 колонки!")
            # Номер колонки соседней с редактируемым значением
            num_col_other = 1 - num_col

            # Проверить не было ли действие удалением числа
            try:
                value_new = float(value_new)
            except ValueError:
                # Если удалено - удалить всю строку
                self.tints.pop(num_row)
                return

            # Если соседнее значение None - это новый интервал
            value_neighbor = self.item(num_row, num_col_other)
            if value_neighbor is None:
                self.tints.append([value_new, value_new])
                return

            # Если просто отредактировали 1 из 2х чисел
            try:
                value_neighbor = float(value_neighbor.text())
            except ValueError:
                # Соседнее значение не число?
                value_neighbor = value_new
            self.tints[num_row] = [value_new, value_neighbor]

        else:
            # Это программный вызов - автообновление и др.
            # Ему не сопутствуют никакие специальные методы,
            # т.к. предполагается, что изменения уже отражены в исходном
            # массиве данных и на гарфике. Остаётся отразить их в таблице.
            pass