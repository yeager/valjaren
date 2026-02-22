"""Väljaren - Visual decision helper for children with autism/NPF."""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import gettext
import locale
import os
import random
import json

__version__ = "0.1.0"
APP_ID = "se.danielnylander.valjaren"
LOCALE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'share', 'locale')
if not os.path.isdir(LOCALE_DIR):
    LOCALE_DIR = "/usr/share/locale"
try:
    locale.bindtextdomain(APP_ID, LOCALE_DIR)
    gettext.bindtextdomain(APP_ID, LOCALE_DIR)
    gettext.textdomain(APP_ID)
except Exception:
    pass
_ = gettext.gettext

# Default choice categories
CATEGORIES = [
    {"name": N_("Food"), "icon": "🍕", "choices": [
        N_("Pizza"), N_("Pasta"), N_("Pancakes"), N_("Sandwich"), N_("Soup")]},
    {"name": N_("Activity"), "icon": "🎮", "choices": [
        N_("Drawing"), N_("Reading"), N_("Playing"), N_("Building"), N_("Music")]},
    {"name": N_("Clothing"), "icon": "👕", "choices": [
        N_("T-shirt"), N_("Sweater"), N_("Jacket"), N_("Hoodie")]},
    {"name": N_("Feelings"), "icon": "😊", "choices": [
        N_("Happy"), N_("Calm"), N_("Tired"), N_("Excited"), N_("Worried")]},
]

def N_(s): return s


class ChoiceCard(Gtk.Button):
    """A large clickable card for a choice."""
    def __init__(self, text, color_index=0):
        super().__init__()
        colors = ["#7c3aed", "#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"]
        color = colors[color_index % len(colors)]
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(16)
        box.set_margin_end(16)
        
        label = Gtk.Label(label=text)
        label.add_css_class("title-2")
        box.append(label)
        
        self.set_child(box)
        self.add_css_class("card")
        self.set_hexpand(True)
        self.set_vexpand(True)


class ValjarenWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title(_("Väljaren"))
        self.set_default_size(600, 500)
        self._history = []

        header = Adw.HeaderBar()
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu = Gio.Menu()
        menu.append(_("About"), "app.about")
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # Categories page
        cat_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        cat_page.set_margin_top(24)
        cat_page.set_margin_bottom(24)
        cat_page.set_margin_start(24)
        cat_page.set_margin_end(24)

        title = Gtk.Label(label=_("What do you want to choose?"))
        title.add_css_class("title-2")
        cat_page.append(title)

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(2)
        grid.set_min_children_per_line(2)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_homogeneous(True)
        grid.set_row_spacing(12)
        grid.set_column_spacing(12)

        for i, cat in enumerate(CATEGORIES):
            btn = Gtk.Button()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box.set_margin_top(16)
            box.set_margin_bottom(16)
            icon = Gtk.Label(label=cat["icon"])
            icon.add_css_class("title-1")
            box.append(icon)
            name = Gtk.Label(label=_(cat["name"]))
            name.add_css_class("title-4")
            box.append(name)
            btn.set_child(box)
            btn.add_css_class("card")
            btn.connect("clicked", self._on_category, i)
            grid.insert(btn, -1)

        # Custom choice button
        custom_btn = Gtk.Button()
        cbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cbox.set_margin_top(16)
        cbox.set_margin_bottom(16)
        ci = Gtk.Label(label="✏️")
        ci.add_css_class("title-1")
        cbox.append(ci)
        cn = Gtk.Label(label=_("Custom"))
        cn.add_css_class("title-4")
        cbox.append(cn)
        custom_btn.set_child(cbox)
        custom_btn.add_css_class("card")
        custom_btn.connect("clicked", self._on_custom)
        grid.insert(custom_btn, -1)

        cat_page.append(grid)
        self._stack.add_titled(cat_page, "categories", _("Choose"))

        # Choices page
        self._choices_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self._choices_page.set_margin_top(24)
        self._choices_page.set_margin_bottom(24)
        self._choices_page.set_margin_start(24)
        self._choices_page.set_margin_end(24)

        self._choice_title = Gtk.Label()
        self._choice_title.add_css_class("title-2")
        self._choices_page.append(self._choice_title)

        self._choices_flow = Gtk.FlowBox()
        self._choices_flow.set_max_children_per_line(2)
        self._choices_flow.set_min_children_per_line(2)
        self._choices_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._choices_flow.set_homogeneous(True)
        self._choices_flow.set_row_spacing(12)
        self._choices_flow.set_column_spacing(12)
        self._choices_flow.set_vexpand(True)
        self._choices_page.append(self._choices_flow)

        back_btn = Gtk.Button(label=_("← Back"))
        back_btn.add_css_class("pill")
        back_btn.connect("clicked", lambda b: self._stack.set_visible_child_name("categories"))
        self._choices_page.append(back_btn)

        self._stack.add_titled(self._choices_page, "choices", _("Choices"))

        # Result page
        self._result_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self._result_page.set_margin_top(48)
        self._result_page.set_margin_bottom(48)
        self._result_page.set_margin_start(24)
        self._result_page.set_margin_end(24)
        self._result_page.set_valign(Gtk.Align.CENTER)

        self._result_icon = Gtk.Label(label="🎉")
        self._result_icon.add_css_class("title-1")
        self._result_page.append(self._result_icon)

        self._result_label = Gtk.Label(label=_("You chose:"))
        self._result_label.add_css_class("title-3")
        self._result_page.append(self._result_label)

        self._result_choice = Gtk.Label()
        self._result_choice.add_css_class("title-1")
        self._result_page.append(self._result_choice)

        result_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        result_btns.set_halign(Gtk.Align.CENTER)
        
        again_btn = Gtk.Button(label=_("Choose again"))
        again_btn.add_css_class("suggested-action")
        again_btn.add_css_class("pill")
        again_btn.connect("clicked", lambda b: self._stack.set_visible_child_name("categories"))
        result_btns.append(again_btn)

        self._result_page.append(result_btns)
        self._stack.add_titled(self._result_page, "result", _("Result"))

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(header)
        main_box.append(self._stack)
        self.set_content(main_box)

    def _on_category(self, btn, index):
        cat = CATEGORIES[index]
        self._show_choices(_(cat["name"]), [_(c) for c in cat["choices"]])

    def _on_custom(self, btn):
        # Show simple 2-choice dialog
        self._show_choices(_("Custom"), [_("Option A"), _("Option B")])

    def _show_choices(self, title, choices):
        self._choice_title.set_text(title)
        # Clear old
        while child := self._choices_flow.get_first_child():
            self._choices_flow.remove(child)
        
        for i, choice in enumerate(choices):
            card = ChoiceCard(choice, i)
            card.connect("clicked", self._on_choice_made, choice)
            self._choices_flow.insert(card, -1)
        
        self._stack.set_visible_child_name("choices")

    def _on_choice_made(self, btn, choice):
        self._result_choice.set_text(choice)
        self._history.append(choice)
        self._stack.set_visible_child_name("result")


class ValjarenApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def _on_activate(self, app):
        win = ValjarenWindow(application=app)
        win.present()

    def _on_about(self, action, param):
        about = Adw.AboutDialog(
            application_name=_("Väljaren"),
            application_icon=APP_ID,
            version=__version__,
            developer_name="Daniel Nylander",
            website="https://github.com/yeager/valjaren",
            license_type=Gtk.License.GPL_3_0,
            comments=_("Visual decision helper for children with autism/NPF"),
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
        )
        about.present(self.get_active_window())

def main():
    app = ValjarenApp()
    app.run()

if __name__ == "__main__":
    main()
