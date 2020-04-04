# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

"""Native type-ahead search

Implements native type-ahead search (also known as search-as-you-type).
When keys are pressed that resemble characters which may be part of file or
directory names, they are used to build up a filter string that selects
matching entries in the current directory in browser view.
"""

from ranger.core.shared import FileManagerAware
from ranger.core.shared import SettingsAware

from ranger.ext.keybinding_parser import key_to_string

# list of characters not interpreted as filename parts
CHAR_BLACKLIST = ['/']


def _key_is_special(key):
    return (len(key) > 2 and not key.endswith('<')
            and not key.startswith('>'))


class TypeAhead(FileManagerAware, SettingsAware):
    current_filter = ""

    def __init__(self, win):
        self.win = win
        self.fm.signal_bind('cd', self.reset, weak=True)
        self.fm.signal_bind('tab.change', self.reset, weak=True)
        self.enabled = self.settings.typeahead_mode
        self.bypass_for_next_keybinding = False

    def handle_key(self, key):
        """Handle a pressed key in type-ahead mode.

        If the key matches a character used in file or directory names
        it is used to start/extend the filter string and execute the
        type-ahead search.

        This method returns True if the key has been consumed by the type-
        ahead mode and is not to be passed further.
        Otherwise it returns False, which indicates that the key should
        be handled normally.
        """

        if not self.enabled:
            return False

        key = key_to_string(key)
        is_filename_selector = (not _key_is_special(key)
                                and key not in CHAR_BLACKLIST)
        key_consumed = False

        if self.bypass_for_next_keybinding:
            key_consumed = False

        elif is_filename_selector:
            self.current_filter += key
            key_consumed = True

        # Space key handling: add whitespace character to filter
        elif key == '<space>':
            # do not let filter begin with space
            if self.current_filter:
                self.current_filter += ' '
                key_consumed = True

        # Backspace key handling: delete last character of filter
        elif key in ['<bs>', '<backspace>', '<backspace2>']:
            if self.current_filter:
                self.current_filter = self.current_filter[:-1]
                key_consumed = True

        if key_consumed:
            self.fm.ui.status.request_redraw()
            self._select()
        elif not self.bypass_for_next_keybinding:
            # if type-ahead mode is still active, change the keymap
            # for this key press before passing further
            self.fm.ui.keymaps.use_keymap('typeahead')

        return key_consumed

    def _select(self, next_match=False):

        def _filter_name(name):
            if self.settings.typeahead_case_insensitive:
                name = name.lower()
            return name

        thisdir = self.fm.thisdir

        if next_match:
            # shift the list elements so that it begins after the current
            # selection pointer (with wrap-around) to look for the next
            # match efficiently
            base_list = thisdir.files
            next_idx = thisdir.pointer + 1
            file_list = (list(base_list[next_idx:])
                         + list(base_list[:next_idx]))
        else:
            file_list = thisdir.files
        for fobj in file_list:
            fobj_name = _filter_name(fobj.relative_path)
            search_filter = _filter_name(self.current_filter)
            if fobj_name.startswith(search_filter):
                thisdir.move_to_obj(fobj)
                break

    def reset(self):
        """Resets the type-ahead filter"""
        self.clear()

    def next_match(self):
        """Select the next entry matching the current filter string.

        Iterates the list of the current directory entries starting
        with the current pointer and selects the next entry matching
        the current filter string (if any).
        """
        self._select(next_match=True)

    def get_current_filter(self):
        """Returns the current filter string"""
        return self.current_filter

    def clear(self):
        """Clears the current filter string"""
        self.current_filter = ""
        self.fm.ui.status.request_redraw()

    def disable(self, temporary=False):
        """Disables the type-ahead mode

        If 'temporary' is True, the mode will be reactivated once
        the next command or keymap has been executed.
        Otherwise this mode will be deactivated until explicitly
        activated again.
        """
        self.clear()
        if temporary:  # pylint: disable=simplifiable-if-statement
            self.bypass_for_next_keybinding = True
        else:
            self.enabled = False

    def on_keybuffer_finished_parsing(self):
        """Re-enables the type-ahead mode if temporarily disabled

        This should be called whenever a keymap binding has been executed
        so that the type-ahead mode can be reactivated accordingly if it
        was only temporarily disabled.
        """
        if self.fm.ui.keybuffer.result == 'typeahead_bypass':
            # they keystroke which led to disable(temporary=True) will also
            # call this method, which we need to filter
            return
        if self.bypass_for_next_keybinding:
            self.bypass_for_next_keybinding = False


if __name__ == '__main__':
    import doctest
    import sys
    sys.exit(doctest.testmod()[0])
