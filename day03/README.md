# Birthday Countdown (Day 03 Assignment)

This project displays how many **months, weeks, and days** are left until your next birthday.  
It includes a GUI built with **Tkinter**, and separate **business logic** for clean structure and testing.

---

## Project Structure

day03/

 gui.py # GUI program (Tkinter)

logic/
-- init.py
-- birthday_logic.py # Business logic: time-to-birthday calculations

tests/
-- conftest.py # Makes logic importable during tests
-- test_birthday_logic.py # Unit tests for the logic


---

## Installation & Setup

### Create a virtual enviorment
uv venv

### Install dependencies
uv pip install pytest

### Running the Program
uv run python gui.py

### Running Tests

To verify that the logic works:

uv run pytest -q

## Use of AI in the Project

1. Structuring the code into business logic + GUI layers.

2. Writing the unit tests for the logic.

3. Debugging common path/import errors.

4. Creating this README.md.

## Prompts Used:

1. “Copy your project from the day02 folder to the new day03 folder. Move the business logic to a separate file.”

2. “Can you tell me how to do it?”

3. “This is my GUI code, please help.”

4. “Add some tests, especially to check the business logic.”

5. “Add a README.md explaining how to install dependencies, if there are any. Also explain how you used AI.”

Each step was reviewed and tested manually after generating with ChatGPT (GPT-5).





