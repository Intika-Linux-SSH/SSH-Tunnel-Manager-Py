# Copyright (c) 2008-2013 Brandon williams
#
# AUTHOR:
# Brandon Williams <opensource@subakutty.net>
#
# This file is part of TunnelManager
#
# TunnelManager is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2, as published by
# the Free Software Foundation.
#
# TunnelManager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tunnelmanager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import os
import signal
import sys
import subprocess

from TunnelManager import ErrorReporter

class KeyInfo(object):
    """This object represents an ssh key"""

    def __getFilename(self):
        return self.__m_filename
    filename = property(__getFilename)

    def __getId(self):
        return self.__m_id
    id = property(__getId)

    def __getType(self):
        return self.__m_type
    type = property(__getType)

    def __getSize(self):
        return self.__m_size
    size = property(__getSize)

    def __getFingerprint(self):
        return self.__m_fingerprint
    fingerprint = property(__getFingerprint)


    def __init__(self,filename):
        """The constructor"""
        self.__m_filename = filename
        self.__m_id = ""
        self.__m_type = ""
        self.__m_size = ""
        self.__m_fingerprint = ""

        self.readAttributesFromFile()


    def __cmp__(self,other):
        return cmp(self.id,other.id)


    def __str__(self):
        return "<key filename='%s' id='%s' type='%s' size='%s' fingerprint='%s'>" % (self.filename, self.id, self.type, self.size, self.fingerprint)


    def readAttributesFromFile(self):
        """Read attributes about key from key file"""
        proc = subprocess.Popen(["/usr/bin/ssh-keygen", "-l", "-f",
                                 self.filename], stdout=subprocess.PIPE)
        stdout = proc.communicate()[0]
        if(proc.returncode != 0):
            #Command failed! Use filename as ID.
            self.__m_id = self.filename
            return
        parts = stdout.split()
        if(len(parts) < 3):
            #Could not get enough attributes for key. Use filename as ID.
            self.__m_id = self.filename
            return

        self.__m_size = parts[0]
        self.__m_fingerprint = parts[1]
        self.__m_id = parts[2]
        if(self.id == self.filename + ".pub"):
            end = self.id.rfind(".pub")
            self.__m_id = self.id[:end]
        if(len(parts) >= 4):
            self.__m_type = parts[3]
        else:
            self.__m_type = "unknown"


    def setAttributesFromAgent(self,fields):
        """Set attributes with info read from agent."""
        if(len(fields) < 4):
            #OOPS! Ignore it.
            return
        self.__m_size = fields[0]
        self.__m_fingerprint = fields[1]
        self.__m_id = fields[2]
        self.__m_type = fields[3]


    def isLoaded(self):
        """Check whether the key is loaded"""
        proc = subprocess.Popen(["/usr/bin/ssh-add", "-l"],
                                stdout=subprocess.PIPE)
        stdout = proc.communicate()[0]
        if(proc.returncode != 0):
            #Trouble with ssh-add. Probably no agent or no keys,
            #so nothing to do here.
            return
        for line in stdout.splitlines():
            if(self.fingerprint == line.split()[1] or
               self.id == line.split()[2]):
                return True

        return False


    def getAttributes(self):
        """Get an array of attributes for the key"""
        returnList = [os.path.basename(self.filename),
                      os.path.basename(self.id),
                      self.type, self.size, self.fingerprint]
        return returnList


    def load(self):
        """Load key. If loading all, Controller.loadKeys is better."""
        cmd = [ "/usr/bin/ssh-add </dev/null " + self.filename ]
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()
        return True if proc.returncode == 0 else False
