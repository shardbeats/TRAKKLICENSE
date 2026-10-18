"""App shell: menubar File/View/Help. No toolbars, no sidebars."""
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from .constants import VIEW_NAMES, VIEW_SHORTCUTS


def build_shell(window: QMainWindow, tabs: QStackedWidget, slots: dict) -> dict:
    """Create menubar actions on `window`. `slots` needs keys:
    generate, export_pdf, save, settings, close, legal, about, show_view(index).
    Returns {"view_actions": [...]}.
    """
    window.act_generate = QAction("Generate preview", window)
    window.act_generate.setShortcut("F5")
    window.act_generate.triggered.connect(slots["generate"])
    window.act_pdf = QAction("Export PDF", window)
    window.act_pdf.triggered.connect(slots["export_pdf"])
    window.act_save = QAction("Save to history", window)
    window.act_save.triggered.connect(slots["save"])
    window.act_settings = QAction("Settings…", window)
    window.act_settings.triggered.connect(slots["settings"])
    window.act_quit = QAction("Exit", window)
    window.act_quit.triggered.connect(slots["close"])

    menubar = window.menuBar()
    m_file = menubar.addMenu("&File")
    m_file.addAction(window.act_generate)
    m_file.addSeparator()
    m_file.addAction(window.act_pdf)
    m_file.addAction(window.act_save)
    m_file.addSeparator()
    m_file.addAction(window.act_settings)
    m_file.addSeparator()
    m_file.addAction(window.act_quit)

    m_view = menubar.addMenu("&View")
    window._view_group = QActionGroup(window)
    window._view_group.setExclusive(True)
    window._view_actions = []
    for i, (label, shortcut) in enumerate(zip(VIEW_NAMES, VIEW_SHORTCUTS)):
        act = QAction(label, window, checkable=True)
        act.setShortcut(shortcut)
        act.triggered.connect(lambda checked=False, idx=i: slots["show_view"](idx))
        m_view.addAction(act)
        window._view_group.addAction(act)
        window._view_actions.append(act)
    window._view_actions[0].setChecked(True)
    tabs.currentChanged.connect(
        lambda idx: window._view_actions[idx].setChecked(True)
        if 0 <= idx < len(window._view_actions) else None)

    m_help = menubar.addMenu("&Help")
    act_about = QAction("About TRAKKLICENSE…", window)
    act_about.triggered.connect(slots["about"])
    m_help.addAction(act_about)
    act_legal = QAction("Legal disclaimer…", window)
    act_legal.triggered.connect(slots["legal"])
    m_help.addAction(act_legal)
    return {"view_actions": window._view_actions}
