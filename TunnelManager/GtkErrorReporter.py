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

import pygtk
pygtk.require("2.0")
import os
import sys
import gtk

from TunnelManager import ErrorReporter

class GtkErrorReporter(ErrorReporter.ErrorReporter):
    """Over-rides ErrorReporter for use in Gtk application."""

    def showError(self,msg):
        """Show error message in a dialog box."""
        dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                                   message_format=msg,
                                   buttons=gtk.BUTTONS_OK)
        dialog.run()
        dialog.destroy()

