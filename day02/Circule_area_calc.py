import math

def calculate_circle_area(radius: float) -> float:
    """
    Calculate the area of a circle using the formula A = πr²
    
    Args:
        radius (float): The radius of the circle
        
    Returns:
        float: The area of the circle
    """
    return math.pi * radius ** 2

def main():
    try:
        # Get input from user
        radius = float(input("Enter the radius of the circle: "))
        
        # Validate input
        if radius <= 0:
            print("Error: Radius must be a positive number")
            return
            
        # Calculate and display the area
        area = calculate_circle_area(radius)
        print(f"\nThe area of the circle is: {area:.2f} square units")
        print(f"Using π = {math.pi:.4f}")
        
    except ValueError:
        print("Error: Please enter a valid number")

if __name__ == "__main__":
    main()