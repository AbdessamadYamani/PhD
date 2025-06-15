import streamlit as st
import os
import zipfile
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # noqa: E402
from tools.agent import process_papers 
import shutil # Added for shutil.which
from tools.regex import process_files

def create_zip_of_results(zip_filename="results_files.zip"):
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        if os.path.exists("results.md"):
            zipf.write("results.md")
        if os.path.exists("results.tex"):
            zipf.write("results.tex")
        if os.path.exists("biblio.bib"):
            zipf.write("biblio.bib")
        if os.path.exists("Results/refinement_cycle_report.md"): # Add refinement report to zip
            zipf.write("Results/refinement_cycle_report.md", arcname="refinement_cycle_report.md")
    return zip_filename

# Constants for status messages from test.py
INVALID_QUERY_STATUS = "INVALID_QUERY_FOR_ACADEMIC_SEARCH"
PROCESSING_FAILED_STATUSES = [
    "NO_PAPERS_FOUND_AFTER_FALLBACK",
    "NO_TEXT_FILES_GENERATED",
    "COULD_NOT_READ_RELEVANT_PAPERS",
    "NO_SUMMARIES_GENERATED",
    "NO_LLM_CONFIRMED_RELEVANT_PAPERS", # Added this status
    "PROCESS_INCOMPLETE_NO_GEMINI_KEY", # New status for missing API key
    "PROCESS_INCOMPLETE_GEMINI_INIT_FAILED", # New status for Gemini model init failure
    "LLM_API_CRITICAL_FAILURE_TOKEN", # New status for critical LLM API errors from agent
]

def main():
    st.title("SLR Markdown Generator")
    st.write("This tool allows you to process papers from ArXiv and manually uploaded PDFs, generate summaries, and create Markdown sections for an SLR.")

    # Check for pdflatex at the beginning
    if not shutil.which("pdflatex"):
        st.warning(
            "`pdflatex` command not found in your system's PATH. "
            "Automated LaTeX compilation and PDF generation will be skipped. "
            "Please install a LaTeX distribution (e.g., MiKTeX, TeX Live) "
            "and ensure `pdflatex` is in your PATH for full functionality."
        )
    # Create necessary directories at startup
    os.makedirs("Results", exist_ok=True)
    os.makedirs("pdf_papers", exist_ok=True)

    gemini_api_key_input = st.text_input(
        "Enter your Gemini API Key:",
        type="password",
        help="Your Google Generative AI API key. This will not be stored after the session."
    )
    scopus_api_key_input = st.text_input(
        "Enter your Scopus API Key (optional):",
        type="password",
        help="Your Elsevier Scopus API key. If provided, Scopus will be used as an additional paper source. This will not be stored after the session."
    )


    # Rest of your code remains the same until the process_files section
    subject = st.text_input(
        "Describe your desired paper topic/goal:",
        help="Enter a natural language description of your research topic (e.g., 'Is Elden Ring the best game ever?'). This will be used to generate an arXiv search query and theme the SLR."
    )
    
    col1, col2 = st.columns(2)
    start_year = col1.number_input("Start Year", min_value=1900, max_value=2100, value=2022)
    end_year = col2.number_input("End Year", min_value=1900, max_value=2100, value=2024)

    num_papers_fetch_per_arxiv_iteration = st.number_input(
        "Number of papers to fetch per ArXiv search iteration:",
        min_value=1, max_value=700, value=3,
        help="For each search query iteration, how many new papers to attempt to fetch."
    )
    num_arxiv_search_iterations = st.number_input(
        "Number of ArXiv Search Query Iterations:",
        min_value=1, max_value=10, value=1, # Default to 1, user can increase
        help="How many times to generate a new ArXiv search query and attempt to fetch papers. Each iteration uses a distinct AI-generated query."
    )
    num_refinement_cycles_ui = st.number_input(
        "Number of Refinement Cycles:",
        min_value=0, max_value=5, value=1,
        help="Number of times the SLR draft will be critiqued and refined by the LLM. '0' means initial generation only, no refinement."
    )
    
    uploaded_files = st.file_uploader(
        "Upload PDFs for manual processing:",
        type=["pdf"],
        accept_multiple_files=True,
        help="You can manually upload PDFs to include them in the processing pipeline."
    )

    if st.button("Generate SLR"):
        if subject and gemini_api_key_input: # Scopus key is optional, so not checking it here for button enablement
            try:
                if uploaded_files:
                    st.write("Saving uploaded PDFs...")
                    for uploaded_file in uploaded_files:
                        with open(os.path.join("pdf_papers", uploaded_file.name), "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    st.success(f"Uploaded {len(uploaded_files)} PDFs successfully!")

                st.write("Processing papers...")
                # Use st.status for detailed, scrollable updates
                with st.status("Starting SLR generation...", expanded=True) as status_container:
                    def streamlit_status_update(message: str):
                        # This function will be called from process_papers
                        status_container.update(label=message)
                        st.write(f"- {message}") # Log message to the main area within the status box

                    # process_papers now returns a tuple: (status_or_final_slr_path, refinement_report_path_or_None)
                    main_output_path_or_status, refinement_report_path = process_papers(
                        natural_language_paper_goal=subject, 
                        year_range=(start_year, end_year),
                        num_papers_to_fetch_per_iteration=num_papers_fetch_per_arxiv_iteration,
                        num_search_iterations=num_arxiv_search_iterations,
                        num_refinement_cycles=num_refinement_cycles_ui, # Pass the new UI value
                        gemini_api_key=gemini_api_key_input, # Pass the API key
                        scopus_api_key=scopus_api_key_input, # Pass the Scopus API key
                        status_update_callback=streamlit_status_update # Pass the callback
                    )
                                
                if main_output_path_or_status == INVALID_QUERY_STATUS:
                    st.warning("The provided paper topic/goal was deemed unsuitable for academic search by the LLM. No arXiv query was executed. Further processing steps are skipped.")
                elif main_output_path_or_status == "LLM_API_CRITICAL_FAILURE_TOKEN": # Specific check for critical LLM API failure
                    st.error("Paper processing stopped due to a critical error with the LLM API (e.g., invalid API key, quota exceeded, or service issue). Please check your API key configuration in `agent.py` (or the UI input if applicable) and ensure the Gemini API service is operational. Review the console logs from `agent.py` for more details.")

                elif main_output_path_or_status in PROCESSING_FAILED_STATUSES:
                    # Display the specific failure reason
                    failure_reason = main_output_path_or_status.replace('_', ' ').title()
                    st.warning(f"Paper processing stopped: {failure_reason}. No papers were fully processed to generate a final report.")
                elif main_output_path_or_status and main_output_path_or_status.startswith("FINAL_SLR_OUTPUT:"):
                    final_slr_file_path = main_output_path_or_status.split(":", 1)[1]
                    st.success(f"Successfully processed papers and generated the SLR!")
                    st.info(f"The final refined SLR LaTeX file is: `{final_slr_file_path}`")
                    if refinement_report_path and os.path.exists(refinement_report_path):
                        st.info(f"A refinement cycle report has been generated: `{refinement_report_path}`")

                    # regex.py (process_files) combines .md files from Results/ into root results.md & results.tex.
                    # test.py's section generation creates .tex files in Results/.
                    # This indicates a potential mismatch if regex.py expects .md section files.
                    # For now, proceeding with the existing call to process_files.
                    # This step might be redundant if the final .tex from test.py is sufficient.
                    # Consider if process_files is still needed or if the final .tex from test.py is the primary output.
                    # For now, let's assume the user might still want the regex.py output.
                    try:
                        st.write("Preparing additional output files (combining sections via regex.py)...")
                        process_files("Results") # Reads from "Results/", outputs to root "results.md" and "results.tex"
                        st.success("Additional output file preparation complete!")
                    except Exception as e_regex:
                        st.warning(f"Could not run regex.py based post-processing: {e_regex}. The primary .tex output from the iterative process should still be available.")

                    # Ensure biblio.bib is at the root for zipping if it was created in Results/
                    # The main process_papers already saves biblio.bib in Results.
                    # The Results() function in test.py also tries to save it.
                    # Let's ensure we use the one from Results/ for consistency.
                    biblio_path_results = os.path.join("Results", "biblio.bib")
                    biblio_path_root = "biblio.bib"
                    
                    # If the primary output is the iterated .tex file, we should make that downloadable.
                    # And the biblio.bib from Results/ should be paired with it.
                    
                    # For zipping, let's ensure biblio.bib is copied to root if regex.py expects it.
                    if os.path.exists(biblio_path_results) and not os.path.exists(biblio_path_root):
                        if os.path.exists(biblio_path_root):
                            try:
                                os.remove(biblio_path_root)
                            except OSError as e:
                                st.error(f"Could not remove existing biblio.bib at root: {e}")
                        try:
                            os.rename(biblio_path_results, biblio_path_root)
                            st.info("Moved biblio.bib to root for packaging.")
                        except OSError as e:
                             st.error(f"Could not move biblio.bib from Results to root: {e}")
                            
                    # Create zip file
                    zip_filename = create_zip_of_results() # Zips root results.md, results.tex, biblio.bib

                    # Download buttons
                    st.subheader("Download Results")
                    col1, col2, col3, col4 = st.columns(4)

                    # Download the primary refined SLR .tex file
                    if os.path.exists(final_slr_file_path):
                        with open(final_slr_file_path, "rb") as f_slr:
                            col1.download_button(label=f"Download Final SLR ({os.path.basename(final_slr_file_path)})", data=f_slr, file_name=os.path.basename(final_slr_file_path), mime="text/x-tex")
                    
                    # Download refinement report
                    if refinement_report_path and os.path.exists(refinement_report_path):
                        with open(refinement_report_path, "rb") as f_report:
                            col2.download_button(label="Download Refinement Report", data=f_report, file_name=os.path.basename(refinement_report_path), mime="text/markdown")

                    # Download biblio.bib (from Results, as it's the most reliable source)
                    if os.path.exists(biblio_path_results):
                        with open(biblio_path_results, "rb") as f_bib:
                            col3.download_button(label="Download biblio.bib", data=f_bib, file_name="biblio.bib", mime="application/x-bibtex")

                    # Download ZIP of all (including regex.py outputs if generated)
                    if os.path.exists(zip_filename):
                        with open(zip_filename, "rb") as f_zip:
                            col4.download_button(label="Download All (ZIP)", data=f_zip, file_name=zip_filename, mime="application/zip")
                    
                    st.markdown("---") # Separator
                    st.write("Outputs from `regex.py` (if generated successfully):")
                    if os.path.exists("results.md"):
                        with open("results.md", "rb") as f:
                            st.download_button(label="Download results.md (from regex.py)", data=f, file_name="results.md", mime="text/markdown")
                    if os.path.exists("results.tex"):
                        with open("results.tex", "rb") as f:
                            st.download_button(label="Download results.tex (from regex.py)", data=f, file_name="results.tex", mime="text/plain")

                elif main_output_path_or_status and main_output_path_or_status.startswith("PROCESS_INCOMPLETE_LAST_QUERY:"):
                    last_query_info_part = main_output_path_or_status.split(":",1)[1] # e.g., "INFO:actual_query" or just "actual_query"
                    st.warning(f"Paper processing was incomplete. The last query information was: `{last_query_info_part}`. A refinement report might still be available.")
                    if refinement_report_path and os.path.exists(refinement_report_path):
                         with open(refinement_report_path, "rb") as f_report:
                            st.download_button("Download Refinement Report (Incomplete Process)", f_report, file_name=os.path.basename(refinement_report_path))
                else: # returned_status_or_query is None or empty string - unexpected
                    st.error("An unexpected error occurred: The paper processing script did not return a valid arXiv query status. Aborting.")

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
        else:
            if not subject:
                st.warning("Please describe your desired paper topic/goal to proceed.")
            if not gemini_api_key_input:
                st.warning("Please enter your Gemini API Key to proceed.")
            # No warning for Scopus key as it's optional


if __name__ == "__main__":
    main()
