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
from ConfigParser import RawConfigParser


class Configuration(object):
    """Configuration object to represent the properties file."""

    def __getFilename(self):
        return self.__m_filename
    filename = property(__getFilename)

    def __getProperties(self):
        return self.__m_properties
    properties = property(__getProperties)

    def __init__(self,filename=None):
        """Object constructor."""
        if(not filename):
            filename = os.environ.get('HOME') + '/.TunnelManager/properties.conf'
        self.__m_filename = filename
        self.__m_properties = RawConfigParser()

        if(os.path.exists(filename)):
            self.properties.read(filename)


    def safeSet(self,section,option,value):
        """Safely set an option value, adding the section if necessary."""
        if(section != 'DEFAULT' and not self.properties.has_section(section)):
            self.properties.add_section(section)
        self.properties.set(section,option,value)


    def safeGet(self,section,option):
        """Safely get an option, reading from DEFAULT if section missing."""
        if(section != 'DEFAULT' and not self.properties.has_section(section)):
            section = 'DEFAULT'
        return self.properties.get(section,option)


    def safeGetBoolean(self,section,option):
        """Safely get an option, reading from DEFAULT if section missing."""
        if(section != 'DEFAULT' and not self.properties.has_section(section)):
            section = 'DEFAULT'
        return self.properties.getboolean(section,option)


    def write(self):
        """Write the properties file."""
        configFile = open(self.filename, 'wb')
        self.properties.write(configFile)
