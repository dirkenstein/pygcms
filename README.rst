*****
PyGCMS
*****

Graphical Control for HP 5890/5971 GC/MS System

These are now rather antique systems and the last officially compatible 
Chemstation version (G1701AA) only runs on Windows 95 with 1 specific, 
obsolete GPIB interface (HP82341)

You can install G1701BA on Win10 but it needs customising as it will not 
run 5971 or 5972 MSDs 

This software is beginning to address that gap

Known to work on Mac, Linux and Windows 

Uses control via VISA using pyvisa and optionally pyvisa-py and linux-gpib 

Supports remote running using rpyc- useful for using a Raspberry Pi as 
a GPIB-Ethernet adapter

Getting Started
***************

spec.py - Read HP/Agilent .MS files, and various manipulations
          * Integrate TIC
          * Baseline
          * Baseline and spectrum substract
          * View spectrum at time
          * Launch NIST (optionally via Wine) 

gcms.py - Control 5890/5971
         * Run method 
         * Edit Method and Tuning parameters
         * Single Scan test
         * Display Tuning peaks 
         * QuickTune (experimental)

You need the file 59XXII.BIN from G1701AA or BA in the application directory.
This is the prooprietary MSD firmware which is automatically loaded on startup  

TODO
****

Sequence support 
Logbook

Full manual tuning 

Reimplement full 5971 Autotune

Command line versions of applications

Better GC parameter setting

Reporting support

Ability to run Chemstation macro files
