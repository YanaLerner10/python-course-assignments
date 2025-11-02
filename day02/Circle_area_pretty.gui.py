import math
import tkinter as tk
from tkinter import ttk, messagebox

class CircleAreaCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Circle Area Calculator")
        self.root.geometry("400x500")
        self.root.configure(bg="#f0f0f0")
        
        # Set theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.TFrame', background='#f0f0f0')
        style.configure('Title.TLabel', 
                       font=('Helvetica', 16, 'bold'), 
                       background='#f0f0f0',
                       foreground='#2c3e50')
        style.configure('Result.TLabel', 
                       font=('Helvetica', 12),
                       background='#f0f0f0',
                       foreground='#34495e')
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="20", style='Custom.TFrame')
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(self.main_frame, 
                               text="Circle Area Calculator",
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Circle canvas
        self.canvas = tk.Canvas(self.main_frame, 
                              width=200, 
                              height=200,
                              bg='#f0f0f0',
                              highlightthickness=0)
        self.canvas.grid(row=1, column=0, columnspan=2, pady=10)
        self.draw_circle()
        
        # Input frame
        input_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        input_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Label(input_frame, 
                 text="Enter radius:",
                 font=('Helvetica', 12),
                 background='#f0f0f0').grid(row=0, column=0, padx=5)
        
        self.radius_var = tk.StringVar()
        self.radius_entry = ttk.Entry(input_frame, 
                                    textvariable=self.radius_var,
                                    width=15,
                                    font=('Helvetica', 12))
        self.radius_entry.grid(row=0, column=1, padx=5)
        
        # Calculate button
        calculate_button = tk.Button(self.main_frame,
                                   text="Calculate Area",
                                   command=self.calculate_area,
                                   bg='#3498db',
                                   fg='white',
                                   font=('Helvetica', 12, 'bold'),
                                   relief='raised',
                                   width=15,
                                   cursor='hand2')
        calculate_button.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Result label
        self.result_var = tk.StringVar()
        self.result_label = ttk.Label(self.main_frame,
                                    textvariable=self.result_var,
                                    style='Result.TLabel')
        self.result_label.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Configure grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        
        # Bind events
        self.radius_entry.bind('<Return>', lambda e: self.calculate_area())
        calculate_button.bind('<Enter>', 
                            lambda e: calculate_button.config(bg='#2980b9'))
        calculate_button.bind('<Leave>', 
                            lambda e: calculate_button.config(bg='#3498db'))

    def draw_circle(self):
        self.canvas.delete("all")
        # Draw circle
        self.canvas.create_oval(20, 20, 180, 180, 
                              outline="#3498db", 
                              width=3,
                              fill="#ebf5fb")
        # Draw radius line
        self.canvas.create_line(100, 100, 180, 100, 
                              fill="#e74c3c", 
                              width=2,
                              arrow=tk.LAST)
        # Draw "r" label
        self.canvas.create_text(140, 90, 
                              text="r", 
                              font=('Helvetica', 14, 'italic'),
                              fill="#2c3e50")

    def calculate_area(self):
        try:
            radius = float(self.radius_var.get())
            if radius <= 0:
                messagebox.showerror("Error", "Radius must be a positive number")
                return
                
            area = math.pi * radius ** 2
            self.result_var.set(
                f"Area = {area:.2f} square units\n"
                f"π = {math.pi:.4f}"
            )
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

def main():
    root = tk.Tk()
    root.configure(bg='#f0f0f0')
    app = CircleAreaCalculator(root)
    root.mainloop()

if __name__ == "__main__":
    main()