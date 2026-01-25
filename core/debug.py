"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Functions:
    * memInfo
    * dumper

    Classes:
    * measureTime
"""

import psutil
import time

class measureTime():
    def __init__(self, what):
        self.last = self.start = time.time()
        self.what = what

    def passed(self, what=None):
        if what is not None:
            self.what = what
        last = time.time()
        print ("   %s: %2.5f [sum: %2.5f]" % (self.what,last-self.last, last-self.start))
        self.last = last

def memInfo():
    process = psutil.Process()
    mem = int(process.memory_info().rss / 1024)
    return "Current memory usage in kbytes: " + str(mem)

def dumper(mclass):
    text = ""
    for attr in dir(mclass):
        if not attr.startswith("_"):
            m = getattr(mclass, attr)
            if isinstance(m, int) or isinstance(m, float) or isinstance(m, str) or  isinstance(m, list):
                text += (" %s = %r\n" % (attr, m))
    return(text)

