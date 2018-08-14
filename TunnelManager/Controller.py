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
import sys
import subprocess
import xmlrpclib
import imp
from xml.dom import minidom


from TunnelManager import PortInfo
from TunnelManager.ErrorReporter import ErrorReporter
from TunnelManager.KeyInfo import KeyInfo
from TunnelManager.TunnelInfo import TunnelInfo


class Controller(object):
    """The configuration controller."""

    def __isDirty(self):
        return self.__m_dirty
    def __setIsDirty(self,dirty):
        self.__m_dirty = dirty
    isDirty = property(__isDirty,__setIsDirty)

    def __getFilename(self):
        return self.__m_filename
    def __setFilename(self,name):
        self.__m_filename = name
    filename = property(__getFilename,__setFilename)

    def __getConfigPath(self):
        return self.__m_configpath
    configpath = property(__getConfigPath)

    def __getIpCmdPath(self):
        return self.__m_ipcmdpath
    ipcmdpath = property(__getIpCmdPath)

    def __getSshBaseArgs(self):
        return self.__m_sshbaseargs
    sshbaseargs = property(__getSshBaseArgs)

    def __isSSHAddRunning(self):
        return self.__m_sshAddRunning
    isSSHAddRunning = property(__isSSHAddRunning)

    def __getTunnelList(self):
        return self.__m_tunnelList
    tunnelList = property(__getTunnelList)

    def __getKeyList(self):
        return self.__m_keyList
    keyList = property(__getKeyList)

    def __init__(self,reporter,config,tunnelFile=None):
        """The object constructor"""
        self.errorReporter = reporter

        self.__m_filename = None
        self.__m_dirty = False
        self.__m_sshAddRunning = False

        self.__m_keyList = []
        self.__m_tunnelList = []

        self.__m_configpath = os.environ.get("HOME") + "/.TunnelManager"
        if not os.path.isdir(self.configpath):
            try:
                os.mkdir(self.configpath)
            except OSError, e:
                print >>sys.stderr, "Failed creating directory %s: %s" % (self.configpath,e.strerror)
                pass

        config.safeSet('DEFAULT','ipcmdpath', "/sbin/ip")
        self.__m_ipcmdpath = config.safeGet('BASE', 'ipcmdpath')

        config.safeSet('DEFAULT','sshbaseargs',
                [ "-N", "-t", "-x", "-o", "ExitOnForwardFailure=yes"])
        tmpstr = config.safeGet('BASE', 'sshbaseargs')
        tmplist = None
        if isinstance(tmpstr, list):
            tmplist = tmplist
        elif isinstance(tmpstr, str):
            try:
                tmplist = eval(tmpstr)
            except:
                print >>sys.stderr, "Bad 'BASE' sshbaseargs config, using DEFAULT"
        if not isinstance(tmplist, list):
            tmplist = config.safeGet('DEFAULT', 'sshbaseargs')
        self.__m_sshbaseargs = tmplist

        config.safeSet('DEFAULT','defaultFile',
                       self.configpath + "/default.xml")
        if(not tunnelFile):
            tunnelFile = config.safeGet('BASE','defaultFile')

        if(tunnelFile and os.path.exists(tunnelFile)):
            self.loadFile(tunnelFile)
        else:
            self.__m_filename = tunnelFile


    def loadFile(self,fileName):
        """Load from config file"""
        parse_result = False
        oldKeyList = self.keyList
        del self.keyList[:]
        oldTunnelList = self.tunnelList
        del self.tunnelList[:]
        try:
            xml_document = minidom.parse(fileName)
            parse_result = ((self.readKeys(xml_document)) and
                            (self.readTunnels(xml_document)))
        except IOError, (errno, strerror):
            self.errorReporter.showError(_("Error loading file: %(file)s: (%(errno)d) %(errstr)s") % { 'file':fileName, 'errno':errno, 'errstr':strerror })
        except TypeError, e:
            self.errorReporter.showError(_("Error parsing XML file: %(file)s: %(err)s") % { 'file':fileName, 'err':e })
        except AttributeError, e:
            self.errorReporter.showError(_("Error parsing XML file: %(file)s: %(err)s") % { 'file':fileName, 'err':e })
        if(not parse_result):
            self.keyList = oldKeyList
            self.tunnelList = oldTunnelList
        else:
            self.filename = fileName
            self.convertRequiredKeys()
        self.__m_dirty = False
        return parse_result


    def readKeys(self,document):
        """Read keys from XML document"""
        for node in document.documentElement.childNodes:
            if(node.nodeName == "SSHKey"):
                keyFile = node.getAttribute("filename")
                if(keyFile):
                    newKey = KeyInfo(keyFile)
                    self.keyList.append(newKey)
                else:
                    self.errorReporter.showError(_("Invalid XML: SSHKey without filename"))
                    return False
        self.updateKeysFromAgent()
        return True


    def readTunnels(self,document):
        """Read Tunnels from XML document"""
        """I don't like this one, it isn't modular enough
           so I'll have to work on that"""
        for node in document.documentElement.childNodes:
            if(node.nodeName == "Tunnel"):
                name = node.getAttribute("name")
                userid = node.getAttribute("userid")
                tunnel_host = node.getAttribute("tunnel_host")
                tunnel_port = node.getAttribute("tunnel_port")
                required_key = node.getAttribute("required_key")
                state = node.getAttribute("state")
                needsActivate = True if state == "active" else False
                newTunnel = TunnelInfo(name,
                                       userid,
                                       tunnel_host,
                                       tunnel_port,
                                       required_key,
                                       self.errorReporter,
                                       self,
                                       needsActivate)

                for pnode in node.childNodes:
                    if(pnode.nodeName == "Port"):
                        type = pnode.getAttribute("type")
                        name = pnode.getAttribute("name")
                        bind_ip = pnode.getAttribute("bind_ip")
                        local_port = pnode.getAttribute("local_port")
                        newPort = None
                        if(type in ("local","local fwd","remote","remote fwd")):
                            remote_host = pnode.getAttribute("remote_host")
                            remote_port = pnode.getAttribute("remote_port")
                            if(not local_port or
                               not remote_host or
                               not remote_port):
                                self.errorReporter.showError(
                                    _("Invalid XML: Port missing attribute(s)"))
                                return False
                            if(type in ("local","local fwd")):
                                newPort = PortInfo.ForwardPort(
                                    PortInfo.LOCAL_TYPE,
                                    name,
                                    bind_ip,
                                    local_port,
                                    remote_host,
                                    remote_port)
                            if(type in ("remote","remote fwd")):
                                newPort = PortInfo.ForwardPort(
                                    PortInfo.REMOTE_TYPE,
                                    name,
                                    bind_ip,
                                    local_port,
                                    remote_host,
                                    remote_port)
                        elif(type == "dynamic"):
                            if(not local_port):
                                self.errorReporter.showError(
                                    _("Invalid XML: Port missing attribute(s)"))
                                return False
                            newPort = PortInfo.DynamicPort(
                                name,
                                bind_ip,
                                local_port)
                        else:
                            self.errorReporter.showError(
                                _("Invalid XML: invalid/missing port type"))
                            return False
                        newTunnel.addPort(newPort)
                #Done adding ports
                self.tunnelList.append(newTunnel)

        #All Tunnel objects created successfully
        return True


    def convertRequiredKeys(self):
        """Convert required key settings from ID to filename."""
        for tunnel in self.tunnelList:
            if(tunnel.requiredKey):
                key = self.lookupKey(tunnel.requiredKey)
                if(key and tunnel.requiredKey != key.filename):
                    tunnel.requiredKey = key.filename


    def saveFile(self,fileName=None):
        """Save to config file"""
        if(not fileName):
            fileName = self.filename
        impl = minidom.getDOMImplementation()
        xml_document = impl.createDocument(None, "TunnelConfig", None)
        self.writeKeys(xml_document)
        self.writeTunnels(xml_document)

        try:
            save_file = open(fileName, 'w')
            xml_document.documentElement.writexml(save_file,
                                                  addindent="  ",
                                                  newl="\n")
            save_file.close()
        except IOError, (errno, strerror):
            self.errorReporter.showError(_("Error saving tunnel config: (%(errno)d) %(errstr)s") % { 'errno':errno, 'errstr':strerror })
            pass
        else:
            self.__m_filename = fileName
            self.__m_dirty = False


    def writeKeys(self,document):
        """Write keys to the XML document"""
        self.keyList.sort()
        for key in self.keyList:
            keyElement = document.createElement("SSHKey")
            keyElement.setAttribute("filename", key.filename)
            document.documentElement.appendChild(keyElement)


    def writeTunnels(self,document):
        """Write all the tunnels to the XML document"""
        self.tunnelList.sort()
        for tunnel in self.tunnelList:
            tunnel.write(document)


    def clear(self):
        """Clear key and tunnel lists."""
        del self.tunnelList[:]
        del self.keyList[:]
        self.__m_dirty = False
        self.__m_filename = None


    def hasActiveTunnel(self):
        """Check whether any tunnels in the list are active."""
        for tunnel in self.tunnelList:
            if(tunnel.isActive):
                return True

        return False


    def insertTunnel(self,tunnel):
        """Add a tunnel to the list."""
        self.__m_dirty = True
        self.tunnelList.append(tunnel)


    def insertKey(self,key):
        """Add a key to the list."""
        self.__m_dirty = True
        self.keyList.append(key)


    def removeTunnel(self,tunnel):
        """Remove a tunnel from the list."""
        try:
            self.tunnelList.remove(tunnel)
            self.__m_dirty = True
        except ValueError, e:
            self.errorReporter.showError(_("Error removing tunnel %(tun)s = %(err)s") % { 'tun':tunnel, 'err':e })
            pass


    def removeKey(self,key):
        """Remove a key from the list."""
        try:
            self.keyList.remove(key)
            self.__m_dirty = True
        except ValueError, e:
            self.errorReporter.showError(_("Error removing key %(key)s = %(err)s") % { 'key':key, 'err':e })
            pass


    def startTunnels(self,scheduleTunnelCleanup,autoStart=False):
        """Start all tunnels; or just the ones marked for autoStart."""
        for tunnel in self.tunnelList:
            if(not autoStart or tunnel.needsActivate()):
                tunnel.cancelActivate()
                tunnel.start(scheduleTunnelCleanup)
                self.isDirty = (not autoStart)


    def startLoadKeys(self):
        """Load all keys that aren't currently loaded."""
        sshCmd = ""
        for key in self.keyList:
            if(not key.isLoaded()):
                sshCmd += " " + key.filename
        if(sshCmd == ""):
            #No keys to load
            return None
        cmd = [ "/usr/bin/ssh-add </dev/null" + sshCmd ]
        proc = subprocess.Popen(cmd, shell=True,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        self.__m_sshAddRunning = True
        return proc


    def checkLoadKeysComplete(self,process,waitForCompletion=False):
        """Check ssh-add for completion, and cleanup if done."""
        if(not self.isSSHAddRunning):
            #Already done; no need to wait
            return False
        elif(waitForCompletion):
            process.wait()
        elif(process.poll() == None):
            #True means to continue waiting
            return True
        if(process.returncode != 0):
            print >>sys.stdout, process.stdout.read()
            print >>sys.stderr, process.stderr.read()
        else:
            self.updateKeysFromAgent()
        self.__m_sshAddRunning = False
        #False means to stop waiting
        return False


    def updateKeysFromAgent(self):
        """Keys were loaded. Update key data from the agent."""
        pipe = subprocess.Popen(["/usr/bin/ssh-add","-l"],
                                stdout=subprocess.PIPE)
        stdout = pipe.communicate()[0]
        if(pipe.returncode == 0):
            for line in stdout.splitlines():
                fields = line.split()
                key = self.lookupKey(fields[2])
                if(key):
                    key.setAttributesFromAgent(fields)


    def stopTunnels(self):
        """Stop all tunnels."""
        for tunnel in self.tunnelList:
            if(tunnel.isActive):
                tunnel.stop()


    def unloadKeys(self):
        """Unload all keys."""
        subprocess.call(["/usr/bin/ssh-add", "-D"])


    def lookupTunnel(self,name):
        """Lookup the named tunnel."""
        for tunnel in self.tunnelList:
            if(tunnel.name == name):
                return tunnel
        return None


    def lookupKey(self,term):
        """Use term to lookup the key by fingerprint, filename, or id."""
        for key in self.keyList:
            if(key.filename == term    or
               key.id == term          or
               key.fingerprint == term ):

                return key

        return None


    def defaultRouteExists(self):
        """Check whether there's a default route."""
        pipe = subprocess.Popen([self.__m_ipcmdpath,"route","show"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        stdout = pipe.communicate()[0]
        if(pipe.returncode == 0):
            for line in stdout.splitlines():
                fields = line.split()
                if(len(fields) >= 3):
                    if(fields[0] == "default" and fields[1] == "via"):
                        ret = subprocess.call(
                            self.__m_ipcmdpath + " -s route get " +
                            fields[2] + " >/dev/null 2>&1", shell=True)
                        if(ret == 0):
                            return True
                        return False
        return False
