import os
import sys
import threading
import time
from functools import wraps
from colorama import Fore, Style


def animate(prefix=""):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):

            def animation():
                animation_chars = ["", ".", "..", "...", "....", "....."]
                while not animation.stop:
                    for char in animation_chars:
                        sys.stdout.write(f'\r{prefix} {char}')
                        sys.stdout.flush()
                        time.sleep(0.3)

            animation.stop = False
            animation_thread = threading.Thread(target=animation)
            animation_thread.start()

            result = function(*args, **kwargs)

            animation.stop = True
            animation_thread.join()

            sys.stdout.write('\r')
            sys.stdout.flush()
            print(f'{prefix} {Fore.GREEN} Complete! {Style.RESET_ALL}')

            return result
        return wrapper
    return decorator
