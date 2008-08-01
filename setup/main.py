# vim:set et sts=4 sw=4:
#
# ibus - The Input Bus
#
# Copyright (c) 2007-2008 Huang Peng <shawn.p.huang@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA  02111-1307  USA

from os import path
import gtk
import gobject
import ibus
from gtk import gdk, glade

(
    COLUMN_NAME,
    COLUMN_ENABLE,
    COLUMN_PRELOAD,
    COLUMN_VISIBLE,
    COLUMN_ICON,
    COLUMN_DATA,
) = range(6)

(
    DATA_NAME,
    DATA_LANG,
    DATA_ICON,
    DATA_AUTHOR,
    DATA_CREDITS,
    DATA_EXEC,
    DATA_STARTED,
    DATA_PRELOAD
) = range(8)

CONFIG_PRELOAD_ENGINES = "/general/preload_engines"

class Setup(object):
    def __init__(self):
        super(Setup, self).__init__()
        try:
            self.__bus = ibus.Bus()
        except:
            import traceback
            traceback.print_exc()
            self.__bus = None

        glade_file = path.join(path.dirname(__file__), "./setup.glade")
        self.__xml = glade.XML(glade_file)
        self.__dialog = self.__xml.get_widget("dialog_setup")
        self.__tree = self.__xml.get_widget("treeview_engines")
        self.__preload_engines = set(self.__bus.config_get_value(CONFIG_PRELOAD_ENGINES, []))
        model = self.__create_model()
        self.__tree.set_model(model)

        # add icon search path
        icon_theme = gtk.icon_theme_get_default()
        dir = path.dirname(__file__)
        icondir = path.join(dir, "..", "icons")
        icon_theme.prepend_search_path(icondir)

        # column for holiday names
        column = gtk.TreeViewColumn()
        column.set_title("Name")

        renderer = gtk.CellRendererPixbuf()
        renderer.set_property("xalign", 0.5)

        column.pack_start(renderer)
        column.set_attributes(renderer, icon_name = COLUMN_ICON, visible = COLUMN_VISIBLE)

        renderer = gtk.CellRendererText()
        renderer.set_property("xalign", 0.0)

        # column.set_clickable(True)
        column.pack_start(renderer)
        column.set_attributes(renderer, text = COLUMN_NAME)

        self.__tree.append_column(column)

        # column for started names
        renderer = gtk.CellRendererToggle()
        renderer.set_data('column', COLUMN_ENABLE)
        renderer.set_property("xalign", 0.5)
        renderer.connect("toggled", self.__item_started_column_toggled_cb, model)

        #col_offset = gtk.TreeViewColumn("Holiday", renderer, text=HOLIDAY_NAME)
        column = gtk.TreeViewColumn("Started", renderer, active = COLUMN_ENABLE, visible = COLUMN_VISIBLE)
        self.__tree.append_column(column)

        # column for preload names
        renderer = gtk.CellRendererToggle()
        renderer.set_data('column', COLUMN_PRELOAD)
        renderer.set_property("xalign", 0.5)
        renderer.connect("toggled", self.__item_preload_column_toggled_cb, model)

        column = gtk.TreeViewColumn("Preload", renderer, active = COLUMN_PRELOAD, visible = COLUMN_VISIBLE)
        self.__tree.append_column(column)


        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("", renderer)
        self.__tree.append_column(column)



    def __item_started_column_toggled_cb(self, cell, path_str, model):

        # get toggled iter
        iter = model.get_iter_from_string(path_str)
        data = model.get_value(iter, COLUMN_DATA)

        # do something with the value
        if data[DATA_STARTED] == False:
            try:
                self.__bus.register_start_engine(data[DATA_LANG], data[DATA_NAME])
            except Exception, e:
                dlg = gtk.MessageDialog(type = gtk.MESSAGE_ERROR,
                        buttons = gtk.BUTTONS_CLOSE,
                        message_format = str(e))
                dlg.run()
                return
        else:
            try:
                self.__bus.register_stop_engine(data[DATA_LANG], data[DATA_NAME])
            except Exception, e:
                dlg = gtk.MessageDialog(type = gtk.MESSAGE_ERROR,
                        buttons = gtk.BUTTONS_CLOSE,
                        message_format = str(e))
                dlg.run()
                return
        data[DATA_STARTED] = not data[DATA_STARTED]

        # set new value
        model.set(iter, COLUMN_ENABLE, data[DATA_STARTED])

    def __item_preload_column_toggled_cb(self, cell, path_str, model):

        # get toggled iter
        iter = model.get_iter_from_string(path_str)
        data = model.get_value(iter, COLUMN_DATA)

        data[DATA_PRELOAD] = not data[DATA_PRELOAD]
        engine = "%s:%s" % (data[DATA_LANG], data[DATA_NAME])

        if data[DATA_PRELOAD]:
            if engine not in self.__preload_engines:
                self.__preload_engines.add(engine)
                self.__bus.config_set_value(CONFIG_PRELOAD_ENGINES, list(self.__preload_engines))
        else:
            if engine in self.__preload_engines:
                self.__preload_engines.remove(engine)
                self.__bus.config_set_value(CONFIG_PRELOAD_ENGINES, list(self.__preload_engines))


        # set new value
        model.set(iter, COLUMN_PRELOAD, data[DATA_PRELOAD])

    def __create_model(self):
        # create tree store
        model = gtk.TreeStore(
            gobject.TYPE_STRING,
            gobject.TYPE_BOOLEAN,
            gobject.TYPE_BOOLEAN,
            gobject.TYPE_BOOLEAN,
            gobject.TYPE_STRING,
            gobject.TYPE_PYOBJECT)

        langs = dict()

        for name, lang, icon, author, credits, _exec, started in self.__bus.register_list_engines():
            _lang = ibus.LANGUAGES.get(lang, "other")
            if _lang not in langs:
                langs[_lang] = list()
            langs[_lang].append([name, lang, icon, author, credits, _exec, started])

        keys = langs.keys()
        keys.sort()
        for key in keys:
            iter = model.append(None)
            model.set(iter,
                COLUMN_NAME, key,
                COLUMN_ENABLE, False,
                COLUMN_PRELOAD, False,
                COLUMN_VISIBLE, False,
                COLUMN_ICON, None,
                COLUMN_DATA, None)
            langs[key].sort()
            for name, lang, icon, author, credits, _exec, started in langs[key]:
                child_iter = model.append(iter)
                is_preload = "%s:%s" % (lang, name) in self.__preload_engines
                model.set(child_iter,
                    COLUMN_NAME, name,
                    COLUMN_ENABLE, started,
                    COLUMN_PRELOAD, is_preload,
                    COLUMN_VISIBLE, True,
                    COLUMN_ICON, icon,
                    COLUMN_DATA,
                    [name, lang, icon, author, credits, _exec, started, is_preload])

        return model


    def run(self):
        return self.__dialog.run()

if __name__ == "__main__":
    Setup().run()
