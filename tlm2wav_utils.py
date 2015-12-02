#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Основные утилиты программы tlm2wav,
предназначенной для преобразования телеметрической информации в аудиофайл *.wav
Возможен запуск из командной строки (возможности в режиме командной строки
ограничены).
"""

import wave
import math
import struct
import numpy as np
import re
import sys
import os
from collections import defaultdict
from PyQt4 import QtCore

__author__ = 'Don D.S'

# Константы обозначающие режим рассчёта: по обеим рамкам / по Л / по П
LEFT = 0b0001   # значение соответствует индексу+1 в паре углов (лев, прав)
RIGHT = 0b0010  # значение соответствует индексу+1 в паре углов (лев, прав)
META = 0b0100
TIME = 0b1000

# Метка опыта для калибровке датчиков
CALIB = 'калибровка'

# Константы-индексы для временных интервалов
TI_START = 0
TI_END = 1


class TimeInterval(object):
    """ Класс представляющий интервал времени
    Имеет вид [time_start, time_end]
    """
    def __init__(self, tstart, tend=None):
        self._tstart = None
        self._tend = None
        if tend is None:
            # if tstart is [start, end]
            if hasattr(tstart, '__iter__'):
                if len(tstart) == 2:
                    tstart, tend = tstart
                else:
                    ValueError("Argument length must be 2, but length is "
                               + str(len(tstart)))
            # if tstart is single value
            else:
                tend = tstart
        self.end = tend
        self.start = tstart

    @property
    def start(self):
        return self._tstart

    @start.setter
    def start(self, value):
        self._tstart = value
        self._organize()

    @property
    def end(self):
        return self._tend

    @end.setter
    def end(self, value):
        self._tend = value
        self._organize()

    def _organize(self):
        # Расположить значения по возрастанию
        if not (self.end and self.start):
            return
        if self.end < self.start:
            self.end, self.start = self.start, self.end

    def __iter__(self):
        yield self.start
        yield self.end

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        else:
            IndexError("TimeInterval index out of range (0, 1)")

    def __setitem__(self, key, value):
        if key == 0:
            self.start = value
        elif key == 1:
            self.end = value
        else:
            IndexError("TimeInterval index out of range (0, 1)")

    def __str__(self):
        return "[{0:.3}...{1:.3}]".format(self.start, self.end)

class TimeIntervalsList(QtCore.QObject):
    """ Класс представляющий список временных интервалов

    Пример представления: [[0, 1], [5, 7], ..., [98, 100]]

    Особенностью класса является исключение взимопересечений и соприкасаний
    интервалов. Подобные интервалы объединяются.
    Интервалы упорядочиваются по возрастанию.

    При изменении интервалов подаётся сигнал 'tints_changed()'
    """
    signal_tints_changed = QtCore.SIGNAL('tints_changed()')

    def __init__(self, tints=None):
        QtCore.QObject.__init__(self)
        self._storage = []
        if tints:
            for tint in tints:
                self.append(tint)

    def ensure_tint(self, obj):
        # Make tint a TimeInterval instance
        if not isinstance(obj, TimeInterval):
            obj = TimeInterval(obj)
        return obj

    @property
    def _tints(self):
        # Used to protect variable from  overwriting.
        # (only modifications allowed)
        return self._storage

    def append(self, obj):
        self.insert(-1, obj)

    def extend(self, obj):
        if not hasattr(obj, '__iter__'):
            obj = self.ensure_tint(obj)
            self.append(obj)
            return
        for tint in obj:
            tint = self.ensure_tint(tint)
            self.append(tint)

    def remove(self, obj):
        obj = self.ensure_tint(obj)
        self._tints.remove(obj)
        # Сигнализировать об изменениях
        self.emit(self.signal_tints_changed)

    def pop(self, index):
        obj = self._tints[index]
        self.remove(obj)
        return obj

    def insert(self, index, obj):
        # Make tint a TimeInterval instance
        obj = self.ensure_tint(obj)
        self._tints.insert(index, obj)
        self._organize()

    def clear(self):
        self._tints.clear()
        # Сигнализировать об изменениях
        self.emit(self.signal_tints_changed)

    def _organize(self):
        # Устранить пересечения и соприкосновения интервалов
        # Получить копию списка
        tints_modified = self._tints.copy()
        for this in self._tints:
            for other in self._tints:
                # Проверить не пересекается ли интервал с уже имеющимся
                if other.start <= this.start <= other.end:
                    this.start = other.start
                    if other in tints_modified:
                        tints_modified.remove(other)
                if other.start <= this.end <= other.end:
                    this.end = other.end
                    if other in tints_modified:
                        tints_modified.remove(other)
                # Проверить не охватыват ли целиком уже имеющийся
                if this.start <= other.start and this.end >= other.end:
                    if other in tints_modified:
                        tints_modified.remove(other)
                # Не  соприкасается ли с имеющимся
                if this.end == other.start:
                    this.end = other.end
                    if other in tints_modified:
                        tints_modified.remove(other)
                if this.start == other.end:
                    this.start = other.start
                    if other in tints_modified:
                        tints_modified.remove(other)
            # Добавить новый интервал в список
            tints_modified.append(this)
        # Поместить новое содержимое в старый массив
        self._tints.clear()
        self._tints.extend(tints_modified)
        # Сортировать по возрастанию
        self._tints.sort(key=lambda x: x[0])
        # Сигнализировать об изменениях
        self.emit(self.signal_tints_changed)

    def __len__(self):
        return len(self._tints)

    def __iter__(self):
        for tint in self._tints:
            yield tint

    def __getitem__(self, item):
        return self._tints[item]

    def __setitem__(self, key, value):
        value = self.ensure_tint(value)
        self._tints[key] = value
        self._organize()

    def __str__(self):
        out = "Time intervals:\n"
        for tint in self._tints:
            out += str(tint)
        return out


class Telemetry(object):
    """ Класс хранит телеметрическую информацию и словарь наблюдений

    Словарь наблюдений observs формируется следующим образом:
    Ключи слеующих типов:
     - наименование наблюдения 'Регистрация данных'
     - пара углов (-45, 60)
     - спцеиальная константа обозначающее калибровку датчиков
    Значения:
     - последовательности временных интервалов в телеметрии, которые
       соответствуют обозначенным в ключах опытах.
    """
    def __init__(self, file):
        self.observs = defaultdict(TimeIntervalsList)
        self.tlm = parse_tlm_txt(file)
        if not self.__bool__():
            raise Exception('Не удалось распознать телеметрию.')

    def __bool__(self):
        return len(self.tlm[TIME]) > 0

    def get_tlm(self, param, sens_left=2, sens_right=1, calib=True, tints=None):
        """ Возвращает указанную телеметрию с учётом калибровки

        :param param:       TIME, LEFT, RIGHT или META
        :param sens_left:  номер датчика левой рамки
        :param sens_right: номер датчика правой рамки
        :param tints:   временной интрвал(ы) для которого возвращаются значения
                        телеметрии. Если не задан, то возвращается вся
                        телеметрия
        :return: np.array
        """
        inds = None
        tlm = None
        if tints:
            #  # Получить индексы телеметрии для указанных временных интервалов
            inds = self.get_inds(tints)

        if param == TIME:
            tlm = self.tlm[TIME]

        if param == META:
            tlm = self.tlm[({1, 2, 3} - {sens_right, sens_left}).pop()]

        if param == LEFT:
            tlm = self.tlm[sens_left]
        elif param == RIGHT:
            tlm = self.tlm[sens_right]

        if tlm is None:
            raise ValueError(
                'Неизвестное значение параметра param={0}'.format(param))

        if calib and (param == LEFT or param == RIGHT):
            calib = self.calib(mode=param)
            tlm_cal = tlm - calib
            inds_g = np.where(tlm_cal > 180)[0]
            tlm_cal[inds_g] = 360 - tlm_cal[inds_g]
            inds_l = np.where(tlm_cal < -180)[0]
            tlm_cal[inds_l] = 360 + tlm_cal[inds_l]
            if inds is not None:
                tlm_cal = tlm_cal[inds]
            return tlm_cal
        else:
            if inds is not None:
                tlm = tlm[inds]
            return tlm

    def get_inds(self, tints):
        """ Получить индексы значений в телеметрии,
        которые находятся внутри указанных промежутках времени
        (или в одном указанном промежутке)

        :param tints:  список промежутков времени в виде
                        [[s1, e1], [s2, e2], ...]
                       или один промежукток в виде
                        [s1, e1]
        :return:       np.array массив индексов
        """
        if (isinstance(tints[0], float) or isinstance(tints[0], int)) \
                and len(tints) == 2:
            # Имеем дело с одним промежутком [s1, e1]
            inds = np.where(
                np.logical_and(self.get_tlm(TIME) > tints[TI_START],
                               self.get_tlm(TIME) < tints[TI_END]))[0]
        else:
            # we have list of time intervals.
            inds = np.array([])
            for tint in tints:
                inds_curr_tint = np.where(np.logical_and(
                    self.get_tlm(TIME) > tint[TI_START],
                    self.get_tlm(TIME) < tint[TI_END]))[0]
                inds = np.append(inds, inds_curr_tint)
        if inds.size == 0:
            raise ValueError(
                "Нет телеметрии для указанного временного интервала \n\
                {0}".format(tints))
        return inds.astype(int)

    def calib(self, mode=LEFT | RIGHT, for_tint=None):
        """Калибровочные значения для датчиков
        получаемые интерполяцией между среднеинтегральными
        значениями в периоды калибровки

        :param mode: режим - по Л, по П или по обеим рамкам
        :param for_tint: интервалы времени, для которых необходимо вернуть калибровочные значения
        :return:     np.array-массив значений
                     или для mode=LEFT | RIGHT кортеж пары np.array-массивов вида
                     (np_array_Left, np_array_Right)
        (которые необходимо вычесть из соответствующей телеметрии для калибровки)
        """
        # Рекурсивная обработка вызова метода для обеих рамок
        if mode == LEFT | RIGHT:
            calibs_left = self.calib(LEFT)
            calibs_right = self.calib(RIGHT)
            return calibs_left, calibs_right
        # ===============================================
        # Обработка вызова для 1 из двух рамок (Л или П)
        # ===============================================
        if CALIB not in self.observs or len(self.observs[CALIB]) == 0:
            # Если калибровочных периодов нет - вернуть нули
            return np.zeros(self.get_tlm(TIME).size)
        # ---------------------------------------------------------------
        # Массивы для опорных точки интерполяции:
        # - моменты времени - середина калибровочных временных интервалов
        time_points = np.array([])
        # - соответствующие им среднеинтегральны калибровочные значения
        calib_points = np.array([])
        # Заполнить массивы опорных точек для интерполяции
        # (перебрав калибровочные временные интервалы)
        for tint in self.observs[CALIB]:
            # Внести средние опказатели временного интервала в масивы
            time_points = np.append(time_points, np.mean(tint))
            # не калиброванное среднее значение по указанной рамке mode
            # в текущем интервале времени tint
            calib_points = np.append(calib_points, self.mean(observ=CALIB, tints=tint, mode=mode, calib=False))
        # ---------------------------------------------------------------
        # Если всего одна точка:
        if calib_points.size == 1:
            # "Размножить" калибровочное смещение на все моменты времени
            if not for_tint:
                times = self.get_tlm(TIME)
            # Или только на моменты времени в заданном интервале
            else:
                times = self.get_tlm(TIME, calib=False, tints=for_tint)
            return np.ones(times.size)*calib_points[0]
        # ---------------------------------------------------------------
        # Чтобы не использовать дополнительно экстраполяцию:
        # - скопировать первую опорную точку на начало временного ряда
        if time_points[0] != 0:
            time_points = np.insert(time_points, 0, 0)
            calib_points = np.insert(calib_points, 0, calib_points[0])
        # - скопировать последнюю опорную точку в конец временного ряда
        if time_points[-1] != self.get_tlm(TIME)[-1]:
            time_points = np.append(time_points, self.get_tlm(TIME)[-1])
            calib_points = np.append(calib_points, calib_points[-1])
        # ---------------------------------------------------------------
        # Калибрующие значения на каждый момент времени
        if not for_tint:
            calibs = np.interp(self.get_tlm(TIME), time_points, calib_points)
        # Калибрующие значения на каждый момент времени в указанном временном интервале
        else:
            times = self.get_tlm(TIME, calib=False, tints=for_tint)
            calibs = np.interp(times, time_points, calib_points)
        return calibs

    def mean(self, observ, tints=None, mode=LEFT | RIGHT, calib=True):
        """ Расчитать среднее (среднеинтегральное) значение
        для заданного типа наблюдений
        (по всем наблюдениям указанного типа)

        :param observ:     тип наблюдений, являющийся ключом в словаре
        экспериментальных данных self.observs
        :param tints:      период для которого вычисляется сренеинтегральное
                           значение. Если не задан, то вычисление для всех
                           периодов наблюдения указанного типа.
        :param mode:       режим расчёта { LEFT | RIGHT }
        :param calib:      True - калибровать / False - нет
        :return:           среднее (среднеинтегральное) значение
        """
        if not tints:
            # Не указано конкретных промежутков времени - выбрать все интералы,
            # на которых осуществлялось наблюдение указанного типа observ
            tints = self.observs[observ]
        if mode == LEFT | RIGHT:
            left = self.get_tlm(param=LEFT, calib=calib, tints=tints)
            right = self.get_tlm(param=RIGHT, calib=calib, tints=tints)
            return np.mean(left), np.mean(right)
        else:
            tlm = self.get_tlm(param=mode, calib=calib, tints=tints)
            return np.mean(tlm)

    def make_sound(self,
                   param=LEFT | RIGHT,
                   multiplier=200,
                   sens_left=2,
                   sens_right=1,
                   outfile='output.wav',
                   framerate=8000,
                   sampwidth=2,
                   nchannels=1
                   ):
        """ Создать аудиофайл из телеметрии

        :param param:       телеметрия по которой генерируется аудиофайл:
                            с левой/правой рамки или усреднить левую и правую:
                            {LEFT, RIGHT, LEFT | RIGHT}
        :param multiplier:  множитель скорости воспроизведения звука по
                            телеметрии
        :param sens_left:
        :param sens_right:
        :param outfile:
        :param framerate:   Гц, фреймов в секунду:
                            ..., 8000, 11025, 16000, 22050, 44100, ...
        :param sampwidth:   Байт, длина сэмпла:
                            2B = 16 bit per sample (1, 2, 3, 4 B)
        :param nchannels:   MONO=1; STEREO=2
        :return:
        """
        # Получить телеметрию
        times = self.get_tlm(TIME).copy()
        if param == LEFT | RIGHT:
            # Среднее по правой и левой
            values = 0.5*(self.get_tlm(LEFT, sens_left, sens_right)
                          + self.get_tlm(RIGHT, sens_left, sens_right)).copy()
        else:
            values = self.get_tlm(param, sens_left, sens_right).copy()

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
        # Привести массив времени к ускоренному виду - сжав в указанное число раз
        times /= multiplier

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
                # Момент, соответствующий текущему фрейму
                time = frame/framerate
                # Амплитуда для этого фрейма
                value = np.interp(time)
                # В этом случае амплитуда от 0 до 255,
                # отрицательные инвертировать.
                if sampwidth == 1:
                    value = np.abs(value, times, values)
                # write the audio frames to file
                wav.writeframesraw(sample_fmt.pack(int(value)))
        return os.path.exists(outfile)

def read_tlm(file, mode=LEFT | RIGHT, sens_left=2, sens_right=1):
    """ Загрузить телеметрию

    :param file:  путь к txt файлу с телеметрией
    :param mode:  загрузить информацию с левой/правой рамки
                  или усреднить левую и правую:
                  {LEFT, RIGHT, LEFT | RIGHT}
    :param sens_left:   датчик, соответствующий левой рамке (1, 2, или 3)
    :param sens_right:  датчик, соответствующий правой рамке (1, 2, или 3)
    :return:      кортеж np.array-массивов вида (ВРЕМЯ, УГОЛ),
                  где 'угол' - в зависимости от значения аргумента 'mode'
    """
    tlm = parse_tlm_txt(file)
    time = tlm[TIME]
    left = tlm[sens_left]
    right = tlm[sens_right]
    if mode == LEFT:
        return time, left
    elif mode == RIGHT:
        return time, right
    elif mode == LEFT | RIGHT:
        return time, (left+right)/2.0


def make_demo():
    """ Создать тестовую аудиозапись с заданными параметрами:
    синусоиду с заданной частотой
    """

    freq = 200.0       # Гц - частота генерируемой синусоиды

    duration = 10        # длительность записи в секундах
    framerate = 80000    # Гц частота кадров 8000 11025 44100?

    nchannels = 1  # MONO = 1, STEREO = 2
    sampwidth = 2  # 2B = 16 bit per sample (1, 2, 3, 4 B)

    # Число кадров
    nframes = duration*framerate

    # Максимальная громкость - максимальное число со знаком,
    # которое может быть записано в заданном числе байт 0x7F...FFF
    max_amp = 2**(sampwidth*8-1)-1
    # Исключение - 8битный сэмпл, который использует беззнаковые целые числа
    if sampwidth == 1:
        max_amp = 2**8-1
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

    with wave.open('demo.wav', 'wb') as wav:
        wav.setnchannels(nchannels)
        wav.setsampwidth(sampwidth)
        wav.setframerate(framerate)
        for s in range(nframes):
            value = int(max_amp*math.sin(2*math.pi*freq*(s/framerate)))
            wav.writeframesraw(sample_fmt.pack(value))


def parse_tlm_txt(path_tlm):
    """ Считывание данных из *.txt файла телеметрии.
    Возвращает numpy-массивы в словаре с ключами-константами:
        TIME, 3, 2, 1

    Пример *.txt файла с телеметрией:
        Время    Угл. пр-ль 3  Угл. пр-ль 1  Угл/ пр-ль 2
        * 0      086°07´58´´   234°24´15´´   269°20´26´´
        500      086°07´58´´   227°46´06´´   274°44´45´´
        ...
    """
    re_tlm_format = re.compile(
        r"""[*]?[ ]?(?P<t>\d+)[ ]+                        # TIME VALUE [MS]
        (?P<s3d>\d{3})°(?P<s3m>\d{2})´(?P<s3s>\d{2})´´[ ]+ # SENSOR 3 [DMS] мета
        (?P<s2d>\d{3})°(?P<s2m>\d{2})´(?P<s2s>\d{2})´´[ ]+ # SENSOR 1 [DMS] лев
        (?P<s1d>\d{3})°(?P<s1m>\d{2})´(?P<s1s>\d{2})´´[ ]+ # SENSOR 2 [DMS] прав
        """, re.VERBOSE)
    # Output values
    t = []
    s3 = []
    s1 = []
    s2 = []
    with open(path_tlm, 'r', encoding='utf8') as f:
        for line in f:
            match = re_tlm_format.search(line)
            if not match:
                continue
            t.append(int(match.group('t'))/1000)
            s3.append(int(match.group('s3d'))
                      + int(match.group('s3m'))/60.0
                      + int(match.group('s3s'))/3600.0)
            s2.append(int(match.group('s2d'))
                      + int(match.group('s2m'))/60.0
                      + int(match.group('s2s'))/3600.0)
            s1.append(int(match.group('s1d'))
                      + int(match.group('s1m'))/60.0
                      + int(match.group('s1s'))/3600.0)
    return {TIME: np.array(t), 3: np.array(s3), 2: np.array(s2), 1: np.array(s1)}


def main():
    # Default arguments
    src = 'input_demo.txt'
    dst = 'output.wav'
    mode = RIGHT
    multiplier = 200
    # Get command line args
    if len(sys.argv) == 3:
        src = sys.argv[1]
        dst = sys.argv[2]
    elif len(sys.argv) == 4:
        src = sys.argv[1]
        dst = sys.argv[2]
        multiplier = int(sys.argv[3])
    elif len(sys.argv) == 5:
        src = sys.argv[1]
        dst = sys.argv[2]
        multiplier = int(sys.argv[3])
        mode = int(sys.argv[4])
    elif len(sys.argv) == 1:
        pass
    else:
        print("Wrong args. Example of using:")
        print(
            "$ python tlm2wav_utils.py source.txt destination.wav 200 [1 or 2 or 3]")
        print("\t200 - optional argument: multiplier"
              "\n\t[1 or 2 or 3] - optional arguments."
              "\n\t1 - use LEFT hand data."
              "\n\t2 - use RIGHT hand data."
              "\n\t3 - use mean value between LEFT and RIGHT hands.")
        return 0

    # Run...
    print("(!) Калибровка нулевого значения в телеметрии недоступна"
          "при работе в режиме командной строки.")
    print('Создаётся аудиофайл "{0}" из телеметрии "{1}"...'.format(src, dst))
    tlm = Telemetry(src)
    tlm.make_sound(param=mode,
                   multiplier=multiplier,
                   sens_left=2,
                   sens_right=1,
                   outfile=dst)
    print('Аудиофайл "{0}" успешно создан.'.format(dst))
    return 0


if __name__ == '__main__':
    # make_demo()
    try:
        sys.exit(main())
    except Exception:
        print(sys.exc_info()[1])
        input()