# DailyMed Side-Effect PDF Downloader

This project downloads **PDF files containing drug side-effect information** from the **DailyMed** online drug database.
The user provides a drug name, and the program automatically searches DailyMed, retrieves the drug’s SPL document, and saves the official side-effect section as a PDF file on the computer.

The project is divided into two parts:

---

## 1. `dailymed_logic.py`

This file contains all **business logic**, including:

* Searching DailyMed for a drug name
* Retrieving DailyMed SPL document metadata (setid, version, URLs)
* Downloading the corresponding **PDF** file
* Handling errors and returning clear status messages

This file contains **no user-interface code** and can be reused in other applications.

---

## 2. `dailymed_gui.py`

This file contains the **Tkinter graphical user interface**, including:

* Input field for drug name
* Buttons for searching + downloading
* File save dialog
* Status messages and error handling
* A progress bar for better user experience

The GUI communicates only with the functions in `dailymed_logic.py`.

---

## Requirements

Install dependencies using:

```
pip install -r requirements.txt
```

The program requires the following packages:

* `requests` — for HTTP requests to DailyMed
* `tkinter` — included with most Python installations

---

## Usage

### Run the GUI:

```
python dailymed_gui.py
```

1. Enter a drug name (e.g., “ibuprofen”)
2. Click **Search & Download**
3. Choose where to save the PDF
4. The PDF is downloaded from the official DailyMed SPL listing

---

## Use of AI in the Project

Artificial intelligence (ChatGPT) was used to help:

* Design the program structure
* Create the separation between logic and GUI
* Write example code for the two Python files
* Generate the README and `requirements.txt` files
* Provide troubleshooting and documentation guidance

All code was reviewed and executed locally before final submission.

---



This project is for educational use.
