import streamlit as st
import os
import zipfile

from test import process_papers, batch_convert_pdfs_to_text, batch_summarize_papers

def create_zip_from_md_files(zip_filename="markdown_files.zip"):
    # Create a Zip file containing all .md files in the current directory
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        for filename in os.listdir():
            if filename.endswith(".md"):
                zipf.write(filename, os.path.basename(filename))
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
                summaries_result = batch_summarize_papers(keywords=subject)  # Pass keywords (subject) here
                st.success("Summaries generated successfully!")

                # Create a zip file containing all the Markdown files
                zip_filename = create_zip_from_md_files()

                # Provide a download button for the zip file
                with open(zip_filename, "rb") as f:
                    st.download_button(
                        label="Download All Markdown Files",
                        data=f,
                        file_name=zip_filename,
                        mime="application/zip"
                    )

                st.success("All Markdown files are packaged in a ZIP file!")

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
        else:
            st.warning("Please enter a subject to proceed.")

if __name__ == "__main__":
    main()
