**This GUI calculates how many days are left until your next birthday. 
I created 2 virsions of it- a simple version with no extanstions needead (regular) and a virsion that you need to download TTKTHEMES.**

I used copilot to help me. 


Prompts I used

  - I want to create a code that will calculte how many months, weaks and days you have until your next birthday. assuming there are 52 weeks, 365 days, and 12 months. it should know the current day, and the birthday is supplied by the user.

    -great, now can you create a nice gui for that. use a nice theme to make it fell like a birthday


At this point I got confussed becuse copilot asked me to install this:

  To use this GUI version, you'll need to install the ttkthemes package first. Open your terminal in VS Code and run:
pip install ttkthemes.

But I know we can't pip install becuse we use UV. so I asked copilot to help me with this- 

uv pip install ttkthemes

**it didn't help so I switched to chatgpt-5 PRO and it told me I need to create a virtul environment- **
  

  You’re super close! Here’s what happened and how to fix it fast on Windows PowerShell:
Why those errors happened


  uv pip install <ttkthemes> → PowerShell thinks < ... > is redirection. Don’t use angle brackets.


  uv pip install ttkthemes → “No virtual environment found” because you hadn’t activated a venv (or told uv to use the system env).


  --system uv pip ... → Flags go after the command, not before.


  .venv\Scripts\activate blocked → PowerShell execution policy is preventing scripts from running.



  Option A (recommended): use a project virtual environment


  Create the venv (you already did):


uv venv
  


  Allow activation scripts for your user (one-time):


  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

  Type A to accept if prompted, then open a new PowerShell window.


  Activate and install:


  .\.venv\Scripts\Activate.ps1
uv pip install ttkthemes


  Tip: If activation still annoys you, you can install to the venv without activating:

.\.venv\Scripts\python.exe -m pip install ttkthemes


  Option B: install into your system (no venv)
If you really want it global for your current Python:
uv pip install --system ttkthemes


  Quick notes


  You had a small typo earlier: ttkrhemes → it’s ttkthemes.


  To run your GUI after installing:


  uv run python .\day02\Circle_area_calc_.gui.py

(or use the venv’s python: .\.venv\Scripts\python.exe .\day02\Circle_area_calc_.gui.py)
If you want, I can also wire this up in VS Code so it uses your .venv automatically.

**CO-pilot also created a GUI that dosen't need any extantions, so this is why I have 2 virsions. **
