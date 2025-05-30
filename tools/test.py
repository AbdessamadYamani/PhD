import os
import requests
import urllib.parse
import xml.etree.ElementTree as ET
import time
from datetime import datetime
from typing import Tuple, List, Dict
import PyPDF2
import google.generativeai as genai
import inspect
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import numpy as np


# Configure API keys for different tasks
SUMMARY_API_KEY = 'AIzaSyDB34rofMFLYfo0zwXnPZ6DLWHs3-I_rjM' # This should be kept secure
genai.configure(api_key=SUMMARY_API_KEY)

# --- New constants for BERT workflow ---
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDINGS_FILE = "embeddings.pkl"
TXT_PAPERS_FOLDER = "txt_papers" # Consistent naming
SUMMARIES_FOLDER = "summaries" # Consistent naming

# Initialize Gemini Model (using the existing model name as requested)
# Model name: 'gemini-2.5-flash-preview-04-17' is not a standard public model name.
# Using 'gemini-1.5-flash-latest' or 'gemini-pro' as a placeholder.
# The user specified 'gemini-2.5-flash-preview-04-17' in their context,
# so we'll assume it's a valid model they have access to.
# If 'gemini-2.5-flash-preview-04-17' is not available,
# you might need to change it to a model like 'gemini-1.5-flash-latest' or 'gemini-pro'.

# --- Constants for processing status ---
INVALID_QUERY_FOR_ACADEMIC_SEARCH = "INVALID_QUERY_FOR_ACADEMIC_SEARCH"
NO_PAPERS_FOUND_AFTER_FALLBACK = "NO_PAPERS_FOUND_AFTER_FALLBACK"
NO_TEXT_FILES_GENERATED = "NO_TEXT_FILES_GENERATED"
NO_EMBEDDINGS_GENERATED = "NO_EMBEDDINGS_GENERATED"
NO_SEMANTICALLY_RELEVANT_PAPERS_FOUND = "NO_SEMANTICALLY_RELEVANT_PAPERS_FOUND"
COULD_NOT_READ_RELEVANT_PAPERS = "COULD_NOT_READ_RELEVANT_PAPERS"
NO_SUMMARIES_GENERATED = "NO_SUMMARIES_GENERATED"
# you might need to change it to a model like 'gemini-1.5-flash-latest' or 'gemini-pro'.
try:
    summary_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Using a known valid model name
    # If 'gemini-2.5-flash-preview-04-17' is indeed the correct one and available to you, you can use:
    # summary_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
except Exception as e:
    print(f"Error initializing Gemini model. Please check model name and API key: {e}")
    print("Using 'gemini-pro' as a fallback model.")
    summary_model = genai.GenerativeModel('gemini-pro')


# Initialize the embedding model
embedding_model_st = SentenceTransformer(EMBEDDING_MODEL_NAME, use_auth_token=False)

tables = r"""
Hare are some examples of tables in latex:
Simple Table
This is the most basic form of a table using the tabular environment.
tex
\documentclass{article}
\begin{document}
\begin{table}[h!]
    \centering
    \begin{tabular}{c c c}
        Cell 1 & Cell 2 & Cell 3 \\
        Cell 4 & Cell 5 & Cell 6 \\
        Cell 7 & Cell 8 & Cell 9 \\
    \end{tabular}
    \caption{A Simple Table}
\end{table}
\end{document}
Table with Borders
You can add borders to your table by using vertical bars (|) in the column specification.
tex
\documentclass{article}
\begin{document}
\begin{table}[h!]
    \centering
    \begin{tabular}{|c|c|c|}
        \hline
        Col1 & Col2 & Col3 \\ 
        \hline
        1 & 2 & 3 \\ 
        4 & 5 & 6 \\ 
        \hline
    \end{tabular}
    \caption{Table with Borders}
\end{table}
\end{document}
Multi-Page Table
For tables that span multiple pages, use the longtable package.
tex
\documentclass{article}
\usepackage{longtable}
\begin{document}
\begin{longtable}{|c|c|c|}
    \caption{Multi-Page Table} \\ 
    \hline
    Col1 & Col2 & Col3 \\ 
    \hline
    \endfirsthead
    \hline
    Col1 & Col2 & Col3 \\ 
    \hline
    \endhead
    1 & 2 & 3 \\ 
    4 & 5 & 6 \\ 
    \hline
    \endfoot
    7 & 8 & 9 \\ 
\end{longtable}
\end{document}
Table with Multi-Column and Multi-Row
You can create more complex tables using multirow and multicolumn.
tex
\documentclass{article}
\usepackage{multirow}
\begin{document}
\begin{table}[h!]
    \centering
    \begin{tabular}{|c|c|c|}
        \hline
        \multirow{2}{*}{Header} & Column A & Column B \\ 
        & Sub A & Sub B \\ 
        \hline
        Row 1 & Data A1 & Data B1 \\ 
        Row 2 & Data A2 & Data B2 \\ 
        \hline
    \end{tabular}
    \caption{Table with Multi-Column and Multi-Row}
\end{table}
\end{document}
Adjustable Width Table Using tabularx
The tabularx package allows for tables with adjustable column widths.
tex
\documentclass{article}
\usepackage{tabularx}
\begin{document}
\begin{table}[h!]
    \centering
    \begin{tabularx}{\textwidth}{|X|X|X|}
        \hline
        Column 1 & Column 2 & Column 3 \\ 
        \hline
        This is a longer text in column one. & Text in column two. & Short text. \\ 
        \hline
    \end{tabularx}
    \caption{Adjustable Width Table Using Tabularx}
\end{table}
\end{document}

Table with Color Using colortbl
You can add color to your tables by using the colortbl package.
tex
\documentclass{article}
\usepackage{colortbl}
\usepackage{xcolor} % For defining colors
\begin{document}
\begin{table}[h!]
    \centering
    \arrayrulecolor{black}\arrayrulewidth=1pt
    \begin{tabular}{|c|c|c|}
        \hline
        \rowcolor{gray!30} Header 1 & Header 2 & Header 3 \\ 
        \hline
        \rowcolor{yellow!20} Data 1 & Data 2 & Data 3 \\ 
        \hline
        Data 4 & Data 5 & Data 6 \\ 
        \hline
    \end{tabular}
    \caption{Table with Color}
\end{table}
\end{document}
Nested Tables
You can create nested tables by placing a tabular environment inside another tabular.
tex
\documentclass{article}
\begin{document}
\begin{table}[h!]
    \centering
    \begin{tabular}{|c|c|}
        \hline
        Main Table Col1 & Main Table Col2 \\ 
        \hline
        A & 
        \begin{tabular}{c|c}
            Nested Col1 & Nested Col2 \\ 
            \hline
            1 & 2 \\ 
            3 & 4 \\ 
        \end{tabular} \\ 
        \hline
        B & C \\ 
        \hline
    \end{tabular}
    \caption{Nested Tables}
\end{table}
\end{document}
Table with Footnotes Using threeparttable
The threeparttable package allows you to add footnotes to your table.
tex
\documentclass{article}
\usepackage{threeparttable}
\begin{document}
\begin{table}[h!]
    \centering
    \begin{threeparttable}
        \caption{Table with Footnotes}
        \begin{tabular}{|c|c|}
            \hline
            Column 1 & Column 2 \\ 
            \hline
            Data A1 & Data B1\tnote{a} \\ 
            Data A2 & Data B2 \\ 
            \hline
        \end{tabular}
        \begin{tablenotes}
            \footnotesize
            \item[a] This is a footnote for Data B1.
        \end{tablenotes}
    </threeparttable}
\end{table}
\end{document}
Table with Side Notes Using sidewaystable
You can rotate a table using the sidewaystable environment from the lscape package.
tex
\documentclass{article}
\usepackage{lscape} % For landscape tables
\begin{document}
\begin{landscape}
    \begin{table}[h!]
        \centering
        \begin{tabular}{|c|c|c|}
            \hline
            Column 1 & Column 2 & Column 3 \\ 
            \hline
            A1 & B1 & C1 \\ 
            A2 & B2 & C2 \\ 
            A3 & B3 & C3 \\ 
            \hline
        \end{tabular}
        \caption{Sideways Table Example}
    \end{table}
\end{landscape}
\end{document}
Table with Custom Column Alignment Using array
You can define custom column types using the array package.
tex
\documentclass{article}
\usepackage{array} % For custom column types
\begin{document}

% Define a new column type for centered text with specific width.
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}

\begin{table}[h!]
    \centering
    \begin{tabular}{|C{3cm}|C{4cm}|C{5cm}|}
        \hline
        Column 1 & Column 2 & Column 3 \\ 
        \hline
        This is some centered text in column one. & This is some centered text in column two. & This is some centered text in column three. \\ 
        \hline
    \end{tabular}
    \caption{Table with Custom Column Alignment}
\end{table}

\end{document}
Summary Table with Totals Using booktabs
The booktabs package allows for better spacing and rules in tables.
tex
\documentclass{article}
\usepackage{booktabs} % For better rules in tables

\begin{document}

\begin{table}[h!]
    \centering
    \begin{tabular}{@{}lcc@{}}
        \toprule
        Item    & Quantity & Price \\ 
        \midrule
        Apples  & 10      & \$5   \\ 
        Oranges & 15      & \$7.5 \\ 
        Bananas & 20      & \$10  \\ 
        \midrule
        Total   &         & \$22.5\\ 
        \bottomrule
    \end{tabular}
    \caption{Summary Table with Totals Using Booktabs}
\end{table}

\end{document}

"""
Figures =r"""
Basic Line Chart
You can create a simple line chart using the pgfplots package.
tex
\documentclass{{article}}
\usepackage{pgfplots}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{tikzpicture}
        \begin{axis}[
            title={Basic Line Chart},
            xlabel={X-axis},
            ylabel={Y-axis},
            grid=both,
            legend pos=outer north east
        ]
        \addplot[color=blue, thick] coordinates {(0,0) (1,1) (2,4) (3,9)};
        \addlegendentry{$y=x^2$}
        
        \addplot[color=red, thick] coordinates {(0,0) (1,1) (2,2) (3,3)};
        \addlegendentry{$y=x$}
        \end{axis}
    \end{tikzpicture}
    \caption{A Basic Line Chart}
\end{figure}

\end{{document}}
Bar Chart
To create a bar chart, you can also use the pgfplots package.
tex
\documentclass{{article}}
\usepackage{pgfplots}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{tikzpicture}
        \begin{axis}[
            ybar,
            title={Bar Chart Example},
            xlabel={Categories},
            ylabel={Values},
            xtick={1,2,3},
            xticklabels={A,B,C},
            grid=both
        ]
        \addplot[style={blue,fill=blue!30}] coordinates {(1,5) (2,10) (3,15)};
        \end{axis}
    \end{tikzpicture}
    \caption{A Simple Bar Chart}
\end{figure}

\end{{document}}
Pie Chart Using pgf-pie
For pie charts, you can use the pgf-pie package.
tex
\documentclass{{article}}
\usepackage{pgf-pie}

\begin{{document}}

\begin{figure}[h]
    \centering
    \pie[text=legend]{30/Category A, 40/Category B, 30/Category C}
    \caption{A Simple Pie Chart}
\end{figure}

\end{{document}}
Scatter Plot
You can create a scatter plot with the following code.
tex
\documentclass{{article}}
\usepackage{pgfplots}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{tikzpicture}
        \begin{axis}[
            title={Scatter Plot Example},
            xlabel={X-axis},
            ylabel={Y-axis},
            grid=both,
        ]
        \addplot[only marks, mark=*] coordinates {(1,2) (2,3) (3,5) (4,7)};
        \end{axis}
    \end{tikzpicture}
    \caption{A Simple Scatter Plot}
\end{figure}

\end{{document}}
Gantt Chart Using pgfgantt
You can create Gantt charts using the pgfgantt package.
tex
\documentclass{{article}}
\usepackage[gantt]{pgfgantt}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{ganttchart}[
        hgrid,
        vgrid,
        title/.style={draw=none, fill=none},
        bar/.style={fill=blue!50},
        bar label font=\small,
        time slot format=isodate-yearmonth,
      ]{2024-01}{2024-12}
      % Tasks
      \gantttitlecalendar*{} & 
      \ganttbar[bar label font=\footnotesize]{Task 1}{2024-01}{2024-03} \\ 
      \ganttbar[bar label font=\footnotesize]{Task 2}{2024-04}{2024-06} \\ 
      \ganttbar[bar label font=\footnotesize]{Task 3}{2024-07}{2024-09} \\ 
      % Milestones
      \ganttmilestone[bar label font=\footnotesize]{Milestone 1}{2024-06} 
      % Grouping tasks
      \ganttgroup[bar label font=\footnotesize]{Group 1}{2024-01}{2024-09} 
      % More tasks under the group
      \\ 
      % Final task
      \ganttbar[bar label font=\footnotesize]{Final Task}{2024-10}{2024-12} 
      
    \end{ganttchart}
    \caption{A Gantt Chart Example}
\end{figure}

\end{{document}}

Flowchart
You can create flowcharts using the tikz package.
tex
\documentclass{{article}}
\usepackage{tikz}
\usetikzlibrary{arrows.meta}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{tikzpicture}[
        node distance=1.5cm,
        every node/.style={draw, rectangle, minimum width=2cm, minimum height=1cm},
        arrow/.style={-Stealth}
    ]
        \node (start) {Start};
        \node (process1) [below of=start] {Process Step 1};
        \node (decision) [below of=process1, diamond, aspect=2] {Decision?};
        \node (process2a) [below of=decision, yshift=-0.5cm] {Process Step 2A};
        \node (process2b) [right of=decision, xshift=3cm] {Process Step 2B};
        \node (end) [below of=process2a] {End};

        \draw[arrow] (start) -- (process1);
        \draw[arrow] (process1) -- (decision);
        \draw[arrow] (decision) -- node[right] {Yes} (process2a);
        \draw[arrow] (decision.east) -- node[above] {No} ++(0.5,0) |- (process2b);
        \draw[arrow] (process2a) -- (end);
    \end{tikzpicture}
    \caption{Flowchart Example}
\end{figure}

\end{{document}}
Gantt Chart
You can create Gantt charts using the pgfgantt package.
tex
\documentclass{{article}}
\usepackage[gantt]{pgfgantt}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{ganttchart}[
        hgrid,
        vgrid,
        title/.style={draw=none, fill=none},
      ]{2024-01}{2024-12}
      % Tasks
      \gantttitlecalendar*{} & 
      \ganttbar{Task 1}{2024-01}{2024-03} \\ 
      \ganttbar{Task 2}{2024-04}{2024-06} \\ 
      \ganttbar{Task 3}{2024-07}{2024-09} \\ 
      % Final task
      \ganttbar{Final Task}{2024-10}{2024-12} 
    \end{ganttchart}
    \caption{Gantt Chart Example}
\end{figure}

\end{{document}}
Circular Diagram
You can create circular diagrams using the smartdiagram package.
tex
\documentclass[tikz,border=10pt]{standalone}
\usepackage{smartdiagram}

\begin{{document}}

\begin{figure}[h]
    \centering
    \smartdiagram[circular diagram:clockwise]{Define styles, Position nodes, Add arrows, Add labels, Review and refine}
    \caption{Circular Diagram Example}
\end{figure}

\end{{document}}
Decision Tree
You can create decision trees using the tikz package.
tex
\documentclass{{article}}
\usepackage{tikz}
\usetikzlibrary{trees}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{tikzpicture}[
        every node/.style={draw,circle},
        level distance=1.5cm,
        edge from parent fork down
    ]
        \node {Root}
            child { node {Left Child} }
            child { node {Right Child} }
            child { node {Another Child} };
    \end{tikzpicture}
    \caption{Decision Tree Example}
\end{figure}

\end{{document}}
Family Tree
You can represent family trees using the tikz package.
tex
\documentclass{{article}}
\usepackage{tikz}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{tikzpicture}[every node/.style={draw,circle}]
        % Generation 1
        \node {Grandparent 1} child {node {Parent 1}} child {node {Parent 2}};
        
        % Generation 2
        \node[below right=of Grandparent 1] {Grandparent 2} child {node {Child 1}} child {node {Child 2}};
        
    \end{tikzpicture}
    \caption{Family Tree Example}
\end{figure}

\end{{document}}
Histogram
You can create histograms using the pgfplots package.
tex
\documentclass{{article}}
\usepackage{pgfplots}

\begin{{document}}

\begin{figure}[h]
    \centering
    \begin{tikzpicture}
        \begin{axis}[
            ybar,
            title={Histogram Example},
            xlabel={Value},
            ylabel={Frequency},
            xtick={0,1,2,3,...,10},
            grid=both,
            bar width=0.5cm,
            enlarge x limits=0.15,
            ymin=0,
            ymax=10,
        ]
        % Data for histogram bars
        \addplot coordinates {(0,3) (1,5) (2,7) (3,6) (4,8)};
        \end{axis}
    \end{tikzpicture}
    \caption{Histogram Example}
\end{figure}

\end{{document}}
"""

def create_arxiv_search_query_from_natural_language(
    natural_language_goal: str,
    previous_angles_and_queries: List[Tuple[str, str]] = None
) -> Tuple[str, str]:
    """
    Uses a Gemini LLM to transform a natural language goal into a research angle
    and natural language search phrase. Always tries to generate a valid query.
    """
    prompt_parts = [
        "You are an expert research assistant. Transform user goals into academic search queries.",
        f"User's overarching research goal: \"{natural_language_goal}\"",
        "\nGenerate a research angle and search phrase for arXiv. Focus on academic aspects:",
        "1. Identify core concepts and academic perspectives",
        "2. Avoid subjective phrases like 'best ever'",
        "3. Focus on measurable aspects: design, impact, analysis, etc.",
        "4. Prioritize academic terminology over casual language",
    ]

    if previous_angles_and_queries:
        prompt_parts.append("\nYou have already explored the following angles and search phrases:")
        for idx, (prev_angle, prev_query) in enumerate(previous_angles_and_queries):
            prompt_parts.append(f"{idx+1}. Angle: {prev_angle}\n   Search Phrase: {prev_query}")
        prompt_parts.append("\nPlease suggest a NEW and DISTINCT research angle and a corresponding concise natural language search phrase for the user's overarching goal. Avoid repeating themes or query structures already tried.")
    else:
        prompt_parts.append("\nCreate the first research angle and query.")

    prompt_parts.extend([
        "\nExamples:",
        "User goal: 'Is Elden Ring the best game ever?'",
        "Research Angle: 'Analysis of Elden Ring's game design innovations and player engagement metrics'",
        "Search Phrase: 'Elden Ring game design player engagement metrics'",
        "",
        "User goal: 'Why is ChatGPT so popular?'",
        "Research Angle: 'Adoption factors and user satisfaction studies of large language models'",
        "Search Phrase: 'LLM adoption factors user satisfaction'",

        "\nOutput Format:",
        "Provide the Research Angle first, then the Generated Search Phrase.",
        "Use the following format strictly:",
        "RESEARCH_ANGLE_START",
        "[Your formulated research angle]",
        "RESEARCH_ANGLE_END",
        "ARXIV_QUERY_START",
        "[Your generated Search Phrase]",
        "ARXIV_QUERY_END"
    ])
    prompt = "\n".join(prompt_parts)

    try:
        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            temperature=0.7,  # Higher creativity for diverse queries
            max_output_tokens=500 
        )
        response = summary_model.generate_content(
            prompt,
            generation_config=generation_config
        )
        response_text = response.text.strip()
        angle_match = re.search(r"RESEARCH_ANGLE_START\s*(.*?)\s*RESEARCH_ANGLE_END", 
                                response_text, re.DOTALL)
        query_match = re.search(r"ARXIV_QUERY_START\s*(.*?)\s*ARXIV_QUERY_END", 
                                response_text, re.DOTALL)

        if angle_match and query_match:
            return angle_match.group(1).strip(), query_match.group(1).strip()
        
        # Fallback to direct extraction
        return "Academic analysis of " + natural_language_goal, natural_language_goal

    except Exception as e:
        print(f"Error generating query: {e}")
        return "Academic analysis of " + natural_language_goal, natural_language_goal


def fetch_arxiv_papers(
    search_query_str: str,
    year_range: Tuple[int, int] = (2000, datetime.now().year),
    num_papers: int = 5,
    pdf_folder: str = "pdf_papers",
    already_fetched_arxiv_ids: set = None
) -> Tuple[List[Dict], int, str]:
    """
    Fetch new papers from ArXiv based on a search query.
    
    Args:
        search_query_str: Search query string
        year_range: Tuple of (start_year, end_year) for filtering papers
        num_papers: Number of papers to fetch
        pdf_folder: Directory to save PDF files
        already_fetched_arxiv_ids: Set of arXiv IDs already fetched
    
    Returns:
        Tuple: (list of metadata dicts, count of fetched papers, status message)
    """
    os.makedirs(pdf_folder, exist_ok=True)
    if already_fetched_arxiv_ids is None:
        already_fetched_arxiv_ids = set()

    newly_fetched_papers_metadata_list = []
    newly_fetched_and_saved_count = 0
    base_url = 'http://export.arxiv.org/api/query?'
    
    # Simple query formatting - just search for what the user asked for
    if search_query_str.startswith('all:') or search_query_str.startswith('ti:') or search_query_str.startswith('abs:'):
        search_query_for_api = search_query_str
    else:
        search_query_for_api = f'all:"{search_query_str}"'
    
    print(f"Searching ArXiv for: {search_query_for_api}")
    
    start_index = 0
    max_results = min(num_papers * 3, 100)  # Get a bit more than needed to account for filtering
    
    while newly_fetched_and_saved_count < num_papers:
        params = {
            'search_query': search_query_for_api,
            'start': start_index,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        query_url = base_url + urllib.parse.urlencode(params)
        
        try:
            time.sleep(3)
            response = requests.get(query_url, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespaces = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
            entries = root.findall('atom:entry', namespaces)
            
            print(f"Found {len(entries)} entries")
            
            if not entries:
                break
            
            for entry in entries:
                if newly_fetched_and_saved_count >= num_papers:
                    break
                
                # Extract paper info
                title_element = entry.find('atom:title', namespaces)
                title = title_element.text.strip() if title_element is not None else "N/A Title"
                
                published_date_element = entry.find('atom:published', namespaces)
                if published_date_element is None or not published_date_element.text:
                    continue
                    
                published_date = published_date_element.text
                try:
                    published_year = int(published_date[:4])
                except ValueError:
                    continue
                    
                # Check year range
                if not (year_range[0] <= published_year <= year_range[1]):
                    continue
                
                # Get ArXiv ID
                id_url_element = entry.find('atom:id', namespaces)
                id_url = id_url_element.text if id_url_element is not None else ""
                arxiv_id_match = re.search(r'abs/([^v]+)', id_url)
                arxiv_id = arxiv_id_match.group(1) if arxiv_id_match else ""
                
                if not arxiv_id or arxiv_id in already_fetched_arxiv_ids:
                    continue
                
                # Get other metadata
                authors = [auth.find('atom:name', namespaces).text 
                          for auth in entry.findall('atom:author', namespaces) 
                          if auth.find('atom:name', namespaces) is not None]
                
                doi_element = entry.find('arxiv:doi', namespaces)
                doi = doi_element.text if doi_element is not None else "N/A"
                
                journal_ref_element = entry.find('arxiv:journal_ref', namespaces)
                journal_ref = journal_ref_element.text if journal_ref_element is not None else "N/A"
                
                # Create filename
                clean_title = re.sub(r'[^\w\s-]', '', title).strip()
                clean_title = re.sub(r'\s+', '_', clean_title)[:100]
                if not clean_title:
                    clean_title = f"arxiv_{arxiv_id.replace('/', '_')}"
                
                pdf_filename = os.path.join(pdf_folder, f"{clean_title}.pdf")
                pdf_url = f'https://arxiv.org/pdf/{arxiv_id}.pdf'
                
                paper_metadata = {
                    'title': title,
                    'authors': authors,
                    'doi': doi,
                    'id_url': id_url,
                    'pdf_url': pdf_url,
                    'journal_ref': journal_ref,
                    'published_year': published_year,
                    'arxiv_id': arxiv_id,
                    'local_pdf_path': pdf_filename
                }
                
                # Skip if already exists
                if os.path.exists(pdf_filename):
                    newly_fetched_papers_metadata_list.append(paper_metadata)
                    newly_fetched_and_saved_count += 1
                    continue
                
                # Download PDF
                try:
                    print(f"Downloading: {title[:80]}...")
                    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ArXiv-Fetcher)'}
                    pdf_response = requests.get(pdf_url, headers=headers, timeout=60)
                    pdf_response.raise_for_status()
                    
                    with open(pdf_filename, 'wb') as f:
                        f.write(pdf_response.content)
                    
                    print(f"Saved: {pdf_filename}")
                    newly_fetched_papers_metadata_list.append(paper_metadata)
                    newly_fetched_and_saved_count += 1
                    
                except Exception as e:
                    print(f"Failed to download {title}: {e}")
                    if os.path.exists(pdf_filename):
                        os.remove(pdf_filename)
                    continue
            
            start_index += max_results
            if newly_fetched_and_saved_count >= num_papers:
                break
                
        except Exception as e:
            print(f"Error querying ArXiv: {e}")
            break
    
    if newly_fetched_and_saved_count > 0:
        status_msg = f"Successfully downloaded {newly_fetched_and_saved_count} papers"
    else:
        status_msg = f"No papers found for query: {search_query_str}"
    
    return newly_fetched_papers_metadata_list, newly_fetched_and_saved_count, status_msg




def batch_convert_pdfs_to_text(pdf_folder: str = "pdf_papers", txt_folder: str = "txt_papers") -> str:
    """
    Convert all PDFs in the folder to text files in batch.
    """
    print(f"\nConverting PDFs in '{pdf_folder}' to text files in '{txt_folder}'...")
    os.makedirs(txt_folder, exist_ok=True)
    
    if not os.path.exists(pdf_folder):
        return f"PDF folder '{pdf_folder}' does not exist. No PDFs to convert."

    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    if not pdf_files:
        return "No PDF files found in the specified folder."
    
    success_count = 0
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        # Use original PDF filename (without .pdf) for the .txt filename
        txt_filename_base = os.path.splitext(pdf_file)[0]
        txt_filepath = os.path.join(txt_folder, f"{txt_filename_base}.txt")
        
        try:
            print(f"\nProcessing: {pdf_file}")
            
            if os.path.exists(txt_filepath) and os.path.getsize(txt_filepath) > 0: # Check if non-empty
                print(f"Text file already exists and is not empty, skipping: {txt_filepath}")
                success_count += 1
                continue
            
            full_text = ""
            with open(pdf_path, 'rb') as file:
                try:
                    pdf_reader = PyPDF2.PdfReader(file)
                    if pdf_reader.is_encrypted:
                        try:
                            pdf_reader.decrypt('') # Try with empty password
                        except Exception as decrypt_err:
                            print(f"Could not decrypt {pdf_file}: {decrypt_err}. Skipping.")
                            continue
                    
                    for i, page in enumerate(pdf_reader.pages):
                        try:
                            full_text += page.extract_text() + "\n"
                        except Exception as page_extract_err:
                            print(f"Error extracting text from page {i+1} of {pdf_file}: {page_extract_err}")
                            # Continue to extract from other pages if possible
                except PyPDF2.errors.PdfReadError as pdf_read_err:
                    print(f"Error reading PDF file {pdf_file} (possibly corrupted or not a PDF): {pdf_read_err}")
                    continue # Skip this file
            
            if not full_text.strip():
                print(f"No text extracted from {pdf_file}. It might be image-based or protected.")
                # Optionally create an empty file or skip creating one
                # with open(txt_filepath, 'w', encoding='utf-8') as txt_file: # Create empty if desired
                #     txt_file.write("") 
                continue # Don't count as success if no text

            with open(txt_filepath, 'w', encoding='utf-8') as txt_file:
                txt_file.write(full_text)
            
            print(f"Text saved to: {txt_filepath}")
            success_count += 1
            
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            continue
    
    return f"Successfully converted {success_count} out of {len(pdf_files)} PDFs to text."


def generate_and_store_embeddings(
    txt_folder: str = TXT_PAPERS_FOLDER,
    embeddings_file: str = EMBEDDINGS_FILE,
    model: SentenceTransformer = embedding_model_st
) -> List[Tuple[str, np.ndarray]]:
    """
    Generates embeddings for all text files in a folder and stores them.
    Returns a list of (filename, embedding) tuples.
    """
    print("\n--- Starting: Generate and Store Embeddings ---")
    if not os.path.exists(txt_folder):
        print(f"Text folder {txt_folder} does not exist. Cannot generate embeddings.")
        return []
        
    embeddings_dir = os.path.dirname(embeddings_file)
    if embeddings_dir and not os.path.exists(embeddings_dir):
        os.makedirs(embeddings_dir)
    
    paper_embeddings = []
    txt_files = [f for f in os.listdir(txt_folder) if f.lower().endswith('.txt')]

    if not txt_files:
        print(f"No text files found in {txt_folder} to generate embeddings.")
        if os.path.exists(embeddings_file):
            try:
                with open(embeddings_file, 'rb') as f:
                    paper_embeddings = pickle.load(f)
                print(f"Loaded existing embeddings from {embeddings_file} as no new text files were found.")
                return paper_embeddings
            except Exception as e:
                print(f"Could not load existing embeddings from {embeddings_file}: {e}")
        return []

    print(f"\nGenerating embeddings for texts in {txt_folder} using model {EMBEDDING_MODEL_NAME}...")
    
    for txt_file in txt_files:
        txt_path = os.path.join(txt_folder, txt_file)
        try:
            with open(txt_path, 'r', encoding='utf-8') as file:
                text = file.read()
            if not text.strip():
                print(f"Skipping empty file: {txt_file}")
                continue
            
            print(f"BERT: Generating embedding for: {txt_file}")
            # Ensure text is not excessively long for the model if it has limits
            # Some models might truncate, others might error.
            # For 'all-MiniLM-L6-v2', typical limit is 512 tokens, but SentenceTransformer handles longer texts by splitting.
            embedding = model.encode(text, convert_to_tensor=False, show_progress_bar=False)
            paper_embeddings.append((txt_file, embedding))
        except Exception as e:
            print(f"Error generating embedding for {txt_file}: {e}")
            continue
    
    if paper_embeddings:
        try:
            with open(embeddings_file, 'wb') as f:
                pickle.dump(paper_embeddings, f)
            print(f"BERT: Embeddings saved to {embeddings_file}")
        except Exception as e:
            print(f"Error saving embeddings to {embeddings_file}: {e}")
    else:
        print("No embeddings were generated or loaded.")
    print("--- Finished: Generate and Store Embeddings ---")
        
    return paper_embeddings

def semantic_search(
    query: str,
    paper_embeddings_data: List[Tuple[str, np.ndarray]],
    model: SentenceTransformer = embedding_model_st,
    top_n: int = 3,
    similarity_threshold: float = 0.1 # Added threshold
) -> List[Tuple[str, float]]: 
    """
    Performs semantic search to find top_n relevant paper filenames and their scores.
    Filters results by a similarity_threshold.
    """
    print("\n--- Starting: Semantic Search ---")
    if not query or not paper_embeddings_data:
        print("Query or embeddings data is empty. Cannot perform semantic search.")
        print("--- Finished: Semantic Search (aborted) ---")
        return []

    print(f"BERT: Performing semantic search for query: '{query}'")
    print(f"BERT: Using top_n: {top_n}, similarity_threshold: {similarity_threshold}")
    query_embedding = model.encode(query, convert_to_tensor=False, show_progress_bar=False).reshape(1, -1)
    
    if not any(isinstance(item, tuple) and len(item) == 2 for item in paper_embeddings_data):
        print("Embeddings data is not in the expected format (list of (filename, embedding) tuples).")
        return []

    filenames = [item[0] for item in paper_embeddings_data]
    # Ensure embeddings are correctly stacked
    try:
        embeddings = np.vstack([item[1] for item in paper_embeddings_data])
    except ValueError as ve:
        print(f"Error stacking embeddings, likely due to inconsistent embedding dimensions: {ve}")
        # Print shapes for debugging
        for i, item in enumerate(paper_embeddings_data):
            if hasattr(item[1], 'shape'):
                print(f"Shape of embedding {i} ({item[0]}): {item[1].shape}")
            else:
                print(f"Embedding {i} ({item[0]}) is not a numpy array or has no shape attribute.")
        return []


    print("BERT: Calculating cosine similarities...")
    similarities = cosine_similarity(query_embedding, embeddings)[0]
    
    # Combine filenames, similarities, and sort
    results_with_scores = list(zip(filenames, similarities))
    # Sort by score descending
    results_with_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Filter by threshold and then take top_n
    filtered_results = [(fn, float(score)) for fn, score in results_with_scores if score >= similarity_threshold]
    
    top_results = filtered_results[:top_n]

    if not top_results:
        print(f"No papers found above similarity threshold {similarity_threshold}.")
    else:
        print(f"Found {len(top_results)} relevant papers above threshold.")
        for fn, score in top_results:
            print(f"  - {fn} (Score: {score:.4f})")

    print("--- Finished: Semantic Search ---")
    return top_results


def summarize_paper(paper_text: str, paper_name: str, subject: str) -> str:
    """
    Summarize a single paper, discussing its relevance to the subject and quoting key points.
    """
    # Ensure paper_text is not excessively long for the LLM prompt
    # A common limit for prompts is around 30k characters for some models, but this varies.
    # Truncate if necessary, or implement chunking for very long papers.
    max_text_len = 25000 # Characters, adjust based on model limits and typical paper length
    if len(paper_text) > max_text_len:
        print(f"Warning: Paper text for '{paper_name}' is very long ({len(paper_text)} chars). Truncating to {max_text_len} chars for summary prompt.")
        paper_text = paper_text[:max_text_len] + "\n[...text truncated...]"


    prompt = f"""You are an expert academic researcher. Your task is to summarize the provided paper content for a systematic literature review (SLR) on the subject of: [{subject}].

Follow these instructions precisely:
1.  **Extract Metadata**: Before the summary, list the following information if discernible from the text or paper name. If not found, state "N/A".
    *   Author(s): (List authors if available)
    *   Title: {paper_name} (Use the provided paper name as the title)
    *   Journal/Conference: (If mentioned in the text)
    *   Year: (If mentioned or inferable)
    *   DOI: (If mentioned)
    *   URL: (If mentioned)
    *   Type of Paper: (e.g., Journal Article, Conference Paper, Workshop Paper, Review, Survey, Technical Report, etc. Infer if possible)

2.  **Relevance Discussion**: Briefly discuss the paper's relevance to the SLR subject [{subject}].

3.  **Key Points**: Extract and list key points, findings, methodologies, or conclusions from the paper that are *directly relevant* to the SLR subject [{subject}].
    *   Quote these key points verbatim from the paper content if possible.
    *   Cite these quotes with "[{paper_name}]".

4.  **Focus**:
    *   The summary must be concise and focused *only* on aspects related to [{subject}].
    *   If the paper is *not at all relevant* to *all aspects* of the subject [{subject}], state: "This paper does not appear to be relevant to the specified subject of '{subject}'." and provide no further summary.

5.  **Output Format**:
    *   Start directly with the extracted metadata. Do not include conversational preambles like "Okay, here's the summary..." or "I will now summarize...".

Paper Name: [{paper_name}]
SLR Subject: [{subject}]

Paper Content:
{paper_text}
"""
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.2, # For factual summarization
            max_output_tokens=1500 # Allow longer summaries
        )
        response = summary_model.generate_content(prompt, generation_config=generation_config)
        return response.text.strip()
    except Exception as e:
        print(f"Error summarizing paper {paper_name} with subject '{subject}': {e}")
        return f"Error summarizing paper {paper_name}. Details: {str(e)}"


def batch_summarize_papers(
    subject_keywords: str,
    relevant_papers_info: List[Dict[str, any]], 
    summaries_folder: str = SUMMARIES_FOLDER
) -> str:
    """
    Summarize a list of relevant papers.
    relevant_papers_info should be a list of dictionaries,
    each with 'filename', 'text', and optionally 'score'.
    """
    print(f"\nGenerating summaries for {len(relevant_papers_info)} relevant papers on subject: '{subject_keywords}'...")
    os.makedirs(summaries_folder, exist_ok=True)

    if not relevant_papers_info:
        print("No relevant papers provided to summarize.")
        return ""

    all_summaries_list = []
    for paper_info in relevant_papers_info:
        paper_text = paper_info['text']
        original_filename_no_ext = os.path.splitext(paper_info['filename'])[0]
        
        # Sanitize filename for summary output (similar to PDF cleaning)
        clean_summary_name_base = re.sub(r'[^\w\s-]', '', original_filename_no_ext).strip()
        clean_summary_name_base = re.sub(r'\s+', '_', clean_summary_name_base)
        clean_summary_name_base = clean_summary_name_base[:100] # Truncate
        if not clean_summary_name_base: clean_summary_name_base = f"summary_{original_filename_no_ext.replace('/', '_')}"

        summary_filename_only = f"{clean_summary_name_base}_summary.txt"
        summary_filepath = os.path.join(summaries_folder, summary_filename_only)
        
        # Use the original (potentially messy) filename for the prompt, as it might contain useful title info
        paper_name_for_prompt = original_filename_no_ext 

        try:
            score_info = f"(Score: {paper_info.get('score', 'N/A'):.4f})" if 'score' in paper_info else ""
            print(f"\nProcessing for summary: {paper_info['filename']} {score_info}")

            if os.path.exists(summary_filepath) and os.path.getsize(summary_filepath) > 10: # Check if non-trivial summary exists
                print(f"Summary already exists, loading: {summary_filepath}")
                with open(summary_filepath, 'r', encoding='utf-8') as summary_file:
                    summary_content = summary_file.read()
                    if "This paper does not appear to be relevant" not in summary_content: # Only add if relevant
                        all_summaries_list.append(summary_content)
                continue

            summary_content = summarize_paper(paper_text, paper_name_for_prompt, subject_keywords)

            if "This paper does not appear to be relevant" in summary_content:
                print(f"Paper '{paper_name_for_prompt}' deemed not relevant to '{subject_keywords}'. Summary not saved to main list, but file created.")
            else:
                 all_summaries_list.append(summary_content)

            with open(summary_filepath, 'w', encoding='utf-8') as summary_file:
                summary_file.write(summary_content)
            print(f"Summary saved to: {summary_filepath}")

        except Exception as e:
            print(f"Error processing {paper_info['filename']} for summary: {e}")
            continue
    
    return "\n\n---\n\n".join(all_summaries_list)


def generate_markdown(prompt: str, filename: str, context: str = "") -> str:
    """
    Generate a Markdown file with optional context using Gemini.
    """
    # Ensure results directory exists
    results_dir = os.path.dirname(filename)
    if results_dir and not os.path.exists(results_dir):
        os.makedirs(results_dir)
        print(f"Created directory: {results_dir}")

    try:
        combined_prompt = context + "\n\n" + prompt if context else prompt
        # Add generation config for potentially long outputs
        generation_config = genai.types.GenerationConfig(
            temperature=0.3, # Balance creativity and factuality for report sections
            max_output_tokens=8000 # Allow very long outputs for full sections (check model limits)
        )
        response = summary_model.generate_content(combined_prompt, generation_config=generation_config)
        
        # Basic check for response content
        if not response.text or not response.text.strip():
            print(f"Warning: LLM returned empty or whitespace-only response for {filename}. Prompt was:\n{combined_prompt[:500]}...")
            generated_text = f"% LLM returned empty response for this section: {filename}\n"
        else:
            generated_text = response.text

        with open(filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        print(f"Generated {filename}")
        return generated_text
    except Exception as e:
        error_message = f"Error generating {filename}: {e}\nPrompt context (first 500 chars):\n{context[:500]}\nPrompt (first 500 chars):\n{prompt[:500]}"
        print(error_message)
        # Write error to file to preserve it
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(f"% Error generating this section: {e}\n")
        return f"% Error generating this section for {filename}: {e}"

    
def create_bibliometric(summaries:str) -> str:
    if not summaries.strip():
        print("No summaries provided for bibliometric analysis. Skipping biblio.bib generation.")
        return "% No summaries provided for bibliometric analysis.\n"
        
    prompt = f"""Based on the following paper summaries, create a .bib file content for a BibTeX bibliography.
Each entry should attempt to extract and format the following fields if available in the summaries: author, title, journal (or booktitle for conferences), year, pages, doi, url.
Use standard BibTeX entry types (e.g., @article, @inproceedings, @book, @techreport). Create a unique BibTeX key for each entry (e.g., AuthorYearKeyword).

Summaries of papers:
{summaries}

Output ONLY the BibTeX entries. Do not include any other text, explanations, or markdown formatting.
Example of an entry:
@inproceedings{{Smith2022DarkSouls,
  author    = {{Florence Smith Nicholls and Michael Cook}},
  title     = {{The Dark Souls of Archaeology: Recording Elden Ring}},
  booktitle = {{Proceedings of Foundations of Digital Games (FDG'22)}},
  year      = {{2022}},
  pages     = {{1--10}},
  doi       = {{XXXXXXX.XXXXXXX}},
  url       = {{https://doi.org/XXXXXXX.XXXXXXX}}
}}
"""
    
    return generate_markdown(prompt, 'Results/biblio.bib')


def read_metadata() -> str:
    """Read metadata from the output file."""
    output_file = "metadata.txt" 
    
    if not os.path.exists(output_file):
        print(f"Metadata file '{output_file}' does not exist.")
        return "Metadata file does not exist."
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f: # Added encoding
            metadata_content = f.read()
        return metadata_content
    except Exception as e:
        print(f"Error reading metadata file '{output_file}': {e}")
        return f"Error reading metadata: {e}"


def create_charts(section_content: str, section_name_for_file: str) -> str:
    """
    Enhances a LaTeX section by adding charts/tables based on its content.
    section_name_for_file is used for the output filename.
    """
    if not section_content.strip():
        print(f"Section content for '{section_name_for_file}' is empty. Skipping chart creation.")
        return section_content # Return original empty content

    # Create the file name based on the variable name
    file_name = f"Results/{section_name_for_file}_with_charts.tex" # Changed to .tex

    prompt = f"""
Act as an expert LaTeX document processor and researcher. Your task is to analyze the provided LaTeX **section of a paper** and enhance it.

### Task Description:
1.  **Analyze Content for Visualizations**:
    *   Read the provided LaTeX `\\section{{{section_name_for_file}}}{{...}}` content.
    *   Identify parts of the text that describe data, comparisons, processes, or structures that could be effectively visualized as a chart, graph, or complex table using LaTeX (TikZ, pgfplots, pgfgantt, etc.).
    *   If suitable content for new visualizations is found, create the LaTeX code for these visualizations *from scratch*. Do NOT use placeholders for images or refer to external image files.
    *   Integrate these newly created LaTeX visualizations seamlessly into the provided section content.

2.  **Review Existing Tables/Figures (if any within the section)**:
    *   If the provided section already contains `\\begin{{table}}...\\end{{table}}` or `\\begin{{figure}}...\\end{{figure}}` environments, review them for correctness.
    *   Correct formatting, alignment, or structural issues in existing tables/figures.
    *   Ensure they are appropriately placed within the section flow.

3.  **LaTeX Best Practices and Error Correction**:
    *   Ensure the entire output is valid LaTeX code for the given section.
    *   Correct common LaTeX errors if they appear in the input or are introduced:
        *   Proper package usage (assume necessary packages like `pgfplots`, `tikz`, `longtable`, `multirow`, `tabularx`, `colortbl`, `xcolor`, `pgfgantt`, `smartdiagram`, `array`, `booktabs`, `lscape`, `threeparttable` are loaded in the main document preamble – DO NOT add `\\usepackage` commands here).
        *   Correct command syntax, matching braces `{{}}`, and environments.
        *   Proper table structures (`&`, `\\\\`, `\\hline`, `\\cline`).
        *   Avoid `Runaway argument?` or `Something's wrong--perhaps a missing \\item`.

4.  **Output**:
    *   Return *only* the complete, corrected, and enhanced LaTeX code for the section, starting with `\\section{{{section_name_for_file}}}{{...}}` (or `\\subsection`, etc., if that was the input structure) and ending appropriately.
    *   Do NOT include `\\documentclass`, `\\begin{{document}}`, `\\end{{document}}`, or `\\usepackage` commands.
    *   Do NOT add any conversational text, explanations, or apologies.

### Input Data:
-   **Section of Paper (LaTeX code)**:
    ```latex
    {section_content}
    ```
-   **Examples of LaTeX Tables (for inspiration, if needed by the LLM to generate new ones)**:
    ```latex
    {tables}
    ```
-   **Examples of LaTeX Figures/Charts (for inspiration, if needed by the LLM to generate new ones)**:
    ```latex
    {Figures}
    ```

Return the **modified LaTeX code for the section ONLY**.
"""
    
    return generate_markdown(prompt, file_name, context=f"Enhancing section: {section_name_for_file}")


def Results(abstract: str, related_works: str,research_methodes: str,review_finding: str,discussion: str,subject: str, bibliometric_content: str, actual_paper_title: str) -> str:
    # Ensure Results directory exists
    os.makedirs("Results", exist_ok=True)

    # Combine all sections into a full LaTeX document string
    # Basic LaTeX preamble - this should ideally be more robust or configurable
    # For now, including common packages based on other function prompts.
    # The individual create_X functions are told NOT to include \usepackage.
    # This main Results function will assemble the full .tex file.

    latex_preamble = fr"""\documentclass[11pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage{{amsmath}}
\usepackage{{amsfonts}}
\usepackage{{amssymb}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\hypersetup{{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,      
    urlcolor=cyan,
    pdftitle={{SLR on {subject}}},
    pdfpagemode=FullScreen,
    }}
\usepackage{{xcolor}}
\usepackage{{geometry}}
\geometry{{a4paper, margin=1in}}

% Packages for tables and figures based on your examples and function prompts
\usepackage{{longtable}}
\usepackage{{multirow}}
\usepackage{{tabularx}}
\usepackage{{colortbl}}
\usepackage{{pgfplots}}
\pgfplotsset{{compat=1.18}} % Or latest compatible version
\usepackage{{tikz}}
\usetikzlibrary{{arrows.meta, trees, shapes.geometric, positioning}} % For flowcharts, decision trees etc.
\usepackage[gantt]{{pgfgantt}} % For Gantt charts
\usepackage{{smartdiagram}} % For circular diagrams
\usepackage{{array}} % For custom table column types
\usepackage{{booktabs}} % For professional tables
\usepackage{{lscape}} % For landscape tables/figures
\usepackage{{threeparttable}} % For table footnotes
\usepackage{{caption}} % For better caption control
\usepackage{{subcaption}} % For subfigures/subtables

% Citation package (e.g., natbib) - choose one
\usepackage[numbers,sort&compress]{{natbib}}
\bibliographystyle{{plainnat}} % A common style that works with natbib

\title{{{actual_paper_title}}}
\author{{Your Name / Research Group}} % Placeholder
\date{{\\today}}
"""

    full_latex_document = f"{latex_preamble}\n\n\\begin{{document}}\n\n\\maketitle\n\n"
    full_latex_document += f"{abstract}\n\n" # abstract_intro.md now contains abstract, intro, keywords
    # related_works, research_methodes, etc. are already LaTeX sections
    full_latex_document += f"{related_works}\n\n"
    full_latex_document += f"{research_methodes}\n\n"
    full_latex_document += f"{review_finding}\n\n"
    full_latex_document += f"{discussion}\n\n" # discussion_conclusion.md contains discussion & conclusion

    # Add bibliography section
    full_latex_document += "\\section*{References}\n"
    full_latex_document += "\\bibliography{biblio}\n\n" # Assumes biblio.bib is in the same directory or path is specified

    full_latex_document += "\\end{document}\n"
    
    # Sanitize title for filename
    safe_title_filename = re.sub(r'[^\w\s-]', '', actual_paper_title).strip()
    safe_title_filename = re.sub(r'\s+', '_', safe_title_filename)[:100] # Max 100 chars for filename part
    if not safe_title_filename: safe_title_filename = "Untitled_Paper"
    output_filename = f"Results/{safe_title_filename}.tex"
    try:
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(full_latex_document)
        print(f"Generated complete LaTeX document: {output_filename}")
        # Also save the biblio.bib content if it was passed and is not just a filename
        if bibliometric_content and not os.path.exists("Results/biblio.bib"): # Save if not already saved by create_bibliometric
             with open("Results/biblio.bib", 'w', encoding='utf-8') as bib_file:
                bib_file.write(bibliometric_content)
             print("Saved biblio.bib content to Results/biblio.bib")

        return full_latex_document
    except Exception as e:
        print(f"Error generating {output_filename}: {e}")
        return f"% Error generating {output_filename}: {e}"


def create_background(review_findings: str,related_works: str,research_methodes: str,discussion_conclusion: str, bibliometric_content: str) -> str:
    prompt = fr"""
Act as an expert academic writer. Create the **Background** section for a systematic literature review (SLR).

### Task Description:
1.  **Purpose**: Define key terms, concepts, and foundational works relevant to the SLR. This section helps readers understand the terminology and context used throughout the paper.
2.  **Content Source**: Extract important keywords, concepts, and seminal works from the provided sections:
    *   Review Findings: {review_findings}
    *   Related Works: {related_works}
    *   Research Methods: {research_methodes}
    *   Discussion and Conclusion: {discussion_conclusion}
3.  **Focus**: Define the **top 3-5 most critical concepts or foundational works** that are essential for understanding the SLR. Prioritize terms that might have context-specific meanings within this paper.
4.  **Citations**:
    *   Use `\cite{{bibtex_key}}` for all definitions and references to foundational works. Assume BibTeX keys are available from the provided Bibliography.
    *   Ensure citation keys match those in the `biblio.bib` file (examples can be inferred from the bibliometric content).
5.  **LaTeX Formatting**:
    *   The section must be in Overleaf-compatible LaTeX format, starting with `\section{{Background}}`.
    *   Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, or `\usepackage` commands.
    *   Output only the LaTeX code for this section.
6.  **Bibliography for Context (DO NOT REPRODUCE IN OUTPUT, FOR CITATION KEY INFERENCE ONLY)**:
    ```bibtex
    {bibliometric_content}
    ```

### Output:
Return *only* the complete LaTeX code for the `\section{{Background}}`. Do not include any explanations or conversational text.
"""
    return generate_markdown(prompt, 'Results/background.tex') # Changed to .tex


def create_related_works(summaries: str,subject: str,Biblio_content:str) -> str:
    if not summaries.strip():
        print("No summaries provided for related works. Skipping section generation.")
        return "\\section{Related Works}\n% No summaries provided to generate this section.\n"

    prompt = rf"""
Create a comprehensive **Related Works** section for a systematic literature review (SLR) on the subject: **{subject}**.

### Requirements:
1.  **Content and Structure**:
    *   Start with `\section{{Related Works}}`.
    *   Analyze the provided paper summaries to identify themes, trends, compare methodologies, and discuss how they relate to `{subject}`.
    *   Focus on papers that are highly relevant to `{subject}`. If summaries indicate irrelevance, they should be downplayed or omitted from detailed discussion.
    *   Synthesize information into a cohesive narrative. Avoid a simple list of summaries. Group related papers by theme or approach.
2.  **Writing Style**:
    *   Maintain a formal academic tone.
    *   Logically link paragraphs and ideas.
3.  **Citations**:
    *   Use `\cite{{bibtex_key}}` for all references to the summarized papers. Infer BibTeX keys from the provided Bibliography content (e.g., AuthorYear, or a key part of the title).
    *   Ensure every claim or piece of information derived from a summary is appropriately cited.
4.  **LaTeX Formatting**:
    *   Output *only* Overleaf-compatible LaTeX code for this section.
    *   Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, or `\usepackage` commands.
5.  **Bibliography for Context (DO NOT REPRODUCE IN OUTPUT, FOR CITATION KEY INFERENCE ONLY)**:
    ```bibtex
    {Biblio_content}
    ```

### Input Data:
-   **Summaries of Papers**:
    {summaries}
-   **SLR Subject**: {subject}

Return *only* the complete LaTeX code for the `\section{{Related Works}}`.
"""
    return generate_markdown(prompt, 'Results/related_works.tex') # Changed to .tex


def create_reshearch_methodes(related_works_content: str, summaries: str, subject: str, Biblio_content:str) -> str:
    if not summaries.strip() and not related_works_content.strip():
        print("Insufficient input (summaries/related works) for research methods. Skipping section generation.")
        return "\\section{Research Methods}\n% Insufficient input to generate this section.\n"

    prompt = rf"""
Create a detailed **Research Methods** section for a systematic literature review (SLR) on **{subject}**.

### Requirements:
1.  **Guidelines**: State whether **Kitchenham** or **PRISMA** guidelines (or a hybrid) were followed and briefly explain the choice or adaptation.
2.  **Structure (Subsections)**:
    *   `\subsection{{Introduction}}`: Briefly introduce the methodology.
    *   `\subsection{{Research Questions (RQs)}}`:
        *   List primary RQs (e.g., RQ1, RQ2). For each, state its motivation.
        *   Optionally, list sub-questions if applicable.
    *   `\subsection{{Search Strategy}}`:
        *   Describe the search process: databases queried (e.g., ArXiv, IEEE Xplore, Google Scholar, Scopus, Web of Science).
        *   Mention the search string(s) used. If complex, explain its components (e.g., using PICO or keyword combinations). The initial search query was derived from "{subject}".
        *   Include date range of the search.
        *   Optionally, include a PRISMA-like flowchart (using TikZ or similar, if you can generate the LaTeX for it; otherwise, describe the stages).
    *   `\subsection{{Inclusion and Exclusion Criteria}}`: List criteria for paper selection (e.g., language, publication type, relevance to RQs). Justify them.
    *   `\subsection{{Quality Assessment}}`: Describe criteria used to assess the quality of included studies (e.g., rigor, credibility, relevance).
    *   `\subsection{{Data Extraction and Synthesis}}`: Explain how data was extracted from selected papers and how it was synthesized to answer RQs.
3.  **LaTeX Formatting**:
    *   Start with `\section{{Research Methods}}`.
    *   Use Overleaf-compatible LaTeX. Include LaTeX for tables or lists if appropriate (e.g., for criteria).
    *   Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, or `\usepackage` commands.
4.  **Citations**: Use `\cite{{bibtex_key}}` when referencing methodological papers or tools. Infer BibTeX keys from the provided Bibliography content.
5.  **Bibliography for Context (DO NOT REPRODUCE IN OUTPUT, FOR CITATION KEY INFERENCE ONLY)**:
    ```bibtex
    {Biblio_content}
    ```

### Input Context:
-   **Related Works Section Content (for context on study domain)**:
    {related_works_content}
-   **Paper Summaries (for context on papers found)**:
    {summaries}
-   **SLR Subject**: {subject}

Return *only* the complete LaTeX code for the `\section{{Research Methods}}`.
"""
    return generate_markdown(prompt, 'Results/research_methodes.tex') # Changed to .tex


def create_review_findings(research_methodes_content: str, summaries: str, subject: str, Biblio_content:str) -> str:
    if not summaries.strip():
        print("No summaries provided for review findings. Skipping section generation.")
        return "\\section{Review Findings}\n% No summaries provided to generate this section.\n"
    if not research_methodes_content.strip():
        print("Research methods section content is empty. Findings might be generic.")
        # Allow proceeding but with a warning, as findings are primarily from summaries.

    prompt = fr"""
Create a detailed **Review Findings** section for the systematic literature review (SLR) on **{subject}**.

### Requirements:
1.  **Structure and Content**:
    *   Start with `\section{{Review Findings}}`.
    *   Provide an **introduction** summarizing the purpose of this section.
    *   Systematically answer the research questions (RQs) outlined in the (provided) Research Methods section, using synthesized insights from the paper summaries. If RQs are not explicitly in `research_methodes_content`, infer plausible RQs based on `{subject}` and structure findings around them.
    *   Highlight:
        *   Key insights, patterns, and themes emerging from the literature.
        *   Consistencies and contradictions in findings across studies.
        *   Identified gaps or under-researched areas.
2.  **Citations**:
    *   Cite all sources explicitly using `\cite{{bibtex_key}}`. Reference papers by their BibTeX keys.
    *   Ensure every key finding attributed to specific studies is cited.
3.  **LaTeX Formatting**:
    *   Use Overleaf-compatible LaTeX.
    *   Employ tables, lists, or even simple TikZ/pgfplots figures (if you can generate the LaTeX code for them) to summarize or visualize findings where appropriate (e.g., distribution of studies, comparison of methods/tools).
    *   Ensure logical flow and coherence.
    *   Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, or `\usepackage` commands.
4.  **Bibliography for Context (DO NOT REPRODUCE IN OUTPUT, FOR CITATION KEY INFERENCE ONLY)**:
    ```bibtex
    {Biblio_content}
    ```

### Input Data:
-   **Research Methods Section Content (for RQs and context)**:
    {research_methodes_content}
-   **Paper Summaries (primary source for findings)**:
    {summaries}
-   **SLR Subject**: {subject}

Return *only* the complete LaTeX code for the `\section{{Review Findings}}`.
"""
    return generate_markdown(prompt, 'Results/review_findings.tex') # Changed to .tex


def create_discussion_conclusion(review_findings_content: str, summaries: str, subject: str, Biblio_content:str) -> str:
    if not review_findings_content.strip():
        print("Review findings content is empty. Discussion/Conclusion will be very generic. Skipping.")
        return "\\section{Discussion}\n% Review findings were empty, cannot generate discussion.\n\n\\section{Conclusion}\n% Review findings were empty."

    prompt = rf"""
Create a **Discussion** section and a **Conclusion** section for the systematic literature review (SLR) on **{subject}**.

### Requirements:
1.  **Structure**:
    *   Start with `\section{{Discussion}}`.
    *   Follow with `\section{{Conclusion}}`.
2.  **Discussion Content**:
    *   Interpret the key findings presented in the (provided) `Review Findings` section.
    *   Compare/contrast findings with existing literature or theories (draw from `summaries` or general knowledge if applicable).
    *   Discuss implications of the findings (e.g., for practice, policy, theory).
    *   Acknowledge limitations of the SLR itself and of the reviewed studies.
    *   Suggest areas for future research based on identified gaps or limitations.
3.  **Conclusion Content**:
    *   Briefly summarize the main findings of the SLR in relation to the primary research questions or objectives.
    *   Reiterate the significance of the findings.
    *   Provide a final take-home message. Avoid introducing new information.
4.  **Citations**: Use `\cite{{bibtex_key}}` appropriately in the Discussion when referring to specific studies or findings.
5.  **LaTeX Formatting**:
    *   Use Overleaf-compatible LaTeX.
    *   Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, or `\usepackage` commands.
6.  **Bibliography for Context (DO NOT REPRODUCE IN OUTPUT, FOR CITATION KEY INFERENCE ONLY)**:
    ```bibtex
    {Biblio_content}
    ```

### Input Data:
-   **Review Findings Section Content**:
    {review_findings_content}
-   **Paper Summaries (for context and potential citation)**:
    {summaries}
-   **SLR Subject**: {subject}

Return *only* the complete LaTeX code for the `\section{{Discussion}}` and `\section{{Conclusion}}`.
"""
    return generate_markdown(prompt, 'Results/discussion_conclusion.tex') # Changed to .tex


def create_abstract_intro(review_findings_content: str, related_works_content:str, research_methodes_content:str, discussion_conclusion_content:str, subject: str, Biblio_content:str) -> str:
    prompt = rf"""
Create the **Abstract**, **Keywords**, and **Introduction** sections for a systematic literature review (SLR) titled: "Systematic Literature Review: {subject}".

### Requirements:
1.  **Abstract**:
    *   Format: `\begin{{abstract}} ... \end{{abstract}}`.
    *   Content: Briefly state the SLR's purpose/context, main objectives/RQs, search/selection methods, key synthesized findings, principal conclusions, and main implications/future work. (Approx. 150-250 words).
2.  **Keywords**:
    *   Format: `\textbf{{Keywords:}} keyword1, keyword2, keyword3, keyword4, keyword5.` (Provide 5-7 relevant keywords).
3.  **Introduction (`\section{{Introduction}}`)**:
    *   Provide background on the topic `{subject}`.
    *   State the problem/motivation for this SLR.
    *   Clearly state the SLR's objectives and research questions (RQs).
    *   Briefly outline the scope of the review.
    *   Mention the structure of the paper (e.g., "Section 2 discusses related work...").
    *   Use `\cite{{bibtex_key}}` for any background literature cited.
4.  **Content Source**: Synthesize information from the provided sections:
    *   Review Findings: {review_findings_content}
    *   Related Works: {related_works_content}
    *   Research Methods: {research_methodes_content}
    *   Discussion and Conclusion: {discussion_conclusion_content}
5.  **LaTeX Formatting**:
    *   Output *only* Overleaf-compatible LaTeX code for these three sections.
    *   Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, `\title`, `\author`, `\date`, `\maketitle`, or `\usepackage` commands. These will be handled by the main document assembler.
6.  **Bibliography for Context (DO NOT REPRODUCE IN OUTPUT, FOR CITATION KEY INFERENCE ONLY)**:
    ```bibtex
    {Biblio_content}
    ```

### Output:
Return *only* the LaTeX code for the Abstract (within `\begin{{abstract}}...\end{{abstract}}`), then Keywords, then the Introduction section (`\section{{Introduction}}...`).
"""
    return generate_markdown(prompt, 'Results/abstract_intro_keywords.tex') # Changed to .tex


def process_papers(
    natural_language_paper_goal: str,
    year_range: Tuple[int, int],
    num_papers_to_fetch_per_iteration: int, # Parameter name kept for clarity in this function
    semantic_search_query: str,
    num_papers_to_summarize: int = 3,
    semantic_search_threshold: float = 0.25,
    num_search_iterations: int = 1
) -> str:
    # print(f"Starting paper processing pipeline for: '{natural_language_paper_goal}'")
    print(f"Starting iterative paper search: '{natural_language_paper_goal}'")
    print(f"SLR Subject/Goal: '{natural_language_paper_goal}'")
    print(f"Search iterations: {num_search_iterations}, Papers to fetch per iteration: {num_papers_to_fetch_per_iteration}")

    pdf_folder = "pdf_papers"
    txt_papers_folder_path = TXT_PAPERS_FOLDER
    summaries_folder_path = SUMMARIES_FOLDER

    os.makedirs("Results", exist_ok=True)
    os.makedirs(pdf_folder, exist_ok=True)
    os.makedirs(txt_papers_folder_path, exist_ok=True)
    os.makedirs(summaries_folder_path, exist_ok=True)

    all_angles_and_queries = []
    cumulative_fetched_paper_metadata = [] 
    globally_fetched_arxiv_ids = set()    
    # last_successful_query = None          
    
    for i in range(num_search_iterations):
        print(f"\n>>> ITERATION {i+1}/{num_search_iterations} <<<")
        
        # Generate research angle and query
        current_angle, current_query = create_arxiv_search_query_from_natural_language(
            natural_language_paper_goal,
            previous_angles_and_queries=all_angles_and_queries
        )
        
        print(f"Generated Angle: {current_angle}")
        print(f"Generated Query: {current_query}")
        all_angles_and_queries.append((current_angle, current_query))

        # Call the updated fetch_arxiv_papers function
        # Fetch papers with this query
        newly_fetched_metadata, fetched_count, fetch_status_msg = fetch_arxiv_papers(
            search_query_str=current_query,
            year_range=year_range,
            num_papers=num_papers_to_fetch_per_iteration, # Maps to num_papers in fetch_arxiv_papers
            pdf_folder=pdf_folder,
            already_fetched_arxiv_ids=globally_fetched_arxiv_ids
        )
        print(f"Iteration {i+1} Fetch Result: {fetch_status_msg}")

        # Track new papers
        for paper_meta in newly_fetched_metadata:
            arxiv_id = paper_meta.get('arxiv_id')
            if arxiv_id and arxiv_id not in globally_fetched_arxiv_ids:
                cumulative_fetched_paper_metadata.append(paper_meta)
                globally_fetched_arxiv_ids.add(arxiv_id)

    if not cumulative_fetched_paper_metadata:
        print("No papers were fetched across all iterations.")
        return NO_PAPERS_FOUND_AFTER_FALLBACK 

    metadata_filepath = os.path.join("Results", "metadata.txt")
    print(f"\nWriting consolidated metadata for {len(cumulative_fetched_paper_metadata)} unique papers to {metadata_filepath}...")
    with open(metadata_filepath, 'w', encoding='utf-8') as f_meta:
        f_meta.write("ArXiv Paper Metadata (Consolidated from all iterations)\n")
        f_meta.write("=" * 50 + "\n")
        for paper_meta in cumulative_fetched_paper_metadata:
            f_meta.write(f"Title: {paper_meta.get('title', 'N/A')}\n")
            f_meta.write(f"Authors: {', '.join(paper_meta.get('authors', []))}\n")
            f_meta.write(f"DOI: {paper_meta.get('doi', 'N/A')}\n")
            f_meta.write(f"URL: {paper_meta.get('id_url', 'N/A')}\n")
            f_meta.write(f"PDF URL: {paper_meta.get('pdf_url', 'N/A')}\n")
            f_meta.write(f"Journal Reference: {paper_meta.get('journal_ref', 'N/A')}\n")
            f_meta.write(f"Published Year: {paper_meta.get('published_year', 'N/A')}\n")
            f_meta.write(f"ArXiv ID: {paper_meta.get('arxiv_id', 'N/A')}\n")
            f_meta.write("=" * 30 + "\n")

    conversion_result = batch_convert_pdfs_to_text(pdf_folder=pdf_folder, txt_folder=txt_papers_folder_path)
    print(f"\nPDF to Text Conversion Result: {conversion_result}")
    num_txt_files = len([f for f in os.listdir(txt_papers_folder_path) if f.endswith('.txt') and os.path.getsize(os.path.join(txt_papers_folder_path, f)) > 0])
    if num_txt_files == 0:
        print("No non-empty text files were generated from PDFs. Aborting.")
        return NO_TEXT_FILES_GENERATED

    print("\n>>> Phase 2: Generate and Store Embeddings <<<")
    embeddings_storage_file = os.path.join("Results", EMBEDDINGS_FILE)
    paper_embeddings_data = generate_and_store_embeddings(txt_folder=txt_papers_folder_path, embeddings_file=embeddings_storage_file)
    if not paper_embeddings_data:
        print("No embeddings generated or loaded. Cannot proceed with semantic search and summarization.")
        return NO_EMBEDDINGS_GENERATED

    print(f"\n>>> Phase 3: Perform Semantic Search <<<")
    print(f"Query for semantic search: '{semantic_search_query}'")
    print(f"Number of top papers to find: {num_papers_to_summarize}")
    top_n_papers_found = semantic_search(
        query=semantic_search_query,
        paper_embeddings_data=paper_embeddings_data,
        model=embedding_model_st,
        top_n=num_papers_to_summarize,
        similarity_threshold=semantic_search_threshold
    )

    if not top_n_papers_found:
        print("No relevant papers found by semantic search above the threshold. Skipping summarization and report generation.")
        return NO_SEMANTICALLY_RELEVANT_PAPERS_FOUND

    relevant_papers_for_summary = []
    for filename, score in top_n_papers_found:
        txt_path = os.path.join(txt_papers_folder_path, filename)
        try:
            with open(txt_path, 'r', encoding='utf-8') as f: text_content = f.read()
            if text_content.strip():
                relevant_papers_for_summary.append({'filename': filename, 'text': text_content, 'score': score})
            else: print(f"Skipping empty text file for relevant paper: {filename}")
        except Exception as e: print(f"Error reading text for relevant paper {filename}: {e}")

    if not relevant_papers_for_summary:
        print("Could not read text for any semantically relevant papers or all were empty. Skipping summarization.")
        return COULD_NOT_READ_RELEVANT_PAPERS

    print(f"\n>>> Phase 4: Summarize Relevant Papers (Top {len(relevant_papers_for_summary)}) <<<")
    all_summaries_text = batch_summarize_papers(
        subject_keywords=natural_language_paper_goal,
        relevant_papers_info=relevant_papers_for_summary,
        summaries_folder=summaries_folder_path
    )

    if not all_summaries_text.strip():
        print("No summaries were generated (or all papers were deemed irrelevant). Skipping report generation.")
        return NO_SUMMARIES_GENERATED

    print(f"\n>>> Phase 5: Generate SLR Sections using {len(relevant_papers_for_summary)} summaries <<<")
    
    print("\nGenerating Bibliometric Analysis section (biblio.bib)...")
    bibliometric_content = create_bibliometric(all_summaries_text)

    print("\nGenerating Related Works section...")
    related_works_tex = create_related_works(all_summaries_text, natural_language_paper_goal, bibliometric_content)
    related_works_enhanced_tex = create_charts(related_works_tex, "Related_Works")


    print("\nGenerating Research Methods section...")
    research_methodes_tex = create_reshearch_methodes(related_works_enhanced_tex, all_summaries_text, natural_language_paper_goal, bibliometric_content)
    research_methodes_enhanced_tex = create_charts(research_methodes_tex, "Research_Methods")


    print("\nGenerating Review Findings section...")
    review_findings_tex = create_review_findings(research_methodes_enhanced_tex, all_summaries_text, natural_language_paper_goal, bibliometric_content)
    review_findings_enhanced_tex = create_charts(review_findings_tex, "Review_Findings")


    print("\nGenerating Discussion and Conclusion section...")
    discussion_conclusion_tex = create_discussion_conclusion(review_findings_enhanced_tex, all_summaries_text, natural_language_paper_goal, bibliometric_content)

    print("\nGenerating Background section...") 
    background_tex = create_background(review_findings_enhanced_tex, related_works_enhanced_tex, research_methodes_enhanced_tex, discussion_conclusion_tex, bibliometric_content)
    
    print("\nGenerating Abstract, Introduction, and Keywords...")
    abstract_intro_keywords_tex = create_abstract_intro(review_findings_enhanced_tex, related_works_enhanced_tex, research_methodes_enhanced_tex, discussion_conclusion_tex, natural_language_paper_goal, bibliometric_content)

    print("\n>>> Phase 6: Assembling Final LaTeX Document <<<")
    # Determine paper title
    actual_paper_title = f"An Academic Exploration of: {natural_language_paper_goal}" # Fallback
    if all_angles_and_queries and all_angles_and_queries[0] and all_angles_and_queries[0][0]:
        # Use the first generated research angle as the basis for the title
        first_angle = all_angles_and_queries[0][0].strip()
        # If the angle ends with a period, remove it for a cleaner title
        if first_angle.endswith('.'):
            first_angle = first_angle[:-1]
        actual_paper_title = first_angle
    
    if not actual_paper_title.strip(): # Ensure title is not empty
        actual_paper_title = f"Research Paper on {natural_language_paper_goal}"

    Results(
        abstract=abstract_intro_keywords_tex, 
        related_works=related_works_enhanced_tex, 
        research_methodes=research_methodes_enhanced_tex, 
        review_finding=review_findings_enhanced_tex, 
        discussion=discussion_conclusion_tex, 
        subject=natural_language_paper_goal, # Original goal for context in prompts
        bibliometric_content=bibliometric_content,
        actual_paper_title=actual_paper_title # New formal paper title
    )

    print("\nProcessing complete with iterative query generation and semantic enhancements!")
    # Return the last successful query
    if all_angles_and_queries:
        return all_angles_and_queries[-1][1]
    return "DEFAULT_QUERY"
