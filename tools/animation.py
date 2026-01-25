import sys
import threading
import time
from functools import wraps
from colorama import Fore, Style, init

# Initialize colorama for Windows support
init()

# Spinner styles
SPINNERS = {
    'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
    'line': ['|', '/', '-', '\\'],
    'arrows': ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'],
    'bounce': ['⠁', '⠂', '⠄', '⡀', '⢀', '⠠', '⠐', '⠈'],
    'blocks': ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█', '▉', '▊', '▋', '▌', '▍', '▎', '▏'],
}

# Fallback for terminals that don't support Unicode
SPINNER_FALLBACK = ['|', '/', '-', '\\']


def _format_time(seconds):
    """Format elapsed time in a human-readable way."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def _get_spinner():
    """Get appropriate spinner based on terminal capabilities."""
    try:
        # Test if terminal supports Unicode
        sys.stdout.write('⠋')
        sys.stdout.write('\r \r')
        sys.stdout.flush()
        return SPINNERS['dots']
    except (UnicodeEncodeError, UnicodeDecodeError):
        return SPINNER_FALLBACK


def animate(prefix="", show_time=True, spinner_style='dots'):
    """
    Decorator that displays an animated spinner while a function executes.

    Args:
        prefix: Text to display before the spinner
        show_time: Whether to show elapsed time
        spinner_style: Which spinner animation to use ('dots', 'line', 'arrows', 'bounce', 'blocks')

    Usage:
        @animate('Loading data')
        def fetch_data():
            # long running operation
            pass
    """
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            # Get spinner characters
            try:
                spinner_chars = SPINNERS.get(spinner_style, SPINNERS['dots'])
                # Test Unicode support
                sys.stdout.write(spinner_chars[0])
                sys.stdout.write('\r \r')
                sys.stdout.flush()
            except (UnicodeEncodeError, UnicodeDecodeError):
                spinner_chars = SPINNER_FALLBACK

            start_time = time.time()

            def animation():
                idx = 0
                while not animation.stop:
                    elapsed = time.time() - start_time
                    spinner = spinner_chars[idx % len(spinner_chars)]

                    # Build the status line
                    if show_time:
                        time_str = f" {Fore.CYAN}[{_format_time(elapsed)}]{Style.RESET_ALL}"
                    else:
                        time_str = ""

                    status_line = f'\r{Fore.YELLOW}{spinner}{Style.RESET_ALL} {prefix}{time_str}'

                    # Clear line and write
                    sys.stdout.write('\r' + ' ' * 80 + '\r')
                    sys.stdout.write(status_line)
                    sys.stdout.flush()

                    idx += 1
                    time.sleep(0.08)

            animation.stop = False
            animation_thread = threading.Thread(target=animation)
            animation_thread.daemon = True
            animation_thread.start()

            try:
                result = function(*args, **kwargs)
            finally:
                animation.stop = True
                animation_thread.join(timeout=0.5)

            # Calculate final time
            elapsed = time.time() - start_time

            # Clear line and show completion
            sys.stdout.write('\r' + ' ' * 80 + '\r')

            # Show completion message with checkmark
            check = f"{Fore.GREEN}\u2713{Style.RESET_ALL}"
            time_str = f" {Fore.CYAN}[{_format_time(elapsed)}]{Style.RESET_ALL}" if show_time else ""
            print(f'{check} {prefix}{time_str} {Fore.GREEN}Done{Style.RESET_ALL}')

            return result
        return wrapper
    return decorator


class ProgressAnimation:
    """
    Context manager for progress animation with manual control.

    Usage:
        with ProgressAnimation('Processing items') as progress:
            for i, item in enumerate(items):
                progress.update(f'Processing item {i+1}/{len(items)}')
                process(item)
    """

    def __init__(self, prefix="", show_time=True):
        self.prefix = prefix
        self.show_time = show_time
        self.start_time = None
        self.stop = False
        self.current_status = ""
        self.thread = None
        self._spinner_chars = None

    def __enter__(self):
        # Get spinner characters
        try:
            self._spinner_chars = SPINNERS['dots']
            sys.stdout.write(self._spinner_chars[0])
            sys.stdout.write('\r \r')
            sys.stdout.flush()
        except (UnicodeEncodeError, UnicodeDecodeError):
            self._spinner_chars = SPINNER_FALLBACK

        self.start_time = time.time()
        self.stop = False
        self.thread = threading.Thread(target=self._animate)
        self.thread.daemon = True
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop = True
        if self.thread:
            self.thread.join(timeout=0.5)

        elapsed = time.time() - self.start_time

        # Clear line
        sys.stdout.write('\r' + ' ' * 100 + '\r')

        if exc_type is None:
            check = f"{Fore.GREEN}\u2713{Style.RESET_ALL}"
            time_str = f" {Fore.CYAN}[{_format_time(elapsed)}]{Style.RESET_ALL}" if self.show_time else ""
            print(f'{check} {self.prefix}{time_str} {Fore.GREEN}Done{Style.RESET_ALL}')
        else:
            cross = f"{Fore.RED}\u2717{Style.RESET_ALL}"
            print(f'{cross} {self.prefix} {Fore.RED}Failed{Style.RESET_ALL}')

        return False

    def update(self, status):
        """Update the current status message."""
        self.current_status = status

    def _animate(self):
        idx = 0
        while not self.stop:
            elapsed = time.time() - self.start_time
            spinner = self._spinner_chars[idx % len(self._spinner_chars)]

            if self.show_time:
                time_str = f" {Fore.CYAN}[{_format_time(elapsed)}]{Style.RESET_ALL}"
            else:
                time_str = ""

            status = f" - {self.current_status}" if self.current_status else ""
            status_line = f'\r{Fore.YELLOW}{spinner}{Style.RESET_ALL} {self.prefix}{status}{time_str}'

            sys.stdout.write('\r' + ' ' * 100 + '\r')
            sys.stdout.write(status_line[:100])
            sys.stdout.flush()

            idx += 1
            time.sleep(0.08)


def print_step(message, status='info'):
    """
    Print a formatted step message.

    Args:
        message: The message to display
        status: 'info', 'success', 'warning', 'error'
    """
    icons = {
        'info': f"{Fore.BLUE}\u2139{Style.RESET_ALL}",
        'success': f"{Fore.GREEN}\u2713{Style.RESET_ALL}",
        'warning': f"{Fore.YELLOW}\u26A0{Style.RESET_ALL}",
        'error': f"{Fore.RED}\u2717{Style.RESET_ALL}",
    }

    # Fallback for terminals without Unicode
    fallback_icons = {
        'info': f"{Fore.BLUE}i{Style.RESET_ALL}",
        'success': f"{Fore.GREEN}+{Style.RESET_ALL}",
        'warning': f"{Fore.YELLOW}!{Style.RESET_ALL}",
        'error': f"{Fore.RED}x{Style.RESET_ALL}",
    }

    try:
        icon = icons.get(status, icons['info'])
        sys.stdout.write(icon)
        sys.stdout.write('\r \r')
        sys.stdout.flush()
    except (UnicodeEncodeError, UnicodeDecodeError):
        icon = fallback_icons.get(status, fallback_icons['info'])

    print(f"{icon} {message}")


def print_header(title, width=60):
    """Print a formatted section header."""
    print()
    print(f"{Fore.CYAN}{'=' * width}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{title.center(width)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * width}{Style.RESET_ALL}")
    print()


def print_summary(items, title="Summary"):
    """
    Print a formatted summary box.

    Args:
        items: Dict of label: value pairs
        title: Title for the summary box
    """
    if not items:
        return

    max_label = max(len(str(k)) for k in items.keys())

    print()
    print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'-' * 40}{Style.RESET_ALL}")

    for label, value in items.items():
        print(f"  {label:<{max_label}} : {Fore.WHITE}{value}{Style.RESET_ALL}")

    print()
