
# -*- coding: utf-8 -*-

def classFactory(iface):  # pylint: disable=invalid-name
    from .string_writer import StringWriter
    return StringWriter(iface)
