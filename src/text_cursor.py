#!/usr/bin/env python -u
# -*- coding: UTF-8 -*-
#------------------------------------------------------------------------------

import colorama
from ctypes import windll, wintypes, Structure, c_short, c_ushort, byref, c_ulong
from pyreadline import console

# Win32 API
SHORT = c_short
WORD = c_ushort
DWORD = c_ulong

STD_OUTPUT_HANDLE = DWORD(-11)    # $CONOUT

# These are already defined, so no need to redefine.
COORD = wintypes._COORD
SMALL_RECT = wintypes.SMALL_RECT
CONSOLE_SCREEN_BUFFER_INFO = console.CONSOLE_SCREEN_BUFFER_INFO

# Main
wk32 = windll.kernel32
hSo = wk32.GetStdHandle(STD_OUTPUT_HANDLE)
GetCSBI = wk32.GetConsoleScreenBufferInfo

def get_cursor_pos():
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    GetCSBI(hSo, byref(csbi))
    xy = csbi.dwCursorPosition
    return (xy.X, xy.Y)




def set_cursor_pos(x, y):
    print("\033[%d;%dH" % (y, x), end="")

def clear_screen():
    print(colorama.ansi.clear_screen())


colorama.init()