"""
dailymed_gui.py

A friendly Tkinter GUI wrapper that uses dailymed_logic.py.

Features:
- Enter drug name and press Search
- List matching labels (title + published date) in a listbox
- Select a label and click "Download PDF" to save the package insert as a PDF
- Background thread for network operations so GUI stays responsive
"""

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional
from pathlib import Path

# Import the logic module you saved as dailymed_logic.py
from dailymed_logic import (
    search_labels,
    get_media_for_setid,
    find_pdf_url_for_setid,
    download_file,
    download_label_pdf_for_drug,
    DailyMedError,
)


class DailyMedDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DailyMed — Label PDF Downloader")
        self.geometry("720x420")
        self.resizable(True, True)

        self._build_ui()
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_result = None

    def _build_ui(self):
        pad = 10
        frm = ttk.Frame(self, padding=pad)
        frm.pack(fill=tk.BOTH, expand=True)

        # Search area
        search_row = ttk.Frame(frm)
        search_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(search_row, text="Drug name:").pack(side=tk.LEFT)
        self.drug_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.drug_var, width=40).pack(side=tk.LEFT, padx=(6, 10))

        self.search_btn = ttk.Button(search_row, text="Search", command=self.on_search)
        self.search_btn.pack(side=tk.LEFT)

        ttk.Label(search_row, text="Results page size:").pack(side=tk.LEFT, padx=(20, 6))
        self.pagesize_var = tk.IntVar(value=10)
        ttk.Spinbox(search_row, from_=1, to=50, textvariable=self.pagesize_var, width=5).pack(side=tk.LEFT)

        # Results list
        list_frame = ttk.LabelFrame(frm, text="Matching labels")
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.results_listbox = tk.Listbox(list_frame, height=12)
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        self.results_listbox.bind("<<ListboxSelect>>", self.on_select_result)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.results_listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        self.results_listbox.config(yscrollcommand=scrollbar.set)

        # Right panel with details + download controls
        right_panel = ttk.Frame(list_frame, width=280)
        right_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=6)

        ttk.Label(right_panel, text="Selected label:").pack(anchor=tk.W)
        self.selected_title_var = tk.StringVar(value="(none)")
        ttk.Label(right_panel, textvariable=self.selected_title_var, wraplength=260).pack(anchor=tk.W, pady=(2, 8))

        ttk.Label(right_panel, text="Published date:").pack(anchor=tk.W)
        self.selected_date_var = tk.StringVar(value="")
        ttk.Label(right_panel, textvariable=self.selected_date_var).pack(anchor=tk.W, pady=(2, 8))

        ttk.Button(right_panel, text="Choose save folder...", command=self.choose_outdir).pack(fill=tk.X)
        self.outdir_var = tk.StringVar(value=str(Path.cwd() / "dailymed_downloads"))
        ttk.Label(right_panel, textvariable=self.outdir_var, wraplength=260).pack(anchor=tk.W, pady=(4, 8))

        self.download_btn = ttk.Button(right_panel, text="Download PDF for selected label", command=self.on_download, state=tk.DISABLED)
        self.download_btn.pack(fill=tk.X, pady=(8, 6))

        self.progress = ttk.Progressbar(frm, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(8, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(frm, textvariable=self.status_var).pack(anchor=tk.W, pady=(6, 0))

    def on_search(self):
        drug = self.drug_var.get().strip()
        if not drug:
            messagebox.showwarning("Input required", "Please enter a drug name to search.")
            return
        pagesize = int(self.pagesize_var.get())
        # disable controls
        self.search_btn.configure(state=tk.DISABLED)
        self.download_btn.configure(state=tk.DISABLED)
        self.progress.start(10)
        self.status_var.set("Searching DailyMed...")
        # run search in background
        thread = threading.Thread(target=self._worker_search, args=(drug, pagesize), daemon=True)
        thread.start()
        self._worker_thread = thread
        self.after(200, self._poll_worker)

    def _worker_search(self, drug, pagesize):
        try:
            results = search_labels(drug, pagesize=pagesize)
            self._worker_result = ("search_ok", results)
        except Exception as e:
            self._worker_result = ("search_err", str(e))

    def _poll_worker(self):
        if self._worker_thread and self._worker_thread.is_alive():
            self.after(200, self._poll_worker)
            return
        # finished
        self.progress.stop()
        self.search_btn.configure(state=tk.NORMAL)
        res = self._worker_result
        if not res:
            self.status_var.set("No result.")
            return
        tag, payload = res
        if tag == "search_ok":
            results = payload
            self._populate_results(results)
            self.status_var.set(f"Found {len(results)} results.")
        else:
            self.status_var.set("Error while searching.")
            messagebox.showerror("Search error", str(payload))

    def _populate_results(self, results):
        # results is list of dicts {'setid','title','published_date','raw'}
        self.results_listbox.delete(0, tk.END)
        self._current_results = results
        for i, r in enumerate(results):
            title = r.get("title", "(no title)")
            date = r.get("published_date") or ""
            display = f"{title} — {date}"
            self.results_listbox.insert(tk.END, display)
        # clear selection details
        self.selected_title_var.set("(none)")
        self.selected_date_var.set("")
        self.download_btn.configure(state=tk.DISABLED)

    def on_select_result(self, evt):
        sel = self.results_listbox.curselection()
        if not sel:
            self.selected_title_var.set("(none)")
            self.selected_date_var.set("")
            self.download_btn.configure(state=tk.DISABLED)
            return
        idx = sel[0]
        item = self._current_results[idx]
        self.selected_title_var.set(item.get("title") or "")
        self.selected_date_var.set(item.get("published_date") or "")
        self.download_btn.configure(state=tk.NORMAL)

    def choose_outdir(self):
        d = filedialog.askdirectory(initialdir=self.outdir_var.get())
        if d:
            self.outdir_var.set(d)

    def on_download(self):
        sel = self.results_listbox.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Please select a label from the list first.")
            return
        idx = sel[0]
        item = self._current_results[idx]
        setid = item.get("setid")
        outdir = self.outdir_var.get()
        Path(outdir).mkdir(parents=True, exist_ok=True)

        # disable UI, start progress
        self.search_btn.configure(state=tk.DISABLED)
        self.download_btn.configure(state=tk.DISABLED)
        self.progress.start(10)
        self.status_var.set("Resolving PDF URL...")

        thread = threading.Thread(target=self._worker_download_pdf, args=(setid, outdir), daemon=True)
        thread.start()
        self._worker_thread = thread
        self.after(200, self._poll_worker_download)

    def _worker_download_pdf(self, setid, outdir):
        try:
            # Try media listing first
            media_json = None
            try:
                media_json = get_media_for_setid(setid)
            except Exception:
                media_json = None
            pdf_url = find_pdf_url_for_setid(setid, media_json=media_json)
            if not pdf_url:
                raise DailyMedError("Could not find any PDF url for this label.")
            filename = f"{setid}.pdf"
            outpath = str(Path(outdir) / filename)
            download_file(pdf_url, outpath)
            self._worker_result = ("download_ok", outpath)
        except Exception as e:
            self._worker_result = ("download_err", str(e))

    def _poll_worker_download(self):
        if self._worker_thread and self._worker_thread.is_alive():
            self.after(200, self._poll_worker_download)
            return
        self.progress.stop()
        self.search_btn.configure(state=tk.NORMAL)
        # keep results selectable
        res = self._worker_result
        if not res:
            self.status_var.set("No operation performed.")
            return
        tag, payload = res
        if tag == "download_ok":
            outpath = payload
            self.status_var.set(f"Saved: {outpath}")
            messagebox.showinfo("Download complete", f"Saved PDF to:\n{outpath}")
            self.download_btn.configure(state=tk.NORMAL)
        else:
            err = payload
            self.status_var.set("Error during download")
            messagebox.showerror("Download error", err)
            self.download_btn.configure(state=tk.NORMAL)


def main():
    app = DailyMedDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
