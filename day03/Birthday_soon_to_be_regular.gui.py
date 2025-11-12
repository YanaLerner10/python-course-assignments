import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import random

# ⬇️ import the logic from the new module
from logic.birthday_logic import calculate_time_to_birthday

class BirthdayApp:
    def __init__(self, root):
        self.root = root
        root.title("🎉 Birthday Countdown")
        root.configure(bg="#fff7f9")
        root.geometry("360x520")
        root.resizable(False, False)

        # Title
        title = tk.Label(root, text="🎂 Birthday Countdown 🎈", font=("Segoe UI", 18, "bold"),
                         bg="#fff7f9", fg="#b30066")
        title.pack(pady=(18, 6))

        # Decorative canvas (cake + confetti)
        self.canvas = tk.Canvas(root, width=300, height=140, bg="#fff7f9", highlightthickness=0)
        self.canvas.pack()
        self.draw_cake()

        # Input frame (day, month, year)
        frame = ttk.Frame(root)
        frame.pack(pady=12)

        ttk.Label(frame, text="Day").grid(row=0, column=0, padx=6, pady=2)
        ttk.Label(frame, text="Month").grid(row=0, column=1, padx=6, pady=2)
        ttk.Label(frame, text="Year").grid(row=0, column=2, padx=6, pady=2)

        self.day_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.year_var = tk.StringVar()

        self.day_entry = ttk.Entry(frame, width=5, textvariable=self.day_var, justify="center")
        self.month_entry = ttk.Entry(frame, width=5, textvariable=self.month_var, justify="center")
        self.year_entry = ttk.Entry(frame, width=8, textvariable=self.year_var, justify="center")

        self.day_entry.grid(row=1, column=0, padx=6)
        self.month_entry.grid(row=1, column=1, padx=6)
        self.year_entry.grid(row=1, column=2, padx=6)

        ttk.Label(root, text="Enter your birthday (numbers only)", background="#fff7f9",
                  foreground="#6b6b6b").pack(pady=(6, 8))

        # Calculate button
        calc_btn = tk.Button(root, text="Calculate Time 🎈", command=self.calculate,
                             bg="#ff78b6", fg="white", bd=0, font=("Segoe UI", 11, "bold"), activebackground="#ff5fa0")
        calc_btn.pack(pady=8, ipadx=6, ipady=6)

        # Results area
        self.result_frame = ttk.Frame(root)
        self.result_frame.pack(pady=14)

        self.months_label = tk.Label(self.result_frame, text="", font=("Segoe UI", 13), bg="#fff7f9", fg="#b30066")
        self.weeks_label = tk.Label(self.result_frame, text="", font=("Segoe UI", 13), bg="#fff7f9", fg="#ff6f91")
        self.days_label = tk.Label(self.result_frame, text="", font=("Segoe UI", 13), bg="#fff7f9", fg="#ff9bb3")

        self.months_label.pack(pady=4)
        self.weeks_label.pack(pady=4)
        self.days_label.pack(pady=4)

        # small tip & footer
        tip = tk.Label(root, text="Assumes: 12 months, 52 weeks, 365 days approximation", bg="#fff7f9",
                       fg="#777777", font=("Segoe UI", 9))
        tip.pack(side="bottom", pady=8)

        # for confetti animation
        self.confetti_items = []
        self.animating = False

        # Bind Enter key to calculate
        root.bind("<Return>", lambda e: self.calculate())

    def draw_cake(self):
        c = self.canvas
        c.delete("all")
        # base cake
        c.create_oval(60, 40, 240, 120, fill="#ffe6f2", outline="#ff9ccf")
        c.create_rectangle(80, 50, 220, 95, fill="#ffd9ec", outline="#ff9ccf")
        # candles
        for i, x in enumerate((110, 140, 170)):
            c.create_rectangle(x - 3, 22, x + 3, 50, fill="#fff7a8", outline="#f7d04d")
            c.create_oval(x - 5, 14, x + 5, 22, fill="#ffb3d9", outline="#ff8fc1")
        c.create_text(150, 105, text="Make a wish!", font=("Segoe UI", 10, "italic"), fill="#b30066")

    def pop_confetti(self):
        # create confetti pieces
        for _ in range(18):
            x = random.randint(10, 290)
            y = random.randint(-20, 0)
            size = random.randint(4, 9)
            color = random.choice(["#ff6f91", "#ffd166", "#a0e7e5", "#b2ff9e", "#ffb3d9"])
            oval = self.canvas.create_oval(x, y, x + size, y + size, fill=color, outline="")
            self.confetti_items.append((oval, random.uniform(1, 3)))  # (id, speed)
        if not self.animating:
            self.animating = True
            self.animate_confetti()

    def animate_confetti(self):
        keep = []
        for item, speed in self.confetti_items:
            self.canvas.move(item, 0, speed)
            coords = self.canvas.coords(item)
            if coords and coords[1] < 160:
                keep.append((item, speed))
            else:
                self.canvas.delete(item)
        self.confetti_items = keep
        if self.confetti_items:
            self.root.after(40, self.animate_confetti)
        else:
            self.animating = False

    def calculate(self):
        try:
            d = int(self.day_var.get())
            m = int(self.month_var.get())
            y_text = self.year_var.get().strip()
            y = int(y_text) if y_text else date.today().year  # year optional; default to current year
            birthday_date = date(y, m, d)  # validates the date
            months, weeks, days = calculate_time_to_birthday(birthday_date)
            self.months_label.config(text=f"🗓️  {months} months")
            self.weeks_label.config(text=f"📅  {weeks} weeks")
            self.days_label.config(text=f"📆  {days} days")
            self.pop_confetti()
        except ValueError:
            messagebox.showerror(
                "Invalid input",
                "Please enter valid numeric day, month and optional year.\nDay and month must form a valid date."
            )

def main():
    root = tk.Tk()
    app = BirthdayApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
