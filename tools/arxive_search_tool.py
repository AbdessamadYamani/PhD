import requests
import urllib.parse
import xml.etree.ElementTree as ET
import time
from datetime import datetime
from typing import Tuple
import pdfplumber  # Make sure to install pdfplumber via pip

def fetch_arxiv_papers(
    Keywords: str,
    year_range: Tuple[int, int] = (2000, datetime.now().year)
) -> str:
    """
    Fetch papers from arXiv using their API, filtered by keywords and publication year range.
    
    Args:
        Keywords (str): Keywords to search for.
        year_range (Tuple[int, int]): Range of publication years (start,end).
    
    Returns:
        str: A message indicating the success or failure of the operation.
    """
    base_url = 'http://export.arxiv.org/api/query?'
    
    max_results: int = 5
    # Build the search query
    search_query = f'all:{Keywords}'
    
    # Build the API query parameters
    params = {
        'search_query': search_query,
        'start': 0,
        'max_results': min(max_results, 100),  # arXiv limits to 100 per request
        'sortBy': 'submittedDate',
        'sortOrder': 'descending'
    }
    
    query_url = base_url + urllib.parse.urlencode(params)
    
    papers = []
    
    try:
        # Add delay to respect arXiv's rate limit (3 seconds between requests)
        time.sleep(3)
        
        response = requests.get(query_url)
        response.raise_for_status()
        
        # Parse the XML response
        root = ET.fromstring(response.content)
        
        # Define XML namespaces used in arXiv's response
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        # Process each entry (paper)
        for entry in root.findall('atom:entry', namespaces):
            # Extract publication date and filter by year range
            published_date = entry.find('atom:published', namespaces).text
            published_year = int(published_date[:4])
            if not (year_range[0] <= published_year <= year_range[1]):
                continue
            
            # Extract authors
            authors = []
            for author in entry.findall('atom:author/atom:name', namespaces):
                authors.append(author.text)
            
            # Get PDF link
            pdf_link = ''
            for link in entry.findall('atom:link', namespaces):
                if link.get('title') == 'pdf':
                    pdf_link = link.get('href')
                    break
            
            # Construct the citation
            citation = f"{', '.join(authors)}. \"{entry.find('atom:title', namespaces).text.strip()}\". arXiv:{entry.find('atom:id', namespaces).text.split('/')[-1]}. Published on {published_date[:10]}."
            
            paper_title = entry.find('atom:title', namespaces).text.strip()
            
            # Download PDF file
            pdf_response = requests.get(pdf_link)
            if pdf_response.status_code == 200:
                pdf_filename = f"{paper_title.replace('/', '_')}.pdf"
                with open(pdf_filename, 'wb') as pdf_file:
                    pdf_file.write(pdf_response.content)

                # Extract text from PDF and save to .txt file
                with pdfplumber.open(pdf_filename) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                
                # Save extracted content to a text file named after the paper title
                txt_filename = f"{paper_title.replace('/', '_')}.txt"
                with open(txt_filename, 'w', encoding='utf-8') as txt_file:
                    txt_file.write(f"Title: {paper_title}\n")
                    txt_file.write(f"Citation: {citation}\n")
                    txt_file.write(f"Published Date: {published_date[:10]}\n")
                    txt_file.write(f"Full Text:\n{full_text}\n")
                    
                paper = {
                    'title': paper_title,
                    'citation': citation,
                    'published': published_date[:10],
                    'pdf_url': pdf_link,
                    'txt_filename': txt_filename  # Save filename for reference
                }
                
                papers.append(paper)

        return "Done: Successfully fetched and saved papers."

    except requests.exceptions.RequestException as e:
        return f"Error fetching papers: {e}"
    except ET.ParseError as e:
        return f"Error parsing XML response: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# Example usage:
result_message = fetch_arxiv_papers("LLM serious games AI", (2022, 2024))
print(result_message)
