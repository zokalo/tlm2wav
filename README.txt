Telemetry converter (tlm2wav)
==============================
Program for converting telemetric data to audiofile *.wav

Telemetric data must be stored in *.txt file, obtained from program
"SKB IS SKIF" (http://www.skbis.ru/). Data can be recorded from three angular
movement transducer "LIR": two for data registering, one - reserved.

Installation:
============
On your system must be installed:
  - python 3.X
  - PyQt4 >= 4.10.4
To install "tlm2wav" program:
  - open comand line in program directory
  - type in command line*:
        $ python setup.py install
    * the following modules will be downloaded from the internet:
       - 'matplotlib >= 1.4.3'
       - 'numpy      >= 1.9.2'
    If you have problems with modules installation, install their manually,
    using pip, easy_install or any other method.
--------------------------------------------------------------------------------
Sources includes two bat-scenarios for Windows for generatig portable EXE
version of program:
- pyinstaller_create_exe_debug.bat;
- pyinstaller_create_exe_release.bat.
Scenarios requires installed on your PC:
 - python 3.X;
 - pyinstaller python module.


********************************************************************************

Конвертер телеметрии (tlm2wav)
==============================
Программа преобразования телеметрической информации в аудиофайл *.wav

Телеметрическая информация (в формате *.txt) должна быть представлена в виде
текстовых выходных данных программы СКБ ИС СКИФ, полученных в результате
регистрации с 3-х датчиков угловых перемещений ЛИР: 2 датчика для регистрации
данных, 3-й датчик - резервный.

К программе прилагаются сценарии windows для создания portable-exe версии:
pyinstaller_create_exe_debug.bat
pyinstaller_create_exe_release.bat


Установка:
==========
Для работы программы требуется:
    - python 3.X
    - PyQt4 >= 4.10.4

Для установки самой программы tlm2wav в командной строке перейти в директорию
с дистрибутивом программы и выполнить*:
    $ python setup.py install
* при этом будут загружены из интернета остальные зависимости:
    - 'matplotlib >= 1.4.3'
    - 'numpy      >= 1.9.2'
В случае проблем с установкой этих зависимостей установите их самостоятельно,
используя pip, easy_install или иной способ установки.