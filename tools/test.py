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
NOTE: If the papers does not related with both LLM and Serious games say it , otherwise mention how these 2 aspect related in the paper mentioning the keys whare they are related.
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
    
def create_bibliometric() -> str:
    summaries = read_metadata()  # Call the read_metadata function without parameters.
    
    prompt = f"""Create the Bibliometric Analysis section Based on these papers Summaries , it should be in a .bib file for Overleaf project. Each paper has to have Author, title, journal, pages, year, doi and URL.
    Summaries of papers:
    {summaries}"""
    
    return generate_markdown(prompt, 'Bibliometric.bib')

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
        file_name = f"{variable_name}_with_charts.md"
    else:
        raise ValueError("Unable to determine the variable name.")

    # Generate the prompt for chart analysis and addition
    prompt = f"""This is a section from a paper. Analyze it to identify paragraphs or sections that can be converted into a chart or graph. Add the appropriate charts and return the entire LaTeX code, preserving the original format with the charts included.
    NOTE: There are no PNGcahrt or pre created chart to import , you should create all the charts from scratch.
    Also correct the tables if they are not in corrected form.
    Section of paper:
    {section}
how to create tables : {tables}
How to create charts : {Figures}
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
    return generate_markdown(prompt, 'result.md')



def create_background(review_findings: str,related_works: str,research_methodes: str,discussion_conclusion: str) -> str:
    prompt = f"""
    Create the background section , it's a section where the creatore of the SRL have to define every keyword or concept that is going to be used in the paper , so the reader can understand the paper without any problem + define the reletive words were there definition maybe deferent from it's acadimic definition based on the context of the SLR, so you will need all the sections to get these keywords and based on the context of each one give there defifnition or what we mean by them, the section should be in Overleaf format starting with \section Background.
    Sections:
    {review_findings}
    {related_works}
    {research_methodes}
    {discussion_conclusion}

    
    
    
    """
    return generate_markdown(prompt, 'background.md')



def create_related_works(summaries: str,subject: str) -> str:
    prompt = f"""Create directly without you telling me what you are going like starting with "Okay, here's the... etc" a comprehensive Related Works section for the systematic literature review (SLR) on the subject [{subject}]. 
    Use the following paper summaries to identify themes, compare approaches, and cite papers with there names, and it should be detailed each information you give should be from a paper of those.
NOTE : Use all the papers .your result should start with the title of the section not with "Okay, here's the... etc" or similars.
Results should be in Overleaf code format starting with "\section Related Works" you can add tables if you want to , the citations should be the name of the paper instead of number in [], add charts , graphes or tables if needed.
NOTE : DO not talk about papers that are not focus totally of the subject not only a part of it . and create a introduction for the section.
NOTE : the paragraphes should be linked logicly , not each paragraph talk about a subject + the papers mentioned should be related and ignore the ones that are not related directly yo the subject, it should not be subsections but one big paragraph .
NOTE: The subject is LLM and Serious games , so mention just papers who talk about both not only one of them , ignore the ones that are not related to both aspect of the subject,(Especialy Serious games not only games)

    Summaries of papers:
    {summaries}

here are some types of tables in latex:



"""
    return generate_markdown(prompt, 'related_works.md')
def create_reshearch_methodes(related_works: str,summaries: str) -> str:
    prompt = f"""Create a Research Methods section for an SLR in Overleaf format starting with \section Research Methods. Base your analysis on ArXiv,Research gates, google scholare, IEEExplore ,web of science papers ,and to create these sections:
0- We Use the Kichenhim or PRIZMA  guidlines so mention one of them.
1-Research questions with sub-questions with motivations for each question answering why its answer would help (as provided)
2-Mapping questions (quantitative focus start with How much ,how many ...etc in goal to extract answers about the papers for example how many papers exist about the subject ... etc)
3-Citation format: use paper names in brackets [PaperName]
4-Search methodology using Kechenhime guidline [Create a chart for it]
5-Inclusion/exclusion criteria section
6-Quality assessment criteria section
7-the search string for all the data bases using PICO techniques .
Format all content for Overleaf, including any relevant chart ,graphes, tables or lists. Start directly with the section content, no introductory phrases."

NOTE: Create the research question with there motivations and sub questiona for each question.and create an introduction for the section
    Summaries of papers:
    {summaries}
    Relative works:
    {related_works}
"""
    
    return generate_markdown(prompt, 'research_methodes.md')
def create_review_findings(research_methodes: str, summaries: str,subject: str) -> str:
    prompt = f"""Create directly without you telling me what you are going like starting with "Okay, here's the... etc" a detailed Review Findings section for the systematic literature review (SLR) on the subject [{subject}].
    Use the research methodes section and paper summaries to answer research questions, explicitly citing papers by names and highlighting gaps and challenges + a review of the results .your result should start with the title of the section not with "Okay, here's the... etc" or similars.
Results should be in Overleaf code format starting with "\section Reviewe finding" you can add tables or lists if you want to.the citations should be the name of the paper instead of number in [].and create an introduction for the section
    {research_methodes}

    Summaries:
    {summaries}"""
    return generate_markdown(prompt, 'review_findings.md')

def create_discussion_conclusion(review_findings: str, summaries: str,subject: str) -> str:
    prompt = f"""Create a detailed Discussion and Conclusion section for the systematic literature review (SLR) on the subject [{subject}].
    Use the review findings and paper summaries to discuss key insights, gaps, and future directions, explicitly citing papers. your result should start with the title of the section not with "Okay, here's the... etc" or similars.
Results should be in Overleaf code format starting with "\section Discussion" you can add tables or lists if you want to.the citations should be the name of the paper instead of number in [].and create an introduction for the section

    Review Findings:
    {review_findings}

    Summaries:
    {summaries}"""
    return generate_markdown(prompt, 'discussion_conclusion.md')

def create_abstract_intro(review_findings: str,related_works:str,research_methodes:str,discussion:str,subject: str) -> str:
    prompt = f"""Create directly without you telling me what you are going like starting with "Okay, here's the... etc" these 3 sections: abstract , the introducion ,the key words , based on these 4 sections Review Findings , Related Works , Research Methodes and Discussion and Conclusion , so the SLR would be completed , the name of the paper should be the subject [{subject}].your result should start with the title of the section not with "Okay, here's the... etc" or similars. (The 3 sections should be short)
Results should be in Overleaf code format starting with "\section Abstract" you can add tables or lists if you want to.
NOTE:gather all the usebapaclage used in all of the sections and make it in top , the package may not be visible in some sections so figure it out and the right package to run the section or code + since the abstract and the instro are the first at the SLR can you make a proper start with title and all thigs that suppose to be at the begining of an SLR .
NOTE:Create only these sections :abstract , the introducion ,the key words 
    Review Findings:
    {review_findings}

    related works:
    {related_works}
    reseach methodes:
    {research_methodes}
    discussion:
    {discussion}

"""
    return generate_markdown(prompt, 'abstract_intro.md')




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
    # print("\nGenerating Bibliometric Analysis section...")
    # bibliometric = create_bibliometric()

    print("\nGenerating Related Works section...")
    related_works = create_related_works(summaries,keywords)

    related_works_c=create_charts(related_works)

    print("\nGenerating Research Methodes section...")
    research_methodes = create_reshearch_methodes(related_works, summaries)

    research_methodes_c=create_charts(research_methodes)

    print("\nGenerating Review Findings section...")
    review_findings = create_review_findings(research_methodes, summaries,keywords)

    review_findings_c=create_charts(review_findings)

    print("\nGenerating Discussion and Conclusion section...")
    discussion_conclusion=create_discussion_conclusion(review_findings, summaries,keywords)
  

    print("\nGenerating Background section...")
    create_background(review_findings_c,related_works_c,research_methodes_c,discussion_conclusion)


    print("\nGenerating Abstract, Introduction, and Keywords...")

    create_abstract_intro(review_findings_c,related_works_c,research_methodes_c,discussion_conclusion,keywords)

    # print("\nGenerating Results section...")
    # Results(abstract,related_works_charts, research_methodes_charts, review_findings_cahrts, discussion_conclusion)

    print("\nProcessing complete!")
    
if __name__ == "__main__":
    process_papers("LLM in serious games", (2022, 2024), num_papers=1)
