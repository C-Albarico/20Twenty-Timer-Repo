# Import necessary modules
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import os
import winsound
import random
import sys
import ctypes
import ctypes.wintypes
import subprocess

# Utility to get idle duration

def get_idle_duration_seconds():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.wintypes.UINT), ("dwTime", ctypes.wintypes.DWORD)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0

CONFIG_FILE = 'screen_time_config.json'

DEFAULT_PREFERENCES = {
    "focus_minutes": 25,
    "break_minutes": 5,
    "color_choice": "Black",
    "idle_limit_minutes": 60,
    "launch_on_startup": False
}

MOTIVATIONAL_QUOTES = [
    "Believe in yourself!",
    "You’re doing great, keep going!",
    "Take this time to breathe and relax.",
    "Every step counts.",
    "A short break can boost productivity.",
    "Drink some water, stay hydrated!",
    "Fun fact: Honey never spoils!",
    "Fun fact: Bananas are berries, but strawberries aren't."
]

class ScreenTimeLimiter:
    def __init__(self, root):
        self.root = root
        self.root.title("EyeCare Enforcer")

        try:
            self.root.iconbitmap("icon.ico")
        except Exception as e:
            print(f"Unable to load icon: {e}")

        self.root.geometry("400x600")
        self.root.configure(bg='#1e1e1e')
        self.running = False
        self.break_active = False
        self.overlay = None
        self.popup_overlay = None
        self.awake_popup = None
        self.break_screen = None
        self.stop_event = threading.Event()

        self.preferences = DEFAULT_PREFERENCES.copy()
        self.load_preferences()
        self.focus_minutes = self.preferences["focus_minutes"]
        self.break_minutes = self.preferences["break_minutes"]
        self.idle_limit_minutes = self.preferences["idle_limit_minutes"]

        self.remaining_seconds = self.focus_minutes * 60
        self.create_widgets()
        self.update_timer_label()

    def load_preferences(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded_prefs = json.load(f)
                    self.preferences.update(loaded_prefs)
            except Exception as e:
                print(f"Error loading config, using defaults. Reason: {e}")
        self.save_preferences()

    def save_preferences(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.preferences, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def pause_for_idle_confirmation(self):
        event = threading.Event()

        def on_response(response):
            if response == "yes":
                print("User is awake. Resuming timer.")
            else:
                print("User is not awake. Stopping timer.")
                self.running = False
                if hasattr(self, 'toggle_button'):
                    self.toggle_button.config(text="Activate Timer")
            event.set()
            popup.destroy()

        popup = tk.Toplevel(self.root)
        popup.title("Are you still there?")
        popup.geometry("300x150+{}+{}".format(
            self.root.winfo_screenwidth() // 2 - 150,
            self.root.winfo_screenheight() // 2 - 75
        ))
        popup.configure(bg="white")
        popup.attributes('-topmost', True)

        label = tk.Label(popup, text="Are you still awake?", font=("Segoe UI", 14), bg="white")
        label.pack(pady=20)

        button_frame = tk.Frame(popup, bg="white")
        button_frame.pack()

        yes_btn = tk.Button(button_frame, text="Yes", width=10, command=lambda: on_response("yes"))
        no_btn = tk.Button(button_frame, text="No", width=10, command=lambda: on_response("no"))
        yes_btn.pack(side="left", padx=10)
        no_btn.pack(side="right", padx=10)

        popup.protocol("WM_DELETE_WINDOW", lambda: on_response("no"))
        popup.grab_set()

        event.wait()

    def create_widgets(self):
        container = tk.Frame(self.root, bg="#1e1e1e")
        container.place(relx=0.5, rely=0.5, anchor="center")

        title = tk.Label(container, text="EyeCare Enforcer", font=("Segoe UI", 16), fg="white", bg="#1e1e1e")
        title.pack(pady=10)

        tk.Label(container, text="Focus Time (minutes):", fg="white", bg="#1e1e1e").pack()
        self.focus_entry = ttk.Entry(container)
        self.focus_entry.insert(0, str(self.focus_minutes))
        self.focus_entry.pack(pady=5)

        tk.Label(container, text="Break Time (minutes):", fg="white", bg="#1e1e1e").pack()
        self.break_entry = ttk.Entry(container)
        self.break_entry.insert(0, str(self.break_minutes))
        self.break_entry.pack(pady=5)

        tk.Label(container, text="Idle Limit (minutes):", fg="white", bg="#1e1e1e").pack()
        self.idle_entry = ttk.Entry(container)
        self.idle_entry.insert(0, str(self.idle_limit_minutes))
        self.idle_entry.pack(pady=5)

        self.launch_var = tk.BooleanVar(value=self.preferences.get("launch_on_startup", False))
        self.launch_checkbox = tk.Checkbutton(
            container,
            text="Launch on Startup",
            variable=self.launch_var,
            bg="#1e1e1e",
            fg="white",
            activebackground="#1e1e1e",
            activeforeground="white",
            selectcolor="#1e1e1e",
            command=self.toggle_startup
        )
        self.launch_checkbox.pack(pady=5)

        self.timer_label = tk.Label(container, text="", font=("Segoe UI", 14), fg="cyan", bg="#1e1e1e")
        self.timer_label.pack(pady=10)

        self.toggle_button = ttk.Button(container, text="Activate Timer", command=self.toggle_timer)
        self.toggle_button.pack(pady=20)

    def show_break_screen(self):
        if self.break_screen and self.break_screen.winfo_exists():
            return  # Already showing
        self.break_screen = tk.Toplevel(self.root)
        self.break_screen.overrideredirect(True)
        self.break_screen.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        self.break_screen.configure(bg="black")
        self.break_screen.attributes("-topmost", True)

        quote = random.choice(MOTIVATIONAL_QUOTES)
        quote_label = tk.Label(
            self.break_screen,
            text=quote,
            font=("Segoe UI", 20),
            fg="white",
            bg="black",
            wraplength=self.root.winfo_screenwidth() - 200,
            justify="center"
        )
        quote_label.place(relx=0.5, rely=0.5, anchor="center")

        self.break_screen.after(self.break_minutes * 60 * 1000, self.hide_break_screen)

    def hide_break_screen(self):
        if self.break_screen and self.break_screen.winfo_exists():
            self.break_screen.destroy()

    def update_timer_label(self):
        if self.running:
            if self.remaining_seconds > 0:
                mins, secs = divmod(self.remaining_seconds, 60)
                time_str = f"{mins:02d}:{secs:02d}"
                if self.break_active:
                    self.timer_label.config(text=f"Break: {time_str}")
                else:
                    self.timer_label.config(text=f"Focus: {time_str}")
                self.remaining_seconds -= 1
            else:
                if not self.break_active:
                    self.break_active = True
                    self.remaining_seconds = self.break_minutes * 60
                    winsound.MessageBeep()
                    self.show_break_screen()
                else:
                    self.break_active = False
                    self.running = False
                    self.toggle_button.config(text="Activate Timer")
                    self.timer_label.config(text="Focus session completed!")
                    self.hide_break_screen()
        else:
            self.timer_label.config(text="Timer is paused.")
        self.root.after(1000, self.update_timer_label)

    def toggle_startup(self):
        self.preferences["launch_on_startup"] = self.launch_var.get()
        self.save_preferences()

    def toggle_timer(self):
        if not self.running:
            try:
                self.focus_minutes = int(self.focus_entry.get())
                self.break_minutes = int(self.break_entry.get())
                self.idle_limit_minutes = int(self.idle_entry.get())
            except ValueError:
                self.focus_minutes = DEFAULT_PREFERENCES["focus_minutes"]
                self.break_minutes = DEFAULT_PREFERENCES["break_minutes"]
                self.idle_limit_minutes = DEFAULT_PREFERENCES["idle_limit_minutes"]
            self.remaining_seconds = self.focus_minutes * 60
        self.running = not self.running
        state = "Deactivate" if self.running else "Activate"
        self.toggle_button.config(text=f"{state} Timer")

if __name__ == '__main__':
    root = tk.Tk()
    app = ScreenTimeLimiter(root)
    root.mainloop()
