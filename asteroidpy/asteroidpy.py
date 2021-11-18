import urwid
import numpy as np


def exit_on_q(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()


def exit_program(button):
    raise urwid.ExitMainLoop()


choices = u'Previsioni Interrogazioni Osservazioni Configurazione Esci'.split()


def menu(title, choices):
    body = [urwid.Text(title), urwid.Divider()]
    for c in choices:
        button = urwid.Button(c)
        urwid.connect_signal(button, 'click', item_chosen, c)
        body.append(urwid.AttrMap(button, None, focus_map='reversed'))
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))


def item_chosen(button, choice):
    response = urwid.Text([u'Hai scelto ', choice, u'\n'])
    done = urwid.Button(u'Ok')
    urwid.connect_signal(done, 'click', exit_program)
    main.original_widget = urwid.Filler(urwid.Pile(
        [response, urwid.AttrMap(done, None, focus_map='reversed')]))

if __name__ == '__main__':
    main = urwid.Padding(
        menu(u'AsteroidPY versione 0.1', choices), left=2, right=2)
    top = urwid.Overlay(main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
                        align='center', width=('relative', 80),
                        valign='middle', height=('relative', 80),
                        min_width=20, min_height=9)

    loop = urwid.MainLoop(
        top, palette=[('reversed', 'standout', '')], unhandled_input=exit_on_q)
    loop.run()
