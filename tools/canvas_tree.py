"""
Enhanced Canvas Tree visualization with colors, icons, statistics, and URLs.
"""

import sys
from treelib import Tree
import warnings
from colorama import Fore, Style, init
from collections import defaultdict

init()

# Icons for different node types
ICONS = {
    # Resource nodes (organizational)
    'Modules': '\U0001F4DA',        # Books
    'Module': '\U0001F4D6',         # Open book
    'Pages': '\U0001F4C4',          # Page
    'Page': '\U0001F4C4',           # Page
    'Assignments': '\U0001F4DD',    # Memo
    'Assignment': '\U0001F4DD',     # Memo
    'Quizzes': '\u2753',            # Question mark
    'Quiz': '\u2753',               # Question mark
    'Discussions': '\U0001F4AC',    # Speech bubble
    'Discussion': '\U0001F4AC',     # Speech bubble
    'Announcements': '\U0001F4E2',  # Loudspeaker
    'Announcement': '\U0001F4E2',   # Loudspeaker
    'CanvasFiles': '\U0001F4C1',    # Folder
    'CanvasMediaObjects': '\U0001F3AC',  # Clapper board
    'CanvasStudio': '\U0001F3A5',   # Movie camera

    # Content nodes (leaf items)
    'Document': '\U0001F4C4',       # Page
    'DocumentSite': '\U0001F310',   # Globe
    'VideoFile': '\U0001F3AC',      # Clapper board
    'VideoSite': '\U0001F4F9',      # Video camera
    'AudioFile': '\U0001F3B5',      # Musical note
    'AudioSite': '\U0001F399',      # Microphone
    'ImageFile': '\U0001F5BC',      # Framed picture
    'FileStorageSite': '\u2601',    # Cloud
    'DigitalTextbook': '\U0001F4DA', # Books
    'CanvasMediaEmbed': '\U0001F39E', # Film frames
    'CanvasStudioEmbed': '\U0001F3A5', # Movie camera
    'Unsorted': '\u2753',           # Question mark
    'BoxPage': '\U0001F4E6',        # Package
}

# Fallback ASCII icons for terminals without Unicode
ICONS_ASCII = {
    'Modules': '[M]',
    'Module': '[m]',
    'Pages': '[P]',
    'Page': '[p]',
    'Assignments': '[A]',
    'Assignment': '[a]',
    'Quizzes': '[Q]',
    'Quiz': '[q]',
    'Discussions': '[D]',
    'Discussion': '[d]',
    'Announcements': '[!]',
    'Announcement': '[!]',
    'CanvasFiles': '[F]',
    'CanvasMediaObjects': '[V]',
    'CanvasStudio': '[S]',
    'Document': '[doc]',
    'DocumentSite': '[web]',
    'VideoFile': '[vid]',
    'VideoSite': '[yt]',
    'AudioFile': '[aud]',
    'AudioSite': '[pod]',
    'ImageFile': '[img]',
    'FileStorageSite': '[box]',
    'DigitalTextbook': '[txt]',
    'CanvasMediaEmbed': '[med]',
    'CanvasStudioEmbed': '[stu]',
    'Unsorted': '[?]',
    'BoxPage': '[box]',
}

# Colors for different node types
COLORS = {
    # Resource nodes - blue/cyan tones
    'Modules': Fore.CYAN,
    'Module': Fore.CYAN,
    'Pages': Fore.BLUE,
    'Page': Fore.BLUE,
    'Assignments': Fore.MAGENTA,
    'Assignment': Fore.MAGENTA,
    'Quizzes': Fore.YELLOW,
    'Quiz': Fore.YELLOW,
    'Discussions': Fore.GREEN,
    'Discussion': Fore.GREEN,
    'Announcements': Fore.RED,
    'Announcement': Fore.RED,
    'CanvasFiles': Fore.WHITE,
    'CanvasMediaObjects': Fore.LIGHTMAGENTA_EX,
    'CanvasStudio': Fore.LIGHTCYAN_EX,

    # Content nodes - lighter tones
    'Document': Fore.LIGHTCYAN_EX,
    'DocumentSite': Fore.LIGHTBLUE_EX,
    'VideoFile': Fore.LIGHTMAGENTA_EX,
    'VideoSite': Fore.LIGHTRED_EX,
    'AudioFile': Fore.LIGHTYELLOW_EX,
    'AudioSite': Fore.LIGHTYELLOW_EX,
    'ImageFile': Fore.LIGHTGREEN_EX,
    'FileStorageSite': Fore.LIGHTWHITE_EX,
    'DigitalTextbook': Fore.LIGHTCYAN_EX,
    'CanvasMediaEmbed': Fore.LIGHTMAGENTA_EX,
    'CanvasStudioEmbed': Fore.LIGHTCYAN_EX,
    'Unsorted': Fore.WHITE,
    'BoxPage': Fore.LIGHTYELLOW_EX,
}


def _supports_unicode():
    """Check if the terminal supports Unicode output."""
    try:
        # Try to encode a Unicode character
        '\u2713'.encode(sys.stdout.encoding or 'utf-8')
        return True
    except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
        return False


# Cache the Unicode support check
_UNICODE_SUPPORT = None

def _use_unicode():
    """Check if we should use Unicode (cached)."""
    global _UNICODE_SUPPORT
    if _UNICODE_SUPPORT is None:
        _UNICODE_SUPPORT = _supports_unicode()
    return _UNICODE_SUPPORT


def _get_icon(node_type):
    """Get icon for node type with fallback."""
    if _use_unicode():
        return ICONS.get(node_type, '\u2022')  # Default bullet
    else:
        return ICONS_ASCII.get(node_type, '*')


def _get_arrow():
    """Get arrow character for URL lines."""
    return '↳' if _use_unicode() else '->'


def _get_tree_chars():
    """Get tree drawing characters."""
    if _use_unicode():
        return {'pipe': '│', 'branch': '├', 'last': '└', 'dash': '─'}
    else:
        return {'pipe': '|', 'branch': '+', 'last': '\\', 'dash': '-'}


def _truncate(text, max_length=50):
    """Truncate text with ellipsis."""
    if not text:
        return ""
    text = str(text)
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text


def _get_node_urls(node):
    """
    Extract all relevant URLs from a node.

    Returns dict with:
        - view_url: URL to view the resource in Canvas
        - download_url: Direct download URL (if applicable)
        - content_url: URL of the actual content (video link, document URL, etc.)
        - source_page_url: URL of the Canvas page where this content was found (assignment, page, etc.)
    """
    urls = {
        'view_url': None,
        'download_url': None,
        'content_url': None,
        'source_page_url': None,
    }

    # View URL - Canvas page to view this resource
    urls['view_url'] = getattr(node, 'html_url', None)

    # Download URL - direct download link
    urls['download_url'] = getattr(node, 'download_url', None)
    if not urls['download_url']:
        # Some nodes have 'url' as the download URL
        url = getattr(node, 'url', None)
        if url and ('download' in str(url) or 'files' in str(url)):
            urls['download_url'] = url

    # Content URL - the actual content link (YouTube, external site, etc.)
    urls['content_url'] = getattr(node, 'url', None)

    # Source page URL - traverse up to find the actual Canvas resource page
    # (Assignment, Page, Quiz, Discussion, etc.) not just the immediate parent
    if hasattr(node, 'parent'):
        urls['source_page_url'] = _find_source_page_url(node.parent)

    return urls


def _find_source_page_url(node):
    """
    Traverse up the tree to find the actual Canvas resource URL.
    Looks for html_url on Assignment, Page, Quiz, Discussion, Module, etc.
    Skips container nodes like 'Modules', 'Pages', 'Assignments' (plural).
    """
    # Container types that don't have meaningful URLs
    container_types = ('Modules', 'Pages', 'Assignments', 'Quizzes',
                       'Discussions', 'Announcements', 'CanvasFiles',
                       'CanvasMediaObjects', 'CanvasStudio')

    current = node
    max_depth = 10  # Prevent infinite loops

    for _ in range(max_depth):
        if current is None:
            break

        # Check if this node has a root_node attribute (means it's the course root)
        if hasattr(current, 'root_node'):
            break

        node_type = current.__class__.__name__

        # Skip container nodes
        if node_type in container_types:
            current = getattr(current, 'parent', None)
            continue

        # Look for html_url first (preferred Canvas URL)
        html_url = getattr(current, 'html_url', None)
        if html_url and 'instructure.com' in str(html_url):
            # Make sure it's not just a course URL
            if '/assignments/' in str(html_url) or \
               '/pages/' in str(html_url) or \
               '/quizzes/' in str(html_url) or \
               '/discussion_topics/' in str(html_url) or \
               '/announcements/' in str(html_url) or \
               '/modules/' in str(html_url):
                return html_url

        # Move up the tree
        current = getattr(current, 'parent', None)

    return None


def _format_url(url, label=None, max_length=60):
    """Format a URL for display with optional label."""
    if not url:
        return None

    url_str = str(url)
    if len(url_str) > max_length:
        url_str = url_str[:max_length - 3] + "..."

    if label:
        return f"{Fore.LIGHTBLACK_EX}{label}: {Style.RESET_ALL}{Fore.BLUE}{url_str}{Style.RESET_ALL}"
    return f"{Fore.BLUE}{url_str}{Style.RESET_ALL}"


def _format_node_display(node, show_urls=True):
    """Create a formatted display string for a node."""
    node_type = node.__class__.__name__
    color = COLORS.get(node_type, Fore.WHITE)
    icon = _get_icon(node_type)

    # Check if it's a content node (has is_content attribute)
    is_content = getattr(node, 'is_content', False)

    if is_content:
        # Content node - show more details
        from core.content_scaffolds import is_hidden

        hidden = is_hidden(node) if hasattr(node, 'parent') else False
        hidden_indicator = f"{Fore.RED}[hidden]{Style.RESET_ALL} " if hidden else ""

        # Get title or URL
        title = getattr(node, 'title', None) or getattr(node, 'url', None) or 'Untitled'
        title = _truncate(title, 40)

        # For video sites, show caption status if available
        caption_info = ""
        if node_type in ('VideoSite', 'VideoFile', 'CanvasStudioEmbed'):
            captioned = getattr(node, 'captioned', None)
            if captioned is True:
                caption_info = f" {Fore.GREEN}[CC]{Style.RESET_ALL}"
            elif captioned is False:
                caption_info = f" {Fore.RED}[no CC]{Style.RESET_ALL}"

        # Build main line
        main_line = f"{icon} {color}{node_type}{Style.RESET_ALL} {hidden_indicator}{Fore.WHITE}{title}{Style.RESET_ALL}{caption_info}"

        # Add URLs if requested
        if show_urls:
            urls = _get_node_urls(node)
            url_lines = []

            # Show content URL (the actual link) - this is the main URL we care about
            tc = _get_tree_chars()
            arrow = _get_arrow()
            if urls['content_url']:
                url_lines.append(f"{tc['pipe']}         {Fore.LIGHTBLACK_EX}{arrow}{Style.RESET_ALL} {Fore.BLUE}{urls['content_url']}{Style.RESET_ALL}")

            # Show download URL only if different from content URL (avoid repetition)
            if urls['download_url'] and urls['download_url'] != urls['content_url']:
                # Check if they're substantially different (not just query params)
                content_base = urls['content_url'].split('?')[0] if urls['content_url'] else ''
                download_base = urls['download_url'].split('?')[0] if urls['download_url'] else ''
                if content_base != download_base:
                    url_lines.append(f"{tc['pipe']}         {Fore.LIGHTBLACK_EX}{arrow} Download:{Style.RESET_ALL} {Fore.GREEN}{urls['download_url']}{Style.RESET_ALL}")

            if url_lines:
                main_line += "\n" + "\n".join(url_lines)

        return main_line

    else:
        # Resource node - show title and view URL
        title = getattr(node, 'title', None) or node_type
        title = _truncate(title, 45)

        # Count children if available
        children = getattr(node, 'children', [])
        child_count = ""
        if children:
            content_count = sum(1 for c in children if getattr(c, 'is_content', False))
            resource_count = len(children) - content_count
            if content_count > 0 or resource_count > 0:
                parts = []
                if resource_count > 0:
                    parts.append(f"{resource_count} items")
                if content_count > 0:
                    parts.append(f"{content_count} content")
                child_count = f" {Fore.CYAN}({', '.join(parts)}){Style.RESET_ALL}"

        main_line = f"{icon} {color}{node_type}{Style.RESET_ALL}: {Fore.WHITE}{title}{Style.RESET_ALL}{child_count}"

        # Add view URL for resource nodes (Assignment, Page, Quiz, Discussion, Module, etc.)
        # Skip container nodes like Modules, Pages, Assignments (plural)
        if show_urls:
            container_types = ('Modules', 'Pages', 'Assignments', 'Quizzes',
                              'Discussions', 'Announcements', 'CanvasFiles',
                              'CanvasMediaObjects', 'CanvasStudio')

            if node_type not in container_types:
                # Try multiple URL attributes - Canvas API uses different names
                view_url = (
                    getattr(node, 'html_url', None) or
                    getattr(node, 'preview_url', None) or
                    getattr(node, 'items_url', None)  # For modules
                )

                # If no direct URL, try to construct one from course_url and id
                if not view_url and hasattr(node, 'root'):
                    course_url = getattr(node.root, 'course_url', None)
                    item_id = getattr(node, 'item_id', None) or getattr(node, 'id', None)

                    if course_url and item_id:
                        # Map node types to URL paths
                        url_paths = {
                            'Assignment': 'assignments',
                            'Page': 'pages',
                            'Quiz': 'quizzes',
                            'Discussion': 'discussion_topics',
                            'Announcement': 'discussion_topics',
                            'Module': 'modules',
                        }
                        path = url_paths.get(node_type)
                        if path:
                            # For pages, use page_id or url attribute
                            if node_type == 'Page':
                                page_url = getattr(node, 'url', None)  # This is the page slug
                                if page_url:
                                    view_url = f"{course_url}/pages/{page_url}"
                                else:
                                    view_url = f"{course_url}/pages/{item_id}"
                            else:
                                view_url = f"{course_url}/{path}/{item_id}"

                if view_url:
                    tc = _get_tree_chars()
                    arrow = _get_arrow()
                    main_line += f"\n{tc['pipe']}         {Fore.LIGHTBLACK_EX}{arrow}{Style.RESET_ALL} {Fore.CYAN}{view_url}{Style.RESET_ALL}"

        return main_line


class CanvasTree:
    """
    Enhanced tree visualization for Canvas course content.
    Uses treelib with improved formatting, colors, statistics, and URLs.
    """

    def __init__(self):
        self.tree = Tree()
        self._node_registry = {}  # Track nodes for statistics
        self._stats = defaultdict(int)
        self._show_urls = True  # Default to showing URLs

    def init_node(self, root):
        """Initialize the root node of the tree."""
        course_url = getattr(root, 'course_url', '') or ''
        # Use graduation cap or [C] for course root
        root_icon = '\U0001F393' if _use_unicode() else '[C]'
        display = f"{root_icon} {Fore.CYAN}{root.title}{Style.RESET_ALL} {Fore.WHITE}| Course ID: {root.course_id}{Style.RESET_ALL}"
        if course_url:
            tc = _get_tree_chars()
            arrow = _get_arrow()
            display += f"\n{tc['pipe']}  {Fore.LIGHTBLACK_EX}{arrow}{Style.RESET_ALL} {Fore.CYAN}{course_url}{Style.RESET_ALL}"
        self.tree.create_node(display, str(id(root)))
        self._node_registry[str(id(root))] = root

    def add_node(self, node):
        """Add a node to the tree with enhanced formatting."""
        node_display = _format_node_display(node, show_urls=self._show_urls)
        node_value = str(id(node))
        parent = str(id(node.parent))

        try:
            self.tree.create_node(node_display, node_value, parent)
            self._node_registry[node_value] = node

            # Track statistics
            node_type = node.__class__.__name__
            self._stats[node_type] += 1

            if getattr(node, 'is_content', False):
                self._stats['_total_content'] += 1
                from core.content_scaffolds import is_hidden
                if is_hidden(node):
                    self._stats['_hidden_content'] += 1
            else:
                self._stats['_total_resources'] += 1

        except Exception as e:
            warnings.warn(f"Could not add node {node}: {e}")

    def show_nodes(self, show_stats=True, show_urls=True):
        """
        Display the tree with optional statistics and URLs.

        Args:
            show_stats: Show content statistics summary
            show_urls: Show URLs for each item
        """
        # Refresh all node displays before showing
        # This ensures URLs are captured after all attributes are set
        self._refresh_node_displays(show_urls)

        if show_stats:
            self._print_header()

        # Show the tree
        print(self.tree.show(stdout=False))

        if show_stats:
            self._print_statistics()
            self._print_url_legend()

    def _refresh_node_displays(self, show_urls=True):
        """
        Refresh all node display strings.
        Called before showing to ensure all URLs are captured
        (since html_url may not be set when add_node was called).
        """
        for node_id, node in self._node_registry.items():
            # Skip the root node (it's formatted differently)
            if hasattr(node, 'root_node'):
                continue

            try:
                new_display = _format_node_display(node, show_urls=show_urls)
                tree_node = self.tree.get_node(node_id)
                if tree_node:
                    tree_node.tag = new_display
            except Exception:
                pass  # Keep original display if refresh fails

    def _print_header(self):
        """Print a header for the tree display."""
        print()
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'COURSE CONTENT TREE':^80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print()

    def _print_statistics(self):
        """Print content statistics summary."""
        print()
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'CONTENT SUMMARY':^80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print()

        # Group stats by category
        resources = []
        content = []

        for node_type, count in sorted(self._stats.items()):
            if node_type.startswith('_'):
                continue
            if node_type in ('Document', 'DocumentSite', 'VideoFile', 'VideoSite',
                           'AudioFile', 'AudioSite', 'ImageFile', 'FileStorageSite',
                           'DigitalTextbook', 'CanvasMediaEmbed', 'CanvasStudioEmbed',
                           'Unsorted', 'BoxPage'):
                content.append((node_type, count))
            else:
                resources.append((node_type, count))

        # Print resources
        if resources:
            print(f"  {Fore.YELLOW}Resources:{Style.RESET_ALL}")
            for node_type, count in resources:
                icon = _get_icon(node_type)
                color = COLORS.get(node_type, Fore.WHITE)
                print(f"    {icon} {color}{node_type:<20}{Style.RESET_ALL} {count:>5}")
            print()

        # Print content
        if content:
            print(f"  {Fore.YELLOW}Content Items:{Style.RESET_ALL}")
            for node_type, count in content:
                icon = _get_icon(node_type)
                color = COLORS.get(node_type, Fore.WHITE)
                print(f"    {icon} {color}{node_type:<20}{Style.RESET_ALL} {count:>5}")
            print()

        # Print totals
        total_content = self._stats.get('_total_content', 0)
        hidden_content = self._stats.get('_hidden_content', 0)
        visible_content = total_content - hidden_content

        print(f"  {Fore.CYAN}{'-' * 40}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Total Content Items:{Style.RESET_ALL}  {total_content:>5}")
        print(f"    {Fore.GREEN}Visible:{Style.RESET_ALL}             {visible_content:>5}")
        print(f"    {Fore.RED}Hidden:{Style.RESET_ALL}              {hidden_content:>5}")
        print()

    def _print_url_legend(self):
        """Print legend explaining URL labels."""
        print(f"  {Fore.YELLOW}URL Labels:{Style.RESET_ALL}")
        print(f"    {Fore.LIGHTBLACK_EX}URL:{Style.RESET_ALL}       Content URL (video link, document, external site)")
        print(f"    {Fore.LIGHTBLACK_EX}Download:{Style.RESET_ALL}  Direct download link for Canvas files")
        print(f"    {Fore.LIGHTBLACK_EX}Found on:{Style.RESET_ALL}  Canvas page where this content was embedded")
        print(f"    {Fore.LIGHTBLACK_EX}View:{Style.RESET_ALL}      Canvas page URL for modules, assignments, etc.")
        print()
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print()

    def get_statistics(self):
        """Return statistics as a dictionary."""
        return dict(self._stats)

    def get_all_urls(self):
        """
        Get all URLs from all nodes in the tree.

        Returns:
            List of dicts containing node info and URLs
        """
        url_list = []

        for node_id, node in self._node_registry.items():
            if not getattr(node, 'is_content', False):
                continue

            urls = _get_node_urls(node)
            node_type = node.__class__.__name__
            title = getattr(node, 'title', None) or 'Untitled'

            url_list.append({
                'type': node_type,
                'title': title,
                'content_url': urls['content_url'],
                'download_url': urls['download_url'],
                'source_page_url': urls['source_page_url'],
                'view_url': urls['view_url'],
            })

        return url_list

    def filter_by_type(self, content_types):
        """
        Get nodes filtered by content type.

        Args:
            content_types: List of content type names (e.g., ['Document', 'VideoFile'])

        Returns:
            List of matching nodes
        """
        return [
            node for node in self._node_registry.values()
            if node.__class__.__name__ in content_types
        ]

    def print_legend(self):
        """Print a legend of icons and their meanings."""
        print()
        print(f"{Fore.CYAN}{'LEGEND':^50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'-' * 50}{Style.RESET_ALL}")

        print(f"\n  {Fore.YELLOW}Resource Types:{Style.RESET_ALL}")
        resource_types = ['Module', 'Page', 'Assignment', 'Quiz', 'Discussion', 'Announcement']
        for rt in resource_types:
            icon = _get_icon(rt)
            color = COLORS.get(rt, Fore.WHITE)
            print(f"    {icon} {color}{rt}{Style.RESET_ALL}")

        print(f"\n  {Fore.YELLOW}Content Types:{Style.RESET_ALL}")
        content_types = ['Document', 'VideoFile', 'VideoSite', 'AudioFile', 'ImageFile', 'Unsorted']
        for ct in content_types:
            icon = _get_icon(ct)
            color = COLORS.get(ct, Fore.WHITE)
            print(f"    {icon} {color}{ct}{Style.RESET_ALL}")

        print(f"\n  {Fore.YELLOW}Status Indicators:{Style.RESET_ALL}")
        print(f"    {Fore.RED}[hidden]{Style.RESET_ALL}  - Content hidden from students")
        print(f"    {Fore.GREEN}[CC]{Style.RESET_ALL}      - Video has captions")
        print(f"    {Fore.RED}[no CC]{Style.RESET_ALL}   - Video missing captions")

        print(f"\n  {Fore.YELLOW}URL Colors:{Style.RESET_ALL}")
        print(f"    {Fore.BLUE}Blue{Style.RESET_ALL}      - Content/external URLs")
        print(f"    {Fore.GREEN}Green{Style.RESET_ALL}     - Download URLs")
        print(f"    {Fore.CYAN}Cyan{Style.RESET_ALL}      - Canvas page URLs")
        print()


def print_url_report(tree):
    """
    Print a detailed URL report from a CanvasTree.

    Args:
        tree: CanvasTree instance
    """
    urls = tree.get_all_urls()

    print()
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'URL REPORT':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print()

    # Group by type
    by_type = defaultdict(list)
    for item in urls:
        by_type[item['type']].append(item)

    for content_type, items in sorted(by_type.items()):
        icon = _get_icon(content_type)
        color = COLORS.get(content_type, Fore.WHITE)

        print(f"{icon} {color}{content_type}{Style.RESET_ALL} ({len(items)} items)")
        print(f"{Fore.CYAN}{'-' * 60}{Style.RESET_ALL}")

        for item in items[:10]:  # Limit to first 10 per type
            print(f"  {Fore.WHITE}{_truncate(item['title'], 50)}{Style.RESET_ALL}")
            if item['content_url']:
                print(f"    {Fore.BLUE}{item['content_url']}{Style.RESET_ALL}")
            if item['download_url'] and item['download_url'] != item['content_url']:
                print(f"    {Fore.GREEN}Download: {item['download_url']}{Style.RESET_ALL}")

        if len(items) > 10:
            print(f"  {Fore.LIGHTBLACK_EX}... and {len(items) - 10} more{Style.RESET_ALL}")
        print()

    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
