import os
import re
import requests
import tempfile
from typing import Dict, List

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

API_KEY = "df21b06b13dd1a95c37ba72e5c47fab5"
SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
SCOPUS_ARTICLE_BASE = "https://api.elsevier.com/content/article/doi/"

SCOPUS_FOLDER = "scopus"
TXT_OUTPUT_FOLDER = r"C:\Users\user\Documents\slr-auto\tools\txt_papers"

# Optional: If tesseract is not in PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    return re.sub(r"(?u)[^\-\w.]", "", name)

def save_abstract(entry: Dict, out_folder: str) -> bool:
    scopus_id_field = entry.get("dc:identifier", "")
    scopus_id = scopus_id_field.split(":")[-1] if ":" in scopus_id_field else scopus_id_field
    title = entry.get("dc:title", "no_title")
    abstract = entry.get("dc:description") or entry.get("description") or ""
    if not abstract:
        return False

    fname = f"{scopus_id}_{sanitize_filename(title)[:50]}.txt"
    path = os.path.join(out_folder, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"Authors: {entry.get('dc:creator', 'N/A')}\n")
        year = entry.get("prism:coverDate", "")
        f.write(f"Year: {year[:4] if year else 'N/A'}\n")
        f.write("\n--- ABSTRACT ---\n\n")
        f.write(abstract.strip())
    return True

def convert_pdf_to_text(pdf_path: str, txt_out_path: str) -> bool:
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(pdf_path, output_folder=temp_dir)
            full_text = ""
            for i, img in enumerate(images):
                text = pytesseract.image_to_string(img)
                full_text += f"\n\n--- Page {i + 1} ---\n{text}"

        os.makedirs(os.path.dirname(txt_out_path), exist_ok=True)
        with open(txt_out_path, "w", encoding="utf-8") as f:
            f.write(full_text.strip())

        return True
    except Exception as e:
        print(f"    [!] OCR failed for {pdf_path}: {e}")
        return False

def download_pdf_by_doi(doi: str, out_folder: str) -> bool:
    if not doi:
        return False

    doi_filename = sanitize_filename(doi.replace("/", "_"))
    pdf_path = os.path.join(out_folder, f"{doi_filename}.pdf")
    txt_path = os.path.join(TXT_OUTPUT_FOLDER, f"{doi_filename}.txt")

    headers = {
        "X-ELS-APIKey": API_KEY,
        "Accept": "application/pdf"
    }
    params = {"httpAccept": "application/pdf"}
    url = SCOPUS_ARTICLE_BASE + doi

    resp = requests.get(url, headers=headers, params=params, stream=True)
    if resp.status_code == 200:
        with open(pdf_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        if convert_pdf_to_text(pdf_path, txt_path):
            print(f"    • PDF converted to TXT: {txt_path}")
            return True
        else:
            print(f"    • PDF downloaded but conversion failed: {pdf_path}")
            return False
    else:
        return False

def fetch_scopus_batch(query: str, start: int, count: int) -> List[Dict]:
    headers = {
        "X-ELS-APIKey": API_KEY,
        "Accept": "application/json"
    }
    params = {
        "query": query,
        "start": start,
        "count": count
    }
    resp = requests.get(SCOPUS_SEARCH_URL, headers=headers, params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"Error fetching Scopus batch: {resp.status_code} — {resp.text}")
    data = resp.json()
    return data.get("search-results", {}).get("entry", [])

def main():
    query = input("Enter your Scopus query (e.g. TITLE-ABS-KEY(algebra)): ").strip()
    try:
        target_n = int(input("Enter the number of papers to save: ").strip())
        if target_n <= 0:
            raise ValueError
    except ValueError:
        print("Please enter a positive integer for the number of papers.")
        return

    os.makedirs(SCOPUS_FOLDER, exist_ok=True)
    os.makedirs(TXT_OUTPUT_FOLDER, exist_ok=True)

    saved_count = 0
    fetched_offset = 0
    page_size = 25

    print(f"\nStarting fetch for `{query}`, aiming to save {target_n} papers...\n")

    while saved_count < target_n:
        try:
            batch = fetch_scopus_batch(query, fetched_offset, page_size)
        except Exception as e:
            print(f"Error during fetch: {e}")
            break

        if not batch:
            print("No more results available from Scopus.")
            break

        for entry in batch:
            if saved_count >= target_n:
                break

            title = entry.get("dc:title", "N/A")
            print(f"[{saved_count + 1}/{target_n}] Processing: {title[:60]} ...")

            did_save = False
            if save_abstract(entry, SCOPUS_FOLDER):
                did_save = True

            doi = entry.get("prism:doi", "")
            if doi:
                if download_pdf_by_doi(doi, SCOPUS_FOLDER):
                    did_save = True
                else:
                    print(f"    • PDF not available or access denied for DOI {doi}")

            if not did_save:
                print("    • No abstract or PDF; skipping this entry.")
                continue

            saved_count += 1

        fetched_offset += len(batch)

    # Print summary as requested
    print(f"Number of waited papers to fetch : {target_n}")
    print(f"Number of fetched papers : {saved_count}")
    print(f"Research query : {query}")

if __name__ == "__main__":
    main()
