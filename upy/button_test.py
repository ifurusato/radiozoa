
import time
from colorama import Fore, Style

from push_button import PushButton

pushbutton = None

def event_handler(arg):
    if pushbutton:
        if pushbutton.value:
            print(Fore.WHITE + 'push button: {}; '.format(arg) + Fore.GREEN + 'ON' + Style.RESET_ALL)
        else:
            print(Fore.WHITE + 'push button: {}; '.format(arg) + Fore.RED + 'OFF' + Style.RESET_ALL)
    else:
        print('no pushbutton')

try:
    pushbutton = PushButton(callback=event_handler)

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print(Fore.CYAN + 'Ctrl-C caught, exiting…' + Style.RESET_ALL)
    pass
except Exception as e:
    print('{} raised by test: {}'.format(type(e), e))
finally:
    print('complete.')
