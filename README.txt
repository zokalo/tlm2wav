Telemetry converter (tlm2wav)
=============================
Program for converting telemetric data to audiofile *.wav

Telemetric data must be stored in *.txt file, obtained from program
"SKB IS SKIF" (http://www.skbis.ru/). Data can be recorded from three angular
movement transducer "LIR": two for data registering, one - reserved.

To start application GUI you can use command:
$ python tlm2wav.pyw
Also you can use command-line interface:
$ python tlm2wav_utils.py

INSTALLATION
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
       - 'PyAudio >= 0.2.7-2build2'
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

LICENSE
=======
GPL v3.0 License. See the LICENSE file.