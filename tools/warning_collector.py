import threading
import warnings
from collections import deque
from colorama import Fore, Style


class WarningCollector:
    """
    Buffers warnings.warn() calls during animated spinners,
    then displays them in a single error report block after
    the entire import completes.
    """

    def __init__(self, max_display=10):
        self._buffer = deque()
        self._lock = threading.Lock()
        self._max_display = max_display
        self._original_showwarning = None
        self._installed = False

    def install(self):
        """Replace warnings.showwarning with our collector."""
        if not self._installed:
            self._original_showwarning = warnings.showwarning
            warnings.showwarning = self._collect_warning
            self._installed = True

    def uninstall(self):
        """Restore the original warnings.showwarning."""
        if self._installed and self._original_showwarning is not None:
            warnings.showwarning = self._original_showwarning
            self._installed = False

    def _collect_warning(self, message, category, filename, lineno, file=None, line=None):
        with self._lock:
            self._buffer.append(str(message))

    def flush(self):
        """Print all buffered warnings as an error report block, then clear."""
        with self._lock:
            if not self._buffer:
                return

            total = len(self._buffer)
            display_items = list(self._buffer)

            if total > self._max_display:
                omitted = total - self._max_display
                display_items = display_items[-self._max_display:]

            print(f"\n{Fore.RED}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.RED}  Error Report ({total} warning{'s' if total != 1 else ''}){Style.RESET_ALL}")
            print(f"{Fore.RED}{'=' * 60}{Style.RESET_ALL}")

            if total > self._max_display:
                print(f"  {Fore.YELLOW}... {omitted} earlier warning(s) omitted{Style.RESET_ALL}")

            for msg in display_items:
                lines = msg.split('\n')
                print(f"  {Fore.RED}!{Style.RESET_ALL} {lines[0]}")
                for line in lines[1:]:
                    print(f"    {Fore.LIGHTBLACK_EX}{line}{Style.RESET_ALL}")

            print(f"{Fore.RED}{'=' * 60}{Style.RESET_ALL}\n")

            self._buffer.clear()


_default_collector = WarningCollector(max_display=10)


def get_collector():
    """Get the global WarningCollector instance."""
    return _default_collector
