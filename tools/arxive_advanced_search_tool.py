import urllib.parse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Tuple
import time
from langchain.tools import tool


def fetch_arxiv_papers(
    Keywords: str,
    max_results: int = 10,
    year_range: Tuple[int, int] = (2000, datetime.now().year)
) -> List[Dict]:
    """
    Fetch papers from arXiv using their API, filtered by keywords and publication year range.

    """
    base_url = 'http://export.arxiv.org/api/query?'
    
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
        
        citation_number = 1  # Start citation numbering
        
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
            
            # Get the main link to the paper
            paper_link = ''
            for link in entry.findall('atom:link', namespaces):
                if link.get('type') == 'text/html':
                    paper_link = link.get('href')
                    break
            
            # Get PDF link
            pdf_link = ''
            for link in entry.findall('atom:link', namespaces):
                if link.get('title') == 'pdf':
                    pdf_link = link.get('href')
                    break
            
            paper = {
                'citation_number': citation_number,
                'title': entry.find('atom:title', namespaces).text.strip(),
                'abstract': entry.find('atom:summary', namespaces).text.strip().replace('\n', ' '),
                'published': published_date[:10],
                'pdf_url': pdf_link
            }
            
            papers.append(paper)
            citation_number += 1  # Increment citation number
            
            # Stop if we’ve collected enough papers
            if len(papers) >= max_results:
                break
            
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error fetching papers: {e}")
    except ET.ParseError as e:
        raise RuntimeError(f"Error parsing XML response: {e}")
    
    return papers


# Example usage:
if __name__ == "__main__":
    # Fetch papers and store the results
    results = fetch_arxiv_papers(Keywords="machine learning", year_range=(2022, 2024))
    
    # Print the returned results in an easy-to-read format
    print(results)
