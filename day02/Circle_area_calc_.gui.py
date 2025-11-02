import math
import tkinter as tk
from tkinter import ttk, messagebox

class CircleAreaCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Circle Area Calculator")
        self.root.geometry("300x200")
        
        # Create and configure main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create widgets
        ttk.Label(self.main_frame, text="Enter radius:").grid(row=0, column=0, pady=5)
        
        self.radius_var = tk.StringVar()
        self.radius_entry = ttk.Entry(self.main_frame, textvariable=self.radius_var)
        self.radius_entry.grid(row=0, column=1, pady=5)
        
        ttk.Button(self.main_frame, text="Calculate", command=self.calculate_area).grid(row=1, column=0, columnspan=2, pady=10)
        
        self.result_var = tk.StringVar()
        ttk.Label(self.main_frame, textvariable=self.result_var).grid(row=2, column=0, columnspan=2, pady=5)
        
        # Center all elements
        for child in self.main_frame.winfo_children():
            child.grid_configure(padx=5)

    def calculate_area(self):
        try:
            radius = float(self.radius_var.get())
            if radius <= 0:
                messagebox.showerror("Error", "Radius must be a positive number")
                return
                
            area = math.pi * radius ** 2
            self.result_var.set(f"Area: {area:.2f} square units\nπ = {math.pi:.4f}")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

def main():
    root = tk.Tk()
    app = CircleAreaCalculator(root)
    root.mainloop()

if __name__ == "__main__":
    main()