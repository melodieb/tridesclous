Installation
=======


If your are familiar with python simply install the depency list as usual.

tridesclous works with python 3 only.



If these are your first steps in the python world you have 2 options:
  * install python and dependencies with anaconda distribution (prefered on window or OSX)
  * use python from your system (in a virtual environement) and install dependencies with standard pip (prefered on Linux Ubuntu/Debian/Mint)

Note that you are free to install Anaconda on Linux.





Case 1 : with anaconda (prefered on window or OSX)
--------------------------------------------------

Do:

  1. Download anaconda here https://www.continuum.io/downloads. Take **python 3.6**
  2. Install it in user mode (no admin password)
  3. Lanch **anaconda navigator**
  4. Go on the tab **environements**, click on **root** context menu.
  5. **Open Terminal**
  6. For the basic::
    
       conda install scipy numpy pandas scikit-learn matplotlib seaborn
     
  
  7. For GUI and running example::
  
       conda install pyqt=5 jupyter
       pip install pyqtgraph==0.10 quantities neo
     
     
  8. And finally install tridesclous from github::
  
       pip install https://github.com/tridesclous/tridesclous/archive/master.zip




Optional if you're up for a fight and you really want fast computing with OpenCL:

  1. install driver for GPU (nvidia/intel/amd), this is quite hard in some cases because you need to download some OpenCL (or cuda) toolkit.
  2. Download PyOpenCl here for windows : http://www.lfd.uci.edu/~gohlke/pythonlibs/
  3. cd C:/users/...../Downloads
  4. pip install pyopencl‑2016.2.1+cl21‑cp36‑cp36m‑win_amd64.whl
 
  

.. WARNING::

    Some user with windows report strong problems. Anaconda is hard to install and also in
    the tridesclous GUI, when a file dialog should open python surddenly crash.
    One possible reason is : on Dell computer an application **Dell Backup and Recovery**
    is installed. This application also used Qt5. For some versions (1.8.xx and maybe others)
    of **Dell Backup and Recovery** this Qt5 have bug and theses Qt5 ddl are mixed up with
    anaconda Qt5, this lead to a total mess hard to debug. So if you have a Dell, you
    should upgrade **Dell Backup and Recovery** or remove it.


Case 2 : with pip (prefered on linux)
-------------------------------------

Here I propose my method that install tridesclous with debian like dstro in an
isolateted environement with virtualenvwrapper. Every other method is also valid.

Open a terminal and do:

  1. sudo apt-get install virtualenvwrapper
  2. mkvirtualenv  tdc   --python=/usr/bin/python3.5
  3. workon tdc
  4. pip install scipy numpy pandas scikit-learn matplotlib seaborn
  5. pip install PyQt5 jupyter pyqtgraph==0.10 quantities neo
  6. pip install https://github.com/tridesclous/tridesclous/archive/master.zip


  

   

   
   
Big GPU, big dataset OpenCL, and CO.
------------------------------------

OpenCL is a language for coding parralel programs that can be run on GPU (graphical processor unit) and
also on CPU multi core.

Some heavy part of the processing chain is coded both in pure python (scipy/numpy) and OpenCL.
So, TDC can be run in any situations.
But if the dataset is too big, you can stop mining cryto-money for while and can try to run TDC on a big-fat-gleaming GPU.
You should gain some speedup.


Depending, the OS and the hardware it used to be difficult to settle correctly the OpenCL drivers (=opencl ICD).
Now, it is more easy (except on OSX, it is becoming more difficult, grrrr.)


Here the solution on linux ubuntu/debian :
   
   1. workon tdc
   2. For intel GPU: sudo apt-get install beignet
      For nvidia GPU: sudo apt-get install nvidia-opencl-XXX
   3. sudo apt-get instll opencl-headers ocl-icd-opencl-dev libclc-dev ocl-icd-libopencl1
   4. pip install pyopencl

   
If you don't have GPU but a multi core CPU you can use POCL on linux:

   sudo apt-get install pocl


Here on windows a solution:

    1. If you have nvidia or intel a a recent windows 10, then opencl driver are already installed
    2. Download PyOpenCl here for windows : http://www.lfd.uci.edu/~gohlke/pythonlibs/
    3. Take the pyopencl file that match your python
    3. cd C:/users/...../Downloads
    4. pip install pyopencl‑2018.1.1+cl12‑cp36‑cp36m‑win_amd64.whl (for instance)



   
Ephyviewer (optional)
---------------------



If you have neo 0.6 installed and want to view signals you can optionally install ephyviewer with::
    
    pip install ephyviewer


Update tridesclous
------------------

There are no official release on pypi at the moment, so you need to take the in developpement code on github.


For updating to not repeat installation of dependencies, just uninstall and reinstall::

  pip uninstall tridesclous
  pip install https://github.com/tridesclous/tridesclous/archive/master.zip

