import streamlit as st
import os
import zipfile
import sys
# Add the parent directory to Python path to import regex.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test import process_papers, batch_convert_pdfs_to_text, batch_summarize_papers
from tools.regex import process_files 


def create_zip_of_results(zip_filename="results_files.zip"):
    """Create a zip file containing results.md and results.tex"""
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        # Add both result files if they exist
        if os.path.exists("results.md"):
            zipf.write("results.md")
        if os.path.exists("results.tex"):
            zipf.write("results.tex")
    return zip_filename

def main():
    st.title("SLR Markdown Generator")
    st.write("This tool allows you to process papers from ArXiv and manually uploaded PDFs, generate summaries, and create Markdown sections for an SLR.")

    # User input for Subject
    subject = st.text_input("Enter the subject:", help="The topic for your systematic literature review (SLR).")
    
    # User input for year range
    col1, col2 = st.columns(2)
    start_year = col1.number_input("Start Year", min_value=1900, max_value=2100, value=2022)
    end_year = col2.number_input("End Year", min_value=1900, max_value=2100, value=2024)

    # User input for number of papers
    num_papers = st.number_input("Number of papers to fetch from ArXiv:", min_value=1, max_value=100, value=5)

    # File uploader for manual PDF upload
    uploaded_files = st.file_uploader(
        "Upload PDFs for manual processing:",
        type=["pdf"],
        accept_multiple_files=True,
        help="You can manually upload PDFs to include them in the processing pipeline."
    )

    if st.button("Generate SLR"):
        if subject:
            try:
                # Create necessary folders
                pdf_folder = "pdf_papers"
                os.makedirs(pdf_folder, exist_ok=True)

                # Save uploaded PDFs
                if uploaded_files:
                    st.write("Saving uploaded PDFs...")
                    for uploaded_file in uploaded_files:
                        with open(os.path.join(pdf_folder, uploaded_file.name), "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    st.success(f"Uploaded {len(uploaded_files)} PDFs successfully!")

                # Process papers: fetch from ArXiv and use uploaded PDFs
                st.write("Processing papers...")
                process_papers(subject, (start_year, end_year), num_papers=num_papers)

                # Convert all PDFs to text
                st.write("Converting PDFs to text...")
                pdf_to_text_result = batch_convert_pdfs_to_text()
                st.info(pdf_to_text_result)

                # Summarize all text files with the subject as the keywords
                st.write("Summarizing papers...")
                summaries_result = batch_summarize_papers(keywords=subject)
                st.success("Summaries generated successfully!")

                # Process the markdown files using regex.py script
                st.write("Processing markdown files...")
                if os.path.exists("Results"):
                    process_files("Results")
                    st.success("Markdown files processed successfully!")

                    # Create a zip file containing the results files
                    zip_filename = create_zip_of_results()

                    # Provide download buttons for individual files and zip
                    col1, col2, col3 = st.columns(3)
                    
                    if os.path.exists("results.md"):
                        with open("results.md", "rb") as f:
                            col1.download_button(
                                label="Download Results.md",
                                data=f,
                                file_name="results.md",
                                mime="text/markdown"
                            )
                    
                    if os.path.exists("results.tex"):
                        with open("results.tex", "rb") as f:
                            col2.download_button(
                                label="Download Results.tex",
                                data=f,
                                file_name="results.tex",
                                mime="text/plain"
                            )
                    
                    with open(zip_filename, "rb") as f:
                        col3.download_button(
                            label="Download All Results",
                            data=f,
                            file_name=zip_filename,
                            mime="application/zip"
                        )

                    st.success("All result files are ready for download!")
                else:
                    st.error("Results directory not found. Please ensure the directory exists.")

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
        else:
            st.warning("Please enter a subject to proceed.")

if __name__ == "__main__":
    main()