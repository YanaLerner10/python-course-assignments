import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from ttkthemes import ThemedTk

# ...existing code...
def calculate_time_to_birthday(birthday_date):
    """
    Return (months, weeks, days) until the next occurrence of birthday_date.
    Uses the approximation: 1 month = 30 days, 1 week = 7 days.
    """
    today = date.today()
    try:
        next_birthday = date(today.year, birthday_date.month, birthday_date.day)
    except ValueError:
        # handle Feb 29 on non-leap year: treat next birthday as Mar 1
        next_birthday = date(today.year, 3, 1)

    if next_birthday < today:
        try:
            next_birthday = date(today.year + 1, birthday_date.month, birthday_date.day)
        except ValueError:
            next_birthday = date(today.year + 1, 3, 1)

    delta = next_birthday - today
    total_days = delta.days
    months = total_days // 30
    remaining_days = total_days % 30
    weeks = remaining_days // 7
    days = remaining_days % 7
    return months, weeks, days
# ...existing code...

class BirthdayCountdownGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎂 Birthday Countdown 🎈")
        self.root.geometry("400x600")
        
        # Configure style
        style = ttk.Style()
        style.configure('Birthday.TFrame', background='#FFE4E1')
        style.configure('Birthday.TLabel',
                       font=('Comic Sans MS', 12),
                       background='#FFE4E1',
                       foreground='#FF69B4')
        style.configure('Title.TLabel',
                       font=('Comic Sans MS', 20, 'bold'),
                       background='#FFE4E1',
                       foreground='#FF1493')
        
        # Main frame
        self.main_frame = ttk.Frame(root, style='Birthday.TFrame', padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title with emojis
        title_label = ttk.Label(self.main_frame,
                               text="🎉 Birthday Countdown 🎉",
                               style='Title.TLabel')
        title_label.pack(pady=20)
        
        # Birthday cake image (using text art)
        cake_art = """
           🎂
        ╱▔▔▔▔▔╲
        │∏∏∏∏∏│
        │∏∏∏∏∏│
        ╲▁▁▁▁▁╱
        """
        cake_label = ttk.Label(self.main_frame,
                              text=cake_art,
                              font=('Courier', 14),
                              style='Birthday.TLabel')
        cake_label.pack(pady=20)
        
        # Date entry frame
        date_frame = ttk.Frame(self.main_frame, style='Birthday.TFrame')
        date_frame.pack(pady=20)
        
        # Date entry fields
        ttk.Label(date_frame, text="Day:", style='Birthday.TLabel').grid(row=0, column=0, padx=5)
        self.day_var = tk.StringVar()
        self.day_entry = ttk.Entry(date_frame, width=3, textvariable=self.day_var)
        self.day_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(date_frame, text="Month:", style='Birthday.TLabel').grid(row=0, column=2, padx=5)
        self.month_var = tk.StringVar()
        self.month_entry = ttk.Entry(date_frame, width=3, textvariable=self.month_var)
        self.month_entry.grid(row=0, column=3, padx=5)
        
        ttk.Label(date_frame, text="Year:", style='Birthday.TLabel').grid(row=0, column=4, padx=5)
        self.year_var = tk.StringVar()
        self.year_entry = ttk.Entry(date_frame, width=5, textvariable=self.year_var)
        self.year_entry.grid(row=0, column=5, padx=5)
        
        # Calculate button
        calculate_button = tk.Button(self.main_frame,
                                   text="🎈 Calculate! 🎈",
                                   command=self.calculate_countdown,
                                   font=('Comic Sans MS', 12, 'bold'),
                                   bg='#FF69B4',
                                   fg='white',
                                   relief='raised',
                                   cursor='hand2')
        calculate_button.pack(pady=20)
        
        # Result labels
        self.result_frame = ttk.Frame(self.main_frame, style='Birthday.TFrame')
        self.result_frame.pack(pady=20)
        
        self.months_var = tk.StringVar()
        self.weeks_var = tk.StringVar()
        self.days_var = tk.StringVar()
        
        ttk.Label(self.result_frame, text="🎁 Time until your next birthday:", 
                 style='Birthday.TLabel').pack(pady=10)
        
        for var, text in [(self.months_var, "Months"), 
                         (self.weeks_var, "Weeks"), 
                         (self.days_var, "Days")]:
            result_label = ttk.Label(self.result_frame,
                                   textvariable=var,
                                   style='Birthday.TLabel')
            result_label.pack(pady=5)

    def calculate_countdown(self):
        try:
            day = int(self.day_var.get())
            month = int(self.month_var.get())
            year = int(self.year_var.get())
            
            birthday_date = date(year, month, day)
            months, weeks, days = calculate_time_to_birthday(birthday_date)
            
            self.months_var.set(f"🎈 {months} months")
            self.weeks_var.set(f"🎁 {weeks} weeks")
            self.days_var.set(f"🎂 {days} days")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid date numbers!")

def main():
    root = ThemedTk(theme="plastik")
    root.configure(background='#FFE4E1')
    app = BirthdayCountdownGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()