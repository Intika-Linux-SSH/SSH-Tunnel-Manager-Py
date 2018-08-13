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

def initialize(controller,locale_dir=None):
    """Initialize localization."""
    try:
        import locale
        import gettext
        locale.setlocale(locale.LC_ALL, "")
        if(controller == "GUI"):
            import gtk
            gtk.glade.bindtextdomain('tunnelmanager', locale_dir)
            gtk.glade.textdomain('tunnelmanager')
        gettext.install('tunnelmanager', locale_dir, unicode=1)
    except (IOError,locale.Error), e:
        print >>sys.stderr, "Warning: tunnelmanager:", e
        __builtins__["_"] = lambda x : x
