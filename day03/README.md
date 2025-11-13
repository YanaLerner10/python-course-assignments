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

### Create and activate a virtual environment
```powershell
uv venv

**### Install dependencies**
uv pip install pytest

**### Running the Program**
uv run python gui.py

**### Running Tests**

To verify that the logic works:

uv run pytest -q




