# Systematic Literature Review (SLR) Automation Tool

This project is a Python-based tool designed to automate various stages of conducting a Systematic Literature Review (SLR). It leverages AI (specifically Google's Gemini models) for tasks like generating search queries, summarizing papers, and drafting SLR sections. The tool interfaces with ArXiv and Scopus for paper fetching and uses Streamlit for its user interface.

## Features

- **Automated Paper Fetching:**
    - Generates academic search queries from natural language goals.
    - Fetches papers from ArXiv and Scopus based on generated or user-defined queries.
    - Supports fetching within a specified year range.
- **Manual PDF Upload:** Allows users to upload their own PDF files for inclusion in the SLR.
- **PDF Processing:**
    - Converts PDF documents to plain text.
    - Uses OCR (Tesseract) for image-based PDFs or Scopus papers.
- **AI-Powered Summarization:**
    - Summarizes papers using Gemini, focusing on relevance to the SLR subject.
    - Filters papers based on LLM-determined relevance.
- **Snowballing:**
    - Extracts references from relevant papers.
    - Attempts to find and fetch these referenced papers from ArXiv and Scopus.
- **LaTeX Document Generation:**
    - Creates individual LaTeX sections for an SLR (Abstract, Introduction, Background, Related Works, Research Methods, Review Findings, Discussion, Conclusion).
    - Incorporates a "human-like" writing style by drawing inspiration from provided text samples.
    - Generates BibTeX files (`biblio.bib`) from fetched paper metadata.
    - Assembles a complete LaTeX document.
    - Attempts to enhance sections with AI-generated charts and tables (using TikZ, pgfplots, etc.).
- **Iterative Refinement:**
    - Generates an initial draft of the SLR.
    - Uses an LLM to critique the draft.
    - Refines the SLR based on the critique over a user-defined number of cycles.
- **Reporting:**
    - Generates a processing summary report detailing timings, fetched papers, and LLM usage.
    - Generates a refinement cycle report detailing critiques and changes.
- **User Interface:** A Streamlit application provides an easy-to-use interface for initiating the SLR process.

## Prerequisites

1.  **Python:** Version 3.8 or higher.
2.  **LaTeX Distribution:** A working LaTeX distribution (e.g., MiKTeX for Windows, TeX Live for Linux/macOS) must be installed and `pdflatex` must be in your system's PATH. This is used by the application to attempt to compile the generated LaTeX, although the Streamlit app currently only warns if `pdflatex` is missing and skips compilation.
3.  **Tesseract OCR:**
    -   Install Tesseract OCR from here.
    -   Ensure `tesseract` is in your system's PATH.
    -   You may also need to install language data (e.g., for English).
    -   If Tesseract is not in your PATH, you'll need to specify its location in `tools/agent.py` (see the commented-out line for `pytesseract.pytesseract.tesseract_cmd`).
4.  **Poppler (for `pdf2image` on Windows):**
    -   If you are on Windows, `pdf2image` requires Poppler. Download the latest binary from here and add the `bin/` directory to your PATH.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    cd slr-auto
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **API Key Configuration:**
    The application requires API keys for Google's Generative AI (Gemini) and Scopus.
    -   **Gemini API Key:** Currently hardcoded as `SUMMARY_API_KEY` in `tools/agent.py`.
    -   **Scopus API Key:** Currently hardcoded as `SCOPUS_API_KEY` in `tools/agent.py`.

    **IMPORTANT:** For security, it is strongly recommended to move these keys out of the code. Consider using environment variables or a `.env` file (and add `.env` to your `.gitignore`).
    For example, using environment variables:
    ```python
    # In tools/agent.py
    import os
    SUMMARY_API_KEY = os.getenv('GEMINI_API_KEY')
    SCOPUS_API_KEY = os.getenv('SCOPUS_API_KEY')
    ```
    And then set these environment variables in your system.

## Usage

1.  **Run the Streamlit Application:**
    ```bash
    streamlit run tools/slr_app.py
    ```
2.  Open your web browser and navigate to the local URL provided by Streamlit (usually `http://localhost:8501`).
3.  **Input SLR Details:**
    -   Enter your desired paper topic or research goal.
    -   Set the start and end years for paper fetching.
    -   Configure the number of papers to fetch per iteration and the number of search iterations.
    -   Set the number of refinement cycles.
    -   Optionally, upload PDF files to be included in the review.
4.  Click "Generate SLR". The application will process the papers and generate the SLR document and associated reports.
5.  Progress will be displayed in the Streamlit interface.
6.  Once complete, download links for the generated files will be provided.

## File Structure

-   `tools/agent.py`: Core logic for paper fetching, processing, summarization, and LaTeX generation.
-   `tools/slr_app.py`: Streamlit user interface.
-   `tools/regex.py`: (Assumed functionality) Post-processing of generated files.
-   `requirements.txt`: Python package dependencies.
-   `README.md`: This file.
-   `pdf_papers/`: Directory where fetched and uploaded PDFs are stored.
-   `txt_papers/`: Directory where extracted text from PDFs is stored.
-   `summaries/`: Directory where paper summaries are stored.
-   `Results/`: Directory where generated LaTeX sections, the final LaTeX document, BibTeX file, and reports are stored.

## Output

-   **Final SLR LaTeX file:** e.g., `A_Systematic_Literature_Review_on_Your_Topic_Cycle_N.tex` in `Results/`.
-   **BibTeX file:** `biblio.bib` in `Results/`.
-   **Refinement Cycle Report:** `refinement_cycle_report.md` in `Results/`.
-   **Processing Summary Report:** `slr_processing_summary_report.txt` in `Results/`.
-   Individual LaTeX section files (e.g., `related_works.tex`) in `Results/`.
-   (Potentially) `results.md` and `results.tex` in the root directory if `regex.py` post-processing is run.

## Troubleshooting

-   **`pdflatex` not found:** Ensure a LaTeX distribution is installed and `pdflatex` is in your PATH. The app will warn but continue without PDF compilation.
-   **Tesseract errors / OCR issues:** Verify Tesseract installation, PATH configuration, and that necessary language data is present. Check `pytesseract.pytesseract.tesseract_cmd` in `agent.py` if needed.
-   **API Key Errors:** Double-check that your Gemini and Scopus API keys are correctly set in `agent.py` (or environment variables if you've modified it). Ensure the keys are valid and have the necessary permissions/quotas.
-   **`pdf2image` errors on Windows:** Ensure Poppler binaries are in your PATH.