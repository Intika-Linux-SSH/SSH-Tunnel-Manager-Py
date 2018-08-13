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

import getopt
import time
import sys

from TunnelManager import Localization
from TunnelManager import PortInfo
from TunnelManager.Controller import Controller
from TunnelManager.TunnelInfo import TunnelInfo
from TunnelManager.KeyInfo import KeyInfo
from TunnelManager.ErrorReporter import ErrorReporter
from TunnelManager.Config import Configuration


class Application(object):
    """An object class to represent the command line interface."""

    def __getExitCode(self):
        return self.__m_exitCode
    exitCode = property(__getExitCode)


    def __init__(self,args):
        """The object constructor."""
        Localization.initialize('CLI', '')

        self.__m_exitCode = 0

        if(not self.parse_opts(args)):
            return

        self.errorReporter = ErrorReporter()
        self.config = Configuration(self.properties)
        self.controller = Controller(self.errorReporter,
                                     self.config,
                                     self.readFile)

        if(self.command == "list-t"):
            self.listTunnels()
        elif(self.command == "add-t"):
            self.addTunnel()
        elif(self.command == "update-t"):
            self.updateTunnel()
        elif(self.command == "delete-t"):
            self.deleteTunnel()
        elif(self.command == "delete-p"):
            self.deletePort()
        elif(self.command == "list-k"):
            self.listKeys()
        elif(self.command == "add-k"):
            self.addKeys()
        elif(self.command == "delete-k"):
            self.deleteKeys()
        elif(self.command == "load-k"):
            self.loadKeys()
        elif(self.command == "unload-k"):
            self.controller.unloadKeys()
        else:
            print >>sys.stderr, _("Unrecognized command: %s") % self.command
            self.usage()
            self.__m_exitCode = 2


    def usage(self):
        """Output usage information"""
        print >>sys.stderr, """\
%(cmd)s: [-h] [-f %(file)s] [-P %(file)s ] -c %(command)s [%(opt)s]
\t-h|--help       -- %(help)s
\t-f|--file       -- %(conf)s
\t-P|--properties -- %(props)s
\t-c|--command    -- %(exec)s
\t-n|--name       -- %(name)s
\t-H|--host       -- %(host)s
\t-p|--port       -- %(port)s
\t-k|--key        -- %(keyid)s
\t-L|--local      -- %(local)s
\t-R|--remote     -- %(remote)s
\t-D|--dynamic    -- %(dynamic)s
\t-K|--keyfile    -- %(keyfile)s
""" % { 'cmd':sys.argv[0], 'file':_("file"), 'command':_("command"),
        'opt':_("options"), 'help':_("output this message"), 
        'conf':_("config file to load"), 'props':_("properties file to load"),
        'exec':_("command to execute"), 'name':_("tunnel name"), 
        'host':_("tunnel host"), 'port':_("tunnel port"),
        'keyid':_("key ID"), 'local':_("local port forward"), 
        'remote':_("remote port forward"), 
        'dynamic':_("dynamic SOCKS proxy port"), 
        'keyfile':_("SSH private key filename") }


    def parse_opts(self,args):
        """Parse the command line options."""
        try:
            opts, args = getopt.getopt(sys.argv[1:], 
                                       "hf:c:n:H:p:k:L:R:D:K:N:P:", [
                                               "help","file=","command=",
                                               "name=","host=","port=","key=",
                                               "local=","remote=","dynamic=",
                                               "keyfile=","newname=",
                                               "properties="])
        except getopt.GetoptError, e:
            print >>sys.stderr, str(e)
            self.usage()
            self.__m_exitCode = 2
            return False

        if(len(args) > 0):
            print >>sys.stderr, _("Extra arguments: "), args
            self.usage()
            self.__m_exitCode = 2
            return False

        self.readFile = None
        self.command = None
        self.tunnel = None
        self.newName = None
        self.tunnelHost = None
        self.tunnelPort = None
        self.requiredKey = None
        self.portList = []
        self.keyList = []
        self.properties = None

        for o,a in opts:
            if o in ("-h", "--help"):
                self.usage()
                self.__m_exitCode = 0
                return False
            elif o in ("-f", "--file"):
                self.readFile = a
            elif o in ("-c", "--command"):
                self.command = a
            elif o in ("-n", "--name"):
                self.tunnel = a
            elif o in ("-H", "--host"):
                self.tunnelHost = a
            elif o in ("-p", "--port"):
                self.tunnelPort = a
            elif o in ("-k", "--key"):
                self.requiredKey = a
            elif o in ("-L", "--local"):
                if(not self.parsePort(PortInfo.LOCAL_TYPE,a)):
                    return False
            elif o in ("-R", "--remote"):
                if(not self.parsePort(PortInfo.REMOTE_TYPE,a)):
                    return False
            elif o in ("-D", "--dynamic"):
                if(not self.parsePort(PortInfo.DYNAMIC_TYPE,a)):
                    return False
            elif o in ("-K", "--keyfile"):
                self.keyList.append(a)
            elif o in ("-N", "--newname"):
                self.newName = a
            elif o in ("-P", "--properties"):
                self.properties = a
            else:
                print >>sys.stderr, _("Unhandled option: "), o
                self.usage()
                self.__m_exitCode = 2
                return False

        if(not self.command):
            print >>sys.stderr, _("No command specified.")
            self.usage()
            self.__m_exitCode = 2
            return False

        return True


    def parsePort(self,type,arg):
        """Parse port string and add to list."""
        fields = arg.split(':')
        newPort = None
        if(type in (PortInfo.LOCAL_TYPE, PortInfo.REMOTE_TYPE)):
            if(len(fields) == 3):
                newPort = PortInfo.ForwardPort(
                    type,"","",fields[0],fields[1],fields[2])
            elif(len(fields) == 4):
                newPort = PortInfo.ForwardPort(
                    type,"",fields[0],fields[1],fields[2],fields[3])
            elif(len(fields) == 5):
                newPort = PortInfo.ForwardPort(
                    type,fields[0],fields[1],fields[2],fields[3],fields[4])
            else:
                print >>sys.stderr, _("Invalid %(type)s fwd port spec: %(opt)s") % {
                   'type':(_("local") if type == PortInfo.LOCAL_TYPE else _("remote")), 'opt':arg }
                self.__m_exitCode = 2
                self.usage()
                return False
            self.portList.append(newPort)
        else:
            if(len(fields) == 1):
                newPort = PortInfo.DynamicPort("","",fields[0])
            elif(len(fields) == 2):
                newPort = PortInfo.DynamicPort("",fields[0],fields[1])
            elif(len(fields) == 3):
                newPort = PortInfo.DynamicPort(fields[0],fields[1],fields[2])
            else:
                print >>sys.stderr, _("Invalid dynamic port spec: %s") % arg
                self.__m_exitCode = 2
                self.usage()
                return False
            self.portList.append(newPort)

        return True


    def listTunnels(self):
        """List tunnels."""
        if(self.tunnel):
            toList = self.controller.lookupTunnel(self.tunnel)
            if(toList):
                self.printTunnel(toList)
            else:
                print >>sys.stderr, _("Tunnel %s does not exist") % self.tunnel
                self.__m_exitCode = 1
        elif(len(self.controller.tunnelList) == 0):
            print >>sys.stderr, _("No Tunnels defined in %s") % self.controller.filename
        else:
            for tunnel in self.controller.tunnelList:
                self.printTunnel(tunnel)


    def printTunnel(self,tunnel):
        """Print tunnel details."""
        print tunnel
        for port in tunnel.portList:
            print "\t%s" % port


    def addTunnel(self):
        """Add tunnel."""
        if(not self.tunnel):
            print >>sys.stderr, _("No tunnel name specified.")
            self.usage()
            self.__m_exitCode = 2
            return
        elif(self.controller.lookupTunnel(self.tunnel)):
            print >>sys.stderr, _("Specified tunnel exists: %s") % self.tunnel
            self.__m_exitCode = 1
            return
        elif(not self.tunnelHost):
            print >>sys.stderr, _("No tunnel host specified for %s") % self.tunnel
            self.usage()
            self.__m_exitCode = 2
            return
        elif(len(self.portList) == 0):
            print >>sys.stderr, _("No ports specified for %s") % self.tunnel
            self.usage()
            self.__m_exitCode = 2
            return

        newTunnel = TunnelInfo(self.tunnel,self.tunnelHost,
                               self.tunnelPort if self.tunnelPort else "22",
                               self.requiredKey,self.errorReporter,
                               self.controller)
        for port in self.portList:
            newTunnel.addPort(port)

        self.controller.insertTunnel(newTunnel)
        self.controller.saveFile(self.readFile)


    def updateTunnel(self):
        """Update tunnel."""
        if(not self.tunnel):
            print >>sys.stderr, _("No tunnel name specified.")
            self.usage()
            self.__m_exitCode = 2
            return

        existingTunnel = self.controller.lookupTunnel(self.tunnel)
        if(not existingTunnel):
            print >>sys.stderr, _("Specified tunnel does not exist: %s") % self.tunnel
            self.__m_exitCode = 1
            return

        if(self.newName):
            existingTunnel.name = self.newName
        if(self.tunnelHost):
            existingTunnel.tunnelHost = self.tunnelHost
        if(self.tunnelPort):
            existingTunnel.tunnelPort = self.tunnelPort
        if(self.requiredKey):
            existingTunnel.requiredKey = self.requiredKey
        for port in self.portList:
            existingTunnel.addPort(port)

        self.controller.saveFile(self.readFile)


    def deleteTunnel(self):
        """Delete tunnel."""
        if(not self.tunnel):
            print >>sys.stderr, _("No tunnel name specified.")
            self.usage()
            self.__m_exitCode = 2
            return

        existingTunnel = self.controller.lookupTunnel(self.tunnel)
        if(not existingTunnel):
            print >>sys.stderr, _("Specified tunnel does not exist: %s") % self.tunnel
            self.__m_exitCode = 1
            return

        self.controller.removeTunnel(existingTunnel)
        self.controller.saveFile(self.readFile)


    def deletePort(self):
        """Delete port from tunnel."""
        if(not self.tunnel):
            print >>sys.stderr, _("No tunnel name specified.")
            self.usage()
            self.__m_exitCode = 2
            return

        existingTunnel = self.controller.lookupTunnel(self.tunnel)
        if(not existingTunnel):
            print >>sys.stderr, _("Specified tunnel does not exist: %s") % self.tunnel
            self.__m_exitCode = 1
            return

        for delPort in self.portList:
            foundMatch = False
            for existingPort in existingTunnel.portList:
                if(existingPort.isMatch(delPort)):
                    foundMatch = True
                    existingTunnel.removePort(existingPort)
                    break
            if(not foundMatch):
                print >>sys.stderr, _("No match for port in tunnel %(tun)s: %(port)s") % {
                    'tun':self.tunnel, 'port':delPort }
                self.__m_exitCode = 1
                return

        self.controller.saveFile(self.readFile)


    def listKeys(self):
        """List keys."""
        if(len(self.controller.keyList) == 0):
            print >>sys.stderr, _("No keys defined in %s") % self.controller.filename
        else:
            for key in self.controller.keyList:
                print key


    def addKeys(self):
        """Add keys."""
        if(len(self.keyList) == 0):
            print >>sys.stderr, _("No keys specified to add.")
            self.usage()
            self.__m_exitCode = 2
        for key in self.keyList:
            if(self.controller.lookupKey(key) != None):
                print >>sys.stderr, _("Specified key exists: %s") % key
                self.__m_errorCode = 1
                return
            newKey = KeyInfo(key)
            self.controller.insertKey(newKey)
        self.controller.saveFile(None)


    def deleteKeys(self):
        """Delete keys."""
        if(len(self.keyList) == 0):
            print >>sys.stderr, _("No keys specified to delete.")
            self.usage()
            self.__m_exitCode = 1
        for key in self.keyList:
            toDel = self.controller.lookupKey(key)
            if(not toDel):
                print >>sys.stderr, _("Specified key does not exist: %s") % key
                self.__m_exitCode = 1
                return
            self.controller.removeKey(toDel)
        self.controller.saveFile(None)


    def loadKeys(self):
        """Load all keys."""
        process = self.controller.startLoadKeys()
        self.controller.checkLoadKeysComplete(process,True)
