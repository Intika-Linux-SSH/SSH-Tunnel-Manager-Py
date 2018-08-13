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


import sys
import gtk

APP_INDICATOR_AVAILABLE = True
try:
    import appindicator
except:
    APP_INDICATOR_AVAILABLE = False

class StatusIcon(object):
    """This class represents the status box icon."""

    def __init__(self,gui):
        """The object constructor."""
        self.gui = gui
        self.menu = None
        self.icon = None
        self.indicator = None


    def is_enabled(self):
        """Is the status icon enabled?"""
        return (self.menu != None)


    def displayMenu(self,widget):
        """Display the menu for the StatusIcon"""
        if (not APP_INDICATOR_AVAILABLE):
            self.menu.popup(None, None, None, 1, 0)


    def disable(self):
        """Disable the status icon"""
        if(self.icon != None):
            self.icon.set_visible(False)
        self.indicator = None
        self.menu = None
        if(self.gui.mainWindow == None):
            self.gui.buildWindow()


    def enable(self):
        """Enable the status icon"""
        if (self.menu == None) :
            self.menu = gtk.Menu()
            if (APP_INDICATOR_AVAILABLE):
                self.indicator = appindicator.Indicator(_("SSH Tunnel Manager"),
                        "network-wired", appindicator.CATEGORY_OTHER)
                self.indicator.set_status(appindicator.STATUS_ACTIVE)
                self.indicator.set_menu(self.menu)
            elif (self.icon != None):
                self.icon.set_visible(True)
            else:
                self.icon = gtk.status_icon_new_from_stock(gtk.STOCK_NETWORK)
                self.icon.set_tooltip(_("SSH Tunnel Manager"))
                self.icon.connect('activate', self.displayMenu)
            self.reloadMenu()


    def reloadMenu(self):
        """Dynamically reload the popup menu."""

        if (self.menu == None):
            return

        if (APP_INDICATOR_AVAILABLE):
            self.menu = gtk.Menu()
        else:
            self.menu.foreach(self.menu.remove)

        keyMenu = gtk.Menu()
        self.addToMenu(keyMenu,_("Load "),gtk.STOCK_CONNECT,
                       self.gui.on_load_keys)
        self.addToMenu(keyMenu,_("Unload"),gtk.STOCK_DISCONNECT,
                       self.gui.on_unload_keys)
        self.addToMenu(keyMenu,_("View Agent"),gtk.STOCK_INFO,
                       self.gui.on_view_agent)

        
        keysItem = self.addToMenu(self.menu,_('Keys'),
                                  gtk.STOCK_DIALOG_AUTHENTICATION)
        keysItem.set_submenu(keyMenu)

        separator = gtk.SeparatorMenuItem()
        self.menu.append(separator)
        separator.show()

        for tunnel in self.gui.controller.tunnelList:
            if(tunnel.isActive):
                self.addToMenu(self.menu,tunnel.name, gtk.STOCK_YES,
                               self.gui.stopTunnel,tunnel)
            else:
                self.addToMenu(self.menu,tunnel.name, gtk.STOCK_NO,
                               self.gui.startTunnel,tunnel)

        separator = gtk.SeparatorMenuItem()
        self.menu.append(separator)
        separator.show()

        
        if(self.gui.mainWindow == None or
                self.gui.mainWindow.iconify_initially):
            self.addToMenu(self.menu, None, gtk.STOCK_EDIT,
                    self.toggleHide)
        self.addToMenu(self.menu, None, gtk.STOCK_PREFERENCES,
                       self.gui.on_preferences)
        self.addToMenu(self.menu, None, gtk.STOCK_QUIT, 
                       self.gui.on_quit)

        if (APP_INDICATOR_AVAILABLE):
            self.indicator.set_menu(self.menu)


    def addToMenu(self,menu,label,stock_id,handler=None,data=None):
        """Add an item to the menu."""
        if stock_id == None:
            item = gtk.MenuItem(label)
        elif stock_id == gtk.STOCK_YES or stock_id == gtk.STOCK_NO:
            item = gtk.CheckMenuItem(label)
            item.set_active(stock_id == gtk.STOCK_YES)
        elif label == None:
            item = gtk.ImageMenuItem(stock_id)
        else:
            item = gtk.ImageMenuItem(label)
            image = gtk.image_new_from_stock(stock_id, gtk.ICON_SIZE_MENU)
            item.set_image(image)
        if(handler):
            if(data):
                item.connect('activate',handler,data)
            else:
                item.connect('activate',handler)
        menu.append(item)
        item.show()
        return item


    def toggleHide(self,widget):
        """Unhide the tunnel manager, if it is hidden."""
        if(self.gui.mainWindow != None):
            if(self.gui.mainWindow.iconify_initially):
                self.gui.mainWindow.deiconify()
                self.gui.mainWindow.present()
            elif(self.gui.config.safeGetBoolean('GUI','showIcon') and
                 self.gui.config.safeGetBoolean('GUI','minToTray')):
                self.gui.destroyWindow()
            else:
                self.gui.mainWindow.iconify()
        else:
            self.gui.buildWindow()
        self.reloadMenu()
