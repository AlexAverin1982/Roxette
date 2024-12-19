import time

import colorama

from text_cursor import *

colorama.init()
clear_screen()
# print('something', end="")
x, y = get_cursor_pos()

for i in range(1,101):
    set_cursor_pos(1, 10)
    print("%d %%" % (i))
    time.sleep(1)

set_cursor_pos(1, 12)
print('line 1')
set_cursor_pos(1, 1)
colorama.deinit()
# print("\033[%d;%dHhere" % (y+1, x), end="")
# print('is', end="")
# set_cursor_pos(x, y)