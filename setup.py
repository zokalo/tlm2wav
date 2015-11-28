from setuptools import setup, find_packages
from os.path import join, dirname

install_requires = [
    'matplotlib>=1.4.3',
    # 'PyQt4>=4.10.4',  # не устанавливается pip или easy_install!
    #  (его нельзя установить перечислив среди зависимостей здесь)
    'numpy>=1.9.2',
]

setup(
    name='tlm2wav',
    version='0.1',
    author='Don Dmitriy Sergeevich',
    author_email='dondmitriys@gmail.com',
    url='https://github.com/zokalo/tlm2wav',
    description=
        'Problem-oriented program for converting text data to audiofile',
    # список всех файлов одиночных модулей:
    py_modules=['qt_gui', 'tlm2wav'],
    # список файлов сценариев python
    scripts=['qt_main.py'],
    # список всех каталогов-модулей python (пакетов)
    packages=find_packages(),
    # список зависимостей от сторонних пакетов
    install_requires=install_requires,
    long_description=open(join(dirname(__file__), 'README.txt')).read(),
)
# ==============================================================================
# Полный перечень возможных аргументов setup():
# +py_modules - список всех файлов одиночных модулей
# +packages - список всех каталогов пакетов
# +scripts - список файлов сценариев
# +name - имя пакета
# +version - номер версии пакета
# author - кто является автором
# author_email - электронная почта автора
# maintainer - кто сопровождает пакет
# maintainer_email - электронная почта мейнтейнера
# url - сайт программы
# description - краткое описание пакета
# long_description - полное описание пакета (может ссылаться на README.txt)
# download_url - адрес, откуда можно загрузить пакет
# classifiers - список строк классификаторов


