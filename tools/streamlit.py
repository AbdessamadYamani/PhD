import streamlit as st
import os
import zipfile
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test import process_papers, batch_convert_pdfs_to_text, batch_summarize_papers
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

def main():
    st.title("SLR Markdown Generator")
    st.write("This tool allows you to process papers from ArXiv and manually uploaded PDFs, generate summaries, and create Markdown sections for an SLR.")

    # Create necessary directories at startup
    os.makedirs("Results", exist_ok=True)
    os.makedirs("pdf_papers", exist_ok=True)

    # Rest of your code remains the same until the process_files section
    subject = st.text_input("Enter the subject:", help="The topic for your systematic literature review (SLR).")
    
    col1, col2 = st.columns(2)
    start_year = col1.number_input("Start Year", min_value=1900, max_value=2100, value=2022)
    end_year = col2.number_input("End Year", min_value=1900, max_value=2100, value=2024)

    num_papers = st.number_input("Number of papers to fetch from ArXiv:", min_value=1, max_value=100, value=5)

    uploaded_files = st.file_uploader(
        "Upload PDFs for manual processing:",
        type=["pdf"],
        accept_multiple_files=True,
        help="You can manually upload PDFs to include them in the processing pipeline."
    )

    if st.button("Generate SLR"):
        if subject:
            try:
                if uploaded_files:
                    st.write("Saving uploaded PDFs...")
                    for uploaded_file in uploaded_files:
                        with open(os.path.join("pdf_papers", uploaded_file.name), "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    st.success(f"Uploaded {len(uploaded_files)} PDFs successfully!")

                st.write("Processing papers...")
                process_papers(subject, (start_year, end_year), num_papers=num_papers)

                st.write("Converting PDFs to text...")
                pdf_to_text_result = batch_convert_pdfs_to_text()
                st.info(pdf_to_text_result)

                st.write("Summarizing papers...")
                summaries_result = batch_summarize_papers(keywords=subject)
                st.success("Summaries generated successfully!")

                # Move results to Results directory if they're not already there
                if os.path.exists("results.md"):
                    os.rename("results.md", os.path.join("Results", "results.md"))
                if os.path.exists("results.tex"):
                    os.rename("results.tex", os.path.join("Results", "results.tex"))

                st.write("Processing markdown files...")
                process_files("Results")
                st.success("Markdown files processed successfully!")

                # Create zip file with results from Results directory
                zip_filename = create_zip_of_results()

                col1, col2, col3 = st.columns(3)
                
                results_md_path = os.path.join("Results", "results.md")
                if os.path.exists(results_md_path):
                    with open(results_md_path, "rb") as f:
                        col1.download_button(
                            label="Download Results.md",
                            data=f,
                            file_name="results.md",
                            mime="text/markdown"
                        )
                
                results_tex_path = os.path.join("Results", "results.tex")
                if os.path.exists(results_tex_path):
                    with open(results_tex_path, "rb") as f:
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

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
        else:
            st.warning("Please enter a subject to proceed.")

if __name__ == "__main__":
    main()