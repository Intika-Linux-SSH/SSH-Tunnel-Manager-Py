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


class TunnelInfo(object):
    """This object represents an ssh tunnel with one or more ports"""

    def __isActive(self):
        return self.__m_active
    isActive = property(__isActive)

    def __getName(self):
        return self.__m_name
    def __setName(self, name):
        self.__m_name = name
    name = property(__getName, __setName)

    def __getUserid(self):
        return self.__m_userid
    def __setUserid(self, userid):
        self.__m_userid = userid
    userid = property(__getUserid, __setUserid)

    def __getTunnelHost(self):
        return self.__m_tunnelHost
    def __setTunnelHost(self,tunnelHost):
        self.__m_tunnelHost = tunnelHost
    tunnelHost = property(__getTunnelHost, __setTunnelHost)

    def __getTunnelPort(self):
        return self.__m_tunnelPort
    def __setTunnelPort(self,tunnelPort):
        self.__m_tunnelPort = tunnelPort
    tunnelPort = property(__getTunnelPort,__setTunnelPort)

    def __getRequiredKey(self):
        return self.__m_requiredKey
    def __setRequiredKey(self,requiredKey):
        self.__m_requiredKey = requiredKey
    requiredKey = property(__getRequiredKey, __setRequiredKey)

    def __getPortList(self):
        return self.__m_portList
    portList = property(__getPortList)

    def __init__(self,name,userid,tunnelHost,tunnelPort,requiredKey,
                 errorReporter,controller,needsActivate=False):
        """The constructor"""
        self.__m_active = False
        self.__m_name = name
        self.__m_userid = userid
        self.__m_tunnelHost = tunnelHost
        self.__m_tunnelPort = tunnelPort
        self.__m_requiredKey = requiredKey
        self.__m_needsActivate = needsActivate

        self.__m_portList = []

        self.errorReporter = errorReporter
        self.controller = controller

        self.process = None
        self.callbackSourceID = None


    def __cmp__(self,other):
        return cmp(self.name,other.name)


    def __str__(self):
        return "<tunnel active='%s' name='%s' userid='%s' tunnelHost='%s' tunnelPort='%s' requiredKey='%s' numPorts='%d'>" % ((self.isActive or self.__m_needsActivate), self.name, self.userid, self.tunnelHost, self.tunnelPort, self.requiredKey, len(self.__m_portList))


    def needsActivate(self):
        return self.__m_needsActivate


    def cancelActivate(self):
        self.__m_needsActivate = False


    def clearPorts(self):
        """Remove all ports"""
        self.__m_portList.clear()


    def addPort(self,port):
        """Add a port"""
        self.__m_portList.append(port)


    def removePort(self,port):
        """Remove a port"""
        try:
            self.__m_portList.remove(port)
        except ValueError, e:
            self.errorReporter.showError(_("Error removing port %(port)s = %(err)s") % { 'port':port, 'err':e })
            pass


    def lookupPort(self,findPort):
        """Lookup a matching port; all fields must matching."""
        for port in self.portList:
            if(port.isMatch(findPort)):
                return port
        return None


    def getAttributes(self):
        """Get tunnel attributes as a list."""
        returnList = []
        returnList.append(self.isActive)
        returnList.append(self.name)
        returnList.append(self.userid)
        returnList.append(self.tunnelHost)
        returnList.append(self.tunnelPort)
        idToDisplay = self.requiredKey
        if(idToDisplay):
            key = self.controller.lookupKey(idToDisplay)
            if(key):
                idToDisplay = key.id
            returnList.append(os.path.basename(idToDisplay))
        else:
            returnList.append(None)
        return returnList


    def write(self,document):
        """Write tunnel definition to XML document"""
        tunnelElement = document.createElement("Tunnel")
        tunnelElement.setAttribute("name", self.name)
        tunnelElement.setAttribute("state", "active" if (self.isActive or self.__m_needsActivate) else "inactive")
        tunnelElement.setAttribute("userid", self.userid)
        tunnelElement.setAttribute("tunnel_host", self.tunnelHost)
        tunnelElement.setAttribute("tunnel_port", self.tunnelPort)
        if(self.requiredKey):
            tunnelElement.setAttribute("required_key", self.requiredKey)
        for port in self.__m_portList:
            port.write(document,tunnelElement)
        document.documentElement.appendChild(tunnelElement)


    def checkRequiredKey(self):
        """Check whether the required key is known to the ssh agent"""
        if(not self.requiredKey):
            return True

        idToCheck = self.requiredKey
        key = self.controller.lookupKey(self.requiredKey)
        if(key):
            idToCheck = key.id

        pipe = subprocess.Popen(["/usr/bin/ssh-add", "-l"],
                                stdout=subprocess.PIPE)
        stdout = pipe.communicate()[0]
        for line in stdout.splitlines():
            keyid = line.split()[2]
            if(idToCheck == keyid):
                return True

        return False


    def start(self,scheduleTunnelCleanup):
        """Start the tunnel"""
        if(self.__m_active):
            self.errorReporter.showError(_("Tunnel already active: %s") % self.name)
            return False

        key = None
        if(not self.checkRequiredKey()):
            key = self.controller.lookupKey(self.requiredKey)
            if(not key):
                self.errorReporter.showError(
                    _("Required key unknown to agent: %s") % self.requiredKey)
                return False

        binPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        cmdline = [ binPath+"/tunnelrunner", "GUI" ]
        cmdline.extend(self.controller.sshbaseargs)
        if(key):
            cmdline.append("-i%s" % key.filename)
        if(self.userid):
            cmdline.append("-l%s" % self.userid)
        for port in self.__m_portList:
            cmdline.append(port.commandString())
        cmdline.append("-p%s" % self.tunnelPort)
        cmdline.append(self.tunnelHost)

        self.process = subprocess.Popen(cmdline,
                                        stderr=subprocess.PIPE,
                                        stdout=subprocess.PIPE)
        self.__m_active = True
        scheduleTunnelCleanup(self)
        return True


    def getTunnelFD(self):
        """Get the tunnel FD for an active tunnel"""
        if(not self.__m_active or self.process == None):
            return -1
        return self.process.stdout.fileno()


    def stop(self):
        """Stop the tunnel"""
        if(not self.__m_active):
            self.errorReporter.showError(_("Tunnel already inactive: %s") % self.name)
            return False

        proc = self.process
        self.process = None
        self.__m_active = False
        if(proc and not proc.returncode):
            try:
                os.kill(proc.pid,signal.SIGINT)
                os.waitpid(proc.pid,0)
            except OSError, e:
                self.errorReporter.showError(_("Failed closing tunnel: %(name)s (%(errno)d/%(errstr)s)") % { 'name':self.name, 'errno':e.errno, 'errstr':e.strerror })
                pass
        return True
