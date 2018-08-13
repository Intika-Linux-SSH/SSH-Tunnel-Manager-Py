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


LOCAL_TYPE   = 0
REMOTE_TYPE  = 1
DYNAMIC_TYPE = 2


class PortInfo(object):
    """This object represents port forwarding information"""

    def __getType(self):
        return self.__m_type
    type = property(__getType)


    def __init__(self, type):
        """The only way to set the type is via initialization"""
        self.__m_type = type


    def isMatch(self,port):
        """Is specified port a match?"""
        if(port.type != self.type):
            return False
        return True


    def getTypeString(self):
        """Get the type to display as a string"""
        return "unknown"
            

    def getAttributes(self):
        """Get the port's attributes as a list."""
        returnList = [self.type]
        return returnList
        

    def commandString(self):
        """Returns the port in the form for a command line arg"""
        return ""


    def write(self, document, tunnelElement):
        """Write the port to the XML document"""
        return



class ForwardPort(PortInfo):
    """This is a forwarding type of port"""

    def __getName(self):
        return self.__m_name
    def __setName(self, name):
        self.__m_name = name
    name = property(__getName, __setName)

    def __getBindIP(self):
        return self.__m_bindIP
    def __setBindIP(self, bindIP):
        self.__m_bindIP = bindIP
    bindIP = property(__getBindIP, __setBindIP)

    def __getLocalPort(self):
        return self.__m_localPort
    def __setLocalPort(self, localPort):
        self.__m_localPort = localPort
    localPort = property(__getLocalPort, __setLocalPort)

    def __getRemoteHost(self):
        return self.__m_remoteHost
    def __setRemoteHost(self, remoteHost):
        self.__m_remoteHost = remoteHost
    remoteHost = property(__getRemoteHost, __setRemoteHost)

    def __getRemotePort(self):
        return self.__m_remotePort
    def __setRemotePort(self, remotePort):
        self.__m_remotePort = remotePort
    remotePort = property(__getRemotePort, __setRemotePort)


    def __init__(self, portType, name, bindIP, localPort, remoteHost, remotePort):
        """The constructor"""
        self.__m_bindIP = bindIP
        self.__m_name = name
        self.__m_localPort = localPort
        self.__m_remoteHost = remoteHost
        self.__m_remotePort = remotePort
        PortInfo.__init__(self, portType)


    def __str__(self):
        return "<port type='%s' name='%s' bind_ip='%s' local_port='%s' remote_host='%s' remote_port='%s'>" % (self.getTypeString(), self.name, self.bindIP, self.localPort, self.remoteHost, self.remotePort)


    def isMatch(self,port):
        """Is specified port a match?"""
        if(not PortInfo.isMatch(self,port)    or
           port.name != self.name             or
           port.bindIP != self.bindIP         or
           port.localPort != self.localPort   or
           port.remoteHost != self.remoteHost or
           port.remotePort != self.remotePort ):
            return False
        return True


    def commandString(self):
        """Return the command line string"""
        flag = ""
        if(self.type == LOCAL_TYPE):
            flag = "-L"
        if(self.type == REMOTE_TYPE):
            flag = "-R"
        if(self.bindIP):
            return "%s%s:%s:%s:%s" % (flag, self.bindIP, self.localPort, self.remoteHost, self.remotePort)
        else:
            return "%slocalhost:%s:%s:%s" % (flag, self.localPort, self.remoteHost, self.remotePort)


    def getTypeString(self):
        """Get the type as a string"""
        if(self.type == LOCAL_TYPE):
            return "local"
        if(self.type == REMOTE_TYPE):
            return "remote"


    def getAttributes(self):
        """Get port attributes as a list; with type as string."""
        returnList = [self.getTypeString(),
                      self.name,
                      self.bindIP,
                      self.localPort,
                      self.remoteHost,
                      self.remotePort]
        return returnList
        

    def write(self, document, tunnelElement):
        """Write the port to XML"""
        portElement = document.createElement("Port")
        portElement.setAttribute("type", self.getTypeString())
        portElement.setAttribute("name", self.name)
        portElement.setAttribute("bind_ip", self.bindIP)
        portElement.setAttribute("local_port", self.localPort)
        portElement.setAttribute("remote_host", self.remoteHost)
        portElement.setAttribute("remote_port", self.remotePort)
        tunnelElement.appendChild(portElement)


class DynamicPort(PortInfo):
    """This is a dynamic type of port"""

    def __getName(self):
        return self.__m_name
    def __setName(self, name):
        self.__m_name = name
    name = property(__getName, __setName)

    def __getBindIP(self):
        return self.__m_bindIP
    def __setBindIP(self, bindIP):
        self.__m_bindIP = bindIP
    bindIP = property(__getBindIP, __setBindIP)

    def __getLocalPort(self):
        return self.__m_localPort
    def __setLocalPort(self, localPort):
        self.__m_localPort = localPort
    localPort = property(__getLocalPort, __setLocalPort)


    def __init__(self, name, bindIP, localPort):
        """The constructor"""
        self.__m_name = name
        self.__m_bindIP = bindIP
        self.__m_localPort = localPort
        PortInfo.__init__(self, DYNAMIC_TYPE)


    def __str__(self):
        return "<port type='%s' name='%s' bind_ip='%s' local_port='%s'>" % (self.getTypeString(), self.name, self.bindIP, self.localPort)


    def isMatch(self,port):
        """Is specified port a match?"""
        if(not PortInfo.isMatch(self,port)    or
           port.name != self.name             or
           port.bindIP != self.bindIP         or
           port.localPort != self.localPort   ):
            return False
        return True


    def commandString(self):
        """Return the command line string"""
        if(self.bindIP):
            return "-D%s:%s" % (self.bindIP, self.localPort)
        else:
            return "-Dlocalhost:%s" % self.localPort


    def getTypeString(self):
        """Get the type as a string"""
        return "dynamic"


    def getAttributes(self):
        """Get port attributes as a list; with type as string."""
        returnList = [self.getTypeString(),
                      self.name,
                      self.bindIP,
                      self.localPort,
                      None,    #All port types must have the same attr count.
                      None];   #All port types must have the same attr count.
        return returnList
        

    def write(self, document, tunnelElement):
        """Write the port to XML"""
        portElement = document.createElement("Port")
        portElement.setAttribute("type", "dynamic")
        portElement.setAttribute("name", self.name)
        portElement.setAttribute("bind_ip", self.bindIP)
        portElement.setAttribute("local_port", self.localPort)
        tunnelElement.appendChild(portElement)
