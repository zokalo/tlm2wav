#!/usr/bin/env python3
import sys
from os.path import join, dirname
from setuptools import setup, find_packages

py_version = sys.version_info[:2]
if py_version < (3, 0):
    print('tlm2wav requires Python version 3.X' +
          ' ({}.{} detected).'.format(*py_version))
    sys.exit(-1)

install_requires = [
    'matplotlib>=1.4.3',
    # 'PyQt4>=4.10.4',  # не устанавливается pip или easy_install!
    #  (его нельзя установить перечислив среди зависимостей здесь)
    'numpy>=1.9.2',
]

VERSION = '1.0'

setup(
    name='tlm2wav',
    version=VERSION,
    author='Don Dmitriy Sergeevich',
    author_email='dondmitriys@gmail.com',
    url='https://github.com/zokalo/tlm2wav',
    description=
        'Problem-oriented program for converting text data to audiofile',
    license='GPLv3.0',
    platforms='GNU/Linux, Microsoft Windows', # (Mac OS X is not tested.)
    # список всех файлов одиночных модулей:
    py_modules=['qt_gui', 'tlm2wav'],
    # список файлов сценариев python
    scripts=['tlm2wav.pyw'],
    # список всех каталогов-модулей python (пакетов)
    packages=find_packages(),
    # список зависимостей от сторонних пакетов
    install_requires=install_requires,
    long_description=open(join(dirname(__file__), 'README.txt')).read(),
)


