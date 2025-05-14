def pause_for_idle_confirmation(self):
    event = threading.Event()

    def on_response(response):
        if response == "yes":
            print("User is awake. Resuming timer.")
            self.running = True
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

    self.root.wait_window(popup)
