import urwid
import numpy as np


def show_or_exit(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()

txt = urwid.Text(u'prova')
loop = urwid.MainLoop(txt, unhandled_input=show_or_exit)
loop.run()
