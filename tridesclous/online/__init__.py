"""
The Peeler have been design to do the processing chunk by chunk in mind.
So Peeler have been adapted to OnlinePeeler to be used in real time.
OnlinePeeler is a pyacq Node.

`pyacq <https://github.com/pyacq/pyacq>`_ is a system for distributed
data acquisition and stream processing. It support some device use in
electrophysiology (Blackrock, Multichannel system, Measurement computing,
National Instrument, ...). Pyacq offer the possibility to dtsribute the
computing a several machine. So it is particulary usefull in online 
spike sorting contexte because for high channel count, the use will be able
to distribute on several machines: the acquisition itself, the OnelinePeeler
and some display.


pyacq and Tridesclous do not offer a strict real real time engine but
an online engine which latency can be controlled by the chunksize.



"""
import pyacq

#test pyacq version
import distutils.version
assert distutils.version.LooseVersion(pyacq.__version__)>='0.2.0-dev'

from .onlinepeeler import OnlinePeeler
from .onlinetools import make_pyacq_device_from_buffer, make_empty_catalogue, lighter_catalogue
from .onlinetraceviewer import OnlineTraceViewer
from .onlinewindow import TdcOnlineWindow
from .onlinewaveformhistviewer import OnlineWaveformHistViewer
