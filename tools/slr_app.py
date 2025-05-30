import streamlit as st
import os
import zipfile
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test import process_papers # Assuming test.py is in tools directory
from tools.regex import process_files

def create_zip_of_results(zip_filename="results_files.zip"):
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        if os.path.exists("results.md"):
            zipf.write("results.md")
        if os.path.exists("results.tex"):
            zipf.write("results.tex")
        if os.path.exists("biblio.bib"):
            zipf.write("biblio.bib")
    return zip_filename

# Constants for status messages from test.py
INVALID_QUERY_STATUS = "INVALID_QUERY_FOR_ACADEMIC_SEARCH"
PROCESSING_FAILED_STATUSES = [
    "NO_PAPERS_FOUND_AFTER_FALLBACK",
    "NO_TEXT_FILES_GENERATED",
    "NO_EMBEDDINGS_GENERATED",
    "NO_SEMANTICALLY_RELEVANT_PAPERS_FOUND",
    "COULD_NOT_READ_RELEVANT_PAPERS",
    "NO_SUMMARIES_GENERATED"
]

def main():
    st.title("SLR Markdown Generator")
    st.write("This tool allows you to process papers from ArXiv and manually uploaded PDFs, generate summaries, and create Markdown sections for an SLR.")

    # Create necessary directories at startup
    os.makedirs("Results", exist_ok=True)
    os.makedirs("pdf_papers", exist_ok=True)

    # Rest of your code remains the same until the process_files section
    subject = st.text_input(
        "Describe your desired paper topic/goal:",
        help="Enter a natural language description of your research topic (e.g., 'Is Elden Ring the best game ever?'). This will be used to generate an arXiv search query and theme the SLR."
    )
    
    col1, col2 = st.columns(2)
    start_year = col1.number_input("Start Year", min_value=1900, max_value=2100, value=2022)
    end_year = col2.number_input("End Year", min_value=1900, max_value=2100, value=2024)

    num_search_iterations = st.number_input(
        "Number of search iterations (times to refine ArXiv query):",
        min_value=1, max_value=10, value=1,
        help="How many times the AI should try to generate a new ArXiv search query to find diverse papers."
    )
    num_papers_fetch_per_iteration = st.number_input(
        "Number of papers to fetch per ArXiv search iteration:",
        min_value=1, max_value=50, value=3,
        help="For each search query iteration, how many new papers to attempt to fetch."
    )

    semantic_query = st.text_input(
        "Enter Semantic Search Query:",
        help="Specific query to find the most relevant papers for summarization (e.g., 'applications of AI agents in serious games for learning')."
    )
    num_papers_summarize = st.number_input("Number of top papers to summarize (after all fetching):", min_value=1, max_value=num_papers_fetch_per_iteration * num_search_iterations, value=3)

    uploaded_files = st.file_uploader(
        "Upload PDFs for manual processing:",
        type=["pdf"],
        accept_multiple_files=True,
        help="You can manually upload PDFs to include them in the processing pipeline."
    )

    if st.button("Generate SLR"):
        if subject and semantic_query:
            try:
                if uploaded_files:
                    st.write("Saving uploaded PDFs...")
                    for uploaded_file in uploaded_files:
                        with open(os.path.join("pdf_papers", uploaded_file.name), "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    st.success(f"Uploaded {len(uploaded_files)} PDFs successfully!")

                st.write("Processing papers...")
                with st.spinner("Generating arXiv search query and processing papers..."):
                    # The main call to the enhanced process_papers function
                    returned_status_or_query = process_papers(
                        natural_language_paper_goal=subject, 
                        year_range=(start_year, end_year),
                        num_papers_to_fetch_per_iteration=num_papers_fetch_per_iteration,
                        semantic_search_query=semantic_query,
                        num_papers_to_summarize=num_papers_summarize,
                        num_search_iterations=num_search_iterations
                    )
                                
                if returned_status_or_query == INVALID_QUERY_STATUS:
                    st.warning("The provided paper topic/goal was deemed unsuitable for academic search by the LLM. No arXiv query was executed. Further processing steps are skipped.")
                elif returned_status_or_query in PROCESSING_FAILED_STATUSES:
                    # Display the specific failure reason
                    failure_reason = returned_status_or_query.replace('_', ' ').title()
                    st.warning(f"Paper processing stopped: {failure_reason}. No papers were fully processed to generate a final report.")
                    # Optionally, if you want to show the query that was attempted before this failure,
                    # process_papers would need to return a tuple (status, query_attempted)
                elif returned_status_or_query: # Implies a successful query string was returned
                    actual_query_used = returned_status_or_query
                    st.info(f"Successfully processed papers. The final arXiv Search Query used was: `{actual_query_used}`")
                    st.success("Core paper processing (fetching, conversion, semantic search, summarization, initial .tex generation) complete! Check console for details.")

                    # regex.py (process_files) combines .md files from Results/ into root results.md & results.tex.
                    # test.py's section generation creates .tex files in Results/.
                    # This indicates a potential mismatch if regex.py expects .md section files.
                    # For now, proceeding with the existing call to process_files.
                    
                    st.write("Preparing final output files (combining sections via regex.py)...")
                    process_files("Results") # Reads from "Results/", outputs to root "results.md" and "results.tex"
                    st.success("Final output file preparation complete!")

                    # Ensure biblio.bib is at the root for zipping if it was created in Results/
                    biblio_path_results = os.path.join("Results", "biblio.bib")
                    biblio_path_root = "biblio.bib"
                    if os.path.exists(biblio_path_results):
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
                            
                    # Create zip file with results from Results directory
                    zip_filename = create_zip_of_results() # Zips root results.md, results.tex, biblio.bib

                    # Download buttons
                    col1, col2, col3 = st.columns(3)
                    # results.md and results.tex are expected at root by download buttons
                    if os.path.exists("results.md"):
                        with open("results.md", "rb") as f:
                            col1.download_button(label="Download Results.md", data=f, file_name="results.md", mime="text/markdown")
                    if os.path.exists("results.tex"):
                        with open("results.tex", "rb") as f:
                            col2.download_button(label="Download Results.tex", data=f, file_name="results.tex", mime="text/plain")
                    if os.path.exists(zip_filename):
                        with open(zip_filename, "rb") as f:
                            col3.download_button(label="Download All Results", data=f, file_name=zip_filename, mime="application/zip")
                    st.success("All result files are ready for download (contents depend on successful paper processing).")
                else: # returned_status_or_query is None or empty string - unexpected
                    st.error("An unexpected error occurred: The paper processing script did not return a valid arXiv query status. Aborting.")

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
        else:
            st.warning("Please enter ArXiv Keywords and a Semantic Search Query to proceed.")

if __name__ == "__main__":
    main()
