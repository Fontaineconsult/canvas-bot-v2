# Canvas Bot v1.2.2 — VPAT 2.5 (WCAG Edition)

**Product:** Canvas Bot v1.2.2
**Report Date:** 2026-02-26
**Description:** Desktop GUI application (Windows, CustomTkinter) for downloading and auditing Canvas LMS course content.
**Contact:** Daniel Fontaine — fontaine@sfsu.edu
**Evaluation Methods:** Manual keyboard testing, code review, WCAG 2.1 criteria walkthrough.

## Conformance Level Key

| Term | Definition |
|------|-----------|
| **Supports** | At least one method meets the criterion without known defects. |
| **Partially Supports** | Some functionality does not meet the criterion. |
| **Does Not Support** | The majority of functionality does not meet the criterion. |
| **Not Applicable** | The criterion is not relevant to the product. |

---

## Table 1: WCAG 2.1 Level A

### Principle 1: Perceivable

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| **1.1.1 Non-text Content** | Supports | Buttons use text labels. No images or icons are used in the GUI. Tooltips provide additional text descriptions for all interactive controls. Content Viewer table rows use background color coding (green/yellow/gray) for review status, but the status value is always displayed as text in the Status column ("Passed", "Needs Review", "Ignore"), providing a text alternative. |
| **1.2.1 Audio-only and Video-only** | Not Applicable | No audio or video content in the application. |
| **1.2.2 Captions (Prerecorded)** | Not Applicable | No media content in the application. |
| **1.2.3 Audio Description or Media Alternative** | Not Applicable | No media content in the application. |
| **1.3.1 Info and Relationships** | Partially Supports | Section headings use bold font styling ("Course Selection", "Output", "Download Options", "Display Options") but are implemented as styled CTkLabel widgets, not semantic heading elements. CustomTkinter does not expose heading levels to assistive technology. Grouped controls (checkboxes in grid layout) are visually associated via section labels. Table columns have text headings. |
| **1.3.2 Meaningful Sequence** | Supports | Content is presented in logical reading order: title bar → course selection → output → options → run button → console. Tab order follows this visual sequence. |
| **1.3.3 Sensory Characteristics** | Supports | Keyboard shortcuts are indicated by underlined characters on buttons and documented in tooltips. The status bar uses text prefixes ("WARNING —") alongside orange color to distinguish error states from normal states. |
| **1.4.1 Use of Color** | Supports | Focus rings use blue (#3B8ED0) as a visual indicator but are also conveyed by border width change (0→2px). Review status buttons include text labels ("Passed", "Needs Review", "Ignore") alongside color coding. The status bar uses "WARNING —" text prefix alongside orange color for error states. Pattern test results use green/orange text color with text prefixes ("MATCH:" / "No matches"). Color is never the sole means of conveying information. |
| **1.4.2 Audio Control** | Not Applicable | No audio playback. |

### Principle 2: Operable

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| **2.1.1 Keyboard** | Supports | All functionality is keyboard-accessible. Tab/Shift+Tab navigates between widgets. Enter activates focused buttons and toggles checkboxes. Alt+key shortcuts are provided for all buttons across all tabs. Tab selectors have Alt+U/N/P and Ctrl+1/2/3 shortcuts. Pattern category list supports Up/Down arrow navigation. All dialogs have Escape to close. |
| **2.1.2 No Keyboard Trap** | Supports | Focus can always be moved away from any widget using Tab or Shift+Tab. Modal dialogs use grab_set() but provide Escape key and close buttons to exit. |
| **2.1.4 Character Key Shortcuts** | Supports | No single-character key shortcuts are used. All shortcuts require a modifier key (Alt, Ctrl). |
| **2.2.1 Timing Adjustable** | Supports | No time limits on any user interaction. Course scanning runs asynchronously without timeout. |
| **2.2.2 Pause, Stop, Hide** | Supports | Console output scrolls during scans but can be reviewed afterward. No auto-scrolling content that cannot be paused. Tooltip auto-dismiss is on mouse leave or focus out (user-controlled). |
| **2.3.1 Three Flashes or Below Threshold** | Supports | No flashing or strobing content. Console spinner animations use carriage return character replacement, not visual flashing. |
| **2.4.1 Bypass Blocks** | Not Applicable | Desktop application, not a web page with repeated content blocks. Tab switching (Alt+U/N/P) provides direct navigation to major sections. |
| **2.4.2 Page Titled** | Supports | Main window title is "Canvas Bot v1.2.2". All dialogs have descriptive titles: "Welcome to Canvas Bot", "About Canvas Bot", "Reset Configuration", "Add Pattern", "Remove Pattern", "Reset Patterns". |
| **2.4.3 Focus Order** | Supports | Focus order follows logical top-to-bottom, left-to-right sequence matching visual layout. Dialogs set initial focus on the primary action button. Entry fields receive focus before action buttons. |
| **2.4.4 Link Purpose (In Context)** | Supports | "Open Source Page" and "Open Site" buttons clearly indicate their purpose. "Open File Location" describes the action. "Browse" buttons are adjacent to their associated entry fields. |
| **2.5.1 Pointer Gestures** | Supports | No multipoint or path-based gestures. All interactions are single-click or keyboard-based. |
| **2.5.2 Pointer Cancellation** | Supports | Standard button click behavior (activated on mouse release, not press). |
| **2.5.3 Label in Name** | Supports | All buttons display their full text label. Visible text matches the accessible name. Alt+key mnemonics are indicated by underlined characters within the visible label. |
| **2.5.4 Motion Actuation** | Not Applicable | No motion-triggered functionality. |

### Principle 3: Understandable

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| **3.1.1 Language of Page** | Does Not Support | CustomTkinter does not expose a language attribute to assistive technology. The application content is in English but this is not programmatically declared. |
| **3.2.1 On Focus** | Supports | Receiving focus on any widget does not initiate a change of context. Focus rings appear but no navigation or content changes occur. |
| **3.2.2 On Input** | Supports | Changing checkbox values updates the Run button's enabled state but does not navigate away or open new content. Course ID and Course List fields are mutually exclusive (entering one clears the other) — this is expected behavior documented in the About dialog. |
| **3.3.1 Error Identification** | Supports | The Add Pattern dialog shows inline red error text ("Pattern cannot be empty", "Invalid regex: ...", "Pattern already exists") and returns focus to the input field on error. Course validation errors print to the console with "ERROR:" prefix. Status bar warning states use "WARNING —" text prefix. |
| **3.3.2 Labels or Instructions** | Supports | All entry fields have adjacent labels ("Course ID:", "Course List:", "Output Folder:"). Placeholder text provides examples ("e.g. 12345", "Path to .txt file"). Tooltips describe expected input format. The Welcome dialog provides step-by-step setup instructions. |

### Principle 4: Robust

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| **4.1.1 Parsing** | Not Applicable | Desktop application, not HTML/web content. CustomTkinter renders natively via Tcl/Tk. |
| **4.1.2 Name, Role, Value** | Does Not Support | CustomTkinter widgets do not expose standard accessibility properties (name, role, value) to platform accessibility APIs. Windows screen readers (NVDA, JAWS, Narrator) have limited ability to read CustomTkinter widget labels and states. Buttons have visible text labels but these are not reliably announced. Checkbox states are not programmatically conveyed to assistive technology. This is a framework-level limitation of CustomTkinter/Tkinter. |

---

## Table 2: WCAG 2.1 Level AA

### Principle 1: Perceivable

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| **1.3.4 Orientation** | Not Applicable | Desktop application with resizable window. No orientation restriction. |
| **1.3.5 Identify Input Purpose** | Does Not Support | CustomTkinter does not support autocomplete attributes or input purpose identification. Entry fields have visible labels and placeholder text but no programmatic input type. |
| **1.4.3 Contrast (Minimum)** | Partially Supports | Uses CustomTkinter's default "blue" theme with system appearance mode (light/dark). Primary text is dark on light (or light on dark). Focus ring blue (#3B8ED0) on default backgrounds likely meets 3:1 for UI components. Not formally tested with a contrast analyzer. Disabled/inactive UI components are exempt from contrast requirements per WCAG 1.4.3. |
| **1.4.4 Resize Text** | Partially Supports | Window is resizable (minsize 700x650). Font sizes are fixed in code (12-14pt body, 20pt title). CustomTkinter does not support system font scaling or user-adjustable text size within the application. Windows display scaling (DPI) is partially respected by Tk. |
| **1.4.5 Images of Text** | Supports | No images of text are used. All text is rendered as actual text. |
| **1.4.10 Reflow** | Partially Supports | Window resizes and content reflows horizontally. Tables use stretch columns. Minimum window size (700x650) prevents content from being hidden. Some long button text may truncate at narrow widths. |
| **1.4.11 Non-text Contrast** | Partially Supports | Focus rings (2px blue border, #3B8ED0) provide visible UI component boundaries. Default CTkButton, CTkEntry, CTkCheckBox styling uses contrasting borders. Not formally measured against the 3:1 requirement. Unfocused border color ("gray75"/"gray25") may be below 3:1 against the frame background. |
| **1.4.12 Text Spacing** | Does Not Support | CustomTkinter does not support user-overridden text spacing (line height, paragraph spacing, letter spacing, word spacing). Text rendering is controlled by Tk's font engine. |
| **1.4.13 Content on Hover or Focus** | Supports | Tooltips appear on hover (after 3s delay) and on keyboard focus. Tooltips are dismissible by moving focus or mouse away. Tooltip content does not obscure the triggering widget. |

### Principle 2: Operable

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| **2.4.5 Multiple Ways** | Supports | Multiple ways to reach each section: tab selector buttons (click), Alt+key shortcuts (Alt+U/N/P), Ctrl+number (Ctrl+1/2/3), and standard Tab key navigation. |
| **2.4.6 Headings and Labels** | Supports | Section headings are descriptive: "Course Selection", "Output", "Download Options", "Display Options", "Categories", "Test URL / Filename". All buttons and checkboxes have descriptive labels. Tab names clearly identify content type. |
| **2.4.7 Focus Visible** | Supports | All interactive widgets display a visible 2px blue (#3B8ED0) border when focused via `_add_focus_ring()`. This applies to all buttons, entry fields, checkboxes, and dynamically created category buttons. Focus is visible in both light and dark appearance modes. |

### Principle 3: Understandable

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| **3.1.2 Language of Parts** | Not Applicable | Application content is entirely in English. No mixed-language content. |
| **3.2.3 Consistent Navigation** | Supports | Title bar buttons (About, View Config, Reset Config) maintain the same position across all tabs. Tab selector bar is always visible. Content Viewer and Pattern Manager have consistent internal layouts. |
| **3.2.4 Consistent Identification** | Supports | "Browse" buttons serve the same purpose wherever they appear. "Cancel" buttons consistently close dialogs. "Open Folder" / "Open File Location" / "Open Source Page" are consistently named. Status buttons ("Passed", "Needs Review", "Ignore") use consistent labels. |
| **3.3.3 Error Suggestion** | Partially Supports | The Add Pattern dialog provides specific error text: "Invalid regex: [details]" with the regex engine's error message. Course ID validation provides clear messages. However, no suggestions are offered for correction (e.g., "Did you mean..."). |
| **3.3.4 Error Prevention (Legal, Financial, Data)** | Supports | Destructive actions require confirmation: "Reset All to Defaults" opens a confirmation dialog. "Remove Pattern" shows the pattern and requires confirmation. No legal or financial transactions occur. |

### Principle 4: Robust

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| **4.1.3 Status Messages** | Does Not Support | Status bar updates ("Status: Ready", "Status: Running...", "Status: Complete") are text-only label changes. Console output is appended to a textbox. Neither mechanism uses platform accessibility APIs to announce status changes to assistive technology. Screen readers would not be notified of status updates without polling focus. |

---

## Keyboard Shortcut Reference

### Global (always active)

| Key | Action |
|-----|--------|
| Alt+R | **R**un scan |
| Alt+V | **V**iew Config |
| Alt+C | Reset **C**onfig |
| Alt+A | **A**bout |
| Alt+U | R**u**n tab |
| Alt+N | Co**n**tent tab |
| Alt+P | **P**atterns tab |
| Ctrl+1/2/3 | Switch to tab 1/2/3 |
| Tab / Shift+Tab | Navigate forward / backward |
| Enter | Activate focused button or toggle checkbox |
| Escape | Close current dialog |

### Content Tab (active when Content tab is showing)

| Key | Action |
|-----|--------|
| Alt+F | Re**f**resh course list |
| Alt+O | **O**pen Folder |
| Alt+E | Op**e**n File Location / Open Site |
| Alt+S | Open **S**ource Page |
| Alt+D | Passe**d** (mark status) |
| Alt+W | Needs Revie**w** (mark status) |
| Alt+I | **I**gnore (mark status) |

### Patterns Tab (active when Patterns tab is showing)

| Key | Action |
|-----|--------|
| Alt+D | A**d**d Pattern |
| Alt+M | Re**m**ove Pattern |
| Alt+L | Va**l**idate |
| Alt+T | **T**est URL |
| Alt+E | R**e**set All to Defaults |
| Up/Down | Navigate category list |

---

## Known Limitations

### Framework-Level (CustomTkinter / Tkinter)

These issues cannot be resolved without migrating to a different GUI framework:

1. **No accessibility API integration** — CustomTkinter widgets do not expose name, role, or value to Windows UI Automation or MSAA. Screen readers (NVDA, JAWS, Narrator) have severely limited support.
2. **No semantic heading hierarchy** — CTkLabel has no heading level concept.
3. **No programmatic language declaration** — No equivalent to HTML `lang` attribute.
4. **No live region announcements** — Status changes cannot be pushed to screen readers.
5. **No input purpose identification** — No autocomplete or input type attributes.
6. **No user text spacing control** — Font rendering is fixed by the Tk engine.

### Application-Level (resolved)

1. ~~**Status bar uses color only**~~ — Fixed: status bar now uses "WARNING —" text prefix alongside orange color.
2. **Contrast not formally verified** — Default theme colors assumed adequate but not measured with a contrast analyzer. Disabled/inactive UI components are exempt per WCAG 1.4.3.
3. ~~**Error focus management**~~ — Fixed: Add Pattern dialog returns focus to the input field when validation fails.
4. ~~**Disabled state contrast**~~ — Not a conformance issue: WCAG 1.4.3 exempts "text that is part of an inactive user interface component."

---

## Conformance Summary

| Principle | Level A | Level AA |
|-----------|---------|----------|
| 1. Perceivable | Supports | Partially Supports |
| 2. Operable | Supports | Supports |
| 3. Understandable | Supports | Partially Supports |
| 4. Robust | Does Not Support | Does Not Support |

**Overall:** Canvas Bot v1.2.2 provides strong keyboard accessibility with comprehensive shortcuts, visible focus indicators, and logical navigation. Color is never used as the sole means of conveying information. Error states are identified with text prefixes and focus management. The primary conformance gaps are in assistive technology compatibility (inherent to the CustomTkinter framework) and formal contrast verification.
