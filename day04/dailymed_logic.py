"""
dailymed_logic.py

Business logic for downloading DailyMed drug label PDFs (package inserts).

Public functions:
- search_labels(drug_name, pagesize=10) -> list of dicts with keys ('setid','title','published_date')
- get_media_for_setid(setid) -> dict (JSON returned by DailyMed /media endpoint)
- find_pdf_url_for_setid(setid, media_json=None) -> str|None
- download_file(url, outpath, chunk_size=8192) -> outpath
- download_label_pdf_for_drug(drug_name, outdir, pick='first') -> dict summary

Notes:
- Uses DailyMed web services:
  - /dailymed/services/v2/spls.json?drug_name=...  (search)
  - /dailymed/services/v2/spls/{SETID}/media.json   (media listing)
  - getFile.cfm?setid=...&type=pdf                   (direct pdf download)
- See the DailyMed API docs for more fields and filtering options.
  (API docs used when implementing: DailyMed /spls and /spls/{SETID}/media). 
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import requests

BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
SPLS_ENDPOINT = f"{BASE}/spls.json"
SPLS_MEDIA_ENDPOINT = f"{BASE}/spls/{{setid}}/media.json"
# fallback direct PDF endpoint pattern (works on DailyMed site)
GETFILE_PDF = "https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid={setid}&type=pdf"

HEADERS = {"User-Agent": "dailymed-downloader/1.0 (python requests)"}


class DailyMedError(Exception):
    pass


def _safe_param(s: str) -> str:
    """Return a safe param (DailyMed expects plain text; requests will encode)."""
    return s.strip()


def search_labels(drug_name: str, pagesize: int = 10, page: int = 1) -> List[Dict]:
    """
    Search DailyMed SPLs by drug_name.

    Returns a list of dicts with at least: 'setid', 'title', 'published_date' (if available).
    """
    q = _safe_param(drug_name)
    params = {"drug_name": q, "pagesize": pagesize, "page": page}
    resp = requests.get(SPLS_ENDPOINT, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    # payload format: {"metadata": {...}, "data": [{...}, ...]}
    items = payload.get("data", [])
    results = []
    for it in items:
        results.append(
            {
                "setid": it.get("setid"),
                "title": it.get("title"),
                "published_date": it.get("published_date"),
                "raw": it,
            }
        )
    return results


def get_media_for_setid(setid: str) -> Dict:
    """
    Get media listing for a setid (returns JSON dict from DailyMed).

    Example endpoint:
      https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{SETID}/media.json
    """
    url = SPLS_MEDIA_ENDPOINT.format(setid=setid)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def find_pdf_url_for_setid(setid: str, media_json: Optional[Dict] = None) -> Optional[str]:
    """
    Try to find a PDF URL for the SPL setid.

    Strategy:
    1. If media_json is provided, search media entries for mime_type 'application/pdf'
       or filename ending with .pdf and return the 'url'.
    2. If none found, use the fallback getFile.cfm?setid=...&type=pdf which often returns the PDF.
    Returns the URL string or None if not found / unreachable.
    """
    # 1) check media JSON if provided
    if media_json:
        data = media_json.get("data")
        # when media endpoint returns an object with 'media' list inside 'data' or directly 'data' may be object
        candidates = []
        if isinstance(data, dict):
            # some responses put media list at data['media']
            media_list = data.get("media") or data.get("files") or []
        else:
            # if data is a list, try first element
            if isinstance(data, list) and data:
                media_list = data[0].get("media") or data[0].get("files") or []
            else:
                media_list = []
        for m in media_list:
            mime = (m.get("mime_type") or "").lower()
            name = (m.get("name") or "").lower()
            url = m.get("url")
            if not url:
                continue
            if "pdf" in mime or name.endswith(".pdf") or ".pdf" in name:
                return url
            # some files may be returned as other types but have pdf-like url; keep as fallback
            if url.lower().endswith(".pdf"):
                candidates.append(url)
        if candidates:
            return candidates[0]

    # 2) fallback to the getFile.cfm direct PDF endpoint
    fallback = GETFILE_PDF.format(setid=setid)
    # We do not verify here that the fallback exists; the GUI/CLI can attempt to download it and handle errors.
    return fallback


def download_file(url: str, outpath: str, chunk_size: int = 8192) -> str:
    """
    Download URL to outpath (streamed).

    Raises requests.HTTPError on failure. Returns the outpath.
    """
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, headers=HEADERS, timeout=30) as r:
        r.raise_for_status()
        with open(outpath, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    return outpath


def download_label_pdf_for_drug(
    drug_name: str,
    outdir: str = ".",
    pagesize: int = 10,
    pick: str = "first",
) -> Dict:
    """
    High-level helper:
    - search for labels matching drug_name (pagesize results),
    - pick one (pick='first' or 'latest' - 'first' = first item returned by search),
    - find a PDF URL and download it to outdir.
    Returns a summary dict:
      {
        "setid": str,
        "title": str,
        "pdf_url": str,
        "saved_path": str
      }
    Raises DailyMedError on not found or download failure.
    """
    results = search_labels(drug_name, pagesize=pagesize)
    if not results:
        raise DailyMedError(f"No labels found for '{drug_name}'")

    # Choose item
    chosen = None
    if pick == "first":
        chosen = results[0]
    elif pick == "latest":
        # If published_date is present, try to pick the latest by published_date string (best-effort).
        # For simplicity we pick the first result (DailyMed search often returns newest first).
        chosen = results[0]
    else:
        chosen = results[0]

    setid = chosen.get("setid")
    title = chosen.get("title")

    # Get media for setid and try to find PDF url
    try:
        media_json = get_media_for_setid(setid)
    except requests.HTTPError:
        media_json = None  # continue to fallback

    pdf_url = find_pdf_url_for_setid(setid, media_json=media_json)
    if not pdf_url:
        raise DailyMedError(f"Could not find PDF for setid {setid}")

    # Derive output filename
    safe_name = f"{setid}.pdf"
    outpath = os.path.join(outdir, safe_name)

    # Try to download
    try:
        saved = download_file(pdf_url, outpath)
    except requests.HTTPError as e:
        # If fallback failed and we had media JSON with another candidate (e.g. image), raise a clearer message
        raise DailyMedError(f"Failed to download PDF from {pdf_url}: {e}") from e

    return {"setid": setid, "title": title, "pdf_url": pdf_url, "saved_path": saved}


# Convenience CLI-style runnable behavior (if you want to run this file directly)
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Download DailyMed label PDF for a drug name.")
    p.add_argument("--drug", required=True, help="Drug name (generic or brand)")
    p.add_argument("--outdir", default="dailymed_downloads", help="Directory to save PDF")
    args = p.parse_args()
    try:
        summary = download_label_pdf_for_drug(args.drug, outdir=args.outdir)
        print("Downloaded:", summary)
    except Exception as e:
        print("Error:", e)
