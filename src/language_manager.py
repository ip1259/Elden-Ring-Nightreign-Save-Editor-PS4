import os
import tkinter as tk
import threading
import gettext
import logging
from globals import WORKING_DIR


logger = logging.getLogger(__name__)


class LanguageManager:
    _instance = None
    _lock = threading.Lock()  # Lock for Singleton instantiation

    def __new__(cls):
        # Double-Checked Locking pattern for thread-safe singleton
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LanguageManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._widgets = []  # List of dicts: {"widget": w, "key": k, "attr": a, "kwargs": kw}
        self._list_lock = threading.Lock()  # Lock for thread-safe list operations
        self._translate_func = lambda s: s
        self._initialized = True

    def register(self, widget, text_key, attr="text", **kwargs):
        """
        Thread-safe registration of a widget for language updates.
        :param widget: The Tkinter widget instance.
        :param text_key: The string constant to be translated (recognized by xgettext).
        :param attr: The widget attribute to update (default is "text").
        :param kwargs: Optional formatting variables for the string.
        """
        with self._list_lock:
            entry = {
                "widget": widget,
                "key": text_key,
                "attr": attr,
                "kwargs": kwargs
            }
            self._widgets.append(entry)

        # Initial translation update
        self._update_widget(entry)

    def refresh_all(self):
        """
        Thread-safe refresh of all registered widgets.
        Can be safely called from background threads.
        """
        with self._list_lock:
            # 1. Filter out destroyed widgets to prevent memory leaks
            self._widgets = [item for item in self._widgets if item["widget"].winfo_exists()]

            # 2. Batch update remaining widgets
            for item in self._widgets:
                self._safe_gui_update(item)

    def _safe_gui_update(self, item):
        """
        Ensures UI updates happen on the Tkinter Main Thread.
        Uses widget.after() to schedule the update if called from another thread.
        """
        widget = item["widget"]
        if widget.winfo_exists():
            # Schedule the update on the main thread's event loop
            widget.after(0, lambda: self._update_widget(item))

    def _update_widget(self, item):
        try:
            widget = item["widget"]
            if not widget.winfo_exists():
                return

            translated = self._translate_func(item["key"])
            if item["kwargs"]:
                translated = translated.format(**item["kwargs"])

            attr = item["attr"]

            if attr == "tab":
                # For tabs, 'widget' is the page (Frame),
                # its master is the Notebook.
                notebook = widget.master
                notebook.tab(widget, text=translated)

            # Special handling for window titles
            elif attr == "title" and isinstance(widget, (tk.Toplevel, tk.Tk)):
                widget.title(translated)

            # Standard widget attributes (text, caption, etc.)
            else:
                widget[attr] = translated
        except Exception as e:
            logger.error(f"LanguageManager Update Error: {e}")

    def load_language(self, lang_code, localedir=WORKING_DIR / 'locales'):
        """
        Loads the .mo file and triggers a UI refresh for all registered widgets.
        """
        try:
            # Create translation object and install _() into builtins
            trans = gettext.translation(
                lang_code,
                localedir=localedir,
                languages=[lang_code],
                fallback=True
            )
            self._translate_func = trans.gettext
            trans.install()
            self.current_lang = lang_code

            # Refresh all registered UI elements
            self.refresh_all()
            return True
        except Exception as e:
            logger.error(f"LanguageManager Error: Failed to load {lang_code}: {e}")
            return False


# Global singleton instance
lang_mgr = LanguageManager()


N_ = lambda s: s
