import streamlit as st
import os
from test import process_papers, batch_convert_pdfs_to_text, batch_summarize_papers

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

    if st.button("Generate Markdown"):
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

                # Summarize all text files
                st.write("Summarizing papers...")
                summaries_result = batch_summarize_papers()
                st.success("Summaries generated successfully!")

                # Provide download buttons for all generated Markdown files
                st.write("Download generated Markdown files:")
                for filename in os.listdir():
                    if filename.endswith(".md"):
                        with open(filename, "r") as file:
                            st.download_button(
                                label=f"Download {filename}",
                                data=file.read(),
                                file_name=filename,
                                mime="text/markdown",
                            )
                st.success("Markdown files generated successfully!")
            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
        else:
            st.warning("Please enter a subject to proceed.")

if __name__ == "__main__":
    main()
