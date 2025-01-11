import os
import requests
import urllib.parse
import xml.etree.ElementTree as ET
import time
from datetime import datetime
from typing import Tuple, List
import PyPDF2
import google.generativeai as genai
import inspect
import re


# Configure API keys for different tasks
SUMMARY_API_KEY = 'AIzaSyDB34rofMFLYfo0zwXnPZ6DLWHs3-I_rjM'
genai.configure(api_key=SUMMARY_API_KEY)

summary_model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Fetch papers from ArXiv
import os
import time
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Tuple

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
    \end{threeparttable}
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



def fetch_arxiv_papers(
    keywords: str,
    year_range: Tuple[int, int] = (2000, datetime.now().year),
    num_papers: int = 5,
    pdf_folder: str = "pdf_papers",
    output_file: str = "metadata.txt"
) -> str:
    """
    Fetch papers from ArXiv and download them as PDFs.
    Extracts metadata including author names, titles, DOIs, URLs, and journal references,
    and saves this information to a text file.
    """
    os.makedirs(pdf_folder, exist_ok=True)

    # Clear the output file at the start
    with open(output_file, 'w') as f:
        f.write("ArXiv Paper Metadata\n")
        f.write("=" * 30 + "\n")

    base_url = 'http://export.arxiv.org/api/query?'
    search_query = f'ti:{keywords} OR abs:{keywords}'
    fetched_papers = 0
    start_index = 0
    max_results = 100

    print(f"Downloading PDFs from ArXiv...")
    print(f"Using search query: {search_query}")

    while fetched_papers < num_papers:
        params = {
            'search_query': search_query,
            'start': start_index,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        query_url = base_url + urllib.parse.urlencode(params)
        print(f"\nQuerying ArXiv API with URL: {query_url}")

        try:
            time.sleep(3)  # Respect ArXiv's rate limits
            response = requests.get(query_url)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom', 
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            entries = root.findall('atom:entry', namespaces)
            
            print(f"Found {len(entries)} entries in response")

            if not entries:
                return f"No papers found matching the search criteria: {keywords}"

            for entry in entries:
                if fetched_papers >= num_papers:
                    break
                
                title = entry.find('atom:title', namespaces).text.strip()
                published_date = entry.find('atom:published', namespaces).text
                published_year = int(published_date[:4])
                
                if not (year_range[0] <= published_year <= year_range[1]):
                    continue
                
                id_url = entry.find('atom:id', namespaces).text
                paper_id = id_url.split('abs/')[-1].strip()
                pdf_url = f'https://arxiv.org/pdf/{paper_id}.pdf'
                
                # Extract authors
                authors = [author.find('atom:name', namespaces).text for author in entry.findall('atom:author', namespaces)]
                
                # Extract DOI if available
                doi_element = entry.find('arxiv:doi', namespaces)
                doi = doi_element.text if doi_element is not None else "N/A"
                
                # Extract journal reference if available
                journal_ref_element = entry.find('arxiv:journal_ref', namespaces)
                journal_ref = journal_ref_element.text if journal_ref_element is not None else "N/A"

                clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:100]
                pdf_filename = os.path.join(pdf_folder, f"{clean_title}.pdf")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                try:
                    print(f"\nDownloading: {clean_title}")
                    pdf_response = requests.get(pdf_url, headers=headers, timeout=30)
                    pdf_response.raise_for_status()
                    
                    with open(pdf_filename, 'wb') as pdf_file:
                        pdf_file.write(pdf_response.content)
                    print(f"PDF saved to: {pdf_filename}")
                    
                    # Save extracted metadata to the output file
                    with open(output_file, 'a') as f:
                        f.write(f"Title: {title}\n")
                        f.write(f"Authors: {', '.join(authors)}\n")
                        f.write(f"DOI: {doi}\n")
                        f.write(f"URL: {id_url}\n")
                        f.write(f"Journal Reference: {journal_ref}\n")
                        f.write("=" * 30 + "\n")
                    
                    fetched_papers += 1
                        
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading PDF: {e}")
                    continue

            start_index += max_results

        except Exception as e:
            print(f"Error in fetch_arxiv_papers: {e}")
            continue

    return f"Successfully downloaded {fetched_papers} PDFs."


def batch_convert_pdfs_to_text(pdf_folder: str = "pdf_papers", txt_folder: str = "txt_papers") -> str:
    """
    Convert all PDFs in the folder to text files in batch.
    """
    print("\nConverting PDFs to text files in batch...")
    os.makedirs(txt_folder, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    if not pdf_files:
        return "No PDF files found in the specified folder."
    
    success_count = 0
    for pdf_file in pdf_files:
        try:
            print(f"\nProcessing: {pdf_file}")
            pdf_path = os.path.join(pdf_folder, pdf_file)
            txt_filename = os.path.join(txt_folder, f"{os.path.splitext(pdf_file)[0]}.txt")
            
            # Skip if text file already exists
            if os.path.exists(txt_filename):
                print(f"Text file already exists, skipping: {txt_filename}")
                success_count += 1
                continue
            
            # Extract text from PDF
            full_text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    full_text += page.extract_text() + "\n"
            
            # Save text content
            with open(txt_filename, 'w', encoding='utf-8') as txt_file:
                txt_file.write(full_text)
            
            print(f"Text saved to: {txt_filename}")
            success_count += 1
            
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            continue
    
    return f"Successfully converted {success_count} out of {len(pdf_files)} PDFs to text."

def summarize_paper(paper_text: str, paper_name: str,subject: str) -> str:
    """
    Summarize a single paper, discussing its relevance to the subject and quoting key points.
    """
    prompt = f"""Summarize directly without you telling me what you are going like starting with "Okay, here's the... etc" the following paper for the systematic literature review (SLR) on the subject [{subject}].befor the summary you should mention these infos :Author ,title,journal,pages,year ,doi and Url.
    Discuss its relevance to the subject,  retreave key points as they wrote in the paper , and include the paper name [{paper_name}] in citations + add the type of the paper.
Note: Mention all the key points related to the subject quoting from the paper.
NOTE: If the papers does not related with all aspects of the Subejct {subject} ignore it.
    Paper Content:
    {paper_text}"""
    try:
        response = summary_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error summarizing paper {paper_name}: {e}")
        return ""

def batch_summarize_papers(keywords: str, txt_folder: str = "txt_papers", summaries_folder: str = "summaries"): #added type hint
    """
    Summarize all text files in the folder.
    """
    print("\nGenerating summaries for all papers...")
    os.makedirs(summaries_folder, exist_ok=True)

    txt_files = [f for f in os.listdir(txt_folder) if f.lower().endswith('.txt')]
    if not txt_files:
        return "No text files found in the specified folder."

    all_summaries = []
    for txt_file in txt_files:
        try:
            print(f"\nProcessing: {txt_file}")
            txt_path = os.path.join(txt_folder, txt_file)
            summary_filename = os.path.join(summaries_folder, f"{os.path.splitext(txt_file)[0]}_summary.txt")

            # Skip if summary already exists
            if os.path.exists(summary_filename):
                print(f"Summary already exists, skipping: {summary_filename}")
                with open(summary_filename, 'r', encoding='utf-8') as summary_file:
                    all_summaries.append(summary_file.read())
                continue

            with open(txt_path, 'r', encoding='utf-8') as file:
                paper_text = file.read()

            paper_name = os.path.splitext(txt_file)[0]
            summary = summarize_paper(paper_text, paper_name, keywords)  # Pass keywords here

            with open(summary_filename, 'w', encoding='utf-8') as summary_file:
                summary_file.write(summary)

            all_summaries.append(summary)
            print(f"Summary saved to: {summary_filename}")

        except Exception as e:
            print(f"Error processing {txt_file}: {e}")
            continue

    return "\n\n---\n\n".join(all_summaries)

def generate_markdown(prompt: str, filename: str, context: str = "") -> str:
    """
    Generate a Markdown file with optional context.
    """
    try:
        combined_prompt = context + "\n\n" + prompt if context else prompt
        response = summary_model.generate_content(combined_prompt)
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(response.text)
        print(f"Generated {filename}")
        return response.text
    except Exception as e:
        print(f"Error generating {filename}: {e}")
        return ""
    
def create_bibliometric(summaries:str) -> str:
    
    prompt = f"""Create the Bibliometric Analysis section Based on these papers Summaries , it should be in a .bib file for Overleaf project. Each paper has to have Author, title, journal, pages, year, doi and URL.
    Summaries of papers:
    {summaries}"""
    
    return generate_markdown(prompt, 'biblio.bib')

def read_metadata() -> str:
    """Read metadata from the output file."""
    output_file = "metadata.txt"  # Fixed filename for reading metadata.
    
    if not os.path.exists(output_file):
        return "Metadata file does not exist."
    
    with open(output_file, 'r') as f:
        summaries = f.read()
    
    return summaries

def create_charts(section: str) -> str:
    # Get the name of the variable passed as the argument
    caller_frame = inspect.currentframe().f_back
    variable_name = None
    for var_name, var_val in caller_frame.f_locals.items():
        if var_val is section:
            variable_name = var_name
            break
    
    # Create the file name based on the variable name
    if variable_name:
        file_name = f"Results/{variable_name}_with_charts.md"
    else:
        raise ValueError("Unable to determine the variable name.")

    # Generate the prompt for chart analysis and addition
    prompt = f"""
Act as an expert researcher and perform the following tasks:

### Task Description:
1. Analyze the provided **section of the paper** to:
   - Identify paragraphs or sections that can be represented as a chart or graph.
   - Create the appropriate charts from scratch (do not use pre-created PNG charts or import them).
   - Integrate the charts into the LaTeX code, preserving the original structure and format.

2. Check the provided **tables**:
   - Correct any issues with formatting or alignment.
   - Ensure tables appear in the correct sections without floating to unrelated pages.

3. **Correct LaTeX Errors**:
   - Fix errors such as:
     - `Unknown option 'gantt' for package 'pgfgantt'`: Ensure proper package loading in the preamble.
     - `Commands in the main body`: Move commands like `documentclass` and `usepackage` into the preamble.
     - `Runaway argument?`: Correct improperly terminated commands or missing braces.
     - `Something's wrong--perhaps a missing \\item`: Ensure proper usage of `itemize` or `enumerate` environments.
     - `Not in outer par mode`: Fix misplaced or incorrect commands used within environments.
     - `Misplaced noalign`: Ensure proper placement of alignment-related commands (e.g., in tables).
     - `Extra alignment tab changed to \\cr`: Resolve misaligned table columns.
     - `Illegal bibstyle command`: Use only one bibliography style (e.g., `natbib` or `biblatex`).

4. **Package Management**:
   - Verify all `\\usepackage` commands are correct and appropriate for the document.
   - Avoid using incorrect options like `\\usepackage[gantt, pgfgantt]` as they do not exist.

5. **Debugging Citations**:
   - Ensure consistency in citation keys (e.g., case sensitivity).
   - Use a single bibliography management system (`natbib` or `biblatex`) and remove conflicts.

6. **Formatting**:
   - Correct placement of tables and figures to ensure they appear on the intended pages.
   - Ensure all charts and graphs are properly formatted using TikZ or pgfplots, without external file dependencies.

### General Tips:
- Check syntax carefully for missing units in length-related commands.
- Maintain consistent case for citation keys.
- Compile the document step-by-step (e.g., pdflatex → bibtex → pdflatex → pdflatex) to debug progressively.

### Input Data:
- **Section of Paper**: {section}
- **Tables**: {tables}
- **Figures**: {Figures}

Return the **corrected and complete LaTeX code** for the paper, integrating charts, correcting tables, and fixing all errors.
- Give only the results without any explanaitions.
- As results give just the usingpackages + the section do not add enything else about the bibliography
"""

    
    # Pass the prompt to the markdown generator and create the file
    return generate_markdown(prompt, file_name)

def Results(abstract: str, related_works: str,research_methodes: str,review_finding: str,discussion: str,subject: str) -> str:
    prompt = f"""Gather all these sections to create the whole Paper under the name {subject} , and give the results in latex code
{abstract}
{related_works}
{research_methodes}
{review_finding}
{discussion}

"""
    return generate_markdown(prompt, 'Results/result.md')



def create_background(review_findings: str,related_works: str,research_methodes: str,discussion_conclusion: str) -> str:
    prompt = fr"""
Act as an expert researcher and perform the following tasks:

### Task Description:
1. Create the **Background Section**:
   - The purpose of this section is to define every keyword or concept used throughout the paper to help readers understand it without confusion.
   - For terms with context-specific meanings that may differ from their academic definitions, provide definitions tailored to the context of the paper.
   - Extract keywords and concepts from the provided sections:
     - {review_findings}
     - {related_works}
     - {research_methodes}
     - {discussion_conclusion}
   - Focus on defining the **top 3 most important concepts or works**, ensuring relevance and clarity.

2. Citation Requirements:
   - Use `\\cite` to cite references whenever defining a term or concept.
   - Ensure citations follow the chosen bibliography management system (e.g., `natbib`, `biblatex`, or standard LaTeX).
   - Verify citation keys are consistent (case-sensitive) to avoid citation-related errors.

3. Formatting:
   - The section must be in proper Overleaf-compatible LaTeX format:
     - Start with `\\section{{Background}}`.
     - Maintain Overleaf-specific requirements for formatting and compatibility.

4. Package Management:
   - Use `\\usepackage` commands only for packages not already included in the preamble.
   - Avoid re-importing packages that are already used in other sections.
   - Verify that only valid packages are used, and incorrect ones like `\\usepackage[gantt, pgfgantt]` are avoided.

5. Debugging Tips:
   - Compile the LaTeX code step-by-step (e.g., `pdflatex → bibtex → pdflatex → pdflatex`) to identify and resolve issues progressively.
   - Ensure all syntax is correct:
     - Avoid missing or incorrect units in commands.
     - Check for proper matching of braces and commands.
   - Use a single bibliography management system to avoid conflicts.

6. General Error Corrections:
   - Address common errors, such as:
     - Undefined or duplicate citations.
     - Commands placed incorrectly in the document body instead of the preamble.
     - Misplaced or unmatched brackets or commands.
     - Missing or inconsistent units in length-related commands.

### Input Data:
- **Sections**:
  - Review Findings: {review_findings}
  - Related Works: {related_works}
  - Research Methods: {research_methodes}
  - Discussion and Conclusion: {discussion_conclusion}

Return the **complete LaTeX code** for the Background section with proper formatting, citations, and corrected errors to ensure flawless execution in Overleaf.
- Give only the results without any explanaitions.
- As results give just the usingpackages + the section do not add enything else about the bibliography

"""

    return generate_markdown(prompt, 'Results/background.md')



def create_related_works(summaries: str,subject: str,Biblio:str) -> str:
    prompt = rf"""
Create a comprehensive **Related Works** section for the systematic literature review (SLR) on the subject [{subject}]. The section must include the following:

### Requirements:
1. **Content and Structure:**
   - Start the section with `\\section{{Related Works}}`.
   - Provide a detailed analysis of the related works, using the provided paper summaries:
     - Identify themes and trends.
     - Compare methodologies and approaches.
     - Use information from all the provided summaries to support your discussion.
   - Focus exclusively on papers that cover both aspects of the subject: **LLM** and **Serious Games**.
     - Ignore papers that do not directly address the combination of these two aspects.
     - Especially exclude papers focusing only on games rather than serious games.

2. **Writing Style:**
   - Create a cohesive and logically linked narrative. Avoid isolated paragraphs discussing unrelated topics.
   - Do not create subsections; the content should form one integrated and well-structured paragraph.

3. **Citations:**
   - Use `\\cite` for citing papers, ensuring every sentence with information derived from the summaries is cited.
   - Do not include bibliography packages (e.g., `biblatex` or `natbib`) at the end of the section, as those will be handled separately.

4. **Formatting and Compatibility:**
   - Return the output in Overleaf-compatible LaTeX code.
   - Ensure proper syntax, correct use of commands, and compatibility with Overleaf.
   - Do not include redundant or incorrect `\\usepackage` commands.
### Inspiration:
1. Introduction to Related Works
Purpose: Briefly explain the purpose of the section: to provide an overview of relevant studies and how they relate to your research.
Scope: Define the scope of the review (e.g., focusing on methodologies, results, gaps, or trends).
Context: Position your work within the broader research landscape.
2. Organizing the Section
Organize the related works based on logical groupings, such as:

Thematic Organization: Divide works into themes or areas relevant to your study.
Chronological Organization: Present works in historical order to show the progression of the field.
Methodological Organization: Compare and contrast different methodologies or techniques.
Problem-Based Organization: Focus on how various works have approached the same or similar problems.
For example:

Theme 1: Early Research and Foundations
Summarize foundational works and their contributions.
Theme 2: Modern Approaches and Innovations
Highlight recent studies, advancements, or innovations.
Theme 3: Current Challenges
Discuss gaps, limitations, or ongoing challenges in the field.
3. Detailed Discussion of Relevant Studies
For each study or group of studies:

Summary: Provide a brief summary of the work, including objectives, methods, and key findings.
Comparison: Highlight similarities or differences with your research.
Relevance: Explain how it relates to your study or how it informs your approach.
Critique: Point out strengths, weaknesses, or limitations (e.g., "While the study provides a robust framework, it lacks empirical validation.").
4. Visual Summaries (Optional)
Use tables or diagrams to compare multiple works:
Methods, tools, datasets, or metrics used.
Key findings or contributions.
Limitations or gaps.
5. Identifying Gaps
Clearly state gaps or open research questions highlighted by the reviewed works.
Show how your research addresses these gaps or advances the field.
6. Summary and Transition
Conclude with a concise summary of the key points covered in the section.
Transition to your research by explaining how it builds upon or diverges from the related works.
Best Practices
Be Selective: Focus on the most relevant and impactful works.
Be Critical: Don’t just summarize; analyze and critique the works.
Be Systematic: Ensure consistent structure for each study discussed.
Cite Appropriately: Provide proper citations to avoid plagiarism.
Be Concise: Avoid overly lengthy descriptions; stick to what’s relevant.
   
### Error Prevention:
- **Syntax Checks:**
  - Ensure no missing or incorrect units in length-related commands.
  - Verify all brackets and commands are properly closed and matched.
- **Citation Management:**
  - Use consistent case-sensitive citation keys.
  - Stick to one bibliography system to avoid conflicts.
- **Debugging Tips:**
  - Compile step-by-step (e.g., `pdflatex -> bibtex -> pdflatex -> pdflatex`) to catch and fix errors.

### Input Data:
Summaries of Papers:
{summaries}
Bibliography:
{Biblio}
Return the complete LaTeX code for the **Related Works** section without adding introductory phrases like "Okay, here's the...". The result must be ready for Overleaf execution and meet all requirements listed above.
- Give only the results without any explanaitions.
- As results give just the usingpackages + the section do not add enything else about the bibliography

"""

    return generate_markdown(prompt, 'Results/related_works.md')
def create_reshearch_methodes(related_works: str,summaries: str, Biblio:str) -> str:
    prompt = rf"""
Create a detailed **Research Methods** section for a systematic literature review (SLR) in Overleaf format, starting with `\\section{{Research Methods}}`. Base the analysis on papers from ArXiv, ResearchGate, Google Scholar, IEEE Xplore, and Web of Science, and include the following subsections:

### Requirements:
1. **Guidelines:**
   - Mention the use of either the **Kitchenham** or **PRISMA** guidelines to structure the research methods. Provide a brief explanation of the chosen guideline.

2. **Content Structure:**
   - **Introduction:** Introduce the section with an overview of the methodology.
   - **Research Questions:** Include:
     - Primary research questions with clear motivations for each.
     - Sub-questions for each primary question with explanations of why answering these is critical.
   - **Mapping Questions:** Focus on quantitative questions (e.g., "How many papers exist on the subject?") to extract numerical insights from the literature.
   - **Search Methodology:**
     - Follow the chosen guideline and create a flowchart representing the search process.
   - **Inclusion/Exclusion Criteria:** Define the criteria for selecting papers and justify these choices.
   - **Quality Assessment Criteria:** List the criteria used to assess the quality of the included studies.
   - **Search String:** Provide the search strings formulated using the **PICO technique** for all databases.

3. **Formatting and Visuals:**
   - Use Overleaf-compatible LaTeX code for the entire section.
   - Include charts, graphs, tables, or lists as needed.
   - Ensure all figures, charts, and tables are properly formatted and labeled for Overleaf.

4. **Citations:**
   - Cite all information using `\\cite` based on the provided summaries.
   - Do not include bibliography packages (e.g., `biblatex`, `natbib`) at the end of the section; these will be handled separately.

### Error Prevention:
- **Syntax Checks:**
  - Ensure no missing or incorrect units in length-related commands.
  - Verify proper syntax and consistent case for citation keys.
- **Bibliography System:**
  - Use a single bibliography system consistently.
  - Avoid mixing commands from different systems.
- **Debugging Tips:**
  - Compile step-by-step (e.g., `pdflatex -> bibtex -> pdflatex -> pdflatex`) to catch and resolve errors.

### Input Data:
- Summaries of Papers:
{summaries}

- Related Works:
{related_works}
- Biblio:
{Biblio}
Return the complete LaTeX code for the **Research Methods** section. Ensure it is Overleaf-compatible and ready for execution. Do not use introductory phrases like "Okay, here's the...". The response must adhere to the outlined requirements and be error-free.
- Give only the results without any explanaitions.
- As results give just the usingpackages + the section do not add enything else about the bibliography

"""

    
    return generate_markdown(prompt, 'Results/research_methodes.md')
def create_review_findings(research_methodes: str, summaries: str,subject: str,Biblio:str) -> str:
    prompt = fr"""
Create a detailed **Review Findings** section for the systematic literature review (SLR) on the subject [{subject}]. Follow these instructions:

### Requirements:
1. **Structure and Content:**
   - Begin with the title `\\section{{Review Findings}}` in Overleaf-compatible LaTeX format.
   - Provide an **introduction** for the section, summarizing the purpose of the findings and their relevance.
   - Answer the research questions outlined in the `research_methodes` section by synthesizing insights from the provided paper summaries.
   - Highlight:
     - Key insights drawn from the studies.
     - Existing gaps and challenges in the literature.
     - A review of results relevant to the SLR subject.

2. **Citations:**
   - Cite all sources explicitly using `\\cite` and reference each paper by name.
   - Ensure every sentence referencing a paper includes a citation.

3. **Formatting and Visuals:**
   - Use Overleaf-compatible code.
   - Include tables or lists as needed to summarize key points.
   - Ensure content flows logically, linking paragraphs rather than discussing unrelated topics in isolation.

4. **General Notes:**
   - Do not add bibliography packages like `biblatex` or `natbib` at the end of the section.
   - Use only packages already included in previous sections of the document.
   - The content should be directly executable in Overleaf.
### Inspirations:
1. Introduction to Findings
Briefly introduce what the section covers.
Explain the scope of the findings (e.g., themes, patterns, or gaps observed in the reviewed literature).
Mention any criteria or frameworks used for synthesis (e.g., thematic analysis, quantitative synthesis, narrative synthesis).
2. Thematic or Research Question-Based Organization
Organize the findings based on:

Themes or Categories: Group results into thematic areas that emerged during the review.
Research Questions: Align the findings directly with the questions the SLR aims to answer.
For example:

Theme 1: Emerging Trends
Discuss key trends found in the literature.
Theme 2: Methodological Approaches
Summarize common methods used in the field.
3. Detailed Synthesis
Provide a detailed synthesis of the literature, emphasizing:

Key Contributions: Highlight significant findings or consensus points in the literature.
Contradictions or Divergences: Address conflicting evidence or differences in methods or outcomes.
Trends Over Time: Show how the research has evolved (if applicable).
Key Metrics or Statistics: If relevant, include quantitative summaries (e.g., "60% of studies used machine learning techniques").
4. Visual Representations
Use figures, tables, or graphs to summarize:

Distribution of studies across themes.
Research methods, technologies, or tools used.
Chronological evolution of research topics.
5. Gaps and Limitations in Literature
Highlight gaps that you observed (e.g., under-researched areas, lack of empirical studies).
Mention any limitations in methodologies, datasets, or generalizability identified in the reviewed literature.
6. Summary
Conclude with a concise summary of the findings.
Link the findings back to the objectives of the SLR or the research questions.
Best Practices
Be Objective: Report findings neutrally, without personal interpretation.
Be Systematic: Ensure every point is backed by references from the reviewed studies.
Be Clear: Use straightforward language to explain complex findings.
Be Concise: Avoid overloading with unnecessary details; stick to the main points.
### Error Prevention:
- **Syntax Checks:**
  - Ensure no missing or incorrect units in length-related commands.
  - Maintain consistent case for citation keys.
- **Bibliography System:**
  - Use one bibliography system consistently.
  - Avoid mixing commands from different systems.
- **Debugging Tips:**
  - Compile the document step-by-step (e.g., `pdflatex -> bibtex -> pdflatex -> pdflatex`) to catch errors.

### Input Data:
- **Research Methods Section:**
{research_methodes}

- **Paper Summaries:**
{summaries}
- **Bibliography:**
{Biblio}
Return the complete LaTeX code for the **Review Findings** section. Ensure it is Overleaf-compatible, logically organized, and error-free. Avoid introductory phrases like "Okay, here's the...". Adhere strictly to the instructions above.
- Give only the results without any explanaitions.
- As results give just the usingpackages + the section do not add enything else about the bibliography

"""

    return generate_markdown(prompt, 'Results/review_findings.md')

def create_discussion_conclusion(review_findings: str, summaries: str,subject: str.capitalize,Biblio:str) -> str:
    prompt = rf"""
Create a detailed **Discussion and Conclusion** section for the systematic literature review (SLR) on the subject [{subject}]. Follow these instructions:

### Requirements:
1. **Structure and Content:**
   - Begin with the title `\\section{{Discussion}}` in Overleaf-compatible LaTeX format.
   - Provide an **introduction** that sets the context for the discussion and its relevance to the SLR subject.
   - Discuss:
     - Key insights gained from the `review_findings`.
     - Identified gaps in the literature and unresolved challenges.
     - Future research directions based on the findings.
   - End with a **Conclusion**, synthesizing the main takeaways and emphasizing the importance of addressing the identified gaps.

2. **Citations:**
   - Explicitly cite relevant papers using `\\cite` in every sentence where a paper is referenced.
   - Ensure that every citation corresponds to the provided `summaries`.

3. **Formatting and Visuals:**
   - Use Overleaf-compatible LaTeX code.
   - Incorporate tables or lists where appropriate to enhance readability.
   - Maintain logical flow, linking paragraphs cohesively rather than presenting disconnected points.

4. **General Notes:**
   - Do not include bibliography packages like `biblatex` or `natbib` in this section.
   - Only use packages that have already been declared in previous sections.
   - Ensure that the content is directly executable in Overleaf without syntax or compilation errors.

### Error Prevention:
- **Syntax Checks:**
  - Double-check for missing or incorrect units in length-related commands.
  - Use consistent case for citation keys.
- **Bibliography System:**
  - Stick to a single bibliography management system.
  - Avoid mixing commands from different systems.
- **Debugging Tips:**
  - Compile the document step-by-step (e.g., `pdflatex -> bibtex -> pdflatex -> pdflatex`) to identify and fix errors.

### Input Data:
- **Review Findings:**
{review_findings}

- **Paper Summaries:**
{summaries}
- **Bibliography:**
{Biblio}
Return the complete LaTeX code for the **Discussion and Conclusion** section. Ensure it adheres to the instructions, is Overleaf-compatible, and does not include any introductory phrases like "Okay, here's the...".
- Give only the results without any explanaitions.
- As results give just the usingpackages + the section do not add enything else about the bibliography

"""

    return generate_markdown(prompt, 'Results/discussion_conclusion.md')

def create_abstract_intro(review_findings: str,related_works:str,research_methodes:str,discussion:str,subject: str,Biblio:str) -> str:
    prompt = rf"""
Create the following sections directly in Overleaf-compatible LaTeX format without introductory phrases like "Okay, here's the...":
1. **Abstract**
2. **Introduction**
3. **Keywords**

### Requirements:
1. **Content Structure:**
   - Use the following sections as the basis:
     - Review Findings: {review_findings}
     - Related Works: {related_works}
     - Research Methods: {research_methodes}
     - Discussion and Conclusion: {discussion}
   - The title of the paper should be [{subject}].
   - Include a proper start to the SLR with all necessary components such as title formatting, author placeholder, date, and document class.

2. **Abstract:**
   - Provide a concise summary of the paper’s purpose, methods, key findings, and significance.
   - Keep it brief and impactful.

3. **Introduction:**
   - Introduce the topic, context, and importance of the SLR.
   - Include clear citations using `\cite` for every statement derived from the provided data.
   - Keep the introduction short but informative.

4. **Keywords:**
   - Provide 5–7 relevant keywords related to the paper’s subject.
   - Format the keywords properly as part of the Overleaf document.

5. **Packages:**
   - Gather all `\usepackage` commands used throughout the sections and include them at the top of the LaTeX document.
   - Ensure no duplicate packages and use only those required for proper functionality.

6. **General Formatting and Error Prevention:**
   - Syntax:
     - Double-check for missing or incorrect units in length-related commands.
     - Use consistent case for citation keys.
   - Bibliography:
     - Stick to one bibliography management system (e.g., natbib, biblatex, or plain LaTeX).
   - Debugging:
     - Compile step-by-step (pdflatex -> bibtex -> pdflatex -> pdflatex) to test functionality.
- Give only the results without any explanaitions.
Bibliography:
{Biblio}
### Output Format:
- Start with the `\documentclass` and necessary preamble, including packages.
- Create the **Abstract**, **Introduction**, and **Keywords** sections in sequence, ensuring Overleaf compatibility.
- Give only the results without any explanaitions.
- As results give just the usingpackages + the section do not add enything else about the bibliography

"""

    return generate_markdown(prompt, 'Results/abstract_intro.md')




def process_papers(keywords: str, year_range: Tuple[int, int], num_papers: int) -> None: #added type hint
    print("Starting paper processing pipeline...")
    # Phase 1: Download PDFs
    result1 = fetch_arxiv_papers(keywords, year_range, num_papers)
    print(f"\nPhase 1 Result: {result1}")

    # Phase 2: Convert PDFs to text
    result2 = batch_convert_pdfs_to_text()
    print(f"\nPhase 2 Result: {result2}")

    # Phase 3: Summarize papers
    summaries = batch_summarize_papers(keywords, "txt_papers", "summaries") # Pass keywords here

    # Phase 4: Create sections
    print("\nGenerating Bibliometric Analysis section...")
    bibliometric = create_bibliometric(summaries)

    print("\nGenerating Related Works section...")
    related_works = create_related_works(summaries,keywords,bibliometric)

    related_works_c=create_charts(related_works)

    print("\nGenerating Research Methodes section...")
    research_methodes = create_reshearch_methodes(related_works, summaries,bibliometric)

    research_methodes_c=create_charts(research_methodes)

    print("\nGenerating Review Findings section...")
    review_findings = create_review_findings(research_methodes, summaries,keywords,bibliometric)

    review_findings_c=create_charts(review_findings)

    print("\nGenerating Discussion and Conclusion section...")
    discussion_conclusion=create_discussion_conclusion(review_findings, summaries,keywords,bibliometric)
  

    print("\nGenerating Background section...")
    create_background(review_findings_c,related_works_c,research_methodes_c,discussion_conclusion)


    print("\nGenerating Abstract, Introduction, and Keywords...")

    create_abstract_intro(review_findings_c,related_works_c,research_methodes_c,discussion_conclusion,keywords,bibliometric)

    # print("\nGenerating Results section...")
    # Results(abstract,related_works_charts, research_methodes_charts, review_findings_cahrts, discussion_conclusion)

    print("\nProcessing complete!")
    
# if __name__ == "__main__":
#     process_papers("LLM in serious games", (2022, 2024), num_papers=1)
