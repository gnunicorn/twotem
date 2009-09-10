#
# (C) Benjamin Kampmann
#

import totem
import gobject
import gtk

class Twotem(totem.Plugin):

    def __init__(self):
        totem.Plugin.__init__(self)

    def activate(self, totem):
        print "Active"

    def deactivate(self, totem):
        print "off"

