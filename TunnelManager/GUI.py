__author__ = "Brandon Williams\n<opensource@subakutty.net>"
__version__ = "0.7.7.2"
__date__ = "Date: 2013/11/17"
__copyright__ = "Copyright (c) 2008-2013 Brandon Williams"
__license__ = "\
This program is free software; you can redistribute it and/or modify\n\
it under the terms of the GNU General Public License version 2 as\n\
published by the Free Software Foundation.\n\
\n\
This program is distributed in the hope that it will be useful,\n\
but WITHOUT ANY WARRANTY; without even the implied warranty of\n\
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n\
GNU General Public License for more details.\n\
\n\
You should have received a copy of the GNU General Public License along\n\
with this program; if not, write to the Free Software Foundation, Inc.,\n\
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA, or view\n\
the following: http://www.subakutty.net/tunnelmanager/LICENSE"


import pygtk
pygtk.require("2.0")
import os
import sys
import getopt
import gtk
import gtk.glade
import gobject
import subprocess

from TunnelManager import Localization
from TunnelManager import PortInfo
from TunnelManager.TunnelInfo import TunnelInfo
from TunnelManager.KeyInfo import KeyInfo
from TunnelManager.GtkErrorReporter import GtkErrorReporter
from TunnelManager.Controller import Controller
from TunnelManager.StatusIcon import StatusIcon
from TunnelManager.Config import Configuration


class Application(object):
    """A class to represent the TunnelManager GUI"""

    def __init__(self,args):
        """The object constructor"""
        Localization.initialize('GUI','/usr/share/locale/')

        (configFile,autoStart,paramFile,gladePath) = self.parse_opts(args)

        self.initializeConfiguration(paramFile)
        self.errorReporter = GtkErrorReporter()
        self.controller = Controller(self.errorReporter, self.config, configFile)
        self.doAutoStart(autoStart)
        self.uiFile = gladePath + "/tunnelmanager.ui"

        self.filter = gtk.FileFilter()
        self.filter.set_name(_("XML files"))
        self.filter.add_pattern("*.xml")

        self.quit_on_destroy = False
        self.in_focus = False

        self.mainWindow = None
        self.statusIcon = StatusIcon(self)
        if(not self.config.safeGetBoolean('GUI','showIcon')):
            self.buildWindow()
        elif(not(self.config.safeGetBoolean('GUI','minToTray') and
            self.config.safeGetBoolean('GUI','launchInTray'))):
            self.buildWindow()
            self.statusIcon.enable()
        else:
            self.statusIcon.enable()


    def buildWindow(self):
        """Build the GUI window"""
        self.widgetTree = gtk.Builder()
        self.widgetTree.add_objects_from_file(self.uiFile, ["MainWindow","uimanager1"])
        self.widgetTree.connect_signals(self)
        self.mainWindow = self.widgetTree.get_object("MainWindow")
        self.mainWindow.set_focus(None)
        self.yesPixbuf = self.mainWindow.render_icon(gtk.STOCK_YES,gtk.ICON_SIZE_MENU)
        self.noPixbuf  = self.mainWindow.render_icon(gtk.STOCK_NO,gtk.ICON_SIZE_MENU)
        self.initializeTunnelView()
        self.loadTunnelView()
        self.setTitleFromFilename(self.controller.filename)
        self.mainWindow.show()


    def destroyWindow(self):
        """Destroy the GUI window"""
        self.mainWindow.destroy()
        self.mainWindow = None
        self.statusIcon.reloadMenu()


    def usage(self):
        """Output usage information"""
        print >>sys.stderr, """\
%(prog)s: [-h] [-a] [-f %(file)s] [-P %(file)s] [-g %(dir)s]
\t-h|--help       -- %(help)s
\t-a|--autostart  -- %(restore)s
\t-f|--file       -- %(conf)s
\t-P|--properties -- %(props)s
\t-g|--gladepath  -- %(glade)s
""" % { 'prog':sys.argv[0], 'file':_("file"), 'dir':_("directory"),
        'help':_("output this message"), 'restore':_("restore tunnel state"),
        'conf':_("config file to load"), 'props':_("properties file to load"),
        'glade':_("alternate glade file location") }


    def parse_opts(self,args):
        """Parse the commandline options."""
        try:
            opts, args = getopt.getopt(sys.argv[1:],
                                       "hag:f:P:",
                                       ["help","autostart",
                                        "gladepath=","file=","properties="])
        except getopt.GetoptError, e:
            print >>sys.stderr, e.strerror
            self.usage()
            sys.exit(2)

        paramFile = None
        configFile = None
        autoStart = None
        gladePath = "/usr/share/tunnelmanager"

        for o,a in opts:
            if o in ("-h", "--help"):
                self.usage()
                sys.exit()
            elif o in ("-a", "--autostart"):
                autoStart = True
            elif o in ("-f", "--file"):
                configFile = a
            elif o in ("-g", "--gladepath"):
                gladePath = a
            elif o in ("-P","--properties"):
                paramFile = a
            else:
                print >>sys.stderr, _("Unhandled option: "), o
                self.usage()
                sys.exit(2)

        if(len(args) > 0):
            print >>sys.stderr, _("Extra arguments: "), args
            self.usage()
            sys.exit(2)

        return (configFile,autoStart,paramFile,gladePath)


    def initializeConfiguration(self,paramFile):
        """Initialize the configuration object and default settings."""
        self.config = Configuration(paramFile)
        self.config.safeSet('DEFAULT','autoSave',"%s" % True)
        self.config.safeSet('DEFAULT','restoreState',"%s" % True)
        self.config.safeSet('DEFAULT','loadkeys',"%s" % True)
        self.config.safeSet('DEFAULT','showIcon',"%s" % True)
        self.config.safeSet('DEFAULT','minToTray',"%s" % True)
        self.config.safeSet('DEFAULT','launchInTray',"%s" % False)


    def doAutoStart(self,autoStart):
        """Handle operations required at autostart."""
        if(not autoStart):
            #First, get setting from config file, if not give by command line
            autoStart = self.config.safeGetBoolean('GUI','restoreState')
        if(not autoStart):
            #Not enabled in config file, either.
            for tunnel in self.controller.tunnelList:
                if tunnel.needsActivate():
                    tunnel.cancelActivate()
        if(self.config.safeGetBoolean('GUI','loadKeys')):
            self.on_load_keys(None)
            gobject.timeout_add(100,self.waitForAutoLoad)
        elif(autoStart):
            self.controller.startTunnels(self.scheduleTunnelCleanup,True)
            if(self.mainWindow != None):
                self.loadTunnelView()
            if(self.statusIcon.is_enabled()):
                self.statusIcon.reloadMenu()


    def setTitleFromFilename(self,fileName):
        """Set the title of the main window"""
        if(not self.mainWindow):
            return
        title = _("SSH Tunnel Manager - ")
        if(fileName):
            title = title + os.path.basename(fileName)
        else:
            title = title + _("Untitled")
        self.mainWindow.set_title(title)


    def initializeTunnelView(self):
        """Initialize the columns in the tunnel view"""
        self.tunnelView = self.widgetTree.get_object("tunnelView")
        self.addPixbufColumn(self.tunnelView, _("State"), 1)
        self.addTextColumn(self.tunnelView, _("Name"), 2)
        self.addTextColumn(self.tunnelView, _("User ID"), 3)
        self.addTextColumn(self.tunnelView, _("Tunnel Host"), 4)
        self.addTextColumn(self.tunnelView, _("Tunnel Port"), 5)
        self.addTextColumn(self.tunnelView, _("Required Key"), 6)
        self.addTextColumn(self.tunnelView, _("Type"), 7)
        self.addTextColumn(self.tunnelView, _("Name"), 8)
        self.addTextColumn(self.tunnelView, _("Bind IP"), 9)
        self.addTextColumn(self.tunnelView, _("Local Port"), 10)
        self.addTextColumn(self.tunnelView, _("Remote Host"), 11)
        self.addTextColumn(self.tunnelView, _("Remote Port"), 12)
        self.tunnelList = gtk.TreeStore(gobject.TYPE_PYOBJECT,
                                        gtk.gdk.Pixbuf,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING)
        self.tunnelView.set_model(self.tunnelList)


    def initializePortView(self, portView):
        """Initialize the columns in the port view"""
        self.addTextColumn(portView, _("Type"), 1)
        self.addTextColumn(portView, _("Name"), 2)
        self.addTextColumn(portView, _("Bind IP"), 3)
        self.addTextColumn(portView, _("Local Port"), 4)
        self.addTextColumn(portView, _("Remote Host"), 5)
        self.addTextColumn(portView, _("Remote Port"), 6)
        self.portList = gtk.ListStore(gobject.TYPE_PYOBJECT,
                                      gobject.TYPE_STRING,
                                      gobject.TYPE_STRING,
                                      gobject.TYPE_STRING,
                                      gobject.TYPE_STRING,
                                      gobject.TYPE_STRING,
                                      gobject.TYPE_STRING)
        portView.set_model(self.portList)


    def initializeKeyView(self, keyView):
        """Initialize the columns in the key view"""
        self.addTextColumn(keyView, _("File Name"), 1)
        self.addTextColumn(keyView, _("ID"), 2)
        self.addTextColumn(keyView, _("Type"), 3)
        self.addTextColumn(keyView, _("Size"), 4)
        self.addTextColumn(keyView, _("Fingerprint"), 5)
        self.keyList = gtk.ListStore(gobject.TYPE_PYOBJECT,
                                     gobject.TYPE_STRING,
                                     gobject.TYPE_STRING,
                                     gobject.TYPE_STRING,
                                     gobject.TYPE_STRING,
                                     gobject.TYPE_STRING)
        keyView.set_model(self.keyList)


    def addTextColumn(self, treeView, title, columnId):
        """Add a text column to tree view"""
        cellRenderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(title, cellRenderer, text=columnId)
        column.set_sort_column_id(columnId)
        treeView.append_column(column)


    def addPixbufColumn(self, treeView, title, columnId):
        """Add a pixbuf column to tree view"""
        cellRenderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(title, cellRenderer, pixbuf=columnId)
        column.set_sort_column_id(columnId)
        treeView.append_column(column)


    def loadKeyView(self):
        """Load key view from config controller."""
        self.keyList.clear()
        for key in self.controller.keyList:
            attributes = [ key ]
            attributes.extend(key.getAttributes())
            self.keyList.append(attributes)


    def loadTunnelView(self):
        """Load tunnel view from config controller."""
        self.tunnelList.clear()
        for tunnel in self.controller.tunnelList:
            self.addTunnelToTunnelView(tunnel,self.tunnelList)


    def updateTunnel(self,tunnel):
        """Update the tunnel in the tunnel view."""
        if(self.mainWindow != None):
            iter = self.tunnelList.get_iter_root()
            while iter:
                obj = self.tunnelList.get_value(iter, 0)
                if(tunnel.name == obj.name):
                    self.addTunnelToTunnelView(tunnel,self.tunnelList,iter)
                    break
                iter = self.tunnelList.iter_next(iter)
        if(self.statusIcon.is_enabled()):
            self.statusIcon.reloadMenu()


    def addTunnelToTunnelView(self,tunnel,list,iter=None):
        """Add/Update tunnel and all ports to list."""
        tunnelViewList = [ tunnel ]
        attrs = tunnel.getAttributes()
        if(attrs[0]):
            tunnelViewList.append(self.yesPixbuf)
        else:
            tunnelViewList.append(self.noPixbuf)
        tunnelViewList.extend(attrs[1:])
        #Pad to fill columns occupied by port information.
        tunnelViewList.extend([None,None,None,None,None,None])
        parent = None
        if(iter):
            #Update; remove and insert back into same position
            parent = list.insert_before(None, iter, tunnelViewList)
            list.remove(iter)
        else:
            parent = list.append(None, tunnelViewList)
        for port in tunnel.portList:
            self.addPortToTunnelView(port,list,parent)


    def addPortToTunnelView(self,port,list,parent):
        """Add port to tunnel view."""
        tunnelViewList = [ port ]
        #Pad to fill columns occupied by tunnel information.
        tunnelViewList.extend([None,None,None,None,None,None])
        tunnelViewList.extend(port.getAttributes())
        list.append(parent,tunnelViewList)


    def addPortToPortView(self,port,list):
        """Add port to port view."""
        portViewList = [ port ]
        portViewList.extend(port.getAttributes())
        list.append(portViewList)


    def confirmQuit(self):
        """Ask for confirmation if there are active tunnels."""
        if(self.controller.hasActiveTunnel()):
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,
                                       message_format=_("Tunnel(s) Active. Really quit?"),
                                       buttons=gtk.BUTTONS_OK_CANCEL)
            response = dialog.run()
            dialog.destroy()
            if(response == gtk.RESPONSE_CANCEL):
                return False
        return True


    def on_quit(self,widget):
        """Handle explicit quit from menu"""
        if(self.confirmQuit()):
            if(self.mainWindow != None):
                self.quit_on_destroy = True
                self.destroyWindow()
            else:
                if(self.config.safeGetBoolean('GUI','autoSave') and
                   self.controller.isDirty):
                    self.on_save(None)
                self.controller.stopTunnels()
                gtk.main_quit()


    def on_MainWindow_delete_event(self,widget,event):
        """Handle main window close button click"""
        if(self.config.safeGetBoolean('GUI','showIcon') and
           self.config.safeGetBoolean('GUI','minToTray')):
            self.destroyWindow()
        elif(self.confirmQuit()):
            self.quit_on_destroy = True
            self.destroyWindow()
        else:
            return True


    def on_MainWindow_destroy(self,widget):
        """Handle object destroy for application window"""
        if(self.quit_on_destroy == False):
            return True
        if(self.config.safeGetBoolean('GUI','autoSave') and
           self.controller.isDirty):
            self.on_save(None)
        self.controller.stopTunnels()
        gtk.main_quit()


    def on_MainWindow_window_state_event(self,widget,event):
        """Hide window when minimized with visible system tray."""
        if((event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED) and
           (event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED) and
           self.config.safeGetBoolean('GUI','showIcon') and
           self.config.safeGetBoolean('GUI','minToTray') and
           self.statusIcon.is_enabled()):
            self.destroyWindow()


    def on_MainWindow_focus_change_event(self,widget,event):
        """Track visibility state for status icon clicks."""
        if(event.in_):
            self.in_focus = True
        else:
            self.in_focus = False
        return False


    def on_new(self,widget):
        """Handle File|New"""
        if(self.controller.hasActiveTunnel()):
            self.errorReporter.showError(_("Tunnel(s) Active. Stop before clearing config"))
            return
        self.controller.clear()
        self.tunnelList.clear()
        self.keyList.clear()
        self.setTitleFromFilename(self.controller.filename)
        if(self.statusIcon.is_enabled()):
            self.statusIcon.reloadMenu()


    def on_open(self,widget):
        """Handle File|Open"""
        if(self.controller.hasActiveTunnel()):
            self.errorReporter.showError(_("Tunnel(s) Active. Stop before clearing config"))
            return
        start_dir = self.controller.configpath
        if(self.controller.filename):
            start_dir = os.path.dirname(os.path.realpath(self.controller.filename))
        if not os.path.isdir(start_dir):
            start_dir = None
        newFile = self.selectFile(gtk.FILE_CHOOSER_ACTION_OPEN,
                                  [self.filter],
                                  base_directory=start_dir,
                                  file_name=self.controller.filename,
                                  file_extension=".xml")
        if newFile:
            self.controller.loadFile(newFile)
            self.loadTunnelView()
            self.setTitleFromFilename(self.controller.filename)
            if(self.statusIcon.is_enabled()):
                self.statusIcon.reloadMenu()


    def on_save(self,widget):
        """Handle File|Save"""
        if(self.controller.filename):
            self.controller.saveFile()
            self.setTitleFromFilename(self.controller.filename)
        else:
            self.on_save_as(widget)


    def on_save_as(self,widget):
        """Handle File|Save As"""
        start_dir = self.controller.configpath
        if(self.controller.filename):
            start_dir = os.path.dirname(os.path.realpath(self.controller.filename))
        if not os.path.isdir(start_dir):
            start_dir = None
        newFile = self.selectFile(gtk.FILE_CHOOSER_ACTION_SAVE,
                                  [self.filter],
                                  base_directory=start_dir,
                                  file_name=self.controller.filename,
                                  file_extension=".xml")
        if newFile:
            self.controller.saveFile(newFile)
            self.setTitleFromFilename(newFile)


    def on_add_tunnel(self,widget):
        """Handle Tunnel|Add"""
        self.runTunnelDialog(widget)


    def on_edit_tunnel(self,widget):
        """Handle Tunnel|Edit"""
        selection = self.tunnelView.get_selection()
        model,selected = selection.get_selected()
        if(selected):
            tunnel = model.get_value(selected,0)
            if(tunnel.isActive):
                self.errorReporter.showError(_("Tunnel %s is active. Stop to edit.") % tunnel.name)
                return
            self.runTunnelDialog(widget,selected)


    def runTunnelDialog(self,widget,oldTunnel=None):
        """Show the tunnel dialog: eventually needs to fill in port view"""
        self.tunnelTree = gtk.Builder()
        self.tunnelTree.add_objects_from_file(self.uiFile, ["tunnelDialog"])
        self.tunnelTree.connect_signals(self)
        tunnelDialog = self.tunnelTree.get_object("tunnelDialog")
        self.portView = self.tunnelTree.get_object("portView")
        self.initializePortView(self.portView)

        nameEntry = self.tunnelTree.get_object("nameEntry1")
        userIDEntry = self.tunnelTree.get_object("userIDEntry")
        tunnelHostEntry = self.tunnelTree.get_object("tunnelHostEntry")
        tunnelPortEntry = self.tunnelTree.get_object("tunnelPortEntry")
        keyEntry = self.tunnelTree.get_object("keyEntry")

        selectedKey = None
        oldTunnelObject = None
        if(oldTunnel):
            oldTunnelObject = self.tunnelList.get_value(oldTunnel,0)
            nameEntry.set_text(oldTunnelObject.name)
            userIDEntry.set_text(oldTunnelObject.userid)
            tunnelHostEntry.set_text(oldTunnelObject.tunnelHost)
            tunnelPortEntry.set_text(oldTunnelObject.tunnelPort)
            selectedKey = oldTunnelObject.requiredKey
            for port in oldTunnelObject.portList:
                self.addPortToPortView(port,self.portList)

        currentIndex =  0
        selectedIndex = 0
        keyList = gtk.ListStore(gobject.TYPE_STRING)
        keyList.append([None])
        for key in self.controller.keyList:
            currentIndex = currentIndex + 1
            displayKey = os.path.basename(key.id)
            if(key.id != key.filename):
                displayKey = os.path.basename(key.filename) + " (" + displayKey + ")"
            keyList.append([displayKey])
            if(selectedKey and selectedKey in (key.id,key.filename)):
                selectedIndex = currentIndex
        if(selectedKey and selectedIndex == 0):
            keyList.append([selectedKey])
            selectedIndex = currentIndex + 1
        keyEntry.set_model(keyList)
        keyEntry.set_active(selectedIndex)
        cell = gtk.CellRendererText()
        keyEntry.pack_start(cell, True)
        keyEntry.add_attribute(cell, "text", 0)

        result = tunnelDialog.run()

        newTunnel = None
        if(result == gtk.RESPONSE_OK):
            selectedIndex = keyEntry.get_active()
            if(selectedIndex > 0):
                if(selectedIndex <= len(self.controller.keyList)):
                    selectedKey = self.controller.keyList[(selectedIndex - 1)].filename
                #else, leave selectedKey alone. It must not have changed.
            else:
                selectedKey = None

            newTunnel = TunnelInfo(nameEntry.get_text(),
                                   userIDEntry.get_text(),
                                   tunnelHostEntry.get_text(),
                                   tunnelPortEntry.get_text(),
                                   selectedKey,
                                   self.errorReporter,
                                   self.controller)
            port = self.portList.get_iter_root()
            while(port):
                newTunnel.addPort(self.portList.get_value(port,0))
                port = self.portList.iter_next(port)
            if(oldTunnelObject):
                self.controller.removeTunnel(oldTunnelObject)
            self.addTunnelToTunnelView(newTunnel,self.tunnelList,oldTunnel)
            self.controller.insertTunnel(newTunnel)
            self.controller.isDirty = True
            if(self.statusIcon.is_enabled()):
                self.statusIcon.reloadMenu()

        tunnelDialog.destroy()


    def on_tunnelDialog_response(self,widget,response):
        """Validate the tunnel dialog."""
        if(response != gtk.RESPONSE_OK):
            return False

        nameEntry = self.tunnelTree.get_object("nameEntry1")
        tunnelHostEntry = self.tunnelTree.get_object("tunnelHostEntry")
        tunnelPortEntry = self.tunnelTree.get_object("tunnelPortEntry")

        invalid = False
        if(not nameEntry.get_text()):
            self.errorReporter.showError(_("The 'Name' field is required"))
            invalid = True
        elif(not tunnelHostEntry.get_text()):
            self.errorReporter.showError(_("The 'Tunnel Host' field is required"))
            invalid = True
        elif(not tunnelPortEntry.get_text()):
            self.errorReporter.showError(_("The 'Tunnel Port' field is required"))
            invalid = True
        elif(not self.portList.get_iter_first()):
            self.errorReporter.showError(_("Specify a port to tunnel."))
            invalid = True
        else:
            try:
                tunnelPort = int(tunnelPortEntry.get_text())
            except ValueError:
                self.errorReporter.showError(_("Invalid 'Tunnel Port': %s") %
                                             tunnelPortEntry.get_text())
                invalid = True
            else:
                if(tunnelPort < 1 or tunnelPort > 65535):
                    self.errorReporter.showError(_("'Tunnel Port' out of range: %d") % tunnelPort)
                    invalid = True

        if(invalid):
            widget.emit_stop_by_name("response")
        return invalid


    def on_cursor_changed(self,widget):
        """Called when the selection changes in the tunnel view"""
        selection = self.tunnelView.get_selection()
        model,selected = selection.get_selected()
        if(selected and model.iter_depth(selected) != 0):
            parent = model.iter_parent(selected)
            selection.select_iter(parent)


    def on_row_activated(self,widget,path,column):
        """Called when a row is double-clicked in the tunnel view"""
        selection = self.tunnelView.get_selection()
        model,selected = selection.get_selected()
        if(selected and model.iter_depth(selected) == 0):
            tunnel = model.get_value(selected,0)
            if(tunnel.isActive):
                if(tunnel.stop()):
                    self.controller.isDirty = True
                    self.addTunnelToTunnelView(tunnel,model,selected)
            else:
                if(tunnel.start(self.scheduleTunnelCleanup)):
                    self.controller.isDirty = True
                    self.addTunnelToTunnelView(tunnel,model,selected)
            if(self.statusIcon.is_enabled()):
                self.statusIcon.reloadMenu()


    def on_tunnelView_button_press_event(self,widget,event):
        """Display context sensitive popup menu."""
        if(event.button == 3):
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = self.tunnelView.get_path_at_pos(x,y)
            if(pthinfo != None):
                path, col, cellx, celly = pthinfo
                self.tunnelView.grab_focus()
                self.tunnelView.set_cursor(path,col,0)
                self.show_tunnel_popup(event.button,time)
            return True


    def show_tunnel_popup(self,button,time):
        """Show a context-sensitive popup menu for a tunnel."""
        selection = self.tunnelView.get_selection()
        model,selected = selection.get_selected()
        if(selected and model.iter_depth(selected) == 0):
            tunnel = model.get_value(selected,0)
            menu = gtk.Menu()
            if(tunnel.isActive):
                self.addToMenu(
                    menu,_("Stop Tunnel"),self.stopTunnel,tunnel)
            else:
                self.addToMenu(
                    menu,_("Start Tunnel"),self.startTunnel,tunnel)
                self.addToMenu(
                    menu,_("Edit Tunnel"),self.on_edit_tunnel)
                self.addToMenu(
                    menu,_("Remove Tunnel"),self.on_remove_tunnel)
            menu.popup(None, None, None, button, time)


    def addToMenu(self,menu,label,handler,data=None):
        """Add item to tunnel context menu."""
        item = gtk.MenuItem(label)
        if(handler):
            if(data):
                item.connect('activate',handler,data)
            else:
                item.connect('activate',handler)
        menu.append(item)
        item.show()
        return item


    def startTunnel(self,widget,tunnel):
        """Start tunnel and update GUI."""
        if(not tunnel.isActive):
            if(tunnel.start(self.scheduleTunnelCleanup)):
                self.controller.isDirty = True
                if(self.mainWindow != None):
                    self.updateTunnel(tunnel)
                if(self.statusIcon.is_enabled()):
                    self.statusIcon.reloadMenu()


    def stopTunnel(self,widget,tunnel):
        """Stop tunnel and update GUI."""
        if(tunnel.isActive):
            if(tunnel.stop()):
                self.controller.isDirty = True
                if(self.mainWindow != None):
                    self.updateTunnel(tunnel)
                if(self.statusIcon.is_enabled()):
                    self.statusIcon.reloadMenu()


    def on_remove_tunnel(self,widget):
        """Handle Tunnel|Remove"""
        selection = self.tunnelView.get_selection()
        model,selected = selection.get_selected()
        if(selected):
            tunnel = model.get_value(selected,0)
            if(tunnel.isActive):
                self.errorReporter.showError(_("Tunnel %s is active. Stop to remove.") % tunnel.name)
                return
            model.remove(selected)
            self.controller.removeTunnel(tunnel)
            self.controller.isDirty = True
            if(self.statusIcon.is_enabled()):
                self.statusIcon.reloadMenu()


    def on_start_tunnel(self,widget):
        """Handle Tunnel|Start"""
        selection = self.tunnelView.get_selection()
        model,selected = selection.get_selected()
        if(selected):
            tunnelObject = model.get_value(selected, 0)
            if(tunnelObject.start(self.scheduleTunnelCleanup)):
                self.controller.isDirty = True
                self.addTunnelToTunnelView(tunnelObject,model,selected)
                if(self.statusIcon.is_enabled()):
                    self.statusIcon.reloadMenu()


    def on_stop_tunnel(self,widget):
        """Handle Tunnel|Stop"""
        selection = self.tunnelView.get_selection()
        model,selected = selection.get_selected()
        if(selected):
            tunnelObject = model.get_value(selected, 0)
            if(tunnelObject.stop()):
                self.controller.isDirty = True
                self.addTunnelToTunnelView(tunnelObject,model,selected)
                if(self.statusIcon.is_enabled()):
                    self.statusIcon.reloadMenu()


    def on_about(self,widget):
        """Handle Help|About"""
        aboutDialog = gtk.AboutDialog()
        aboutDialog.set_name("tunnelmanager")
        aboutDialog.set_authors([__author__])
        aboutDialog.set_version(__version__)
        aboutDialog.set_copyright(__copyright__)
        aboutDialog.set_license(__license__)
        aboutDialog.run()
        aboutDialog.destroy()


    def on_add_port(self,widget):
        """Handle Tunnel Info|Add Port button click"""
        self.portTree = gtk.Builder()
        self.portTree.add_objects_from_file(self.uiFile, ["portDialog"])
        self.portTree.connect_signals(self)
        portDialog = self.portTree.get_object("portDialog")
        typeEntry = self.portTree.get_object("typeEntry")
        typeList = gtk.ListStore(gobject.TYPE_STRING)
        typeList.append([_("Local")])
        typeList.append([_("Remote")])
        typeList.append([_("Dynamic")])
        typeEntry.set_model(typeList)
        typeEntry.set_active(0)
        cell = gtk.CellRendererText()
        typeEntry.pack_start(cell, True)
        typeEntry.add_attribute(cell, "text", 0)
        result = portDialog.run()
        if(result == gtk.RESPONSE_OK):
            #User clicked 'OK' in port dialog: apply preferences"
            newPort = None
            nameEntry = self.portTree.get_object("nameEntry2")
            bindIPEntry = self.portTree.get_object("bindIPEntry")
            localPortEntry = self.portTree.get_object("localPortEntry")
            if(typeEntry.get_active() == PortInfo.LOCAL_TYPE or
               typeEntry.get_active() == PortInfo.REMOTE_TYPE):
                remoteHostEntry = self.portTree.get_object("remoteHostEntry")
                remotePortEntry = self.portTree.get_object("remotePortEntry")
                newPort = PortInfo.ForwardPort(typeEntry.get_active(),
                                               nameEntry.get_text(),
                                               bindIPEntry.get_text(),
                                               localPortEntry.get_text(),
                                               remoteHostEntry.get_text(),
                                               remotePortEntry.get_text())
            else:
                newPort = PortInfo.DynamicPort(nameEntry.get_text(),
                                               bindIPEntry.get_text(),
                                               localPortEntry.get_text())
            self.addPortToPortView(newPort,self.portList)
        portDialog.destroy()


    def on_remove_port(self,widget):
        """Handle Tunnel Info|Remove Port button click"""
        selection = self.portView.get_selection()
        model, selection_iter = selection.get_selected()
        if(selection_iter):
            model.remove(selection_iter)


    def on_typeEntry_changed(self,widget):
        """Handle change to typeEntry on portDialog"""
        typeEntry = self.portTree.get_object("typeEntry")
        enabled = True
        if(typeEntry.get_active() == PortInfo.DYNAMIC_TYPE):
            enabled = False
        remoteHostLabel = self.portTree.get_object("remoteHostLabel")
        remoteHostLabel.set_sensitive(enabled)
        remoteHostEntry = self.portTree.get_object("remoteHostEntry")
        remoteHostEntry.set_sensitive(enabled)
        remotePortLabel = self.portTree.get_object("remotePortLabel")
        remotePortLabel.set_sensitive(enabled)
        remotePortEntry = self.portTree.get_object("remotePortEntry")
        remotePortEntry.set_sensitive(enabled)


    def on_portDialog_response(self,widget,response):
        """Validate the port dialog."""
        if(response != gtk.RESPONSE_OK):
            return False

        typeEntry = self.portTree.get_object("typeEntry")
        localPortEntry = self.portTree.get_object("localPortEntry")
        remoteHostEntry = self.portTree.get_object("remoteHostEntry")
        remotePortEntry = self.portTree.get_object("remotePortEntry")

        invalid = False
        if(not localPortEntry.get_text()):
            self.errorReporter.showError(_("The 'Local Port' field is required"))
            invalid = True
        else:
            port = None
            try:
                port = int(localPortEntry.get_text())
            except ValueError:
                self.errorReporter.showError(_("Invalid 'Local Port': %s") %
                                             localPortEntry.get_text())
                invalid = True
            else:
                if(port < 1 or port > 65535):
                    self.errorReporter.showError(_("'Local Port' out of range: %d") % port)
                    invalid = True

        if(not invalid and typeEntry.get_active() != PortInfo.DYNAMIC_TYPE):
            if(not remoteHostEntry.get_text()):
                self.errorReporter.showError(_("The 'Remote Host' field is required"))
                invalid = True
            elif(not remotePortEntry.get_text()):
                self.errorReporter.showError(_("The 'Remote Port' field is required"))
                invalid = True
            else:
                port = None
                try:
                    port = int(remotePortEntry.get_text())
                except ValueError:
                    self.errorReporter.showError(_("Invalid 'Remote Port': %s") %
                                                 remotePortEntry.get_text())
                    invalid = True
                else:
                    if(port < 1 or port > 65535):
                        self.errorReporter.showError(_("'Remote Port' out of range: %d") % port)
                        invalid = True

        if(invalid):
            widget.emit_stop_by_name("response")
        return invalid


    def on_manage_keys(self,widget):
        """Run the SSH keys dialog"""
        self.keyTree = gtk.Builder()
        self.keyTree.add_objects_from_file(self.uiFile, ["keyDialog"])
        self.keyTree.connect_signals(self)
        keyDialog = self.keyTree.get_object("keyDialog")
        self.keyView = self.keyTree.get_object("keyView")
        self.initializeKeyView(self.keyView)
        self.loadKeyView()
        keyDialog.run()
        keyDialog.destroy()


    def on_add_key(self,widget):
        """Add an ssh key to the list of registered keys"""
        title=_("Select Private Key")
        directory=os.environ.get("HOME")+"/.ssh"
        filename = self.selectFile(gtk.FILE_CHOOSER_ACTION_OPEN, [],
                                   title=title,
                                   base_directory=directory)
        if(filename != ""):
            newKey = KeyInfo(filename)
            self.controller.insertKey(newKey)
            self.loadKeyView()
            self.controller.isDirty = True


    def on_remove_key(self,widget):
        """Remove an ssh key from the list of registered keys"""
        selection = self.keyView.get_selection()
        model, selection_iter = selection.get_selected()
        if(selection_iter):
            key = self.keyList.get_value(selection_iter,0)
            self.controller.removeKey(key)
            self.loadKeyView()
            self.controller.isDirty = True


    def on_load_keys(self,widget):
        """Load all registered keys into the ssh-agent"""
        proc = self.controller.startLoadKeys()
        if(proc):
            gobject.timeout_add(100,self.cleanupLoadKeys,proc)


    def on_unload_keys(self,widget):
        """Unload all registered keys from the ssh-agent"""
        self.controller.unloadKeys()


    def on_view_agent(self,widget):
        """View details of currently running ssh agent"""
        agentTree = gtk.Builder()
        agentTree.add_objects_from_file(self.uiFile, ["agentDialog"])
        agentDialog = agentTree.get_object("agentDialog")
        agentView = agentTree.get_object("agentView")
        agentList = self.initializeKeyView(agentView)
        self.loadAgentDialog(agentTree, agentView.get_model())
        agentDialog.run()
        agentDialog.destroy()


    def loadAgentDialog(self, agentTree, agentList):
        """Fill the data fields in the agent dialog"""
        pid = os.environ.get("SSH_AGENT_PID")
        if pid is not None:
            pidEntry = agentTree.get_object("pidEntry")
            pidEntry.set_text(pid)
        sock = os.environ.get("SSH_AUTH_SOCK")
        if sock is not None:
            sockEntry = agentTree.get_object("sockEntry")
            sockEntry.set_text(sock)
        pipe = subprocess.Popen(["/usr/bin/ssh-add","-l"],
                                stdout=subprocess.PIPE)
        stdout = pipe.communicate()[0]
        if(pipe.returncode == 0):
            for line in stdout.splitlines():
                fields = line.split()
                if len(fields) < 4:
                    continue
                key = self.controller.lookupKey(fields[2])
                filename = os.path.basename(key.filename) if key else None
                agentList.append([None, filename,
                                  os.path.basename(fields[2]),
                                  fields[3], fields[0], fields[1]])

    def on_preferences(self,widget):
        """Run the preferences dialog."""
        self.preferencesTree = gtk.Builder()
        self.preferencesTree.add_objects_from_file(self.uiFile, ["preferencesDialog"])
        self.preferencesTree.connect_signals(self)
        preferencesDialog = self.preferencesTree.get_object("preferencesDialog")
        preferencesDialog.set_focus(None)

        defaultFileEntry = self.preferencesTree.get_object('defaultFileEntry')
        autoSaveEntry = self.preferencesTree.get_object('autoSaveEntry')
        restoreStateEntry = self.preferencesTree.get_object('restoreStateEntry')
        loadKeysEntry = self.preferencesTree.get_object('loadKeysEntry')
        showIconEntry = self.preferencesTree.get_object('showIconEntry')
        minToTrayEntry = self.preferencesTree.get_object('minToTrayEntry')
        minToTrayLabel = self.preferencesTree.get_object('minToTrayLabel')
        launchInTrayEntry = self.preferencesTree.get_object('launchInTrayEntry')
        launchInTrayLabel = self.preferencesTree.get_object('launchInTrayLabel')

        #Load current config values.
        defaultFileEntry.set_text(self.config.safeGet('BASE','defaultFile'))
        autoSaveEntry.set_active(self.config.safeGetBoolean('GUI','autoSave'))
        restoreStateEntry.set_active(self.config.safeGetBoolean('GUI','restoreState'))
        loadKeysEntry.set_active(self.config.safeGetBoolean('GUI','loadKeys'))
        minToTrayEntry.set_active(self.config.safeGetBoolean('GUI','minToTray'))
        launchInTrayEntry.set_active(self.config.safeGetBoolean('GUI','launchInTray'))
        showIconEntry.set_active(self.config.safeGetBoolean('GUI','showIcon'))

        minToTrayLabel.set_sensitive(showIconEntry.get_active())
        minToTrayEntry.set_sensitive(showIconEntry.get_active())
        launchInTrayLabel.set_sensitive(showIconEntry.get_active() and
                                       minToTrayEntry.get_active())
        launchInTrayEntry.set_sensitive(showIconEntry.get_active() and
                                       minToTrayEntry.get_active())

        #Run dialog and update config values.
        result = preferencesDialog.run()
        if(result == gtk.RESPONSE_OK):
            needSave = False
            if(defaultFileEntry.get_text() !=
               self.config.safeGet('BASE','defaultFile')):
                self.config.safeSet('BASE','defaultFile',
                                    defaultFileEntry.get_text())
                needSave = True
            if(autoSaveEntry.get_active() !=
               self.config.safeGetBoolean('GUI','autoSave')):
                self.config.safeSet('GUI','autoSave',
                                    "%s" % autoSaveEntry.get_active())
                needSave = True
            if(restoreStateEntry.get_active() !=
               self.config.safeGetBoolean('GUI','restoreState')):
                self.config.safeSet('GUI','restoreState',
                                    "%s" % restoreStateEntry.get_active())
                needSave = True
            if(loadKeysEntry.get_active() !=
               self.config.safeGetBoolean('GUI','loadKeys')):
                self.config.safeSet('GUI','loadKeys',
                                    "%s" % loadKeysEntry.get_active())
                needSave = True
            if(showIconEntry.get_active() !=
               self.config.safeGetBoolean('GUI','showIcon')):
                self.config.safeSet('GUI','showIcon',
                                    "%s" % showIconEntry.get_active())
                if(showIconEntry.get_active()):
                    self.statusIcon.enable()
                else:
                    self.statusIcon.disable()
                needSave = True
            if(minToTrayEntry.get_active() !=
               self.config.safeGetBoolean('GUI','minToTray')):
                self.config.safeSet('GUI','minToTray',
                                    "%s" % minToTrayEntry.get_active())
                needSave = True
            if(launchInTrayEntry.get_active() !=
               self.config.safeGetBoolean('GUI','launchInTray')):
                self.config.safeSet('GUI','launchInTray',
                                    "%s" % launchInTrayEntry.get_active())
                needSave = True
            if(needSave):
                self.config.write()

        preferencesDialog.destroy()


    def on_iconEntry_toggled(self,widget):
        """An icon-related checkbox has been toggled."""
        showIconEntry = self.preferencesTree.get_object('showIconEntry')
        minToTrayLabel = self.preferencesTree.get_object('minToTrayLabel')
        minToTrayEntry = self.preferencesTree.get_object('minToTrayEntry')
        minToTrayLabel.set_sensitive(showIconEntry.get_active())
        minToTrayEntry.set_sensitive(showIconEntry.get_active())
        launchInTrayEntry = self.preferencesTree.get_object('launchInTrayEntry')
        launchInTrayLabel = self.preferencesTree.get_object('launchInTrayLabel')
        launchInTrayLabel.set_sensitive(showIconEntry.get_active() and
                                       minToTrayEntry.get_active())
        launchInTrayEntry.set_sensitive(showIconEntry.get_active() and
                                       minToTrayEntry.get_active())


    def on_defaultFileSelector_clicked(self,widget):
        """Run file selector."""
        defaultFileEntry = self.preferencesTree.get_object('defaultFileEntry')
        start_file = defaultFileEntry.get_text()
        start_dir = os.path.dirname(start_file)
        if not os.path.isdir(start_dir):
            start_dir = None
        newFile = self.selectFile(gtk.FILE_CHOOSER_ACTION_SAVE,
                                  [self.filter],
                                  base_directory=start_dir,
                                  file_name=start_file,
                                  file_extension=".xml",
                                  title=_("Select Default Configuration"))
        if newFile:
            defaultFileEntry.set_text(newFile)


    def cleanupLoadKeys(self,process):
        """Cleanup a running 'loadKeys' operation."""
        return self.controller.checkLoadKeysComplete(process)


    def cleanupTunnel(self,tunnel):
        """Cleanup a running 'TunnelInfo.start' operation."""

        process = tunnel.process
        if(process == None):
            return False

        if(process.poll() != None):
            errMsg = _("Unexpected termination of tunnel: %s") % tunnel.name
            if(process.returncode != 0):
                errMsg = errMsg + "\n\n" + process.stderr.read() + process.stdout.read()
            tunnel.errorReporter.showError(errMsg)
            tunnel.process = None
            tunnel.stop()
            self.controller.isDirty = True
            self.updateTunnel(tunnel)
            return False

        #still running
        return True


    def scheduleTunnelCleanup(self,tunnel):
        """Schedule tunnel cleanup after tunnel start."""
        gobject.timeout_add(100,self.cleanupTunnel,tunnel)


    def waitForAutoLoad(self):
        """Autoload tunnels if ssh-add is done."""
        if(self.controller.isSSHAddRunning):
            return True

        if(self.controller.defaultRouteExists() == False):
            return True

        self.controller.startTunnels(self.scheduleTunnelCleanup,True)
        if(self.mainWindow != None):
            self.loadTunnelView()
        if(self.statusIcon.is_enabled()):
            self.statusIcon.reloadMenu()
        return False


    def initialIconify(self):
        """Handle initial iconification."""
        self.mainWindow.iconify()
        return False


    def selectFile(self, action, filters, title=None,
                   file_extension=None, file_name=None, base_directory=None):
        """This function is used to select a file to open"""

        if(action == gtk.FILE_CHOOSER_ACTION_OPEN):
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            if(title == None):
                title = _("Open File")
        else:
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_SAVE, gtk.RESPONSE_OK)
            if(title == None):
                title = _("Save File")

        dialog = gtk.FileChooserDialog(title=title,
                                       action=action,
                                       buttons=buttons)
        if(action == gtk.FILE_CHOOSER_ACTION_SAVE and file_name):
            dialog.set_current_name(file_name)
            base_directory = os.path.dirname(file_name)
        if(base_directory):
            dialog.set_current_folder(base_directory)

        for filter in filters:
            dialog.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name(_("All files"))
        filter.add_pattern("*")
        dialog.add_filter(filter)

        result = ""
        if(dialog.run() == gtk.RESPONSE_OK):
            result = dialog.get_filename()
            if(action == gtk.FILE_CHOOSER_ACTION_SAVE):
                result,extension = os.path.splitext(result)
                if((not extension or extension == "") and file_extension):
                        result = result + file_extension
                elif(extension and extension != ""):
                    result = result + extension
        dialog.destroy()

        return result
