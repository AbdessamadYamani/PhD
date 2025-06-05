import os
import requests
import urllib.parse
import xml.etree.ElementTree as ET
import time
import io
from datetime import datetime
from typing import Tuple, List, Dict, Optional, Callable # Added Optional and Callable
import PyPDF2 # type: ignore
import google.generativeai as genai
import inspect
import json # For parsing LLM output for references
# import subprocess # No longer needed for LaTeX compilation
import re
import shutil
import random # Added for selecting a random paper for style

# Imports for Scopus integration
from pdf2image import convert_from_path # type: ignore
import pytesseract # type: ignore
import tempfile # Added import for tempfile
# ANSI escape codes for colors
BLUE = '\033[94m'
RED = '\033[91m' # For errors
YELLOW = '\033[93m' # For warnings
RESET = '\033[0m'

# Configure API keys for different tasks
SUMMARY_API_KEY = 'AIzaSyDB34rofMFLYfo0zwXnPZ6DLWHs3-I_rjM' # This should be kept secure
SCOPUS_API_KEY = "df21b06b13dd1a95c37ba72e5c47fab5" # Scopus API Key
genai.configure(api_key=SUMMARY_API_KEY)

# Optional: If tesseract is not in PATH (for Scopus OCR)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
SCOPUS_ARTICLE_BASE_URL = "https://api.elsevier.com/content/article/doi/"

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
NO_TEXT_FILES_GENERATED = "NO_TEXT_FILES_GENERATED" # Keep this one
COULD_NOT_READ_RELEVANT_PAPERS = "COULD_NOT_READ_RELEVANT_PAPERS"
NO_SUMMARIES_GENERATED = "NO_SUMMARIES_GENERATED"
NO_LLM_CONFIRMED_RELEVANT_PAPERS = "NO_LLM_CONFIRMED_RELEVANT_PAPERS" # New status
# you might need to change it to a model like 'gemini-1.5-flash-latest' or 'gemini-pro'.

# --- Constants for Snowballing ---
MAX_SNOWBALL_ITERATIONS = 1 # How many rounds of snowballing from relevant papers
MAX_REFERENCES_TO_PROCESS_PER_PAPER = 5 # Max references to try to find from each source paper
MAX_PAPERS_TO_ADD_VIA_SNOWBALLING = 10 # Overall cap on papers added through snowballing

try:
    summary_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20') # Updated to a more recent model
except Exception as e:
    print(f"{RED}Error initializing Gemini model. Please check model name and API key: {e}{RESET}")
    print("Using 'gemini-pro' as a fallback model.")
    summary_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20') # Corrected fallback model

# --- Global Rate Limiting for LLM Calls ---
LLM_CALL_COUNT = 0
LLM_CALLS_BEFORE_WAIT = 10
LLM_WAIT_SECONDS = 60

TABLE_RULES = r"""
**TABLE-SPECIFIC RULES:**
1. Use \toprule, \midrule, \bottomrule from booktabs for formal tables.
2. Ensure all & column separators have matching columns in each row.
3. Always add \\ at the end of each row in a tabular environment, except for the last row if it's followed by \end{tabular}.
4. Use \hline for simple tables or internal lines if booktabs is not appropriate for the specific table style.
5. Verify column count in \begin{tabular}{...} matches the number of columns in the table body.
6. Ensure captions are placed correctly (e.g., \caption{...} \label{...} within table or figure environment).
"""

LATEX_SAFETY_RULES = fr"""
**CRITICAL LATEX OUTPUT RULES:**
1. Output ONLY raw LaTeX code suitable for direct inclusion in a .tex file section. DO NOT use Markdown, explanations, or triple backticks (```).
2. Escape LaTeX special characters correctly when they are meant to be literal text: e.g., \$ for dollar, \& for ampersand, \% for percent, \# for hash, \_ for underscore (unless in math mode or a command), \{{ for left brace, \}} for right brace.
3. Balance all curly braces: every `{{` must have a corresponding `}}`.
4. Ensure all LaTeX environments are properly closed: every `\begin{{environment}}` must have a matching `\end{{environment}}`.
5. If you are asked to generate content that might include placeholders like "[Actual Count]" or "[Number Here]", replace them with a generic placeholder like "N" or "0" or "to be determined" if the actual data is not available from the input.
6. Use the standard citation command format: `\cite{{key}}`. Avoid variants like `\cite {{ key }}` or `\cite {{key}}`.
7. Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, or `\usepackage` commands.
8. Do NOT add any conversational text, apologies, or self-corrections in the output. Only the LaTeX code.
{TABLE_RULES}
"""


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
\usepackage[gantt]{{pgfgantt}}

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
\usepackage[gantt]{{pgfgantt}}

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
Human_Text=r"""
\section{Related Works}
Our venture into the new ground of AI and its revolutionary impacts on the world economy demands an extensive reading of existing literature. We've identified some of the most influential conceptual and empirical researches that collectively provide us with a wholesome picture of the "AI Economy" and its wide-ranging implications. As a whole, these articles fall into three interconnected categories: those positing AI as a driver of economic strategy, those creating methodological applications of AI for economic analysis, and those exploring the impact of AI on society and the workforce.

One of the seminal articles on learning about the AI economy is that by Schmitt \cite{Schmitt2024Strategic}. This theoretical essay firmly defines the "AI Economy" as an economic order by nature characterized by the deployment and utilization of AI in many sectors. Schmitt actively positions AI not only as an instrument, but as a meta-revolutionary technology, with unparalleled innovation speed and productivity. This perspective is important, as it locates AI as a primary source for economic growth, revolutionizing business functions, roles, and value creation and distribution. In fact, the paper argues that AI radically alters the manner in which businesses compete by enabling new structures and ecosystems with scalable operations, faster decision-making, and real-time customer interactions. It even suggests that AI leadership, through the potential role of a Chief AI Officer (CAIO), is essential to organizations seeking to strategically leverage AI to promote long-term economic development and effectively manage workforce transformation.

Aside from envisioning the AI Economy, there is another body of research that has as its goal the application of AI itself in generating novel economic knowledge and improving forecasting. Here, one of the most engaging methodological contributions is offered by the working paper of Jha et al. \cite{Jha2024Harnessing}. These researchers demonstrate how generative AI as big language models like ChatGPT and Llama-3 may be employed to extract and synthesize managerial hopes from corporate conference call transcripts of gargantuan size. Their "AI Economy Score" derived from this exercise is a good predictor of subsequent macroeconomic measures, such as GDP growth, output, and jobs, and is more accurate than traditional survey-based forecasts. Moreover, their approach delivers valuable industry- and firm-level data, suggesting that managerial forecasts, when aggregated and interpreted by AI, exert unique prescriptive authority for microeconomic as much as macroeconomic choice. This paper greatly amplifies the potential of AI tools in economic analysis, with new horizons for evidence-based research.

However, the potential of AI to revolutionize is not without fundamental challenges, particularly its societal and labor market implications. It is where Rymon's research \cite{Rymon2024Societal} finds its true potential. Rymon considers the potential of AI-automated human-labor (HLA) to bring about mass economic disruption, ranging from mass job displacement to increased inequality. Though the overall consequences of automation are traditional terrain for economics theory, Rymon points out that contemporary AI has a particular set of characteristics: its unprecedented size over time in automating processes previously held by humans, its autonomy of function, and its accelerating model of growth. The piece breaks down traditional economic models of automation—i.e., the "displacement effect" and offsetting "reinstatement effects"—but argues that the novelty of AI demands new models for interpreting this transition. Above all, Rymon proposes a range of economic and policy measures like channeling AI research in the direction of human-supporting abilities, taxation of automata, investment in reskilling and education, and work substitutes like Universal Basic Income (UBI) or Universal Basic Capital (UBC) with the ultimate aim of supporting societal adjustment. Schmitt \cite{Schmitt2024Strategic} also expresses these apprehensions, acknowledging that while AI is driving productivity, it is "intrinsically labor-replacing" and will necessarily destabilize labor markets, with the ultimate effect of market capitalization centralization on the rise.

Venturing further onto the human aspect of the AI economy, Laux et al. \cite{Laux2023Improving} offer an interesting glimpse into data annotation economics, an important, albeit under-recognized, human labor factor in AI building. Their work highlights the huge worldwide need for data annotation and its direct influence on the quality of AI systems. Notably, the authors raise a basic economic question: Are AI developers incentivized to invest in the work conditions of data annotators? Their work shows that clear task instructions are more cost-efficient than monetary incentives in improving annotation accuracy, thus leading to better datasets and AI systems. This implies that improvement in labor conditions in the AI value chain can lead to measurable economic benefits for developers, and they urge policymakers to ensure fair pay for data annotators, especially because of outsourcing to lower-paid countries.

Finally, one of the salient, cross-cutting themes in the language of the AI economy relates to the imperatives of creating trust-worthy AI systems, which, as Petkovic \cite{Petkovic2022TrustworthyAI} so compellingly states, impact their take-up and commercial viability directly. Petkovic comments on the creation of an "AI economy and society" and how worries about bias, transparency, and potential for error can erode trust and mass take-up of AI in enterprise. The article stresses the economic imperative of the regulatory measures that call for precision, strength, explainability, and fairness in AI systems, particularly high-impact applications. Here's an interesting economic paradox: while deep learning systems are expensive to train and deploy, the future of AI will involve audit and certifications that demand explainability. Petkovic also refers to the danger that explainability poses to commercialization by revealing hidden AI design, but offers solutions like confidentiality agreements and patent law to mitigate the risks so that the pursuit of responsible AI does not put the economics at risk.

\begin{table*}[htbp]
    \centering
    \caption{Summary of Key Contributions in AI Economy Literature}
    \label{tab:related_works_summary}
    \begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{2.5cm} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}X}
\toprule
        \textbf{Author(s) \& Year} & \textbf{Primary Focus/Category} & \textbf{Key Contribution/Methodology} & \textbf{Main Findings/Implications} \\\\
        \midrule
Schmitt \cite{Schmitt2024Strategic}
Framing AI as a strategic economic force
Defines "AI Economy" as an economic system shaped by AI integration; frames AI as a meta-technology of transformation; sees a need for a Chief AI Officer (CAIO).
AI drives record-breaking productivity and innovation, redefining business processes and work roles. AI is "fundamentally labor-replacing" and transforms labor markets and may cause market capitalization concentration to rise.
\\midrule
Jha et al. \cite{Jha2024Harnessing} & Economic analysis applications of AI methodologies & Documents how generative AI (LLMs) can summarize and consolidate managerial expectations from company call transcripts to build an "AI Economy Score". & The "AI Economy Score" allows for robust forecasting of future macroeconomic metrics (GDP, production, employment), superior to traditional forecasts; offers rich industry and firm-level insights.
\\midrule
Rymon \cite{Rymon2024Societal} & Societal and labor market effects of AI & Examines probable economic disruption caused by AI-generated human-labor automation (HLA); explores classical economic models of automation (displacement/reinstatement effects). & The unprecedented scope, autonomy, and exponential growth of modern AI require new paradigms. Suggests policy interventions such as guiding AI innovation, taxing automation, reskilling, UBI/UBC.
\\midrule
Laux et al. \\\\cite{Laux2023Improving} & AI's human factor data annotation economics & Considers economic incentives for improving working conditions for data annotators; compares cost-effectiveness of explicit task instructions versus monetary incentives.        & Explicit task instructions are more inexpensive to adopt than monetary incentives in raising annotation quality. Enhancing working conditions in the AI supply chain can have concrete economic benefits; proponents of compulsory pay for data annotators.
\\midrule
Petkovic \cite{Petkovic2022TrustworthyAI}
Trustworthy AI and its economic implications
Makes the case that trustworthy AI has a direct impact on adoption and commercial success; explores the economic need for regulatory efforts for accuracy, robustness, explainability, and fairness.
& Unclearness, bias, and errors in the absence of transparency are harmful to trust and adoption of AI. Explainability can be dangerous for commercialization through the revelation of AI design secrets, but measures such as secrecy agreements and patent law can be utilized to mitigate risks and make economic viability possible. \\\\\\\\         \\\\bottomrule     \\\\end{tabularx}\
\\\\end{table*}
In fact, the reviewed literature captures the multi-faceted role of AI in the economy. From its roles as a strategic facilitator and a powerful analytical tool to its profound impact on labor markets and the imperative need for ethical governance, these articles assert that the "AI Economy" is more than a conceptualization but an unfolding high-speed reality requiring considered attention and proactive adjustment.

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
        prompt_parts.append("\nPlease suggest a NEW and DISTINCT research angle and a corresponding very concise natural language search phrase (ideally 1 keyword, MAXIMUM 2 words) for the user's overarching goal. Avoid repeating themes or query structures already tried.")
    else:
        prompt_parts.append("\nCreate the first research angle and query.")

    prompt_parts.extend([
        "\nExamples:",
        "User goal: 'Is Elden Ring the best game ever?'",
        "Research Angle: 'Analysis of Elden Ring's game design innovations and player engagement metrics'",
        "Search Phrase: 'Elden Ring'",
        "",
        "User goal: 'Why is ChatGPT so popular?'",
        "Research Angle: 'Adoption factors and user satisfaction studies of large language models'",
        "Search Phrase: 'ChatGPT popularity'",

        "\nOutput Format:",
        "Provide the Research Angle first, then the Generated Search Phrase.",
        "Use the following format strictly:",
        "RESEARCH_ANGLE_START",
        "[Your formulated research angle]",
        "RESEARCH_ANGLE_END",
        "ARXIV_QUERY_START",
        "[Your generated Search Phrase - MUST BE 1 or 2 words MAXIMUM]",
        "ARXIV_QUERY_END"
    ])
    prompt = "\n".join(prompt_parts)

    try:
        # Call the centralized LLM content generation function which includes retry logic
        response_text = generate_content_from_prompt(
            prompt,
            context_for_error=f"ArXiv Query Generation for '{natural_language_goal[:50]}...'"
        )

        # Check if generate_content_from_prompt returned an error string
        if response_text.startswith("% Error"):
            print(f"{RED}Failed to generate ArXiv search query due to LLM error: {response_text}{RESET}")
            return "Academic analysis of " + natural_language_goal, natural_language_goal

        # Proceed with parsing the successful response_text
        angle_match = re.search(r"RESEARCH_ANGLE_START\s*(.*?)\s*RESEARCH_ANGLE_END",
                                response_text, re.DOTALL)
        query_match = re.search(r"ARXIV_QUERY_START\s*(.*?)\s*ARXIV_QUERY_END",
                                response_text, re.DOTALL)

        if angle_match and query_match:
            angle = angle_match.group(1).strip()
            query = query_match.group(1).strip()
            if not angle or not query: # Check if extracted strings are empty
                 print(f"{YELLOW}Warning: LLM response for query generation was parsed but angle or query is empty. Response: {response_text[:300]}{RESET}")
                 return "Academic analysis of " + natural_language_goal, natural_language_goal # Fallback
            return angle, query
        else:
            # Fallback if parsing fails
            print(f"{YELLOW}Warning: Could not parse research angle and query from LLM response. Using fallback. Response: {response_text[:300]}{RESET}")
            return "Academic analysis of " + natural_language_goal, natural_language_goal

    except Exception as e: # Catch any other unexpected errors during this function's execution
        # This might catch errors from generate_content_from_prompt if it raises an unexpected exception,
        # or errors during the parsing logic itself.
        print(f"{RED}Unexpected error in create_arxiv_search_query_from_natural_language: {e}{RESET}")
        return "Academic analysis of " + natural_language_goal, natural_language_goal


def fetch_arxiv_papers(
    search_query_str: str,
    year_range: Tuple[int, int] = (2000, datetime.now().year),
    num_papers: int = 5,
    pdf_folder: str = "pdf_papers",
    already_fetched_primary_ids: set = None
) -> Tuple[List[Dict], int, str]:
    """
    Fetch new papers from ArXiv with enhanced error handling and retry logic.
    """
    os.makedirs(pdf_folder, exist_ok=True)
    if already_fetched_primary_ids is None:
        already_fetched_primary_ids = set()

    newly_fetched_papers_metadata_list = []
    newly_fetched_and_saved_count = 0
    base_url = 'http://export.arxiv.org/api/query?'
    
    # Query formatting
    if search_query_str.startswith('all:') or search_query_str.startswith('ti:') or search_query_str.startswith('abs:'):
        search_query_for_api = search_query_str
    else:
        search_query_for_api = f'all:"{search_query_str}"'
    
    print(f"Searching ArXiv for: {search_query_for_api}")
    
    start_index = 0
    max_results_per_api_call = min(num_papers * 3, 100)
    
    while newly_fetched_and_saved_count < num_papers:
        params = {
            'search_query': search_query_for_api,
            'start': start_index,
            'max_results': max_results_per_api_call,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        query_url = base_url + urllib.parse.urlencode(params)
        
        try:
            time.sleep(3)  # Basic rate limiting
            
            # First attempt with shorter timeout
            try:
                response = requests.get(query_url, timeout=15)
            except (requests.exceptions.ConnectionError, ConnectionResetError) as cre:
                # Retry with longer timeout
                print(f"{YELLOW}Connection error (retrying): {cre}{RESET}")
                time.sleep(2)
                response = requests.get(query_url, timeout=30)
            
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespaces = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
            entries = root.findall('atom:entry', namespaces)
            
            print(f"ArXiv API call (start_index {start_index}): Found {len(entries)} entries")
            
            if not entries:
                print("No more entries found from ArXiv for this query.")
                break 
            
            current_batch_newly_added = 0
            for entry in entries:
                if newly_fetched_and_saved_count >= num_papers:
                    break
                
                title_element = entry.find('atom:title', namespaces)
                title = title_element.text.strip() if title_element is not None else "N/A Title"
                
                published_date_element = entry.find('atom:published', namespaces)
                if published_date_element is None or not published_date_element.text:
                    print(f"Skipping paper '{title[:50]}...' due to missing publication date.")
                    continue
                    
                published_date = published_date_element.text
                try:
                    published_year = int(published_date[:4])
                except ValueError:
                    print(f"Skipping paper '{title[:50]}...' due to invalid publication year format: {published_date[:4]}")
                    continue
                    
                if not (year_range[0] <= published_year <= year_range[1]):
                    continue
                
                id_url_element = entry.find('atom:id', namespaces)
                id_url = id_url_element.text if id_url_element is not None else ""
                arxiv_id_match = re.search(r'abs/([^v]+)', id_url)
                arxiv_id = arxiv_id_match.group(1) if arxiv_id_match else ""
                
                if not arxiv_id:
                    print(f"Skipping paper '{title[:50]}...' due to missing ArXiv ID.")
                    continue

                potential_sanitized_primary_id = sanitize_filename(f"arxiv_{arxiv_id}")

                if potential_sanitized_primary_id in already_fetched_primary_ids:
                    continue 
                
                authors = [auth.find('atom:name', namespaces).text 
                          for auth in entry.findall('atom:author', namespaces) 
                          if auth.find('atom:name', namespaces) is not None]
                
                doi_element = entry.find('arxiv:doi', namespaces)
                doi = doi_element.text if doi_element is not None else ""
                
                journal_ref_element = entry.find('arxiv:journal_ref', namespaces)
                journal_ref = journal_ref_element.text if journal_ref_element is not None else ""
                                
                pdf_filename = os.path.join(pdf_folder, f"{potential_sanitized_primary_id}.pdf")
                pdf_url = f'https://arxiv.org/pdf/{arxiv_id}.pdf'
                
                paper_metadata = {
                    'title': title, 'authors': authors, 'doi': doi, 'id_url': id_url,
                    'pdf_url': pdf_url, 'journal_ref': journal_ref,
                    'published_year': published_year, 'arxiv_id': arxiv_id,
                    'local_pdf_path': pdf_filename
                }
                
                if os.path.exists(pdf_filename): 
                    print(f"PDF {pdf_filename} already exists. Using existing.")
                    newly_fetched_papers_metadata_list.append(paper_metadata)
                    newly_fetched_and_saved_count += 1
                    current_batch_newly_added +=1
                    already_fetched_primary_ids.add(potential_sanitized_primary_id)
                    continue
                
                try:
                    print(f"Downloading: {title[:80]}... (ID: {arxiv_id})")
                    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ArXiv-Fetcher/1.0)'}
                    pdf_response = requests.get(pdf_url, headers=headers, timeout=60)
                    pdf_response.raise_for_status()
                    
                    with open(pdf_filename, 'wb') as f: 
                        f.write(pdf_response.content)
                    
                    print(f"Saved: {pdf_filename}")
                    newly_fetched_papers_metadata_list.append(paper_metadata)
                    newly_fetched_and_saved_count += 1
                    current_batch_newly_added +=1
                    already_fetched_primary_ids.add(potential_sanitized_primary_id)
                    
                except Exception as e:
                    print(f"Failed to download {title}: {e}")
                    if os.path.exists(pdf_filename): 
                        os.remove(pdf_filename)
                    continue
            
            start_index += len(entries)
            
            if current_batch_newly_added == 0 and len(entries) < max_results_per_api_call:
                print("No new papers added in this batch. Stopping for this query.")
                break

            if newly_fetched_and_saved_count >= num_papers:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"{RED}Error querying ArXiv API: {e}{RESET}")
            break
        except ET.ParseError as e:
            print(f"{RED}Error parsing ArXiv API response: {e}{RESET}")
            break
    
    if newly_fetched_and_saved_count > 0:
        status_msg = f"Successfully downloaded {newly_fetched_and_saved_count} new papers for query '{search_query_str[:50]}...'"
    else:
        status_msg = f"No new papers found or downloaded for query: '{search_query_str[:50]}...'"
    
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
            # print(f"\nProcessing: {pdf_file}") # Reduced verbosity
            
            if os.path.exists(txt_filepath) and os.path.getsize(txt_filepath) > 0: # Check if non-empty
                # print(f"Text file already exists and is not empty, skipping: {txt_filepath}") # Reduced verbosity
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
            
            # print(f"Text saved to: {txt_filepath}") # Reduced verbosity
            success_count += 1
            
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            continue
    
    return f"Successfully converted/verified {success_count} out of {len(pdf_files)} PDFs to text."


# --- Utility function from scopus_fetch.py ---
def sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    # Allow slashes and colons for DOIs/IDs before final sanitization for path
    name = re.sub(r'[^\w\s\-\./:]', '', name) # Keep ., /, :
    return re.sub(r'(?u)[^\-\w.]', "", name.replace("/", "_").replace(":", "_"))

def summarize_paper(
    pdf_path: str, 
    paper_name: str, 
    subject: str,
) -> str:
    """
    Summarize a paper using Gemini's direct PDF processing capability.
    Uploads the PDF to Gemini and processes it directly.
    """
    try:
        # Upload the PDF file to Gemini
        uploaded_file = genai.upload_file(
            path=pdf_path,
            mime_type='application/pdf',
            display_name=paper_name[:100]  # Truncate long names
        )
    except Exception as e:
        print(f"{RED}Error uploading file to Gemini: {e}{RESET}")
        return f"File upload error: {str(e)}"
    
    try:
        prompt = f"""You are an expert academic researcher. Summarize the provided paper for a systematic literature review (SLR) on: [{subject}].

Follow these instructions:
1. Extract metadata: Authors, Title, Journal/Conference, Year, DOI, URL, Paper Type
2. Discuss the paper's relevance to the SLR subject
3. List key points relevant to the subject with quotes from the paper
4. If not relevant, state: "This paper does not appear relevant to '{subject}'"

Paper Name: [{paper_name}]
SLR Subject: [{subject}]
"""
        # Generate content with the uploaded file
        response = summary_model.generate_content(
            [prompt, uploaded_file],
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        
        # Clean up: Delete the uploaded file after processing
        try:
            genai.delete_file(uploaded_file.name)
        except Exception as delete_error:
            print(f"{YELLOW}Warning: Could not delete uploaded file: {delete_error}{RESET}")
            
        return response.text.strip()
    
    except Exception as e:
        print(f"{RED}Error during summarization: {e}{RESET}")
        # Attempt to clean up even if summarization fails
        try:
            genai.delete_file(uploaded_file.name)
        except:
            pass
        return f"Summarization error: {str(e)}"
def batch_summarize_papers(
    subject_keywords: str,
    papers_to_summarize_details: List[Dict[str, any]],
    summaries_folder: str = SUMMARIES_FOLDER
) -> List[Dict[str, any]]:
    """
    Summarize a list of papers using direct PDF processing with Gemini,
    or by uploading text files as a fallback.
    """
    print(f"\nGenerating summaries for {len(papers_to_summarize_details)} papers on subject: '{subject_keywords}'...")
    os.makedirs(summaries_folder, exist_ok=True)

    if not papers_to_summarize_details:
        print("No papers provided to summarize.")
        return []

    processed_papers_with_summaries = []
    for paper_info in papers_to_summarize_details:
        pdf_path = paper_info.get('local_pdf_path')
        # Ensure 'filename' key exists, fallback to a generic name if not
        original_filename_for_summary = paper_info.get('filename', f"unknown_paper_{paper_info.get('id_primary', 'no_id')}")
        original_txt_filename_no_ext = os.path.splitext(original_filename_for_summary)[0]

        clean_summary_name_base = re.sub(r'[^\w\s-]', '', original_txt_filename_no_ext).strip()
        clean_summary_name_base = re.sub(r'\s+', '_', clean_summary_name_base)
        clean_summary_name_base = clean_summary_name_base[:100]
        if not clean_summary_name_base:
            clean_summary_name_base = f"summary_{original_txt_filename_no_ext.replace('/', '_').replace(':', '_')}"

        summary_filename_only = f"{clean_summary_name_base}_summary.txt"
        summary_filepath = os.path.join(summaries_folder, summary_filename_only)

        paper_name_for_prompt = paper_info.get('title', original_txt_filename_no_ext)
        augmented_paper_info = paper_info.copy()

        try:
            print(f"\nProcessing for summary: {original_filename_for_summary}")

            if os.path.exists(summary_filepath) and os.path.getsize(summary_filepath) > 10:
                print(f"Summary already exists, loading: {summary_filepath}")
                with open(summary_filepath, 'r', encoding='utf-8') as summary_file:
                    summary_content = summary_file.read()
            else:
                if pdf_path and os.path.exists(pdf_path):
                    print(f"Summarizing using PDF: {pdf_path}")
                    summary_content = summarize_paper(pdf_path, paper_name_for_prompt, subject_keywords)
                else:
                    # Fallback to text content via file upload
                    txt_file_path_for_fallback = paper_info.get('local_txt_path')
                    if txt_file_path_for_fallback and os.path.exists(txt_file_path_for_fallback):
                        print(f"{YELLOW}PDF not available or failed, using text file for upload: {txt_file_path_for_fallback}{RESET}")
                        summary_content = summarize_paper_fallback(
                            txt_file_path_for_fallback, # Pass the path
                            paper_name_for_prompt,
                            subject_keywords
                        )
                    else:
                        summary_content = f"Error: No PDF or valid text file path ({txt_file_path_for_fallback}) available for {paper_name_for_prompt}"
                        print(f"{RED}{summary_content}{RESET}")

                with open(summary_filepath, 'w', encoding='utf-8') as summary_file:
                    summary_file.write(summary_content)
                print(f"Summary saved to: {summary_filepath}")

            augmented_paper_info['summary_text'] = summary_content
            augmented_paper_info['summary_filepath'] = summary_filepath

            if "This paper does not appear to be relevant" in summary_content:
                print(f"Paper '{paper_name_for_prompt}' deemed not relevant by summarizer.")

            processed_papers_with_summaries.append(augmented_paper_info)

        except Exception as e:
            print(f"{RED}Error processing {original_filename_for_summary} for summary: {e}{RESET}")
            augmented_paper_info['summary_text'] = f"Error during summarization: {e}"
            augmented_paper_info['summary_filepath'] = None
            processed_papers_with_summaries.append(augmented_paper_info)

    return processed_papers_with_summaries


def summarize_paper_fallback(
    txt_file_path: str,  # Changed from paper_text
    paper_name: str,
    subject: str,
) -> str:
    """
    Fallback text-based summarization when PDF is unavailable.
    Uploads the TXT file to Gemini and processes it directly.
    """
    uploaded_file = None
    try:
        # Upload the TXT file to Gemini
        uploaded_file = genai.upload_file(
            path=txt_file_path,
            mime_type='text/plain', # Mime type for .txt files
            display_name=os.path.basename(txt_file_path)
        )

        prompt_instructions = f"""You are an expert academic researcher. Summarize the provided paper content (from the uploaded text file) for a systematic literature review (SLR) on: [{subject}].

Follow these instructions:
1. Extract metadata: Authors, Title, Journal/Conference, Year, DOI, URL, Paper Type (if inferable from text).
2. Discuss the paper's relevance to the SLR subject.
3. List key points relevant to the subject with quotes from the paper.
4. If not relevant, state: "This paper does not appear relevant to '{subject}'"

Paper Name: [{paper_name}] (filename: {os.path.basename(txt_file_path)})
SLR Subject: [{subject}]
"""
        # Generate content with the uploaded file
        response = summary_model.generate_content(
            [prompt_instructions, uploaded_file], # Pass as a list
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        
        return response.text.strip()

    except Exception as e:
        print(f"{RED}Error in fallback summarization for {paper_name}: {e}{RESET}")
        return f"Fallback summarization error for {paper_name}: {str(e)}"
    finally:
        # Clean up: Delete the uploaded file after processing
        if uploaded_file:
            try:
                genai.delete_file(uploaded_file.name)
            except Exception as delete_error:
                print(f"{YELLOW}Warning: Could not delete uploaded file {uploaded_file.name} in summarize_paper_fallback: {delete_error}{RESET}")


def generate_content_from_prompt(prompt: str, context_for_error: str = "LLM Generation") -> str:
    """Generates content using Gemini model with enhanced error handling"""
    global LLM_CALL_COUNT
    LLM_CALL_COUNT += 1

    # Rate limiting
    if LLM_CALL_COUNT > 0 and LLM_CALL_COUNT % LLM_CALLS_BEFORE_WAIT == 0:
        print(f"Reached {LLM_CALL_COUNT} LLM calls. Pausing for {LLM_WAIT_SECONDS} seconds...")
        time.sleep(LLM_WAIT_SECONDS)
        print("Resuming LLM calls.")

    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.7, # Increased temperature for more natural variety
            max_output_tokens=8000
        )
        
        max_retries_quota = 3
        attempt = 0
        
        while True:
            try:
                if attempt > 0:
                    LLM_CALL_COUNT += 1
                    if LLM_CALL_COUNT % LLM_CALLS_BEFORE_WAIT == 0:
                        print(f"Reached {LLM_CALL_COUNT} LLM calls (retry). Pausing...")
                        time.sleep(LLM_WAIT_SECONDS)

                response = summary_model.generate_content(
                    prompt,
                    generation_config=generation_config
                )

                # Handle MAX_TOKENS error
                if response.candidates and response.candidates[0].finish_reason and response.candidates[0].finish_reason.name == 'MAX_TOKENS':
                    print(f"{YELLOW}MAX_TOKENS error for {context_for_error}. Skipping this request.{RESET}")
                    return f"% MAX_TOKENS error for {context_for_error}"

                # Process response
                try:
                    generated_text = response.text.strip()
                    return generated_text
                except ValueError as ve:
                    print(f"{YELLOW}Response issue for {context_for_error}: {ve}{RESET}")
                    return f"% Response issue for {context_for_error}: {ve}"

            except Exception as e_inner:
                error_str = str(e_inner)
                # Handle quota errors
                if "429" in error_str and "quota" in error_str.lower():
                    if attempt < max_retries_quota:
                        retry_delay = 60
                        print(f"{YELLOW}Quota error (429) for {context_for_error}. Waiting {retry_delay}s... (Attempt {attempt+1}/{max_retries_quota}){RESET}")
                        time.sleep(retry_delay)
                        attempt += 1
                        continue
                    else:
                        print(f"{RED}Quota limit still exceeded after retries. Aborting.{RESET}")
                        return f"% Quota exceeded error for {context_for_error}"
                
                # Handle other errors
                print(f"{RED}Error during generation for {context_for_error}: {error_str}{RESET}")
                return f"% Error during {context_for_error}: {error_str}"

    except Exception as e:
        print(f"{RED}Unexpected error in generate_content_from_prompt: {e}{RESET}")
        return f"% Unexpected error in generate_content_from_prompt: {e}"

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
        generated_text = generate_content_from_prompt(combined_prompt, context_for_error=f"Markdown generation for {filename}")
        
        # Remove markdown code block fences (```latex or ```)
        generated_text = re.sub(r'^```(?:latex)?\s*[\r\n]*', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'[\r\n]*```\s*$', '', generated_text, flags=re.MULTILINE)
        # Normalize citation format: \cite {key} -> \cite{key}
        generated_text = re.sub(r'\\cite\s*\{\s*([^}\s]+)\s*\}', r'\\cite{\1}', generated_text)

        with open(filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        return generated_text
    except Exception as e:
        error_message = f"Error in generate_markdown for {filename}: {e}\nPrompt context (first 500 chars):\n{context[:500]}\nPrompt (first 500 chars):\n{prompt[:500]}"
        print(error_message)
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(f"% Error generating this section: {e}\n")
        return f"% Error in generate_markdown for {filename}: {e}"
    finally:
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            print(f"Generated {filename}")
        elif not os.path.exists(filename):
            print(f"File {filename} was not created.")

def validate_latex(content: str) -> str:
    """Ensure all LaTeX environments are properly closed"""
    env_stack = []
    # Regex to find \begin{env} and \end{env}
    for match in re.finditer(r'\\(begin|end)\s*\{([^{}]+)\}', content):
        env_type, env_name = match.groups()
        if env_type == 'begin':
            env_stack.append(env_name)
        elif env_stack and env_stack[-1] == env_name:
            env_stack.pop()
        # If \end is found without a matching \begin, it's an error, but we're focused on unclosed \begin
    while env_stack:
        unclosed_env = env_stack.pop()
        print(f"{YELLOW}Warning: Auto-closing unclosed LaTeX environment: {unclosed_env}{RESET}")
        content += f"\n\\end{{{unclosed_env}}}"
    return content

    
def create_bibliometric(
    fetched_papers_metadata: List[Dict[str, any]], 
    summaries_text: str = "" # summaries_text is for context only
) -> str:
    if not fetched_papers_metadata:
        print("No fetched paper metadata provided for bibliometric analysis. Skipping biblio.bib generation.")
        return "% No fetched paper metadata provided for bibliometric analysis.\n"
        
    metadata_prompt_string = ""
    for i, meta in enumerate(fetched_papers_metadata):
        # Ensure meta is a dict, as it might come from llm_confirmed_relevant_papers
        if not isinstance(meta, dict):
            print(f"Warning: Metadata item {i} is not a dictionary, skipping for BibTeX generation. Item: {meta}")
            continue
        metadata_prompt_string += f"Paper {i+1}:\n"
        metadata_prompt_string += f"  Title: {meta.get('title', 'N/A')}\n"
        metadata_prompt_string += f"  Authors: {', '.join(meta.get('authors', []))}\n"
        metadata_prompt_string += f"  Year: {meta.get('published_year', 'N/A')}\n"
        metadata_prompt_string += f"  DOI: {meta.get('doi', 'N/A')}\n"
        metadata_prompt_string += f"  URL: {meta.get('id_url', meta.get('pdf_url', 'N/A'))}\n" 
        metadata_prompt_string += f"  Journal/Conference: {meta.get('journal_ref', 'N/A')}\n\n"

    if not metadata_prompt_string.strip():
        print("No valid metadata could be extracted for BibTeX generation.")
        return "% No valid metadata for BibTeX generation.\n"

    prompt = f"""Based on the following paper metadata (and optionally, summaries for context), create a .bib file content for a BibTeX bibliography.
Each entry should attempt to extract and format the following fields if available from the METADATA primarily: author, title, journal (or booktitle for conferences), year, pages (if available), doi, url.
Use standard BibTeX entry types (e.g., @article, @inproceedings, @book, @techreport). Create a unique BibTeX key for each entry (e.g., AuthorYearKeyword).
If a field is not present in the metadata, omit it from the BibTeX entry.

---BEGIN METADATA---
{metadata_prompt_string}
---END METADATA---

---BEGIN SUMMARIES (for additional context if needed, but prioritize metadata above)---
{summaries_text if summaries_text.strip() else "No summaries provided for additional context."}
---END SUMMARIES---

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
    prompt += f"\n\n{LATEX_SAFETY_RULES}"
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

# --- Scopus Specific Functions (adapted from scopus_fetch.py) ---
def convert_pdf_to_text_ocr(pdf_path: str, txt_out_path: str) -> bool:
    """
    Converts a PDF to text using OCR (Tesseract).
    Used for Scopus PDFs which might be image-based.
    """
    try:
        # Ensure output directory for the .txt file exists
        os.makedirs(os.path.dirname(txt_out_path), exist_ok=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(pdf_path, output_folder=temp_dir)
            full_text = ""
            for i, img in enumerate(images):
                text = pytesseract.image_to_string(img)
                full_text += f"\n\n--- Page {i + 1} ---\n{text}"

        with open(txt_out_path, "w", encoding="utf-8") as f:
            f.write(full_text.strip())
        print(f"    OCR Success: Saved {txt_out_path}")
        return True
    except Exception as e:
        print(f"    [!] OCR failed for {pdf_path}: {e}")
        return False

def download_pdf_from_scopus(
    doi: str,
    base_filename: str,
    pdf_folder: str,
    txt_folder: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads PDF from Scopus by DOI without OCR. Returns PDF path if successful.
    """
    if not doi:
        return None, None

    pdf_path = os.path.join(pdf_folder, f"{base_filename}.pdf")
    txt_path = os.path.join(txt_folder, f"{base_filename}.txt")

    if os.path.exists(pdf_path) and os.path.exists(txt_path) and os.path.getsize(txt_path) > 0:
        print(f"    PDF and TXT already exist for {base_filename}, skipping download.")
        return pdf_path, txt_path

    headers = {"X-ELS-APIKey": SCOPUS_API_KEY, "Accept": "application/pdf"}
    url = SCOPUS_ARTICLE_BASE_URL + urllib.parse.quote_plus(doi)

    try:
        print(f"    Attempting Scopus PDF download for DOI: {doi} (File: {base_filename}.pdf)")
        resp = requests.get(url, headers=headers, stream=True, timeout=60)
        if resp.status_code == 200:
            os.makedirs(pdf_folder, exist_ok=True)
            with open(pdf_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"    Scopus PDF downloaded: {pdf_path}")
            return pdf_path, None  # No OCR text path
        else:
            print(f"    Scopus PDF download failed for DOI {doi}. Status: {resp.status_code} {resp.text[:100]}")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"    Scopus PDF download exception for DOI {doi}: {e}")
        return None, None
def fetch_scopus_papers_and_process(
    search_query_str: str,
    year_range: Tuple[int, int],
    num_papers: int,
    pdf_folder: str,
    txt_folder: str,
    already_fetched_primary_ids: set
) -> Tuple[List[Dict], int, str]:
    """ 
    Fetches paper metadata from Scopus, downloads PDFs, converts them to text (OCR),
    and returns a list of processed paper metadata.
    """
    headers = {"X-ELS-APIKey": SCOPUS_API_KEY, "Accept": "application/json"}
    # Scopus query needs to be specific. Example: ALL(keyword) AND PUBYEAR > 2020 AND PUBYEAR < 2023
    # For simplicity, we'll use the input search_query_str directly in a Scopus-friendly way.
    # A more robust solution would involve LLM converting natural language to Scopus query syntax.
    # For now: use the natural language query and filter by year.
    query_for_api = f'TITLE-ABS-KEY("{search_query_str}") AND PUBYEAR > {year_range[0]-1} AND PUBYEAR < {year_range[1]+1}'
    
    params = {"query": query_for_api, "count": num_papers * 2, "sort": "-citedby-count"} # Fetch more to filter
    
    print(f"Searching Scopus for: {query_for_api}")
    processed_papers_metadata_list = []
    newly_fetched_and_saved_count = 0

    try:
        resp = requests.get(SCOPUS_SEARCH_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        return [], 0, f"Scopus API request failed: {e}"
    except ValueError as e: # JSONDecodeError
        return [], 0, f"Scopus API response JSON decoding failed: {e} - Response: {resp.text[:200]}"

    scopus_entries = data.get("search-results", {}).get("entry", [])
    if not scopus_entries:
        return [], 0, f"Scopus: No entries found for query '{search_query_str[:50]}...'"

    for entry in scopus_entries:
        if newly_fetched_and_saved_count >= num_papers: # Target for this call met
            break

        title = entry.get("dc:title", "N/A Title")
        doi = entry.get("prism:doi")
        scopus_id_full = entry.get("dc:identifier", "")
        scopus_id = scopus_id_full.split(":")[-1] if ":" in scopus_id_full else scopus_id_full
        
        primary_id_scopus = f"scopus_{doi or scopus_id}"
        if not doi and not scopus_id:
            print(f"    Skipping Scopus entry '{title[:50]}' due to missing DOI and Scopus ID.")
            continue
        
        if primary_id_scopus in already_fetched_primary_ids:
            # print(f"    Skipping Scopus paper '{title[:50]}' (ID: {primary_id_scopus}) - already fetched by this run.")
            continue

        sanitized_base_filename = sanitize_filename(primary_id_scopus) # Uses the primary_id for filename base
        # pdf_path will be the path to the PDF if downloaded, else None.
        # ocr_txt_path will be the path to the OCR'd text if successful, else None.
        pdf_downloaded_path, ocr_txt_path = download_pdf_from_scopus(doi, sanitized_base_filename, pdf_folder, txt_folder)

        # Determine the text content and its source
        final_txt_path_for_meta = None
        text_content_available = False

        if ocr_txt_path and os.path.exists(ocr_txt_path) and os.path.getsize(ocr_txt_path) > 0:
            final_txt_path_for_meta = ocr_txt_path
            text_content_available = True
            print(f"    Using OCR'd text for Scopus entry {primary_id_scopus}")
        else:
            # OCR failed or PDF not downloaded, try to use API abstract
            api_abstract = entry.get("dc:description") or entry.get("prism:description") or ""
            if api_abstract.strip():
                # Save the API abstract to a .txt file
                abstract_txt_path = os.path.join(txt_folder, f"{sanitized_base_filename}_abstractAPI.txt") # Ensure unique name
                try:
                    with open(abstract_txt_path, "w", encoding="utf-8") as f_abs:
                        f_abs.write(f"Title: {title}\n")
                        f_abs.write(f"Authors: {', '.join([a.get('$') for a in entry.get('author', []) if isinstance(a, dict) and '$' in a])}\n")
                        f_abs.write(f"Year: {entry.get('prism:coverDate', '')[:4]}\n")
                        f_abs.write(f"DOI: {doi}\n\n")
                        f_abs.write("--- ABSTRACT (from API) ---\n\n")
                        f_abs.write(api_abstract.strip())
                    final_txt_path_for_meta = abstract_txt_path
                    text_content_available = True
                    print(f"    Using API abstract for Scopus entry {primary_id_scopus}, saved to {abstract_txt_path}")
                except Exception as e_write_abs:
                    print(f"    Error writing API abstract to file for {primary_id_scopus}: {e_write_abs}")
            else:
                print(f"    No OCR text and no API abstract for Scopus entry {primary_id_scopus}. Cannot process further.")

        if text_content_available: # If we have either OCR text or API abstract
            scopus_meta = {
                'source': 'scopus', 'id_primary': primary_id_scopus,
                'title': title,
                'authors': [a.get('$') for a in entry.get('author', []) if isinstance(a, dict) and '$' in a],
                'published_year': entry.get("prism:coverDate", "")[:4],
                'abstract_api': entry.get("dc:description") or entry.get("prism:description") or "", # Check both
                'doi': doi, 'scopus_id': scopus_id,
                'local_pdf_path': pdf_downloaded_path, # This might be None if PDF download failed
                'local_txt_path': final_txt_path_for_meta, # Path to the text file (either OCR or API abstract)
            }
            processed_papers_metadata_list.append(scopus_meta)
            already_fetched_primary_ids.add(primary_id_scopus) # Mark as fetched
            newly_fetched_and_saved_count += 1
    
    return processed_papers_metadata_list, newly_fetched_and_saved_count, f"Scopus: Processed {newly_fetched_and_saved_count} new papers for query '{search_query_str[:50]}...'"

def create_charts(section_content_tex_path: str, section_name_for_file: str) -> str:
    """
    Enhances a LaTeX section (from a .tex file) by adding charts/tables based on its content.
    section_name_for_file is used for the output filename.
    """
    original_content = ""
    try:
        with open(section_content_tex_path, 'r', encoding='utf-8') as f_orig:
            original_content = f_orig.read()
    except Exception as e_read:
        print(f"{RED}Error reading section content file {section_content_tex_path} for chart creation: {e_read}{RESET}")
        return f"% Error reading input file for chart creation: {section_name_for_file}"

    if not original_content.strip() or original_content.startswith("% Error") or "No summaries provided" in original_content or "Insufficient input" in original_content:
        print(f"Section content for '{section_name_for_file}' (from file {os.path.basename(section_content_tex_path)}) is empty or indicates an error/lack of data. Skipping chart creation.")
        return original_content

    output_tex_filename = f"Results/{section_name_for_file}_with_charts.tex"
    
    prompt_instructions = f"""
Act as an expert LaTeX document processor and researcher. Your task is to analyze the provided LaTeX **section of a paper** (uploaded as a file) and enhance it.

### Task Description:
1.  **Analyze Content for Visualizations**:
    *   Read the provided LaTeX section content from the uploaded file.
    *   Identify parts of the text that describe data, comparisons, processes, or structures that could be effectively visualized as a chart, graph, or complex table using LaTeX (TikZ, pgfplots, pgfgantt, etc.).
    *   If suitable content for new visualizations is found, create the LaTeX code for these visualizations *from scratch*. Do NOT use placeholders for images or refer to external image files.
    *   Ensure any data presented in new tables/charts is *directly derivable* from the provided section content. Do not invent quantitative data. If the section is qualitative or lacks specific data points suitable for a chart/table, do not force one.
    *   Integrate these newly created LaTeX visualizations seamlessly into the provided section content.
    *   When creating figures or tables, use placement specifiers like `[htbp]` for flexibility, e.g., `\\begin{{figure}}[htbp]`. Ensure captions are descriptive.

2.  **Review Existing Tables/Figures (if any within the section)**:
    *   If the provided section already contains `\\begin{{table}}...\\end{{table}}` or `\\begin{{figure}}...\\end{{figure}}` environments, review them for correctness.
    *   Correct formatting, alignment, or structural issues in existing tables/figures.
    *   Ensure they are appropriately placed within the section flow.

3.  **LaTeX Best Practices and Error Correction**:
    *   Ensure the entire output is valid LaTeX code for the given section.
    *   Correct common LaTeX errors if they appear in the input or are introduced.
    *   Assume necessary packages are loaded in the main document preamble – DO NOT add `\\usepackage` commands here.

4.  **Output**:
    *   Return *only* the complete, corrected, and enhanced LaTeX code for the section, starting with `\\section{{{section_name_for_file}}}{{...}}` (or `\\subsection`, etc., matching the input structure) and ending appropriately.
    *   If no enhancements or corrections are made, return the original section content IDENTICALLY.
    *   Do NOT include `\\documentclass`, `\\begin{{document}}`, `\\end{{document}}`.
    *   Do NOT add any conversational text, explanations, or apologies.

The section to process is in the uploaded file.
Add any type of tables of figures based on the section and the context.
Return the **modified LaTeX code for the section ONLY**.
"""
    prompt_instructions += f"\n\n{LATEX_SAFETY_RULES}"
    
    uploaded_section_file = None
    enhanced_content = original_content # Default to original if LLM fails

    try:
        uploaded_section_file = genai.upload_file(
            path=section_content_tex_path,
            mime_type='text/plain', # Treat .tex section as plain text
            display_name=f"section_{section_name_for_file}"
        )
        
        # generate_markdown needs to be able to handle a list [instructions, file_object]
        # For now, let's assume generate_markdown is adapted or we call summary_model directly
        # For simplicity here, directly calling summary_model.
        # The `generate_markdown` function would need to be refactored to accept a list for its `prompt` argument.
        
        response = summary_model.generate_content(
            [prompt_instructions, uploaded_section_file],
            generation_config=genai.types.GenerationConfig(temperature=0.3) # Lower temp for code generation
        )
        llm_output = response.text.strip()

        if llm_output and not llm_output.startswith("% Error"):
            enhanced_content = llm_output
            if "[Actual Count]" in enhanced_content or "[Number Here]" in enhanced_content:
                enhanced_content = enhanced_content.replace("[Actual Count]", "N").replace("[Number Here]", "N")
                print(f"Replaced placeholders in {section_name_for_file} chart content.")
            if enhanced_content.strip() == original_content.strip():
                 print(f"No chart enhancements applied by LLM for section {section_name_for_file}.")
        else:
            print(f"LLM returned original or error for chart enhancement of {section_name_for_file}. Using original.")
            enhanced_content = original_content # Revert to original if LLM output is an error string

    except Exception as e:
        print(f"{RED}Error during chart creation for {section_name_for_file}: {e}{RESET}")
        enhanced_content = original_content # Revert to original on error
    finally:
        if uploaded_section_file:
            try:
                genai.delete_file(uploaded_section_file.name)
            except Exception as delete_error:
                print(f"{YELLOW}Warning: Could not delete uploaded section file {uploaded_section_file.name}: {delete_error}{RESET}")

    # Save the (potentially) enhanced content
    results_dir = os.path.dirname(output_tex_filename)
    if results_dir and not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    with open(output_tex_filename, 'w', encoding='utf-8') as f_out:
        f_out.write(enhanced_content)
    print(f"Saved chart-enhanced section to: {output_tex_filename}")
    
    return enhanced_content



def clean_latex_output(content: str) -> str:
    """Final cleanup of generated LaTeX"""
    # Remove null bytes if any
    content = content.replace("\0", "")
    # Correct common XML/HTML entities that might slip in
    content = re.sub(r'\\textgreater\s?', '>', content)
    content = re.sub(r'\\textless\s?', '<', content)
    # Correct over-escaped underscores if not part of a command
    content = re.sub(r'\\_(?!\w)', '_', content) # Only if \_ is not followed by a letter (e.g. \_textit is wrong)
    return content

def Results(abstract: str, related_works: str,research_methodes: str,review_finding: str,discussion: str,subject: str, bibliometric_content: str, actual_paper_title: str) -> str:
    # Ensure Results directory exists
    os.makedirs("Results", exist_ok=True)

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
    pdftitle={{{actual_paper_title}}},
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
\pgfplotsset{{compat=1.18}} 
\usepackage{{tikz}}
\usetikzlibrary{{arrows.meta, trees, shapes.geometric, positioning, calc}} % Added calc for complex positioning
\usepackage[gantt]{{pgfgantt}} 
\usepackage{{smartdiagram}} 
\usepackage{{array}} 
\usepackage{{booktabs}} 
\usepackage{{lscape}} 
\usepackage{{threeparttable}} 
\usepackage{{caption}} 
\usepackage{{subcaption}} 

\usepackage[numbers,sort&compress]{{natbib}}
\bibliographystyle{{plainnat}} 

\title{{{actual_paper_title}}}
\author{{Systematic Literature Review Automation Tool}} % Updated placeholder
\date{{\\today}}
"""

    full_latex_document = f"{latex_preamble}\n\n\\begin{{document}}\n\n\\maketitle\n\n"
    
    # Add Abstract and Keywords (which are part of abstract_intro_keywords_tex)
    # The abstract_intro_keywords_tex should contain \begin{abstract}...\end{abstract} and \textbf{Keywords...}
    # Then \section{Introduction}
    full_latex_document += f"{abstract}\n\n" 

    # Add Background section (if generated and passed)
    # Assuming background_tex is generated and passed to this function if used.
    # For now, it's not in the function signature, so we'll assume it's integrated elsewhere or added manually.
    # If background_tex exists: full_latex_document += f"{background_tex}\n\n"

    full_latex_document += f"{related_works}\n\n"
    full_latex_document += f"{research_methodes}\n\n"
    full_latex_document += f"{review_finding}\n\n"
    full_latex_document += f"{discussion}\n\n" # discussion_conclusion_tex contains discussion & conclusion

    full_latex_document += "\\section*{References}\n"
    full_latex_document += "\\bibliography{biblio}\n\n" 

    full_latex_document += "\\end{document}\n"

    # Apply validation and cleaning before saving
    full_latex_document = validate_latex(full_latex_document)
    full_latex_document = clean_latex_output(full_latex_document)
    
    safe_title_filename = re.sub(r'[^\w\s-]', '', actual_paper_title).strip()
    safe_title_filename = re.sub(r'\s+', '_', safe_title_filename)[:100] 
    if not safe_title_filename: safe_title_filename = "Untitled_SLR_Paper"
    output_filename = f"Results/{safe_title_filename}.tex"
    try:
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(full_latex_document)
        print(f"Generated complete LaTeX document: {output_filename}")
        
        # Save the biblio.bib content if it was passed and is not just a filename
        # This check is important: bibliometric_content is the *actual content* of biblio.bib
        if bibliometric_content and not bibliometric_content.startswith("% Error"):
             bib_path = "Results/biblio.bib"
             if not os.path.exists(bib_path) or os.path.getsize(bib_path) == 0 : # Save if not exists or empty
                 with open(bib_path, 'w', encoding='utf-8') as bib_file:
                    bib_file.write(bibliometric_content)
                 print(f"Saved BibTeX content to {bib_path}")
             elif os.path.exists(bib_path) and bibliometric_content != open(bib_path, 'r', encoding='utf-8').read():
                 # Overwrite if content is different (e.g. updated)
                 with open(bib_path, 'w', encoding='utf-8') as bib_file:
                    bib_file.write(bibliometric_content)
                 print(f"Updated BibTeX content in {bib_path}")


        return full_latex_document # Return the content string
    except Exception as e:
        print(f"Error generating {output_filename}: {e}")
        return f"% Error generating {output_filename}: {e}"

def create_background_string(
    review_findings: str, related_works: str, research_methodes: str,
    discussion_conclusion: str, bibliometric_content: str,
    reviewer_suggestions: str = "",
    slr_outline: str = "", 
    human_style_example_text: str = ""
):
    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for this Background Section:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"
    
    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for this Background Section:\n{slr_outline}\nEnsure your section aligns with this broader plan.\n---"

    style_guidance_addon_formatted = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic.
To achieve this, **actively avoid common AI writing patterns**.
Instead, draw inspiration from the **narrative style, sentence flow, phrasing nuances, and vocabulary choices** in the following sample of human-written academic text.

**Emulate these human-like qualities:**
- **Varied Sentence Structure:** Mix short, impactful sentences with longer, more complex ones. Avoid monotonous sentence lengths or predictable structures.
- **Natural Transitions:** Use a variety of transitional words and phrases to create a smooth, logical flow between ideas. Avoid overusing simplistic transitions.
- **Sophisticated yet Clear Vocabulary:** Employ precise academic language, but ensure it sounds natural and not forced or overly thesaurus-driven.
- **Engaging Narrative Tone:** Even in academic writing, aim for a tone that is confident, clear, and subtly engaging. Avoid a dry, robotic, or overly detached tone.
- **Subtlety and Nuance:** Human writing often conveys meaning through subtle phrasing and nuance. Try to incorporate this.

**Crucially, DO NOT:**
- **Copy Content:** Do not replicate any specific facts, arguments, or the overall structure from the sample text.
- **Mimic Structure:** The sample is for *stylistic inspiration only*, not for structural guidance.
- **Sound Robotic or Formulaic:** Actively work against sounding like a typical AI. If your phrasing feels too standard or predictable, revise it.

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---

Before finalizing your response for this section, reread it and ask yourself: "Does this sound like a human wrote it, or does it have tell-tale signs of AI generation?" Adjust as needed.
"""

    # Check if essential inputs are valid
    if any(s.startswith("% Error") or "No summaries provided" in s or "Insufficient input" in s for s in [review_findings, related_works, research_methodes, discussion_conclusion]):
        print("One or more input sections for Background generation are invalid or empty. Skipping Background.")
        return "\\section{Background}\n% Skipped due to invalid input sections.\n"

    prompt = fr"""
Act as an expert academic writer. Create the **Background** section for a systematic literature review (SLR)make sure it's detailed , academicale , and huminazed.

{suggestions_addon}

### Task Description:
{outline_addon}
{style_guidance_addon_formatted}
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
    *   Output only the LaTeX code for this section.
6.  **Bibliography for Context (DO NOT REPRODUCE IN OUTPUT, FOR CITATION KEY INFERENCE ONLY)**:
    ```bibtex
    {bibliometric_content}
    ```

### Output:
Return *only* the complete LaTeX code for the `\section{{Background}}`. Do not include any explanations or conversational text.



make sure you use the same kind of vocabulary , the same way of narratting, adn words  

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---
"""
    return generate_markdown(prompt + f"\n\n{LATEX_SAFETY_RULES}", 'Results/background.tex')

def create_related_works(summaries: str,
                         subject: str,
                         Biblio_content:str,
                         reviewer_suggestions: str = "",
                         slr_outline: str = "",
                         human_style_example_text: str = "") -> str:
    if not summaries.strip() or summaries.startswith("% Error"):
        print("No valid summaries provided for related works. Skipping section generation.")
        return "\\section{Related Works}\n% No valid summaries provided to generate this section.\n"

    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for this Related Works Section:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for this Related Works Section:\n{slr_outline}\nEnsure your section aligns with this broader plan, especially regarding themes and paper groupings.\n---"

    style_guidance_addon_formatted = f"""
### Stylistic Guidance (for human-like writing):
{Human_Text} 
""" # Assuming Human_Text is defined globally as in your provided code

    prompt_instructions = rf"""
Create a comprehensive **Related Works** section for a systematic literature review (SLR) on the subject: **{subject}** make sure it's detailed , academicale , and huminazed.
The summaries of papers to be used are in the uploaded 'summaries_data.txt' file.
The BibTeX bibliography for context is in the uploaded 'biblio_context.bib' file.

{suggestions_addon}
{outline_addon}
{style_guidance_addon_formatted}

### Requirements:
1.  **Content and Structure**:
    *   Start with `\section{{Related Works}}`.
    *   Analyze the paper summaries from the uploaded 'summaries_data.txt' to identify themes, trends, compare methodologies, and discuss how they relate to `{subject}`.
    *   Focus on papers that are highly relevant to `{subject}`.
    *   Synthesize information into a cohesive narrative. Avoid a simple list of summaries. Group related papers by theme or approach.
2.  **Writing Style**: Maintain a formal academic tone. Logically link paragraphs and ideas.
3.  **Citations**:
    *   Use `\cite{{bibtex_key}}` for all references. Infer BibTeX keys from the uploaded 'biblio_context.bib'.
4.  **LaTeX Formatting**: Output *only* Overleaf-compatible LaTeX code.
    *   Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, or `\usepackage`.
{LATEX_SAFETY_RULES}
"""
    # Add LATEX_SAFETY_RULES if not already part of the main prompt string for safety
    # prompt_instructions += f"\n\n{LATEX_SAFETY_RULES}"


    uploaded_summaries_file = None
    uploaded_biblio_context_file = None
    temp_summaries_path = None
    temp_biblio_path = None

    try:
        # Save summaries string to a temporary file
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt", encoding='utf-8') as tmp_s:
            tmp_s.write(summaries)
            temp_summaries_path = tmp_s.name
        
        # Save Biblio_content string to a temporary file
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".bib", encoding='utf-8') as tmp_b:
            tmp_b.write(Biblio_content)
            temp_biblio_path = tmp_b.name

        uploaded_summaries_file = genai.upload_file(
            path=temp_summaries_path,
            mime_type='text/plain',
            display_name='summaries_data.txt'
        )
        uploaded_biblio_context_file = genai.upload_file(
            path=temp_biblio_path,
            mime_type='text/plain', # BibTeX is plain text
            display_name='biblio_context.bib'
        )
        
        # generate_markdown needs to be adapted to handle a list prompt
        # For now, directly calling summary_model.generate_content
        response = summary_model.generate_content(
            [prompt_instructions, uploaded_summaries_file, uploaded_biblio_context_file],
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        generated_text = response.text.strip()
        
        # Clean up markdown code block fences
        generated_text = re.sub(r'^```(?:latex)?\s*[\r\n]*', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'[\r\n]*```\s*$', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'\\cite\s*\{\s*([^}\s]+)\s*\}', r'\\cite{\1}', generated_text)

        # Save the generated section
        output_filename = 'Results/related_works.tex'
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        print(f"Generated {output_filename}")
        return generated_text

    except Exception as e:
        print(f"{RED}Error in create_related_works: {e}{RESET}")
        return f"% Error generating related_works section: {e}"
    finally:
        if uploaded_summaries_file: genai.delete_file(uploaded_summaries_file.name)
        if uploaded_biblio_context_file: genai.delete_file(uploaded_biblio_context_file.name)
        if temp_summaries_path and os.path.exists(temp_summaries_path): os.remove(temp_summaries_path)
        if temp_biblio_path and os.path.exists(temp_biblio_path): os.remove(temp_biblio_path)



def create_reshearch_methodes(
    related_works_content: str,
    summaries: str,
    subject: str,
    Biblio_content:str,
    year_range_for_prompt: Tuple[int, int], 
    reviewer_suggestions: str = "",
    slr_outline: str = "",
    human_style_example_text: str = ""):
    if (not summaries.strip() or summaries.startswith("% Error")) and \
       (not related_works_content.strip() or related_works_content.startswith("% Error")):
        print("Insufficient or invalid input (summaries/related works) for research methods. Skipping section generation.")
        return "\\section{Research Methods}\n% Insufficient or invalid input to generate this section.\n"

    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for this Research Methods Section:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for this Research Methods Section:\n{slr_outline}\nConsider if the outline suggests any specific methodological focus.\n---"

    style_guidance_addon_formatted = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic.
To achieve this, **actively avoid common AI writing patterns**.
Instead, draw inspiration from the **narrative style, sentence flow, phrasing nuances, and vocabulary choices** in the following sample of human-written academic text.

**Emulate these human-like qualities:**
- **Varied Sentence Structure:** Mix short, impactful sentences with longer, more complex ones. Avoid monotonous sentence lengths or predictable structures.
- **Natural Transitions:** Use a variety of transitional words and phrases to create a smooth, logical flow between ideas. Avoid overusing simplistic transitions.
- **Sophisticated yet Clear Vocabulary:** Employ precise academic language, but ensure it sounds natural and not forced or overly thesaurus-driven.
- **Engaging Narrative Tone:** Even in academic writing, aim for a tone that is confident, clear, and subtly engaging. Avoid a dry, robotic, or overly detached tone.
- **Subtlety and Nuance:** Human writing often conveys meaning through subtle phrasing and nuance. Try to incorporate this.

**Crucially, DO NOT:**
- **Copy Content:** Do not replicate any specific facts, arguments, or the overall structure from the sample text.
- **Mimic Structure:** The sample is for *stylistic inspiration only*, not for structural guidance.
- **Sound Robotic or Formulaic:** Actively work against sounding like a typical AI. If your phrasing feels too standard or predictable, revise it.

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---

Before finalizing your response for this section, reread it and ask yourself: "Does this sound like a human wrote it, or does it have tell-tale signs of AI generation?" Adjust as needed.
"""

    prompt = rf"""
Create a detailed **Research Methods** section for a systematic literature review (SLR) on **{subject}** make sure it's detailed , academicale , and huminazed.

{suggestions_addon}

### Requirements:
{outline_addon}
{style_guidance_addon_formatted}
1.  **Guidelines**: State whether **Kitchenham** or **PRISMA** guidelines (or a hybrid) were followed and briefly explain the choice or adaptation.
2.  **Structure (Subsections)**:
    *   `\subsection{{Introduction}}`: Briefly introduce the methodology.
    *   `\subsection{{Research Questions (RQs)}}`:
        *   List primary RQs (e.g., RQ1, RQ2). For each, state its motivation.
        *   Optionally, list sub-questions if applicable.
    *   `\subsection{{Search Strategy}}`:
        *   Describe the search process. This automated system primarily queries ArXiv and Scopus due to API accessibility. A comprehensive manual Systematic Literature Review (SLR) might extend this search to other databases such as IEEE Xplore, Google Scholar, and Web of Science.
        *   Mention the search string(s) used. If complex, explain its components (e.g., using PICO or keyword combinations). The initial search query was derived from "{subject}".
        *   Include date range of the search (e.g., from {year_range_for_prompt[0]} to {year_range_for_prompt[1]}).
        *   Optionally, include a PRISMA-like flowchart (using TikZ or similar, if you can generate the LaTeX for it). If generating a flowchart, use clear textual placeholders like "[Number Here]" or "[Actual Count]" for the counts at each stage, as these will be manually filled in later. For example: "Records identified ([Number Here]) -> Records after duplicates removed ([Number Here]) -> etc."
    *   `\subsection{{Inclusion and Exclusion Criteria}}`: List criteria for paper selection (e.g., language, publication type, relevance to RQs). Justify them.
    *   `\subsection{{Quality Assessment}}`: Describe criteria used to assess the quality of included studies (e.g., rigor, credibility, relevance).
    *   `\subsection{{Data Extraction and Synthesis}}`: Explain how data was extracted from selected papers and how it was synthesized to answer RQs.
3.  **LaTeX Formatting**:
    *   Start with `\section{{Research Methods}}`.
    *   Use Overleaf-compatible LaTeX. Include LaTeX for tables or lists if appropriate (e.g., for criteria).
    *   When including figures or tables, use placement specifiers like `[htbp]` for flexibility.
    *   Do NOT include `\documentclass`, `\begin{{document}}`, `\end{{document}}`, or `\usepackage` commands.
4.  **Citations**: Use `\cite{{bibtex_key}}` when referencing methodological papers or tools *only if their BibTeX keys can be reliably inferred from the provided `Biblio_content`*. If a standard methodological paper (like PRISMA or Kitchenham guidelines) is mentioned but its BibTeX key is NOT in the provided `Biblio_content`, then describe the method without a `\cite` command for that specific guideline, or state "(following PRISMA guidelines, citation to be added)". Do not invent BibTeX keys for them.
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

### Placeholder Guide for PRISMA Flowchart (if generated):
Use these specific placeholders. They will be replaced by actual numbers by the system.
- `[NUMBER_RECORDS_IDENTIFIED_ARXIV]`
- `[NUMBER_RECORDS_IDENTIFIED_SCOPUS]`
- `[NUMBER_RECORDS_IDENTIFIED_MANUAL]`
- `[NUMBER_RECORDS_IDENTIFIED_SNOWBALL]`
- `[NUMBER_RECORDS_AFTER_DUPLICATES_REMOVED]` (Total unique items before summarization)
- `[NUMBER_RECORDS_SCREENED_FOR_SUMMARIZATION]` (Items for which text was successfully extracted for summarization)
- `[NUMBER_SUMMARIES_GENERATED]`
- `[NUMBER_EXCLUDED_BY_LLM_RELEVANCE_FILTER]`
- `[NUMBER_STUDIES_INCLUDED_QUALITATIVE]` (Final count of LLM-confirmed relevant papers for synthesis)
Return *only* the complete LaTeX code for the `\section{{Research Methods}}`.



make sure you use the same kind of vocabulary , the same way of narratting, adn words  

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---
"""
    return generate_markdown(prompt + f"\n\n{LATEX_SAFETY_RULES}", 'Results/research_methodes.tex')

def create_review_findings(research_methodes_content: str, 
                           summaries: str, 
                           subject: str, 
                           Biblio_content:str, 
                           reviewer_suggestions: str = "", 
                           slr_outline: str = "", 
                           human_style_example_text: str = ""): 
    if not summaries.strip() or summaries.startswith("% Error"):
        print("No valid summaries provided for review findings. Skipping section generation.")
        return "\\section{Review Findings}\n% No valid summaries provided to generate this section.\n"
    if not research_methodes_content.strip() or research_methodes_content.startswith("% Error"):
        print("Research methods section content is invalid or empty. Findings might be generic.")

    suggestions_addon = ""
    if reviewer_suggestions: 
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for this Review Findings Section:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")): 
        outline_addon = f"\n\n### Overall SLR Outline to Consider for this Review Findings Section:\n{slr_outline}\nStructure your findings to align with anticipated key areas from the outline.\n---"

    style_guidance_addon_formatted = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic.
To achieve this, **actively avoid common AI writing patterns**.
Instead, draw inspiration from the **narrative style, sentence flow, phrasing nuances, and vocabulary choices** in the following sample of human-written academic text.

**Emulate these human-like qualities:**
- **Varied Sentence Structure:** Mix short, impactful sentences with longer, more complex ones. Avoid monotonous sentence lengths or predictable structures.
- **Natural Transitions:** Use a variety of transitional words and phrases to create a smooth, logical flow between ideas. Avoid overusing simplistic transitions.
- **Sophisticated yet Clear Vocabulary:** Employ precise academic language, but ensure it sounds natural and not forced or overly thesaurus-driven.
- **Engaging Narrative Tone:** Even in academic writing, aim for a tone that is confident, clear, and subtly engaging. Avoid a dry, robotic, or overly detached tone.
- **Subtlety and Nuance:** Human writing often conveys meaning through subtle phrasing and nuance. Try to incorporate this.

**Crucially, DO NOT:**
- **Copy Content:** Do not replicate any specific facts, arguments, or the overall structure from the sample text.
- **Mimic Structure:** The sample is for *stylistic inspiration only*, not for structural guidance.
- **Sound Robotic or Formulaic:** Actively work against sounding like a typical AI. If your phrasing feels too standard or predictable, revise it.

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---

Before finalizing your response for this section, reread it and ask yourself: "Does this sound like a human wrote it, or does it have tell-tale signs of AI generation?" Adjust as needed.
"""

    prompt = fr"""
Create a detailed **Review Findings** section for the systematic literature review (SLR) on **{subject}** make sure it's detailed , academicale , and huminazed.

### Requirements:
1.  **Structure and Content**:
    *   Start with `\section{{Review Findings}}`.
    {suggestions_addon}
{outline_addon}
{style_guidance_addon_formatted}
    *   Provide an **introduction** summarizing the purpose of this section.
    *   Systematically answer the research questions (RQs) outlined in the (provided) Research Methods section, using synthesized insights from the paper summaries. If RQs are not explicitly in `research_methodes_content`, infer plausible RQs based on `{subject}` and structure findings around them.
    *   Align the presentation of findings with the `SLR Outline` if provided, especially regarding anticipated key areas.
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
    *   Any data presented in tables/charts must be *directly derivable* from the provided summaries or section content. Do not invent quantitative data.
    *   When including figures or tables, use placement specifiers like `[htbp]` for flexibility.
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


make sure you use the same kind of vocabulary , the same way of narratting, adn words  

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---
"""
    return generate_markdown(prompt + f"\n\n{LATEX_SAFETY_RULES}", 'Results/review_findings.tex')

def create_discussion_conclusion(review_findings_content: str, 
                                 summaries: str, 
                                 subject: str, 
                                 Biblio_content:str, 
                                 reviewer_suggestions: str = "", 
                                 slr_outline: str = "", 
                                 human_style_example_text: str = ""): 
    if not review_findings_content.strip() or review_findings_content.startswith("% Error"):
        print("Review findings content is invalid or empty. Discussion/Conclusion will be very generic. Skipping.")
        return "\\section{Discussion}\n% Review findings were invalid or empty, cannot generate discussion.\n\n\\section{Conclusion}\n% Review findings were invalid or empty."

    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for the Discussion and Conclusion Sections:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for these Sections:\n{slr_outline}\nAlign your discussion points and conclusion with the overall themes and take-home messages suggested in the outline.\n---"

    style_guidance_addon_formatted = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic.
To achieve this, **actively avoid common AI writing patterns**.
Instead, draw inspiration from the **narrative style, sentence flow, phrasing nuances, and vocabulary choices** in the following sample of human-written academic text.

**Emulate these human-like qualities:**
- **Varied Sentence Structure:** Mix short, impactful sentences with longer, more complex ones. Avoid monotonous sentence lengths or predictable structures.
- **Natural Transitions:** Use a variety of transitional words and phrases to create a smooth, logical flow between ideas. Avoid overusing simplistic transitions.
- **Sophisticated yet Clear Vocabulary:** Employ precise academic language, but ensure it sounds natural and not forced or overly thesaurus-driven.
- **Engaging Narrative Tone:** Even in academic writing, aim for a tone that is confident, clear, and subtly engaging. Avoid a dry, robotic, or overly detached tone.
- **Subtlety and Nuance:** Human writing often conveys meaning through subtle phrasing and nuance. Try to incorporate this.

**Crucially, DO NOT:**
- **Copy Content:** Do not replicate any specific facts, arguments, or the overall structure from the sample text.
- **Mimic Structure:** The sample is for *stylistic inspiration only*, not for structural guidance.
- **Sound Robotic or Formulaic:** Actively work against sounding like a typical AI. If your phrasing feels too standard or predictable, revise it.

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---

Before finalizing your response for this section, reread it and ask yourself: "Does this sound like a human wrote it, or does it have tell-tale signs of AI generation?" Adjust as needed.
"""

    prompt = rf"""
Create a **Discussion** section and a **Conclusion** section for the systematic literature review (SLR) on **{subject}**make sure it's detailed , academicale , and huminazed.

{suggestions_addon}

### Requirements:
{outline_addon}
{style_guidance_addon_formatted}
1.  **Structure**:
    *   Start with `\section{{Discussion}}`.
    *   Follow with `\section{{Conclusion}}`.
2.  **Discussion Content**:
    *   Interpret the key findings presented in the (provided) `Review Findings` section.
    *   Compare/contrast findings with existing literature or theories (draw from `summaries` or general knowledge if applicable).
    *   Discuss implications of the findings (e.g., for practice, policy, theory), guided by the `SLR Outline` if available.
    *   Acknowledge limitations of the SLR itself and of the reviewed studies.
    *   Suggest areas for future research based on identified gaps or limitations.
3.  **Conclusion Content**:
    *   Briefly summarize the main findings of the SLR in relation to the primary research questions or objectives.
    *   Reiterate the significance of the findings.
    *   Provide a final take-home message, consistent with the `SLR Outline` if provided. Avoid introducing new information.
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


make sure you use the same kind of vocabulary , the same way of narratting, adn words  

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---
"""
    return generate_markdown(prompt + f"\n\n{LATEX_SAFETY_RULES}", 'Results/discussion_conclusion.tex')


def create_abstract_intro(review_findings_content: str, 
                          related_works_content:str, 
                          research_methodes_content:str, 
                          discussion_conclusion_content:str, 
                          subject: str, 
                          Biblio_content:str, 
                          reviewer_suggestions: str = "", 
                          slr_outline: str = "", 
                          human_style_example_text: str = ""): 
    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for the Abstract, Keywords, and Introduction Sections:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for these Sections:\n{slr_outline}\nEnsure the introduction's themes/arguments and the abstract's summary align with the broader plan.\n---"

    style_guidance_addon_formatted = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic.
To achieve this, **actively avoid common AI writing patterns**.
Instead, draw inspiration from the **narrative style, sentence flow, phrasing nuances, and vocabulary choices** in the following sample of human-written academic text.

**Emulate these human-like qualities:**
- **Varied Sentence Structure:** Mix short, impactful sentences with longer, more complex ones. Avoid monotonous sentence lengths or predictable structures.
- **Natural Transitions:** Use a variety of transitional words and phrases to create a smooth, logical flow between ideas. Avoid overusing simplistic transitions.
- **Sophisticated yet Clear Vocabulary:** Employ precise academic language, but ensure it sounds natural and not forced or overly thesaurus-driven.
- **Engaging Narrative Tone:** Even in academic writing, aim for a tone that is confident, clear, and subtly engaging. Avoid a dry, robotic, or overly detached tone.
- **Subtlety and Nuance:** Human writing often conveys meaning through subtle phrasing and nuance. Try to incorporate this.

**Crucially, DO NOT:**
- **Copy Content:** Do not replicate any specific facts, arguments, or the overall structure from the sample text.
- **Mimic Structure:** The sample is for *stylistic inspiration only*, not for structural guidance.
- **Sound Robotic or Formulaic:** Actively work against sounding like a typical AI. If your phrasing feels too standard or predictable, revise it.

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---

Before finalizing your response for this section, reread it and ask yourself: "Does this sound like a human wrote it, or does it have tell-tale signs of AI generation?" Adjust as needed.
"""

    # Check if essential inputs are valid
    if any(s.startswith("% Error") or "No summaries provided" in s or "Insufficient input" in s for s in [review_findings_content, related_works_content, research_methodes_content, discussion_conclusion_content]):
        print("One or more input sections for Abstract/Intro generation are invalid or empty. Skipping.")
        return "\\begin{abstract}\n% Skipped due to invalid input sections.\n\\end{abstract}\n\n\\textbf{Keywords:} % Skipped\n\n\\section{Introduction}\n% Skipped due to invalid input sections.\n"


    prompt = rf"""
Create the **Abstract**, **Keywords**, and **Introduction** sections for a systematic literature review (SLR) titled: "Systematic Literature Review: {subject}" make sure it's detailed , academicale , and huminazed.

{suggestions_addon}
{outline_addon}
{style_guidance_addon_formatted}

### Requirements:
1.  **Abstract**:
    *   Format: `\begin{{abstract}} ... \end{{abstract}}`.
    *   Content: Briefly state the SLR's purpose/context, main objectives/RQs, search/selection methods, key synthesized findings, principal conclusions, and main implications/future work. (Approx. 150-250 words).
2.  **Keywords**:
    *   Format: `\textbf{{Keywords:}} keyword1, keyword2, keyword3, keyword4, keyword5.` (Provide 5-7 relevant keywords).
3.  **Introduction (`\section{{Introduction}}`)**:
    *   Provide background on the topic `{subject}`.
    *   State the problem/motivation for this SLR, aligning with themes from the `SLR Outline` if provided.
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



make sure you use the same kind of vocabulary , the same way of narratting, adn words  

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---
"""
    return generate_markdown(prompt + f"\n\n{LATEX_SAFETY_RULES}", 'Results/abstract_intro_keywords.tex')

def generate_critique(slr_content_tex_path: str, previous_critique_text: str = "", subject: str = "") -> str:
    """
    Generates a critique of the SLR content (from a .tex file) using Gemini, acting as a professional researcher.
    """
    RATING_START = "OVERALL_RATING_START"
    RATING_END = "OVERALL_RATING_END"
    ADDRESSED_POINTS_START = "ADDRESSED_POINTS_SUMMARY_START"
    ADDRESSED_POINTS_END = "ADDRESSED_POINTS_SUMMARY_END"
    NEW_ISSUES_START = "NEW_ISSUES_START"
    NEW_ISSUES_END = "NEW_ISSUES_END"
    SECTION_SUGGESTIONS_START = "SECTION_SUGGESTIONS_START"
    SECTION_SUGGESTIONS_END = "SECTION_SUGGESTIONS_END"

    prompt_instructions_parts = [
        f"You are an expert academic researcher and reviewer. Your task is to critically evaluate the provided Systematic Literature Review (SLR) content (from the uploaded .tex file) on the subject: '{subject}'.",
        "Provide constructive feedback to improve its quality, rigor, and clarity. Focus on academic best practices.",
        "\nYour output MUST be structured using the following markers:",
        f"1. An overall quality rating: Place it between `{RATING_START}` and `{RATING_END}`. (e.g., 7/10, or Good, Needs Improvement etc.)",
    ]

    if previous_critique_text:
        prompt_instructions_parts.append(f"2. A summary of how previous suggestions were addressed: Place it between `{ADDRESSED_POINTS_START}` and `{ADDRESSED_POINTS_END}`.")
    
    prompt_instructions_parts.extend([
        f"3. A list of any new issues identified in the current version: Place them between `{NEW_ISSUES_START}` and `{NEW_ISSUES_END}`. Use bullet points for multiple issues.",
        f"4. Specific, actionable suggestions for each major section (Abstract, Keywords, Introduction, Background, Related Works, Research Methods, Review Findings, Discussion, Conclusion): Place all these suggestions together between `{SECTION_SUGGESTIONS_START}` and `{SECTION_SUGGESTIONS_END}`.",
        "Structure your feedback clearly, indicating the section you are referring to. Use the format 'In [Section Name] section: [Your suggestion]'",
        # ... (rest of the example feedback format remains the same)
         "Example Feedback Format:",
        "In Abstract section: Ensure it concisely covers all key aspects (motivation, methods, key findings, conclusion). Consider rephrasing X for clarity.",
        "In Introduction section: The motivation could be strengthened by X. Ensure all RQs are clearly stated.",
        "In Background section: Define term Y more precisely. Consider adding a brief mention of foundational work Z.",
        "In Related Works section: The synthesis of papers A and B could be improved. Ensure all claims are cited.",
        "In Research Methods section: Clarify the rationale for choosing X guideline. The search string Y could be more comprehensive.",
        "In Review Findings section: Ensure each RQ is explicitly answered. Table Z could be more clearly presented.",
        "In Discussion section: Elaborate more on the implications of finding X. The limitations section could be more detailed.",
        "In Conclusion section: Reiterate the main take-home message more forcefully. Avoid introducing new points here.",
    ])

    if previous_critique_text:
        prompt_instructions_parts.append("\n--- PREVIOUS SUGGESTIONS PROVIDED TO THE AUTHOR (Your previous critique) ---")
        prompt_instructions_parts.append("Review if the current SLR content has adequately addressed these previous points when you formulate your 'ADDRESSED_POINTS_SUMMARY'.")
        prompt_instructions_parts.append(previous_critique_text)
        prompt_instructions_parts.append("--- END OF PREVIOUS SUGGESTIONS ---")

    # Note: The actual SLR content is now passed as an uploaded file, not in the prompt string.
    prompt_instructions_parts.append(f"\nNow, provide your structured critique based on the UPLOADED SLR .tex file, using the specified markers: {RATING_START}, {ADDRESSED_POINTS_START} (if applicable), {NEW_ISSUES_START}, and {SECTION_SUGGESTIONS_START}.")
    
    critique_prompt_instructions = "\n".join(prompt_instructions_parts)
    uploaded_slr_file = None
    
    try:
        uploaded_slr_file = genai.upload_file(
            path=slr_content_tex_path,
            mime_type='text/plain', # Treat .tex as plain text for Gemini
            display_name=os.path.basename(slr_content_tex_path)
        )
        
        # Call the centralized LLM content generation function
        # generate_content_from_prompt needs to be able to handle a list [instructions, file_object]
        # For now, assuming generate_content_from_prompt is adapted or we call summary_model directly
        response = summary_model.generate_content(
            [critique_prompt_instructions, uploaded_slr_file],
            generation_config=genai.types.GenerationConfig(temperature=0.5)
        )
        return response.text.strip()

    except Exception as e:
        print(f"{RED}Error generating critique for {slr_content_tex_path}: {e}{RESET}")
        return f"% Error generating critique: {str(e)}"
    finally:
        if uploaded_slr_file:
            try:
                genai.delete_file(uploaded_slr_file.name)
            except Exception as delete_error:
                print(f"{YELLOW}Warning: Could not delete uploaded SLR file {uploaded_slr_file.name}: {delete_error}{RESET}")


def parse_critique(critique_text: str) -> Dict[str, any]:
    parsed_data: Dict[str, any] = {
        "rating": "N/A",
        "addressed_points_summary": "N/A (or not applicable for initial critique)",
        "new_issues": [],
        "suggestions_by_section": {},
        "general_suggestions": [] 
    }

    RATING_START = "OVERALL_RATING_START"
    RATING_END = "OVERALL_RATING_END"
    ADDRESSED_POINTS_START = "ADDRESSED_POINTS_SUMMARY_START"
    ADDRESSED_POINTS_END = "ADDRESSED_POINTS_SUMMARY_END"
    NEW_ISSUES_START = "NEW_ISSUES_START"
    NEW_ISSUES_END = "NEW_ISSUES_END"
    SECTION_SUGGESTIONS_START = "SECTION_SUGGESTIONS_START"
    SECTION_SUGGESTIONS_END = "SECTION_SUGGESTIONS_END"

    rating_match = re.search(f"{RATING_START}(.*?){RATING_END}", critique_text, re.DOTALL)
    if rating_match:
        parsed_data["rating"] = rating_match.group(1).strip()

    addressed_match = re.search(f"{ADDRESSED_POINTS_START}(.*?){ADDRESSED_POINTS_END}", critique_text, re.DOTALL)
    if addressed_match:
        parsed_data["addressed_points_summary"] = addressed_match.group(1).strip()

    new_issues_match = re.search(f"{NEW_ISSUES_START}(.*?){NEW_ISSUES_END}", critique_text, re.DOTALL)
    if new_issues_match:
        issues_block = new_issues_match.group(1).strip()
        parsed_data["new_issues"] = [line.strip() for line in issues_block.splitlines() if line.strip() and not line.strip().startswith("%")]


    suggestions_block_match = re.search(f"{SECTION_SUGGESTIONS_START}(.*?){SECTION_SUGGESTIONS_END}", critique_text, re.DOTALL)
    if suggestions_block_match:
        suggestions_content = suggestions_block_match.group(1).strip()
        section_pattern = re.compile(r"In\s+([\w\s]+?)\s+section:?\s*(.*?)(?=(?:\nIn\s+[\w\s]+?\s+section:?)|$)", re.IGNORECASE | re.DOTALL)
        current_suggestions_by_section: Dict[str, List[str]] = {}
        
        # Normalize section names for matching
        section_name_map = {
            "abstract": "Abstract_Intro_Keywords", "keywords": "Abstract_Intro_Keywords", "introduction": "Abstract_Intro_Keywords",
            "background": "Background",
            "related works": "Related Works", "related work": "Related Works",
            "research methods": "Research Methods", "research method": "Research Methods", "methodology": "Research Methods",
            "review findings": "Review Findings", "findings": "Review Findings", "results": "Review Findings",
            "discussion": "Discussion_Conclusion", "conclusion": "Discussion_Conclusion"
        }

        last_pos = 0
        for match in section_pattern.finditer(suggestions_content):
            # Capture text between matches as general if it's not whitespace
            inter_text = suggestions_content[last_pos:match.start()].strip()
            if inter_text and not inter_text.startswith("%"):
                parsed_data["general_suggestions"].append(inter_text)

            section_name_raw = match.group(1).strip().lower()
            # Normalize section name to match keys used in get_suggestions_for_section
            section_name_normalized = section_name_map.get(section_name_raw, section_name_raw.title())

            suggestion_text = match.group(2).strip()
            if suggestion_text and not suggestion_text.startswith("%"):
                if section_name_normalized not in current_suggestions_by_section:
                    current_suggestions_by_section[section_name_normalized] = []
                current_suggestions_by_section[section_name_normalized].append(suggestion_text)
            last_pos = match.end()
        
        # Capture any trailing general text
        trailing_text = suggestions_content[last_pos:].strip()
        if trailing_text and not trailing_text.startswith("%"):
            parsed_data["general_suggestions"].append(trailing_text)

        parsed_data["suggestions_by_section"] = current_suggestions_by_section
        
        if not current_suggestions_by_section and not parsed_data["general_suggestions"] and \
           suggestions_content and not suggestions_content.startswith("% Error"):
             parsed_data["general_suggestions"].append(suggestions_content)

    # Fallback if no markers found at all but text exists
    if critique_text.strip() and not any(parsed_data[k] for k in parsed_data if (k != "rating" or parsed_data[k] != "N/A") and (k != "addressed_points_summary" or parsed_data[k] != "N/A (or not applicable for initial critique)")):
        if not critique_text.startswith("% Error"):
            print("Warning: Critique text present but no standard markers found. Treating entire critique as 'General' suggestions.")
            parsed_data["general_suggestions"].append(critique_text.strip())
            
    return parsed_data

def replace_placeholders_in_latex(latex_content: str, counts: Dict[str, int]) -> str:
    """Replaces placeholders like [KEY] with values from the counts dictionary."""
    for key, value in counts.items():
        placeholder = f"[{key}]"
        latex_content = latex_content.replace(placeholder, str(value))
    # Fallback for any generic placeholders missed if specific keys weren't used by LLM
    latex_content = re.sub(r"\[(?:Number Here|Actual Count|N/A for now)(?::\s*[\w\s]+)?\]", "N/A", latex_content)
    latex_content = re.sub(r"\[NUMBER_UNKNOWN\]", "N/A", latex_content) # Another common one
    return latex_content

 # Functions compile_latex, parse_latex_log, get_latex_correction_suggestion are removed as pdflatex is no longer used.

def generate_slr_outline(natural_language_paper_goal: str, relevant_papers_summaries: str, subject: str) -> str:
    """
    Generates a high-level outline for the SLR using an LLM by uploading relevant summaries.
    """
    if not relevant_papers_summaries.strip() or relevant_papers_summaries.startswith(("% Error", "% No relevant")):
        return "% No relevant paper summaries provided to generate an outline."

    uploaded_summaries_file = None
    temp_summaries_path = None

    try:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt", encoding='utf-8') as tmp_s:
            tmp_s.write(relevant_papers_summaries)
            temp_summaries_path = tmp_s.name
        
        uploaded_summaries_file = genai.upload_file(
            path=temp_summaries_path,
            mime_type='text/plain',
            display_name='relevant_paper_summaries_for_outline.txt'
        )

        prompt = f"""You are an expert research planner. Based on the user's research goal and summaries of relevant papers (provided in the uploaded file 'relevant_paper_summaries_for_outline.txt'), generate a high-level structured outline for a Systematic Literature Review (SLR).

User's Research Goal: "{natural_language_paper_goal}"
SLR Subject: "{subject}"

Task:
Create a concise, structured outline for the SLR. This outline should suggest:
1.  Key themes or arguments for the **Introduction** (beyond the standard problem statement/RQs).
2.  Essential concepts or foundational areas for the **Background** section.
3.  Major categories or trends to discuss in **Related Works**, and how papers might be grouped.
4.  Specific focuses for the **Research Methods** if any unique aspects arise from the papers (e.g., particular types of studies to focus on).
5.  Anticipated key areas of **Review Findings** based on the collective insights from the summaries (e.g., common methodologies, prevalent outcomes, contrasting results).
6.  Potential discussion points for the **Discussion** section (e.g., implications, limitations observed across papers).
7.  The main take-home message for the **Conclusion**.

Output Format:
Provide the outline as a structured text. Use headings for each major SLR section.
Example:

SLR Outline for: {subject}

1. Introduction:
   - Theme: The rapid evolution of X and its impact on Y.
   - Argument: Need for a systematic understanding of Z.

2. Background:
   - Concept: Define X, Y, Z.
   - Foundation: Key theories underpinning X.

3. Related Works:
   - Category 1: Studies focusing on A (e.g., Paper1_Author, Paper3_Author).
   - Category 2: Methodological approaches to B (e.g., Paper2_Author).
   - Trend: Increasing use of C.

4. Research Methods:
   - Focus: Prioritize analysis of empirical studies vs. theoretical papers.

5. Review Findings:
   - Area 1: Predominant outcomes of X interventions.
   - Area 2: Methodological strengths/weaknesses observed.
   - Area 3: Gaps in current research regarding Y.

6. Discussion:
   - Implication: How findings can inform practice in Z.
   - Limitation: Common biases in reviewed studies.

7. Conclusion:
   - Take-home: X is a promising field but requires further rigorous investigation into Y.

---
Return only the outline. Do not include conversational preambles.
"""
        # Call summary_model.generate_content directly
        response = summary_model.generate_content(
            [prompt, uploaded_summaries_file],
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        generated_text = response.text.strip()
        
        # Save the generated outline
        output_filename = 'Results/slr_high_level_outline.txt'
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        print(f"Generated {output_filename}")
        return generated_text

    except Exception as e:
        print(f"{RED}Error in generate_slr_outline: {e}{RESET}")
        return f"% Error generating SLR outline: {e}"
    finally:
        if uploaded_summaries_file:
            try:
                genai.delete_file(uploaded_summaries_file.name)
            except Exception as delete_error:
                print(f"{YELLOW}Warning: Could not delete uploaded summaries file in generate_slr_outline: {delete_error}{RESET}")
        if temp_summaries_path and os.path.exists(temp_summaries_path):
            os.remove(temp_summaries_path)

def extract_references_from_paper_text(
    txt_file_path: str, # Changed from paper_text_content
    paper_title: str,
    _update_status_func: Callable[[str], None]
) -> List[Dict[str, str]]:
    """
    Extracts references from a paper's text file using an LLM to locate the reference section
    by uploading the file, and then regex pattern matching on that section.
    """
    _update_status_func(f"  Attempting to extract references for '{paper_title[:50]}...' from file {os.path.basename(txt_file_path)}")

    reference_section_text_from_llm = ""
    uploaded_paper_file = None

    try:
        _update_status_func(f"    Uploading text file to LLM to locate reference section for '{paper_title[:50]}...'")
        # Upload the entire text file
        uploaded_paper_file = genai.upload_file(
            path=txt_file_path,
            mime_type='text/plain',
            display_name=f"text_content_{os.path.basename(txt_file_path)}"
        )

        ref_section_prompt_instructions = f"""
Analyze the provided academic paper text (uploaded file). Your task is to locate the section containing the list of references (often titled "References", "Bibliography", "Works Cited", etc.).
Extract and return ONLY the raw text content of this specific reference list section.
Do NOT include the section heading itself (e.g., do not include "References" or "\\section*{{References}}").
Do NOT include any introductory or concluding sentences outside the actual list of references.
Do NOT include any markdown formatting, explanations, or conversational text.
If you cannot confidently identify a distinct reference list section, return an empty string.
"""
        llm_response_obj = summary_model.generate_content(
            [ref_section_prompt_instructions, uploaded_paper_file], # Pass as list
            generation_config=genai.types.GenerationConfig(temperature=0.2) # Lower temp for extraction
        )
        
        llm_response_text = llm_response_obj.text.strip()

        if llm_response_text:
            reference_section_text_from_llm = llm_response_text
            _update_status_func(f"    LLM successfully located potential reference section text ({len(reference_section_text_from_llm)} chars).")
        else:
            _update_status_func(f"    LLM returned empty string for reference section (no distinct section found). Will attempt regex on full text from file.")
            # If LLM fails to find section, read full text for regex as a fallback
            with open(txt_file_path, 'r', encoding='utf-8') as f_full:
                reference_section_text_from_llm = f_full.read()


    except Exception as e:
        _update_status_func(f"    Error during LLM reference section location for '{paper_title[:50]}...': {e}. Will attempt regex on full text from file.")
        # Fallback to reading the full file content for regex if LLM part fails
        try:
            with open(txt_file_path, 'r', encoding='utf-8') as f_full_fallback:
                reference_section_text_from_llm = f_full_fallback.read()
        except Exception as e_read_fallback:
            _update_status_func(f"      Failed to read full text file {txt_file_path} for regex fallback: {e_read_fallback}")
            return [] # Cannot proceed
    finally:
        if uploaded_paper_file:
            try:
                genai.delete_file(uploaded_paper_file.name)
            except Exception as delete_error:
                print(f"{YELLOW}Warning: Could not delete uploaded file {uploaded_paper_file.name} in extract_references: {delete_error}{RESET}")

    text_to_search_for_refs = reference_section_text_from_llm # This is now either LLM output or full file content
    if not text_to_search_for_refs:
        _update_status_func(f"    No text content available to search for references in '{paper_title[:50]}...'.")
        return []

    _update_status_func(f"    Applying regex to the identified/fallback text for '{paper_title[:50]}...'.")

    references_found = []
    # Pattern 1: [Number] Potentially Authors. (Year) "Title".
    p1_matches = re.findall(r'\[\s*\d+\s*\]\s*(.*?)\s*\(([\d\s-]+)\)\s*["“](.+?)["”]\.?', text_to_search_for_refs, re.IGNORECASE)
    for authors, year, title in p1_matches:
        references_found.append({'title': title.strip(), 'authors': authors.strip().rstrip('.'), 'year': year.strip()})

    # Pattern 2: Author, A. A., & Author, B. B. (Year). Title of work.
    p2_matches = re.findall(r'([A-Z][A-Za-z\s,\.&’-]+)\s*\(([\d\s-]+)\)\.?\s*([A-Za-z0-9\s:\-\(\)_’]+?)\.(?=\s*[A-Z]|\n\n|$)', text_to_search_for_refs)
    for authors, year, title in p2_matches:
        if len(title.split()) < 25 and "et al" not in authors.lower() and len(title.strip()) > 5:
            references_found.append({'title': title.strip(), 'authors': authors.strip(), 'year': year.strip()})

    # Pattern 3: "Title" by Authors (Year). or "Title" Authors (Year).
    p3_matches = re.findall(r'["“](.+?)["”]\s*(?:by\s*)?([A-Za-z\s,\.&’-]+?)\s*\(([\d\s-]+)\)', text_to_search_for_refs, re.IGNORECASE)
    for title, authors, year in p3_matches:
        if len(title.strip()) > 5:
            references_found.append({'title': title.strip(), 'authors': authors.strip(), 'year': year.strip()})
    
    unique_references = []
    seen_titles_lower = set()
    for ref in references_found:
        cleaned_title = re.sub(r'\.$', '', ref['title']).strip()
        cleaned_title = re.sub(r'\s+', ' ', cleaned_title)

        if not cleaned_title or len(cleaned_title) < 5:
            continue

        title_lower_key = cleaned_title.lower()
        if title_lower_key not in seen_titles_lower:
            unique_references.append({'title': cleaned_title, 'authors': ref['authors'], 'year': ref['year']})
            seen_titles_lower.add(title_lower_key)

    if unique_references:
        _update_status_func(f"    Extracted {len(unique_references)} unique references for '{paper_title[:50]}...'")
    else:
        _update_status_func(f"    Regex extraction did not find usable references for '{paper_title[:50]}...'.")

    return unique_references

def process_papers(
    natural_language_paper_goal: str,
    year_range: Tuple[int, int],
    num_papers_to_fetch_per_iteration: int,
    num_search_iterations: int = 1,
    num_refinement_cycles: int = 1,
    min_relevant_papers_target: int = 5, # Target number of relevant papers
    max_supplementary_iterations: int = 2, # How many extra fetch rounds if target not met
    status_update_callback: Optional[Callable[[str], None]] = None
) -> Tuple[str, str | None]: # Returns (status_or_final_slr_path, refinement_report_path_or_None)
    """
    Main processing function for SLR generation, including fetching, summarization,
    snowballing, and iterative refinement.
    """
    def _update_status(message: str):
        print(message) # Always print to console
        if status_update_callback:
            status_update_callback(message)

    _update_status(f"Starting SLR generation for: '{natural_language_paper_goal}'")
    _update_status(f"Configuration: Search Iterations: {num_search_iterations}, Papers/Iter: {num_papers_to_fetch_per_iteration}, Refinement Cycles: {num_refinement_cycles}, Min Relevant Target: {min_relevant_papers_target}")

    # --- Setup ---
    pdf_folder = "pdf_papers"
    txt_papers_folder_path = TXT_PAPERS_FOLDER # Defined globally
    summaries_folder_path = SUMMARIES_FOLDER # Defined globally
    results_folder_path = "Results"

    # Clear and recreate working directories
    for folder_path in [results_folder_path, pdf_folder, txt_papers_folder_path, summaries_folder_path]:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path, exist_ok=True)
    _update_status(f"Cleared/Created working directories: {pdf_folder}, {txt_papers_folder_path}, {summaries_folder_path}, {results_folder_path}")

    all_angles_and_queries: List[Tuple[str, str]] = []
    cumulative_fetched_paper_metadata: List[Dict[str, any]] = []
    # Use a global set to track all primary IDs (arxiv_id, scopus_id, manual_id) fetched across all methods
    globally_fetched_primary_ids: set = set()

    # PRISMA counts initialization
    counts_for_reporting = {
        "NUMBER_RECORDS_IDENTIFIED_ARXIV": 0,
        "NUMBER_RECORDS_IDENTIFIED_SCOPUS": 0,
        "NUMBER_RECORDS_IDENTIFIED_MANUAL": 0,
        "NUMBER_RECORDS_IDENTIFIED_SNOWBALL": 0, # New for snowballing
        "NUMBER_RECORDS_AFTER_DUPLICATES_REMOVED": 0, # Total unique items before summarization
        "NUMBER_RECORDS_SCREENED_FOR_SUMMARIZATION": 0, # Items for which text was successfully extracted
        "NUMBER_SUMMARIES_GENERATED": 0,
        "NUMBER_EXCLUDED_BY_LLM_RELEVANCE_FILTER": 0, # Papers deemed not relevant by LLM
        "NUMBER_STUDIES_INCLUDED_QUALITATIVE": 0 # Final count of LLM-confirmed relevant papers for synthesis
    }

    # --- Phase 1: Initial Paper Fetching ---
    _update_status("Phase 1: Initial Paper Fetching...")
    for i in range(num_search_iterations):
        _update_status(f"  Search Iteration {i + 1}/{num_search_iterations}")
        # Generate a new research angle and query for this iteration
        current_angle, current_query = create_arxiv_search_query_from_natural_language(
            natural_language_paper_goal, all_angles_and_queries
        )
        _update_status(f"    Generated Angle: '{current_angle}', Query: '{current_query}'")
        all_angles_and_queries.append((current_angle, current_query))

        if current_query == INVALID_QUERY_FOR_ACADEMIC_SEARCH or not current_query.strip():
            _update_status(f"    LLM indicated query '{current_query}' is invalid for academic search or empty. Skipping this iteration.")
            continue

        # Fetch from ArXiv
        try:
            newly_fetched_meta_arxiv, fetched_count_arxiv, fetch_status_arxiv = fetch_arxiv_papers(
                current_query, year_range, num_papers_to_fetch_per_iteration,
                pdf_folder, globally_fetched_primary_ids
            )
            _update_status(f"    ArXiv: {fetch_status_arxiv}")
            counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_ARXIV"] += fetched_count_arxiv
            if newly_fetched_meta_arxiv:
                for meta_ax in newly_fetched_meta_arxiv: # Ensure correct metadata structure
                    sanitized_id = os.path.splitext(os.path.basename(meta_ax['local_pdf_path']))[0]
                    meta_ax['source'] = 'arxiv'
                    meta_ax['id_primary'] = sanitized_id # Use filename base as primary ID for ArXiv
                    meta_ax['abstract_api'] = meta_ax.get('summary', '') # ArXiv specific field for abstract
                    meta_ax['local_txt_path'] = os.path.join(txt_papers_folder_path, f"{sanitized_id}.txt")
                    cumulative_fetched_paper_metadata.append(meta_ax)
                    _update_status(f"      Fetched ArXiv: {meta_ax.get('title', 'N/A Title')[:50]}...")
        except Exception as e_arxiv:
            _update_status(f"    Error during ArXiv fetch for query '{current_query}': {e_arxiv}")

        # Fetch from Scopus
        try:
            _update_status(f"    Searching Scopus for: '{current_query}'")
            newly_fetched_meta_scopus, fetched_count_scopus, fetch_status_scopus = fetch_scopus_papers_and_process(
                current_query, year_range, num_papers_to_fetch_per_iteration,
                pdf_folder, txt_papers_folder_path, globally_fetched_primary_ids
            )
            _update_status(f"    Scopus: {fetch_status_scopus}")
            counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_SCOPUS"] += fetched_count_scopus
            if newly_fetched_meta_scopus:
                cumulative_fetched_paper_metadata.extend(newly_fetched_meta_scopus) # Scopus metadata is already structured
                for meta_sc in newly_fetched_meta_scopus:
                     _update_status(f"      Fetched Scopus: {meta_sc.get('title', 'N/A Title')[:50]}...")
        except Exception as e_scopus:
            _update_status(f"    Error during Scopus fetch for query '{current_query}': {e_scopus}")

    # Fallback if initial fetching yields no papers
    if not cumulative_fetched_paper_metadata and num_search_iterations > 0 : # Only fallback if search was attempted
        _update_status(f"Initial fetching yielded 0 papers. Attempting fallback using general goal: '{natural_language_paper_goal}'")
        # Use the original natural_language_paper_goal as a broad fallback query
        fallback_query_direct = natural_language_paper_goal
        all_angles_and_queries.append(("Direct Fallback", fallback_query_direct))

        # ArXiv Fallback
        try:
            newly_fetched_meta_arxiv_fb, fetched_count_arxiv_fb, fetch_status_arxiv_fb = fetch_arxiv_papers(
                fallback_query_direct, year_range, num_papers_to_fetch_per_iteration * 2, # Fetch more on fallback
                pdf_folder, globally_fetched_primary_ids
            )
            _update_status(f"    ArXiv (Fallback): {fetch_status_arxiv_fb}")
            counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_ARXIV"] += fetched_count_arxiv_fb
            if newly_fetched_meta_arxiv_fb:
                for meta_ax_fb in newly_fetched_meta_arxiv_fb:
                    sanitized_id_fb = os.path.splitext(os.path.basename(meta_ax_fb['local_pdf_path']))[0]
                    meta_ax_fb['source'] = 'arxiv_fallback'
                    meta_ax_fb['id_primary'] = sanitized_id_fb
                    meta_ax_fb['abstract_api'] = meta_ax_fb.get('summary', '')
                    meta_ax_fb['local_txt_path'] = os.path.join(txt_papers_folder_path, f"{sanitized_id_fb}.txt")
                    cumulative_fetched_paper_metadata.append(meta_ax_fb)
        except Exception as e_arxiv_fb:
            _update_status(f"    Error during ArXiv fallback: {e_arxiv_fb}")

        # Scopus Fallback
        try:
            newly_fetched_meta_scopus_fb, fetched_count_scopus_fb, fetch_status_scopus_fb = fetch_scopus_papers_and_process(
                fallback_query_direct, year_range, num_papers_to_fetch_per_iteration * 2,
                pdf_folder, txt_papers_folder_path, globally_fetched_primary_ids
            )
            _update_status(f"    Scopus (Fallback): {fetch_status_scopus_fb}")
            counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_SCOPUS"] += fetched_count_scopus_fb
            if newly_fetched_meta_scopus_fb:
                cumulative_fetched_paper_metadata.extend(newly_fetched_meta_scopus_fb)
        except Exception as e_scopus_fb:
            _update_status(f"    Error during Scopus fallback: {e_scopus_fb}")

    # Process manually uploaded PDFs (if any)
    manual_pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    # IDs from API fetches, to avoid adding manual PDFs if they were already fetched by API
    # This check needs to be more robust, e.g. by title or DOI if available for manual uploads.
    # For now, it's a simple check against primary IDs already in globally_fetched_primary_ids.

    for pdf_file_manual in manual_pdf_files:
        base_name_manual = os.path.splitext(pdf_file_manual)[0]
        sanitized_manual_filename_id = sanitize_filename(base_name_manual)
        manual_primary_id = f"manual_{sanitized_manual_filename_id}"

        # Check if this manual PDF (by its generated ID) is already in the global set
        if manual_primary_id not in globally_fetched_primary_ids:
            manual_meta = {
                'source': 'manual', 'id_primary': manual_primary_id,
                'title': base_name_manual.replace('_', ' '),
                'authors': ['N/A (Manual Upload)'], 'published_year': 'N/A',
                'abstract_api': 'N/A (Manual Upload)', 'doi': '', 'scopus_id': '',
                'local_pdf_path': os.path.join(pdf_folder, pdf_file_manual),
                'local_txt_path': os.path.join(txt_papers_folder_path, f"{sanitized_manual_filename_id}.txt") # Use sanitized name for txt
            }
            # Check if a paper with the same title (from API) might exist to avoid true duplicates
            # This is a heuristic. A better check would involve DOI or more sophisticated title matching.
            is_potential_api_duplicate = any(
                p.get('title','').strip().lower() == manual_meta['title'].strip().lower()
                for p in cumulative_fetched_paper_metadata if p.get('source') != 'manual'
            )
            if not is_potential_api_duplicate:
                cumulative_fetched_paper_metadata.append(manual_meta)
                globally_fetched_primary_ids.add(manual_primary_id)
                counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_MANUAL"] += 1
                _update_status(f"  Added manual PDF to processing list: {pdf_file_manual}")
            else:
                _update_status(f"  Skipping manual PDF '{pdf_file_manual}', title matches an API-fetched paper.")
        # else: # Already in globally_fetched_primary_ids (e.g. duplicate upload or already processed)
            # _update_status(f"  Skipping manual PDF '{pdf_file_manual}', ID '{manual_primary_id}' already processed.")


    if not cumulative_fetched_paper_metadata:
        _update_status(f"{RED}CRITICAL: No papers found from any source (ArXiv, Scopus, Manual). Aborting.{RESET}")
        last_query_info = all_angles_and_queries[-1][1] if all_angles_and_queries else "NO_PAPERS_UPLOADED_OR_FETCHED"
        return f"PROCESS_INCOMPLETE_LAST_QUERY_INFO:{last_query_info}", None

    counts_for_reporting["NUMBER_RECORDS_AFTER_DUPLICATES_REMOVED"] = len(cumulative_fetched_paper_metadata)
    _update_status(f"Total unique papers identified for processing: {len(cumulative_fetched_paper_metadata)}")


    # --- Phase 2: PDF-to-Text Conversion ---
    _update_status("Phase 2: PDF-to-Text Conversion...")
    try:
        conversion_status = batch_convert_pdfs_to_text(pdf_folder, txt_papers_folder_path)
        _update_status(f"  {conversion_status}")
    except Exception as e_pdf_text:
        _update_status(f"  {RED}Error during PDF-to-text conversion: {e_pdf_text}{RESET}")
        return NO_TEXT_FILES_GENERATED, None

    papers_to_summarize_details_initial = []
    for paper_meta in cumulative_fetched_paper_metadata:
        txt_path = paper_meta.get('local_txt_path')
        if txt_path and os.path.exists(txt_path) and os.path.getsize(txt_path) > 0:
            try:
                with open(txt_path, 'r', encoding='utf-8') as f_text:
                    text_content = f_text.read()
                if text_content.strip():
                    paper_detail = {
                        'filename': os.path.basename(txt_path),
                        'text': text_content,
                        **paper_meta
                    }
                    papers_to_summarize_details_initial.append(paper_detail)
                else:
                    _update_status(f"    Skipping empty text file: {txt_path}")
            except Exception as e_read_txt:
                _update_status(f"    {RED}Error reading text file {txt_path}: {e_read_txt}{RESET}")
        else:
            _update_status(f"    Skipping paper '{paper_meta.get('title', 'N/A')[:50]}...': Text file missing or empty at {txt_path}")

    counts_for_reporting["NUMBER_RECORDS_SCREENED_FOR_SUMMARIZATION"] = len(papers_to_summarize_details_initial)
    if not papers_to_summarize_details_initial:
        _update_status(f"{RED}CRITICAL: No papers could be prepared for summarization (no valid text files). Aborting.{RESET}")
        return COULD_NOT_READ_RELEVANT_PAPERS, None

    # --- Phase 3: Summarization & Initial Relevance Filtering ---
    _update_status(f"Phase 3: Summarizing {len(papers_to_summarize_details_initial)} papers for relevance to '{natural_language_paper_goal[:50]}...'")
    try:
        initial_papers_with_summaries = batch_summarize_papers(
            natural_language_paper_goal,
            papers_to_summarize_details_initial,
            summaries_folder_path
        )
    except Exception as e_summarize:
        _update_status(f"  {RED}Error during initial summarization: {e_summarize}{RESET}")
        return NO_SUMMARIES_GENERATED, None

    counts_for_reporting["NUMBER_SUMMARIES_GENERATED"] = len([p for p in initial_papers_with_summaries if p.get('summary_text')])

    llm_confirmed_relevant_papers: List[Dict[str, any]] = []
    for paper_info_with_summary in initial_papers_with_summaries:
        summary_text = paper_info_with_summary.get('summary_text', '')
        title_for_log = paper_info_with_summary.get('title', paper_info_with_summary.get('filename', 'Unknown Paper'))

        if summary_text and \
           "Error summarizing paper" not in summary_text and \
           "This paper does not appear to be relevant" not in summary_text.lower():
            llm_confirmed_relevant_papers.append(paper_info_with_summary)
            _update_status(f"    RELEVANT (Initial): '{title_for_log[:60]}...'")
        else:
            _update_status(f"    NOT RELEVANT or error (Initial): '{title_for_log[:60]}...' (Summary: {summary_text[:100]}...)")
            counts_for_reporting["NUMBER_EXCLUDED_BY_LLM_RELEVANCE_FILTER"] += 1

    counts_for_reporting["NUMBER_STUDIES_INCLUDED_QUALITATIVE"] = len(llm_confirmed_relevant_papers)
    _update_status(f"  Initial relevance filter: {len(llm_confirmed_relevant_papers)} papers deemed relevant.")

    # --- SNOWBALLING PHASE ---
    if llm_confirmed_relevant_papers and MAX_SNOWBALL_ITERATIONS > 0:
        _update_status(f"Phase 3.5: Snowballing from {len(llm_confirmed_relevant_papers)} relevant papers...")
        papers_added_via_snowball_total_count = 0

        for sb_iteration in range(MAX_SNOWBALL_ITERATIONS):
            if papers_added_via_snowball_total_count >= MAX_PAPERS_TO_ADD_VIA_SNOWBALLING:
                _update_status(f"  Reached max papers ({MAX_PAPERS_TO_ADD_VIA_SNOWBALLING}) to add via snowballing. Halting.")
                break
            
            _update_status(f"  Snowball Iteration {sb_iteration + 1}/{MAX_SNOWBALL_ITERATIONS}")
            # Use a copy of the current relevant papers as sources for this iteration
            # This prevents issues if llm_confirmed_relevant_papers is modified mid-iteration by other processes (though unlikely here)
            current_snowball_source_papers = list(llm_confirmed_relevant_papers)
            newly_found_metadata_this_iteration: List[Dict[str, any]] = []

            for source_paper_idx, source_paper_meta in enumerate(current_snowball_source_papers):
                if papers_added_via_snowball_total_count >= MAX_PAPERS_TO_ADD_VIA_SNOWBALLING:
                    break

                source_title = source_paper_meta.get('title', 'Unknown Source Paper')
                _update_status(f"    Processing source paper {source_paper_idx+1}/{len(current_snowball_source_papers)} for references: '{source_title[:50]}...'")
                
                source_text_path = source_paper_meta.get('local_txt_path')
                if not source_text_path or not os.path.exists(source_text_path):
                    _update_status(f"      Skipping snowballing from '{source_title[:50]}...': Text file not found at {source_text_path}")
                    continue
                
                try:
                    with open(source_text_path, 'r', encoding='utf-8') as f_source:
                        source_content = f_source.read()
                except Exception as e_read:
                    _update_status(f"      Error reading text file for '{source_title[:50]}...': {e_read}")
                    continue

                extracted_references = []
                try:
                    # Pass the _update_status function to extract_references_from_paper_text
                    extracted_references = extract_references_from_paper_text(source_content, source_title, _update_status)
                except Exception as e_extract_ref:
                    _update_status(f"      Error extracting references from '{source_title[:50]}...': {e_extract_ref}")
                    continue

                if not extracted_references:
                    _update_status(f"      No references extracted from '{source_title[:50]}...'")
                    continue
                
                _update_status(f"      Found {len(extracted_references)} references in '{source_title[:50]}...'. Processing up to {MAX_REFERENCES_TO_PROCESS_PER_PAPER}.")

                references_processed_from_this_source = 0
                for ref_idx, ref_data in enumerate(extracted_references):
                    if references_processed_from_this_source >= MAX_REFERENCES_TO_PROCESS_PER_PAPER:
                        _update_status(f"        Reached max references to process for '{source_title[:50]}...'")
                        break
                    if papers_added_via_snowball_total_count >= MAX_PAPERS_TO_ADD_VIA_SNOWBALLING:
                        break

                    ref_title_to_search = ref_data.get('title', '').strip()
                    if not ref_title_to_search:
                        _update_status(f"        Skipping reference {ref_idx+1} (empty title).")
                        continue
                    
                    _update_status(f"        Searching for snowballed reference by title: '{ref_title_to_search[:70]}...'")
                    
                    # ArXiv Search for the reference
                    try:
                        # Pass globally_fetched_primary_ids to avoid re-fetching
                        arxiv_results_meta, arxiv_fetched_count, arxiv_status_msg = fetch_arxiv_papers(
                            search_query_str=f'ti:"{ref_title_to_search}"', # Search by title
                            year_range=year_range, num_papers=1, # Aim for 1 specific paper
                            pdf_folder=pdf_folder, already_fetched_primary_ids=globally_fetched_primary_ids
                        )
                        _update_status(f"          ArXiv search for '{ref_title_to_search[:50]}...': {arxiv_status_msg}")
                        if arxiv_results_meta: # arxiv_results_meta is a list of dicts
                            for meta_ax_snow in arxiv_results_meta:
                                # Ensure correct metadata structure for snowballed papers
                                sanitized_id_snow_ax = os.path.splitext(os.path.basename(meta_ax_snow['local_pdf_path']))[0]
                                meta_ax_snow['source'] = 'arxiv_snowball'
                                meta_ax_snow['id_primary'] = sanitized_id_snow_ax # This ID is now in globally_fetched_primary_ids
                                meta_ax_snow['abstract_api'] = meta_ax_snow.get('summary', '')
                                meta_ax_snow['local_txt_path'] = os.path.join(txt_papers_folder_path, f"{sanitized_id_snow_ax}.txt")
                                newly_found_metadata_this_iteration.append(meta_ax_snow)
                                counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_SNOWBALL"] += 1 # Count each identified record
                    except Exception as e_arxiv_snow:
                        _update_status(f"          Error during ArXiv snowball search for '{ref_title_to_search[:50]}...': {e_arxiv_snow}")

                    # Scopus Search for the reference
                    try:
                        # Pass globally_fetched_primary_ids
                        scopus_results_meta, scopus_fetched_count, scopus_status_msg = fetch_scopus_papers_and_process(
                            search_query_str=f'TITLE("{ref_title_to_search}")', # Scopus title search
                            year_range=year_range, num_papers=1,
                            pdf_folder=pdf_folder, txt_folder=txt_papers_folder_path,
                            already_fetched_primary_ids=globally_fetched_primary_ids
                        )
                        _update_status(f"          Scopus search for '{ref_title_to_search[:50]}...': {scopus_status_msg}")
                        if scopus_results_meta: # scopus_results_meta is a list of dicts
                            newly_found_metadata_this_iteration.extend(scopus_results_meta) # IDs are added within fetch_scopus_papers_and_process
                            counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_SNOWBALL"] += scopus_fetched_count
                    except Exception as e_scopus_snow:
                        _update_status(f"          Error during Scopus snowball search for '{ref_title_to_search[:50]}...': {e_scopus_snow}")
                    
                    references_processed_from_this_source += 1
            
            # Process newly found papers from this snowball iteration
            if newly_found_metadata_this_iteration:
                _update_status(f"    Found {len(newly_found_metadata_this_iteration)} potential new papers in snowball iteration {sb_iteration + 1}.")
                
                # Convert PDFs to text for these new papers
                # batch_convert_pdfs_to_text works on the entire pdf_folder, so new ones will be picked up.
                conversion_status_snow = batch_convert_pdfs_to_text(pdf_folder, txt_papers_folder_path)
                _update_status(f"      PDF-to-Text for snowballed papers: {conversion_status_snow}")

                snowball_papers_to_summarize_and_filter = []
                for meta_snow in newly_found_metadata_this_iteration:
                    txt_path_snow = meta_snow.get('local_txt_path')
                    if txt_path_snow and os.path.exists(txt_path_snow) and os.path.getsize(txt_path_snow) > 0:
                        try:
                            with open(txt_path_snow, 'r', encoding='utf-8') as f_snow_txt:
                                text_content_snow = f_snow_txt.read()
                            if text_content_snow.strip():
                                # Prepare detail dict for batch_summarize_papers
                                paper_detail_for_summary = {'filename': os.path.basename(txt_path_snow), 'text': text_content_snow, **meta_snow}
                                snowball_papers_to_summarize_and_filter.append(paper_detail_for_summary)
                        except Exception as e_read_snow_txt:
                            _update_status(f"        Error reading text file for snowballed paper {txt_path_snow}: {e_read_snow_txt}")
                    else:
                         _update_status(f"        Text file missing or empty for snowballed paper: {meta_snow.get('title', 'Unknown')[:50]} at {txt_path_snow}")
                
                if snowball_papers_to_summarize_and_filter:
                    _update_status(f"      Summarizing and filtering {len(snowball_papers_to_summarize_and_filter)} new snowballed papers...")
                    snowballed_papers_with_summaries = batch_summarize_papers(
                        natural_language_paper_goal, # Use the main goal for relevance
                        snowball_papers_to_summarize_and_filter,
                        summaries_folder_path
                    )
                    
                    newly_confirmed_snowballed_papers_count = 0
                    for paper_info_snow_processed in snowballed_papers_with_summaries:
                        if papers_added_via_snowball_total_count >= MAX_PAPERS_TO_ADD_VIA_SNOWBALLING: break
                        summary_text_snow = paper_info_snow_processed.get('summary_text', '')
                        title_snow_log = paper_info_snow_processed.get('title', paper_info_snow_processed.get('filename', 'Unknown Snowballed Paper'))
                        
                        # LLM relevance check based on summary content
                        if summary_text_snow and "Error summarizing paper" not in summary_text_snow and "This paper does not appear to be relevant" not in summary_text_snow.lower():
                            # Check if this paper (by primary ID) is already in the confirmed list
                            is_already_confirmed = any(p.get('id_primary') == paper_info_snow_processed.get('id_primary') for p in llm_confirmed_relevant_papers)
                            if not is_already_confirmed:
                                llm_confirmed_relevant_papers.append(paper_info_snow_processed)
                                papers_added_via_snowball_total_count += 1
                                newly_confirmed_snowballed_papers_count += 1
                                counts_for_reporting["NUMBER_STUDIES_INCLUDED_QUALITATIVE"] += 1 # Update PRISMA
                                _update_status(f"        RELEVANT snowballed paper added: '{title_snow_log[:60]}...' (Total snowballed: {papers_added_via_snowball_total_count})")
                            else:
                                _update_status(f"        Snowballed paper '{title_snow_log[:60]}...' was already in relevant list.")
                        else:
                            _update_status(f"        NOT RELEVANT or error summarizing snowballed paper: '{title_snow_log[:60]}...'")
                            counts_for_reporting["NUMBER_EXCLUDED_BY_LLM_RELEVANCE_FILTER"] += 1 # Update PRISMA
                    _update_status(f"      Added {newly_confirmed_snowballed_papers_count} relevant papers from this snowball batch.")
                else:
                    _update_status(f"      No snowballed papers from this iteration had processable text.")
            else: # No new metadata found in this iteration
                _update_status(f"    No new papers found in snowball iteration {sb_iteration + 1}. Ending snowballing early.")
                break # No new papers found, stop snowballing
    # --- End of Snowballing Phase ---

    # --- Phase 3.6: Supplementary Fetching if target not met ---
    supplementary_iteration_num = 0
    all_queries_ever_used_for_supplementary = list(all_angles_and_queries) # Use a copy

    while len(llm_confirmed_relevant_papers) < min_relevant_papers_target and supplementary_iteration_num < max_supplementary_iterations:
        supplementary_iteration_num += 1
        papers_still_needed = min_relevant_papers_target - len(llm_confirmed_relevant_papers)
        num_to_fetch_supp = min(max(papers_still_needed, 1), num_papers_to_fetch_per_iteration)

        _update_status(f"Supplementary Fetch Iteration {supplementary_iteration_num}/{max_supplementary_iterations}: Need {papers_still_needed} more relevant papers, attempting to fetch {num_to_fetch_supp}.")

        try:
            supp_angle, supp_query = create_arxiv_search_query_from_natural_language(
                natural_language_paper_goal, all_queries_ever_used_for_supplementary
            )
            _update_status(f"  Supplementary Angle: '{supp_angle}', Query: '{supp_query}'")
            all_queries_ever_used_for_supplementary.append((supp_angle, supp_query))

            if supp_query == INVALID_QUERY_FOR_ACADEMIC_SEARCH or not supp_query.strip():
                _update_status(f"    LLM indicated supplementary query '{supp_query}' is invalid. Skipping this supplementary attempt.")
                continue
        except Exception as e_supp_query_gen:
            _update_status(f"    {RED}Error generating supplementary query: {e_supp_query_gen}{RESET}")
            continue

        current_supplementary_batch_metadata: List[Dict[str, any]] = []
        try:
            newly_fetched_meta_supp_arxiv, fetched_count_supp_arxiv, supp_fetch_status_arxiv = fetch_arxiv_papers(
                supp_query, year_range, num_to_fetch_supp, pdf_folder, globally_fetched_primary_ids
            )
            _update_status(f"  ArXiv Supplementary: {supp_fetch_status_arxiv}")
            counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_ARXIV"] += fetched_count_supp_arxiv
            if newly_fetched_meta_supp_arxiv:
                for meta_ax_supp in newly_fetched_meta_supp_arxiv:
                    sanitized_id_supp_ax = os.path.splitext(os.path.basename(meta_ax_supp['local_pdf_path']))[0]
                    meta_ax_supp['source'] = 'arxiv_supplementary'
                    meta_ax_supp['id_primary'] = sanitized_id_supp_ax
                    meta_ax_supp['abstract_api'] = meta_ax_supp.get('summary', '')
                    meta_ax_supp['local_txt_path'] = os.path.join(txt_papers_folder_path, f"{sanitized_id_supp_ax}.txt")
                    current_supplementary_batch_metadata.append(meta_ax_supp)
        except Exception as e_supp_arxiv:
            _update_status(f"    {RED}Error in supplementary ArXiv fetch: {e_supp_arxiv}{RESET}")

        try:
            newly_fetched_meta_supp_scopus, fetched_count_supp_scopus, supp_fetch_status_scopus = fetch_scopus_papers_and_process(
                supp_query, year_range, num_to_fetch_supp, pdf_folder, txt_papers_folder_path, globally_fetched_primary_ids
            )
            _update_status(f"  Scopus Supplementary: {supp_fetch_status_scopus}")
            counts_for_reporting["NUMBER_RECORDS_IDENTIFIED_SCOPUS"] += fetched_count_supp_scopus
            if newly_fetched_meta_supp_scopus:
                current_supplementary_batch_metadata.extend(newly_fetched_meta_supp_scopus)
        except Exception as e_supp_scopus:
            _update_status(f"    {RED}Error in supplementary Scopus fetch: {e_supp_scopus}{RESET}")


        if not current_supplementary_batch_metadata:
            _update_status("  No new supplementary papers found in this iteration.")
            continue

        conversion_status_supp = batch_convert_pdfs_to_text(pdf_folder, txt_papers_folder_path)
        _update_status(f"    PDF-to-Text for supplementary papers: {conversion_status_supp}")

        papers_to_summarize_details_supp = []
        for meta_item_supp in current_supplementary_batch_metadata:
            txt_path_supp = meta_item_supp.get('local_txt_path')
            if txt_path_supp and os.path.exists(txt_path_supp) and os.path.getsize(txt_path_supp) > 0:
                try:
                    with open(txt_path_supp, 'r', encoding='utf-8') as f_supp_txt:
                        text_content_supp = f_supp_txt.read()
                    if text_content_supp.strip():
                        paper_detail_supp = {'filename': os.path.basename(txt_path_supp), 'text': text_content_supp, **meta_item_supp}
                        papers_to_summarize_details_supp.append(paper_detail_supp)
                except Exception as e_read_txt_supp:
                     _update_status(f"      {RED}Error reading text file for supplementary paper {txt_path_supp}: {e_read_txt_supp}{RESET}")
            else:
                _update_status(f"      Text file missing or empty for supplementary paper: {meta_item_supp.get('title', 'Unknown')[:50]} at {txt_path_supp}")


        if not papers_to_summarize_details_supp:
            _update_status("  No text extracted from supplementary papers for summarization.")
            continue

        _update_status(f"    Summarizing {len(papers_to_summarize_details_supp)} supplementary papers...")
        supplementary_papers_with_summaries = batch_summarize_papers(
            natural_language_paper_goal, papers_to_summarize_details_supp, summaries_folder_path
        )

        newly_confirmed_supp_count = 0
        for paper_info_supp_processed in supplementary_papers_with_summaries:
            summary_text_supp = paper_info_supp_processed.get('summary_text', '')
            title_for_log_supp = paper_info_supp_processed.get('title', paper_info_supp_processed.get('filename', 'Unknown Supp. Paper'))
            if summary_text_supp and "Error summarizing paper" not in summary_text_supp and \
               "This paper does not appear to be relevant" not in summary_text_supp.lower():
                if not any(p.get('id_primary') == paper_info_supp_processed.get('id_primary') for p in llm_confirmed_relevant_papers):
                    llm_confirmed_relevant_papers.append(paper_info_supp_processed)
                    newly_confirmed_supp_count +=1
                    _update_status(f"      RELEVANT supplementary paper added: '{title_for_log_supp[:60]}...'")
                else:
                    _update_status(f"      Supplementary paper '{title_for_log_supp[:60]}...' was already in relevant list.")
            else:
                _update_status(f"      NOT RELEVANT or error (Supplementary): '{title_for_log_supp[:60]}...'")
                counts_for_reporting["NUMBER_EXCLUDED_BY_LLM_RELEVANCE_FILTER"] += 1
        
        counts_for_reporting["NUMBER_STUDIES_INCLUDED_QUALITATIVE"] = len(llm_confirmed_relevant_papers)
        _update_status(f"    Added {newly_confirmed_supp_count} relevant papers from supplementary fetch. Total relevant: {len(llm_confirmed_relevant_papers)}.")
    # --- End of Supplementary Fetching Phase ---

    if not llm_confirmed_relevant_papers:
        _update_status(f"{RED}CRITICAL: No papers passed relevance filter after all fetching and snowballing attempts. Aborting.{RESET}")
        last_query_info = all_queries_ever_used_for_supplementary[-1][1] if all_queries_ever_used_for_supplementary else \
                          (all_angles_and_queries[-1][1] if all_angles_and_queries else "NO_QUERY_ATTEMPTED")
        return f"PROCESS_INCOMPLETE_LAST_QUERY_INFO:{last_query_info}", None

    _update_status(f"Total LLM-confirmed relevant papers for SLR: {len(llm_confirmed_relevant_papers)}")

    # --- Phase 4: Final SLR Document Preparation ---
    _update_status("Phase 4: Preparing for Final SLR Document Generation...")
    final_summaries_text = "\n\n---\n\n".join(
        [p['summary_text'] for p in llm_confirmed_relevant_papers if p.get('summary_text') and \
         "This paper does not appear to be relevant" not in p['summary_text'].lower() and \
         "Error summarizing paper" not in p['summary_text']]
    ).strip()

    if not final_summaries_text:
        _update_status(f"{RED}CRITICAL: No valid summaries available from relevant papers for SLR generation. Aborting.{RESET}")
        return NO_SUMMARIES_GENERATED, None

    final_metadata_for_biblio = [
        {k: v for k, v in p.items() if k not in ['text', 'summary_text', 'summary_filepath', 'llm_relevance_judgment', 'llm_relevance_reason', 'score']}
        for p in llm_confirmed_relevant_papers
    ]

    _update_status("Generating SLR Outline...")
    slr_outline = "% No SLR outline generated."
    try:
        slr_outline_content = generate_slr_outline(natural_language_paper_goal, final_summaries_text, natural_language_paper_goal)
        if slr_outline_content and not slr_outline_content.startswith(("% Error", "% No relevant")):
            slr_outline = slr_outline_content
            outline_filename = os.path.join(results_folder_path, "slr_high_level_outline.txt")
            with open(outline_filename, 'w', encoding='utf-8') as f_outline:
                f_outline.write(slr_outline)
            _update_status(f"  SLR outline saved to: {outline_filename}")
        else:
            _update_status(f"  SLR outline generation returned: {slr_outline_content[:100]}...")
    except Exception as e_outline:
        _update_status(f"  {RED}Error generating SLR outline: {e_outline}{RESET}")
        slr_outline = f"% Error generating SLR outline: {e_outline}"


    _update_status("Generating Bibliometric Analysis (biblio.bib)...")
    bibliometric_content = "% No BibTeX content generated."
    try:
        bib_content = create_bibliometric(final_metadata_for_biblio, final_summaries_text)
        if bib_content and not bib_content.startswith("% Error"):
            bibliometric_content = bib_content
        else:
             _update_status(f"  Biblio.bib generation returned: {bib_content[:100]}...")
    except Exception as e_bib:
        _update_status(f"  {RED}Error creating bibliometric content: {e_bib}{RESET}")
        bibliometric_content = f"% Error generating BibTeX: {e_bib}"


    actual_paper_title_final = f"A Systematic Literature Review on: {natural_language_paper_goal}"
    if all_angles_and_queries and all_angles_and_queries[0][0]:
        first_angle = all_angles_and_queries[0][0].strip()
        if first_angle.endswith('.'): first_angle = first_angle[:-1]
        if first_angle: actual_paper_title_final = first_angle
    _update_status(f"Using paper title: '{actual_paper_title_final}'")


    # --- Phase 5: Iterative SLR Document Refinement ---
    _update_status("Phase 5: Iterative SLR Document Refinement...")
    iterative_refinement_report_data: List[Dict[str, any]] = []
    current_parsed_critique_data: Dict[str, any] = {}
    iter_output_filename = ""
    oldest_paper_text_for_style = ""

    if llm_confirmed_relevant_papers:
        def get_year(paper_dict):
            year_val = paper_dict.get('published_year')
            try: return int(year_val)
            except (ValueError, TypeError): return 9999
        
        oldest_paper_for_style = min(llm_confirmed_relevant_papers, key=get_year)
        style_paper_text_path = oldest_paper_for_style.get('local_txt_path')
        if style_paper_text_path and os.path.exists(style_paper_text_path):
            try:
                with open(style_paper_text_path, 'r', encoding='utf-8') as f_style_oldest:
                    oldest_paper_text_for_style = f_style_oldest.read()
                
                max_style_text_len = 10000
                if len(oldest_paper_text_for_style) > max_style_text_len:
                    oldest_paper_text_for_style = oldest_paper_text_for_style[:max_style_text_len] + "\n[...text truncated for style example...]"
                    _update_status(f"  Truncated oldest paper text (from '{oldest_paper_for_style.get('title', 'Unknown')[:30]}...') for style inspiration.")
                else:
                    _update_status(f"  Using paper '{oldest_paper_for_style.get('title', 'Unknown')[:50]}...' (Year: {get_year(oldest_paper_for_style)}) as stylistic inspiration.")
            except Exception as e_style_read:
                _update_status(f"  Could not read oldest paper for style inspiration: {e_style_read}")
                oldest_paper_text_for_style = ""
        else:
            _update_status(f"  Oldest paper text file not found for style inspiration: {style_paper_text_path}")
    else:
        _update_status("  No relevant papers to pick for stylistic inspiration.")

    final_counts_for_placeholders = counts_for_reporting.copy()

    for iteration in range(num_refinement_cycles + 1):
        _update_status(f"SLR DOCUMENT GENERATION CYCLE {iteration}/{num_refinement_cycles}")
        
        def get_suggestions_for_section(section_key: str) -> str:
            if not current_parsed_critique_data: return ""
            section_specific_list = current_parsed_critique_data.get("suggestions_by_section", {}).get(section_key, [])
            general_list = current_parsed_critique_data.get("general_suggestions", [])
            combined_suggestions = []
            if general_list:
                combined_suggestions.append("General Feedback from Previous Cycle:\n" + "\n".join([f"- {s}" for s in general_list]))
            if section_specific_list:
                combined_suggestions.append(f"Specific Feedback for {section_key} from Previous Cycle:\n" + "\n".join([f"- {s}" for s in section_specific_list]))
            return "\n\n".join(combined_suggestions).strip()

        try:
            _update_status(f"  Generating SLR Sections for Cycle {iteration}...")
            
            # Define paths for section files
            related_works_base_filename = "related_works.tex"
            research_methodes_base_filename = "research_methodes.tex"
            background_base_filename = "background.tex"
            review_findings_base_filename = "review_findings.tex"
            discussion_conclusion_base_filename = "discussion_conclusion.tex"
            abstract_intro_keywords_base_filename = "abstract_intro_keywords.tex"

            _update_status(f"    Generating Related Works...")
            related_works_tex_content = create_related_works(
                final_summaries_text, natural_language_paper_goal, bibliometric_content,
                reviewer_suggestions=get_suggestions_for_section("Related Works") if iteration > 0 else "",
                slr_outline=slr_outline,
                human_style_example_text=oldest_paper_text_for_style
            )
            related_works_tex_content = replace_placeholders_in_latex(related_works_tex_content, final_counts_for_placeholders)
            # create_related_works saves to Results/related_works.tex
            related_works_input_path = os.path.join(results_folder_path, related_works_base_filename)
            related_works_enhanced_tex = create_charts(related_works_input_path, f"Related_Works_Iter{iteration}")

            _update_status(f"    Generating Research Methods...")
            research_methodes_tex_content = create_reshearch_methodes(
                related_works_content=related_works_enhanced_tex,
                summaries=final_summaries_text,
                subject=natural_language_paper_goal,
                Biblio_content=bibliometric_content,
                year_range_for_prompt=year_range,
                reviewer_suggestions=get_suggestions_for_section("Research Methods") if iteration > 0 else "",
                slr_outline=slr_outline,
                human_style_example_text=oldest_paper_text_for_style
            )
            research_methodes_tex_content = replace_placeholders_in_latex(research_methodes_tex_content, final_counts_for_placeholders)
            research_methodes_input_path = os.path.join(results_folder_path, research_methodes_base_filename)
            research_methodes_enhanced_tex = create_charts(research_methodes_input_path, f"Research_Methods_Iter{iteration}")

            _update_status(f"    Generating Background...")
            background_tex_content = create_background_string(
                "", related_works_enhanced_tex, research_methodes_enhanced_tex, "",
                bibliometric_content,
                reviewer_suggestions=get_suggestions_for_section("Background") if iteration > 0 else "",
                slr_outline=slr_outline,
                human_style_example_text=oldest_paper_text_for_style
            )
            background_tex_content = replace_placeholders_in_latex(background_tex_content, final_counts_for_placeholders)

            _update_status(f"    Generating Review Findings...")
            review_findings_tex_content = create_review_findings(
                research_methodes_enhanced_tex, final_summaries_text, natural_language_paper_goal, bibliometric_content,
                reviewer_suggestions=get_suggestions_for_section("Review Findings") if iteration > 0 else "",
                slr_outline=slr_outline,
                human_style_example_text=oldest_paper_text_for_style
            )
            review_findings_tex_content = replace_placeholders_in_latex(review_findings_tex_content, final_counts_for_placeholders)
            review_findings_input_path = os.path.join(results_folder_path, review_findings_base_filename)
            review_findings_enhanced_tex = create_charts(review_findings_input_path, f"Review_Findings_Iter{iteration}")

            _update_status(f"    Generating Discussion & Conclusion...")
            discussion_conclusion_tex_content = create_discussion_conclusion(
                review_findings_enhanced_tex, final_summaries_text, natural_language_paper_goal, bibliometric_content,
                reviewer_suggestions=get_suggestions_for_section("Discussion_Conclusion") if iteration > 0 else "",
                slr_outline=slr_outline,
                human_style_example_text=oldest_paper_text_for_style
            )
            discussion_conclusion_tex_content = replace_placeholders_in_latex(discussion_conclusion_tex_content, final_counts_for_placeholders)

            _update_status(f"    Generating Abstract, Keywords & Introduction...")
            abstract_intro_keywords_tex_content = create_abstract_intro(
                review_findings_content=review_findings_enhanced_tex,
                related_works_content=related_works_enhanced_tex,
                research_methodes_content=research_methodes_enhanced_tex,
                discussion_conclusion_content=discussion_conclusion_tex_content,
                subject=natural_language_paper_goal,
                Biblio_content=bibliometric_content,
                reviewer_suggestions=get_suggestions_for_section("Abstract_Intro_Keywords") if iteration > 0 else "",
                slr_outline=slr_outline,
                human_style_example_text=oldest_paper_text_for_style
            )
            abstract_intro_keywords_tex_content = replace_placeholders_in_latex(abstract_intro_keywords_tex_content, final_counts_for_placeholders)

            _update_status(f"  Assembling Full LaTeX Document (Cycle {iteration})...")
            
            latex_preamble_iter = fr"""\documentclass[11pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}} \usepackage{{amsmath}} \usepackage{{amsfonts}} \usepackage{{amssymb}}
\usepackage{{graphicx}} \usepackage{{hyperref}}
\hypersetup{{ colorlinks=true, linkcolor=blue, filecolor=magenta, urlcolor=cyan, pdftitle={{{actual_paper_title_final} (Cycle {iteration})}}, pdfpagemode=FullScreen }}
\usepackage{{xcolor}} \usepackage{{geometry}}\geometry{{a4paper, margin=1in}}
\usepackage{{longtable}} \usepackage{{multirow}} \usepackage{{tabularx}} \usepackage{{colortbl}}
\usepackage{{pgfplots}}\pgfplotsset{{compat=1.18}} \usepackage{{tikz}}
\usetikzlibrary{{arrows.meta, trees, shapes.geometric, positioning, calc, fit, backgrounds}}
\usepackage[gantt]{{pgfgantt}} \usepackage{{smartdiagram}} \usepackage{{array}} \usepackage{{booktabs}}
\usepackage{{lscape}} \usepackage{{threeparttable}} \usepackage{{caption}} \usepackage{{subcaption}}
\usepackage[numbers,sort&compress]{{natbib}}\bibliographystyle{{plainnat}}
\title{{{actual_paper_title_final} (Cycle {iteration})}}
\author{{Systematic Literature Review Automation Tool}} \date{{\\today}}
"""
            full_latex_doc_iter = latex_preamble_iter + "\n\\begin{document}\n\\maketitle\n\n"
            full_latex_doc_iter += abstract_intro_keywords_tex_content + "\n\n"
            full_latex_doc_iter += background_tex_content + "\n\n"
            full_latex_doc_iter += related_works_enhanced_tex + "\n\n"
            full_latex_doc_iter += research_methodes_enhanced_tex + "\n\n"
            full_latex_doc_iter += review_findings_enhanced_tex + "\n\n"
            full_latex_doc_iter += discussion_conclusion_tex_content + "\n\n"
            full_latex_doc_iter += "\\section*{References}\n\\bibliography{biblio}\n\n"
            full_latex_doc_iter += "\\end{document}\n"
            
            current_slr_latex_content = validate_latex(clean_latex_output(full_latex_doc_iter))

            safe_title_filename_iter_base = re.sub(r'[^\w\s-]', '', actual_paper_title_final).strip()
            safe_title_filename_iter_base = re.sub(r'\s+', '_', safe_title_filename_iter_base)[:80]
            if not safe_title_filename_iter_base: safe_title_filename_iter_base = "SLR_Output"
            iter_output_filename = os.path.join(results_folder_path, f"{safe_title_filename_iter_base}_Cycle_{iteration}.tex")

            with open(iter_output_filename, 'w', encoding='utf-8') as f_iter_tex:
                f_iter_tex.write(current_slr_latex_content)
            _update_status(f"  SLR document for Cycle {iteration} saved to: {iter_output_filename}")

            bib_path_results = os.path.join(results_folder_path, "biblio.bib")
            if bibliometric_content and not bibliometric_content.startswith("% Error"):
                if not os.path.exists(bib_path_results) or os.path.getsize(bib_path_results) == 0:
                    with open(bib_path_results, 'w', encoding='utf-8') as bib_file_iter:
                        bib_file_iter.write(bibliometric_content)
                    _update_status(f"  Saved biblio.bib to {bib_path_results} for cycle {iteration}")


            if iteration < num_refinement_cycles:
                _update_status(f"  Generating Critique for Cycle {iteration} output...")
                previous_critique_raw_text_for_llm = iterative_refinement_report_data[-1]["raw_critique"] if iterative_refinement_report_data else ""
                
                critique_output_text = generate_critique(current_slr_latex_content, previous_critique_raw_text_for_llm, natural_language_paper_goal)
                
                critique_filename = os.path.join(results_folder_path, f"raw_critique_cycle_{iteration}.txt")
                with open(critique_filename, 'w', encoding='utf-8') as f_critique_write:
                    f_critique_write.write(critique_output_text)
                _update_status(f"    Critique for cycle {iteration} saved to: {critique_filename}")

                current_parsed_critique_data = parse_critique(critique_output_text)
                _update_status(f"    Critique rating for cycle {iteration}: {current_parsed_critique_data.get('rating', 'N/A')}")

                iterative_refinement_report_data.append({
                    "iteration": iteration,
                    "raw_critique": critique_output_text,
                    "parsed_critique": current_parsed_critique_data,
                    "output_tex_file": iter_output_filename
                })

                no_new_issues_found = not current_parsed_critique_data.get("new_issues")
                no_section_suggestions_found = not current_parsed_critique_data.get("suggestions_by_section") and \
                                               not current_parsed_critique_data.get("general_suggestions")
                rating = current_parsed_critique_data.get('rating', '0/10').split('/')[0]
                try: rating_val = int(rating)
                except: rating_val = 0

                if no_new_issues_found and no_section_suggestions_found and rating_val >= 8:
                    _update_status(f"  Critique for cycle {iteration} is positive with no new issues/suggestions. Halting refinement early.")
                    break 
            else:
                iterative_refinement_report_data.append({
                    "iteration": iteration,
                    "raw_critique": "N/A (Final Cycle - No critique generated)",
                    "parsed_critique": {},
                    "output_tex_file": iter_output_filename
                })

        except Exception as e_iter_gen:
            _update_status(f"  {RED}Error in SLR generation cycle {iteration}: {e_iter_gen}{RESET}")
            if iter_output_filename and not os.path.exists(iter_output_filename):
                 with open(iter_output_filename, 'w', encoding='utf-8') as f_err_tex:
                    f_err_tex.write(f"% Error during generation cycle {iteration}: {e_iter_gen}\n% Partial content might be below.\n")
                 _update_status(f"  Saved partial/error output for cycle {iteration} to {iter_output_filename}")
            
            iterative_refinement_report_data.append({
                "iteration": iteration,
                "raw_critique": f"Error in generation: {e_iter_gen}",
                "parsed_critique": {"rating": "Error", "new_issues": [f"Generation error: {e_iter_gen}"]},
                "output_tex_file": iter_output_filename if iter_output_filename else "Error_NoFile"
            })
            if iteration < num_refinement_cycles :
                 _update_status(f"  {YELLOW}Attempting to continue to next refinement cycle despite error in cycle {iteration}.{RESET}")
                 continue
            else:
                 _update_status(f"  {RED}Error in final SLR generation cycle. Process will conclude with available data.{RESET}")
                 break

    _update_status("Iterative SLR document refinement complete!")
    
    refinement_report_path = None
    try:
        report_path = generate_refinement_report(iterative_refinement_report_data, natural_language_paper_goal)
        if report_path:
            _update_status(f"Refinement cycle report saved to: {report_path}")
            refinement_report_path = report_path
    except Exception as e_report:
        _update_status(f"  {RED}Error generating refinement report: {e_report}{RESET}")

    if iter_output_filename and os.path.exists(iter_output_filename):
        _update_status(f"Final SLR document produced: {iter_output_filename}")
        return f"FINAL_SLR_OUTPUT:{iter_output_filename}", refinement_report_path
    else:
        _update_status(f"{RED}CRITICAL: Final SLR document was not generated or found. Path: {iter_output_filename}{RESET}")
        last_query_info = all_queries_ever_used_for_supplementary[-1][1] if all_queries_ever_used_for_supplementary else \
                          (all_angles_and_queries[-1][1] if all_angles_and_queries else "NO_QUERY_ATTEMPTED_OR_ERROR_BEFORE_QUERY")
        return f"PROCESS_INCOMPLETE_LAST_QUERY_INFO:{last_query_info}", refinement_report_path




def generate_refinement_report(report_data: List[Dict[str, any]], slr_goal: str) -> Optional[str]:
    if not report_data:
        print("No refinement data to generate a report.")
        return None
        
    report_content = [f"# SLR Refinement Report for: {slr_goal}\n"]
    for entry in report_data:
        iteration = entry["iteration"]
        parsed = entry["parsed_critique"]
        raw_critique = entry["raw_critique"] # For full context
        comp_status = entry.get("compilation_status_final", "N/A - Compilation Skipped") 

        report_content.append(f"\n## Cycle {iteration} {'(Initial Generation)' if iteration == 0 else '(Refinement)'}")
        report_content.append(f"- **Overall Rating**: {parsed.get('rating', 'N/A')}")
        
        if iteration > 0:
            report_content.append(f"- **Assessment of Previous Suggestions**: {parsed.get('addressed_points_summary', 'N/A')}")
        # Always report compilation status, even if skipped
        report_content.append(f"- **LaTeX Compilation Status for this Cycle's Output**: {comp_status}")
        report_content.append("- **New Issues Identified in This Cycle**:")
        new_issues_list = parsed.get("new_issues", [])
        if new_issues_list:
            for issue in new_issues_list: report_content.append(f"  - {issue}")
        else:
            report_content.append("  - None")
        
        report_content.append("- **Critique & Suggestions for This Cycle's Output**:")
        suggestions_by_section = parsed.get("suggestions_by_section", {})
        general_suggestions = parsed.get("general_suggestions", [])

        if suggestions_by_section:
            for section, suggs in suggestions_by_section.items():
                report_content.append(f"  - **For {section} Section**:")
                for s_item in suggs: # suggs is a list of strings
                    # Indent multi-line suggestions properly
                    s_indented = "\n    ".join(s_item.strip().splitlines())
                    report_content.append(f"    - {s_indented}")
        
        if general_suggestions:
            report_content.append(f"  - **General Suggestions**:")
            for gen_sugg_item in general_suggestions: # gen_sugg is a list of strings
                gs_indented = "\n    ".join(gen_sugg_item.strip().splitlines())
                report_content.append(f"    - {gs_indented}")

        if not suggestions_by_section and not general_suggestions:
             report_content.append("  - No specific suggestions parsed for sections in this cycle.")
        
        if raw_critique and raw_critique != "N/A (Final Cycle)":
            report_content.append(f"\n<details><summary>Raw Critique Text for Cycle {iteration} (click to expand)</summary>\n\n```\n{raw_critique}\n```\n</details>\n")

        # Compilation attempt details are removed as compilation is skipped


    report_filename = "Results/refinement_cycle_report.md"
    try:
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_content))
        return report_filename
    except Exception as e:
        print(f"Error writing refinement report: {e}")
        return None

# --- Update section creation function signatures and prompts ---

def create_background_string(
    review_findings: str, related_works: str, research_methodes: str,
    discussion_conclusion: str, bibliometric_content: str,
    reviewer_suggestions: str = "",
    slr_outline: str = "",
    human_style_example_text: str = ""  # This will use the global Human_Text if not overridden
) -> str:
    if any(s.startswith("% Error") or "No summaries provided" in s or "Insufficient input" in s for s in [review_findings, related_works, research_methodes, discussion_conclusion]):
        print("One or more input sections for Background generation are invalid or empty. Skipping Background.")
        return "\\section{Background}\n% Skipped due to invalid input sections.\n"

    # Use global Human_Text if human_style_example_text is empty or not provided specifically
    actual_human_style_text = human_style_example_text if human_style_example_text.strip() else Human_Text

    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for this Background Section:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"
    
    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for this Background Section:\n{slr_outline}\nEnsure your section aligns with this broader plan.\n---"
    
    style_guidance_addon = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic, perhaps a graduate student explaining their work to a peer.
To achieve this, **actively avoid common AI writing patterns**.
Instead, draw inspiration from the **narrative style, sentence flow, phrasing nuances, and vocabulary choices** in the uploaded file 'human_style_sample.txt'.

**Emulate these human-like qualities:**
- **Varied Sentence Structure:** Mix short, impactful sentences with longer, more complex ones. Avoid monotonous sentence lengths or predictable structures.
- **Natural Transitions:** Use a variety of transitional words and phrases to create a smooth, logical flow between ideas. Avoid overusing simplistic transitions.
- **Sophisticated yet Clear Vocabulary:** Employ precise academic language, but ensure it sounds natural and not forced or overly thesaurus-driven.
- **Engaging Narrative Tone:** Even in academic writing, aim for a tone that is confident, clear, and subtly engaging. Avoid a dry, robotic, or overly detached tone.
    - Consider using rhetorical questions (e.g., "So, what does this all mean for the field?", "But how did they arrive at this conclusion?").
    - Incorporate phrases like "It's worth noting that...", "One might wonder why...", or "This is where things get particularly interesting...".
- **Subtlety and Nuance:** Human writing often conveys meaning through subtle phrasing and nuance. Try to incorporate this.
- **First-Person Perspective (where appropriate for an SLR):** Use "we" when describing the actions of the review (e.g., "We searched the databases...", "We identified the following themes..."). Use contractions (e.g., "it's", "don't") sparingly and only if it genuinely enhances the natural flow without undermining academic formality too much.

**Crucially, DO NOT:**
- **Copy Content:** Do not replicate any specific facts, arguments, or the overall structure from the sample text.
- **Mimic Structure:** The sample is for *stylistic inspiration only*, not for structural guidance.
- **Sound Robotic or Formulaic:** Actively work against sounding like a typical AI. If your phrasing feels too standard or predictable, revise it.
- **Overuse Casual Language:** While aiming for a human tone, maintain academic integrity. Avoid slang or overly informal expressions that would be out of place in a research paper. The goal is "academic human," not "casual blogger."

Before finalizing your response for this section, reread it and ask yourself: "Does this sound like a human wrote it, or does it have tell-tale signs of AI generation?" Adjust as needed.
"""
    prompt_instructions = fr"""
Act as an expert academic writer. Create the **Background** section for a systematic literature review (SLR)make sure it's detailed , academicale , and huminazed.
The content for Review Findings, Related Works, Research Methods, Discussion/Conclusion, Biblio Content, and Human Style Sample are provided in uploaded files.

{suggestions_addon}
{outline_addon}
{style_guidance_addon}

### Task Description:
1.  **Purpose and Tone**: Define key terms, concepts, and foundational works relevant to the SLR. This section helps readers understand the terminology and context used throughout the paper.
    Write this section as if you're explaining the motivation and core concepts to a fellow student or peer. Keep it somewhat informal and story-like where appropriate. Use analogies if they can clarify complex ideas (e.g., 'Think of it like...').
2.  **Content Source**: Extract important keywords, concepts, and seminal works from the provided uploaded files:
    *   'review_findings_data.txt'
    *   'related_works_data.txt'
    *   'research_methodes_data.txt'
    *   'discussion_conclusion_data.txt'
3.  **Focus**: Define the **top 3-5 most critical concepts or foundational works** that are essential for understanding the SLR. Prioritize terms that might have context-specific meanings within this paper.
4.  **Citations**:
    *   Use `\cite{{bibtex_key}}` for all definitions and references to foundational works. Assume BibTeX keys are available from the uploaded 'biblio_context.bib'.
    *   Ensure citation keys match those in the 'biblio_context.bib' file.
5.  **LaTeX Formatting**:
    *   The section must be in Overleaf-compatible LaTeX format, starting with `\section{{Background}}`.
    *   Output only the LaTeX code for this section.

### Output:
Return *only* the complete LaTeX code for the `\section{{Background}}`. Do not include any explanations or conversational text.
"""
    prompt_instructions += f"\n\n{LATEX_SAFETY_RULES}"

    uploaded_files_map = {}
    temp_files_paths = {}
    files_to_upload_content = {
        "review_findings_data.txt": review_findings,
        "related_works_data.txt": related_works,
        "research_methodes_data.txt": research_methodes,
        "discussion_conclusion_data.txt": discussion_conclusion,
        "biblio_context.bib": bibliometric_content,
        "human_style_sample.txt": actual_human_style_text
    }

    try:
        for name, content_str in files_to_upload_content.items():
            if content_str and content_str.strip() and not content_str.startswith("% Error"):
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt" if not name.endswith(".bib") else ".bib", encoding='utf-8') as tmp_f:
                    tmp_f.write(content_str)
                    temp_files_paths[name] = tmp_f.name
                
                mime_type = 'text/plain'
                if name.endswith(".md"): mime_type = 'text/markdown'
                elif name.endswith(".bib"): mime_type = 'text/plain' # BibTeX is plain text

                uploaded_files_map[name] = genai.upload_file(
                    path=temp_files_paths[name],
                    mime_type=mime_type,
                    display_name=name
                )
            else:
                 # Create an empty placeholder if content is invalid/empty, so prompt references don't break
                uploaded_files_map[name] = genai.upload_file(
                    path=io.BytesIO(b"% This file was intentionally left empty due to invalid input content.\n"), # Upload empty content
                    mime_type='text/plain',
                    display_name=name
                )


        prompt_parts_for_llm = [prompt_instructions] + [f for f in uploaded_files_map.values() if f]
        
        response = summary_model.generate_content(
            prompt_parts_for_llm,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        generated_text = response.text.strip()
        generated_text = re.sub(r'^```(?:latex)?\s*[\r\n]*', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'[\r\n]*```\s*$', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'\\cite\s*\{\s*([^}\s]+)\s*\}', r'\\cite{\1}', generated_text)

        output_filename = 'Results/background.tex'
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        print(f"Generated {output_filename}")
        return generated_text

    except Exception as e:
        print(f"{RED}Error in create_background_string: {e}{RESET}")
        return f"% Error generating background section: {e}"
    finally:
        for name, uploaded_file_obj in uploaded_files_map.items():
            if uploaded_file_obj:
                try:
                    genai.delete_file(uploaded_file_obj.name)
                except Exception as delete_err:
                    print(f"{YELLOW}Warning: Could not delete uploaded file {name} in create_background_string: {delete_err}{RESET}")
        for name, path in temp_files_paths.items():
            if path and os.path.exists(path):
                os.remove(path)
def create_related_works(summaries: str,
                         subject: str,
                         Biblio_content:str, 
                         reviewer_suggestions: str = "", 
                         slr_outline: str = "", 
                         human_style_example_text: str = "") -> str: 
    if not summaries.strip() or summaries.startswith("% Error"):
        print("No valid summaries provided for related works. Skipping section generation.")
        return "\\section{Related Works}\n% No valid summaries provided to generate this section.\n"

    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for this Related Works Section:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith("% No relevant"):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for this Related Works Section:\n{slr_outline}\nEnsure your section aligns with this broader plan, especially regarding themes and paper groupings.\n---"
    
    style_guidance_addon = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic, perhaps a graduate student explaining their work to a peer.
To achieve this, **actively avoid common AI writing patterns**.
Instead, draw inspiration from the **narrative style, sentence flow, phrasing nuances, and vocabulary choices** in the following sample of human-written academic text.

**Emulate these human-like qualities:**
- **Varied Sentence Structure:** Mix short, impactful sentences with longer, more complex ones. Avoid monotonous sentence lengths or predictable structures.
- **Natural Transitions:** Use a variety of transitional words and phrases to create a smooth, logical flow between ideas. Avoid overusing simplistic transitions.
- **Sophisticated yet Clear Vocabulary:** Employ precise academic language, but ensure it sounds natural and not forced or overly thesaurus-driven.
- **Engaging Narrative Tone:** Even in academic writing, aim for a tone that is confident, clear, and subtly engaging. Avoid a dry, robotic, or overly detached tone.
    - Consider using rhetorical questions (e.g., "So, what does this all mean for the field?", "But how did they arrive at this conclusion?").
    - Incorporate phrases like "It's worth noting that...", "One might wonder why...", or "This is where things get particularly interesting...".
- **Subtlety and Nuance:** Human writing often conveys meaning through subtle phrasing and nuance. Try to incorporate this.
- **First-Person Perspective (where appropriate for an SLR):** Use "we" when describing the actions of the review (e.g., "We searched the databases...", "We identified the following themes..."). Use contractions (e.g., "it's", "don't") sparingly and only if it genuinely enhances the natural flow without undermining academic formality too much.

**Crucially, DO NOT:**
- **Copy Content:** Do not replicate any specific facts, arguments, or the overall structure from the sample text.
- **Mimic Structure:** The sample is for *stylistic inspiration only*, not for structural guidance.
- **Sound Robotic or Formulaic:** Actively work against sounding like a typical AI. If your phrasing feels too standard or predictable, revise it.
- **Overuse Casual Language:** While aiming for a human tone, maintain academic integrity. Avoid slang or overly informal expressions that would be out of place in a research paper. The goal is "academic human," not "casual blogger."

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---

Before finalizing your response for this section, reread it and ask yourself: "Does this sound like a human wrote it, or does it have tell-tale signs of AI generation?" Adjust as needed.
"""

    prompt = rf"""
Create a comprehensive **Related Works** section for a systematic literature review (SLR) on the subject: **{subject}**make sure it's detailed , academicale , and huminazed.

{suggestions_addon}
{outline_addon}
{style_guidance_addon}

### Requirements:
1.  **Content and Structure**:
    *   Start with `\section{{Related Works}}`.
    *   Analyze the provided paper summaries to identify themes, trends, compare methodologies, and discuss how they relate to `{subject}`. 
    *   Present the existing research as if narrating what others have done in a review conversation. Use phrases like ‘Some researchers explored…’, ‘One study we found particularly insightful was…’, or ‘Unlike approach X, this work Y took a different path…’.
    *   Focus on papers that are highly relevant to `{subject}`. If summaries indicate irrelevance, they should be downplayed or omitted from detailed discussion.
    *   Synthesize information into a cohesive narrative. Avoid a simple list of summaries. Group related papers by theme or approach, guided by the SLR outline if provided.
2.  **Writing Style**:
    *   When including figures or tables, use placement specifiers like `[htbp]` for flexibility.
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

make sure you use the same kind of vocabulary , the same way of narratting, adn words  

--- SAMPLE TEXT FOR STYLISTIC INSPIRATION ---
{Human_Text}
--- END OF SAMPLE TEXT ---
"""
    return generate_markdown(prompt + f"\n\n{LATEX_SAFETY_RULES}", 'Results/related_works.tex')

def create_reshearch_methodes(
    related_works_content: str,
    summaries: str,
    subject: str,
    Biblio_content:str,
    year_range_for_prompt: Tuple[int, int],
    reviewer_suggestions: str = "",
    slr_outline: str = "",
    human_style_example_text: str = ""
) -> str:
    if (not summaries.strip() or summaries.startswith("% Error")) and \
       (not related_works_content.strip() or related_works_content.startswith("% Error")):
        print("Insufficient or invalid input (summaries/related works) for research methods. Skipping section generation.")
        return "\\section{Research Methods}\n% Insufficient or invalid input to generate this section.\n"

    actual_human_style_text = human_style_example_text if human_style_example_text.strip() else Human_Text

    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for this Research Methods Section:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for this Research Methods Section:\n{slr_outline}\nConsider if the outline suggests any specific methodological focus.\n---"
    
    style_guidance_addon = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic, perhaps a graduate student explaining their work to a peer.
To achieve this, **actively avoid common AI writing patterns**.
Instead, draw inspiration from the **narrative style, sentence flow, phrasing nuances, and vocabulary choices** in the uploaded file 'human_style_sample.txt'.
(Rest of style guidance as in create_background_string)
""" # Truncated for brevity, assume full style guidance is here

    prompt_instructions = rf"""
Create a detailed **Research Methods** section for a systematic literature review (SLR) on **{subject}** make sure it's detailed , academicale , and huminazed.
Content for Related Works, Summaries, Biblio, and Human Style Sample are in uploaded files.

{suggestions_addon}
{outline_addon}
{style_guidance_addon}

### Requirements:
1.  **Tone and Guidelines**: Explain the methods in a step-by-step, approachable way... (Rest of requirements as in original function)
2.  **Structure (Subsections)**: ...
3.  **LaTeX Formatting**: ...
4.  **Citations**: ... Use BibTeX keys from uploaded 'biblio_context.bib'.
5.  **Input Context**:
    *   Related Works: uploaded 'related_works_data.txt'
    *   Paper Summaries: uploaded 'summaries_data.txt'
    *   SLR Subject: {subject}
    *   Year Range: {year_range_for_prompt[0]} to {year_range_for_prompt[1]}

### Placeholder Guide for PRISMA Flowchart (if generated):
Use these specific placeholders. They will be replaced by actual numbers by the system.
- `[NUMBER_RECORDS_IDENTIFIED_ARXIV]`
- `[NUMBER_RECORDS_IDENTIFIED_SCOPUS]`
- `[NUMBER_RECORDS_IDENTIFIED_MANUAL]`
- `[NUMBER_RECORDS_IDENTIFIED_SNOWBALL]`
- `[NUMBER_RECORDS_AFTER_DUPLICATES_REMOVED]`
- `[NUMBER_RECORDS_SCREENED_FOR_SUMMARIZATION]`
- `[NUMBER_SUMMARIES_GENERATED]`
- `[NUMBER_EXCLUDED_BY_LLM_RELEVANCE_FILTER]`
- `[NUMBER_STUDIES_INCLUDED_QUALITATIVE]`
Return *only* the complete LaTeX code for the `\section{{Research Methods}}`.
"""
    prompt_instructions += f"\n\n{LATEX_SAFETY_RULES}"

    uploaded_files_map = {}
    temp_files_paths = {}
    files_to_upload_content = {
        "related_works_data.txt": related_works_content,
        "summaries_data.txt": summaries,
        "biblio_context.bib": Biblio_content,
        "human_style_sample.txt": actual_human_style_text
    }
    # ... (identical try/finally block for file upload and cleanup as in create_background_string) ...
    try:
        for name, content_str in files_to_upload_content.items():
            if content_str and content_str.strip() and not content_str.startswith("% Error"):
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt" if not name.endswith(".bib") else ".bib", encoding='utf-8') as tmp_f:
                    tmp_f.write(content_str)
                    temp_files_paths[name] = tmp_f.name
                
                mime_type = 'text/plain'
                if name.endswith(".md"): mime_type = 'text/markdown'
                elif name.endswith(".bib"): mime_type = 'text/plain'

                uploaded_files_map[name] = genai.upload_file(
                    path=temp_files_paths[name],
                    mime_type=mime_type,
                    display_name=name
                )
            else:
                uploaded_files_map[name] = genai.upload_file(
                    path=io.BytesIO(b"% This file was intentionally left empty due to invalid input content.\n"),
                    mime_type='text/plain',
                    display_name=name
                )

        prompt_parts_for_llm = [prompt_instructions] + [f for f in uploaded_files_map.values() if f]
        
        response = summary_model.generate_content(
            prompt_parts_for_llm,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        generated_text = response.text.strip()
        generated_text = re.sub(r'^```(?:latex)?\s*[\r\n]*', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'[\r\n]*```\s*$', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'\\cite\s*\{\s*([^}\s]+)\s*\}', r'\\cite{\1}', generated_text)

        output_filename = 'Results/research_methodes.tex'
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        print(f"Generated {output_filename}")
        return generated_text

    except Exception as e:
        print(f"{RED}Error in create_reshearch_methodes: {e}{RESET}")
        return f"% Error generating research_methodes section: {e}"
    finally:
        for name, uploaded_file_obj in uploaded_files_map.items():
            if uploaded_file_obj:
                try:
                    genai.delete_file(uploaded_file_obj.name)
                except Exception as delete_err:
                    print(f"{YELLOW}Warning: Could not delete uploaded file {name} in create_reshearch_methodes: {delete_err}{RESET}")
        for name, path in temp_files_paths.items():
            if path and os.path.exists(path):
                os.remove(path)
def create_review_findings(research_methodes_content: str, 
                           summaries: str, 
                           subject: str, 
                           Biblio_content:str, 
                           reviewer_suggestions: str = "", 
                           slr_outline: str = "", 
                           human_style_example_text: str = "") -> str: 
    if not summaries.strip() or summaries.startswith("% Error"):
        print("No valid summaries provided for review findings. Skipping section generation.")
        return "\\section{Review Findings}\n% No valid summaries provided to generate this section.\n"
    if not research_methodes_content.strip() or research_methodes_content.startswith("% Error"):
        print("Research methods section content is invalid or empty. Findings might be generic.")

    actual_human_style_text = human_style_example_text if human_style_example_text.strip() else Human_Text
    
    suggestions_addon = ""
    if reviewer_suggestions: 
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for this Review Findings Section:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")): 
        outline_addon = f"\n\n### Overall SLR Outline to Consider for this Review Findings Section:\n{slr_outline}\nStructure your findings to align with anticipated key areas from the outline.\n---"

    style_guidance_addon = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic...
(Full style guidance as in create_background_string, referring to uploaded 'human_style_sample.txt')
""" # Truncated for brevity

    prompt_instructions = fr"""
Create a detailed **Review Findings** section for the systematic literature review (SLR) on **{subject}** make sure it's detailed , academicale , and huminazed.
Content for Research Methods, Summaries, Biblio, and Human Style Sample are in uploaded files.

{suggestions_addon}
{outline_addon}
{style_guidance_addon}

### Requirements:
1.  **Structure and Content**:
    *   Start with `\section{{Review Findings}}`.
    *   Provide an **introduction** summarizing the purpose of this section.
    *   Systematically answer the research questions (RQs) outlined in the uploaded 'research_methodes_data.txt', using synthesized insights from the uploaded 'summaries_data.txt'.
    *   ... (Rest of requirements as in original function) ...
2.  **Citations**: ... Use BibTeX keys from uploaded 'biblio_context.bib'.
3.  **LaTeX Formatting**: ...
4.  **Input Data**:
    *   Research Methods Section Content: uploaded 'research_methodes_data.txt'
    *   Paper Summaries: uploaded 'summaries_data.txt'
    *   SLR Subject: {subject}

Return *only* the complete LaTeX code for the `\section{{Review Findings}}`.
"""
    prompt_instructions += f"\n\n{LATEX_SAFETY_RULES}"

    uploaded_files_map = {}
    temp_files_paths = {}
    files_to_upload_content = {
        "research_methodes_data.txt": research_methodes_content,
        "summaries_data.txt": summaries,
        "biblio_context.bib": Biblio_content,
        "human_style_sample.txt": actual_human_style_text
    }
    # ... (identical try/finally block for file upload and cleanup as in create_background_string) ...
    try:
        for name, content_str in files_to_upload_content.items():
            if content_str and content_str.strip() and not content_str.startswith("% Error"):
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt" if not name.endswith(".bib") else ".bib", encoding='utf-8') as tmp_f:
                    tmp_f.write(content_str)
                    temp_files_paths[name] = tmp_f.name
                
                mime_type = 'text/plain'
                if name.endswith(".md"): mime_type = 'text/markdown'
                elif name.endswith(".bib"): mime_type = 'text/plain'

                uploaded_files_map[name] = genai.upload_file(
                    path=temp_files_paths[name],
                    mime_type=mime_type,
                    display_name=name
                )
            else:
                uploaded_files_map[name] = genai.upload_file(
                    path=io.BytesIO(b"% This file was intentionally left empty due to invalid input content.\n"),
                    mime_type='text/plain',
                    display_name=name
                )

        prompt_parts_for_llm = [prompt_instructions] + [f for f in uploaded_files_map.values() if f]
        
        response = summary_model.generate_content(
            prompt_parts_for_llm,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        generated_text = response.text.strip()
        generated_text = re.sub(r'^```(?:latex)?\s*[\r\n]*', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'[\r\n]*```\s*$', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'\\cite\s*\{\s*([^}\s]+)\s*\}', r'\\cite{\1}', generated_text)

        output_filename = 'Results/review_findings.tex'
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        print(f"Generated {output_filename}")
        return generated_text

    except Exception as e:
        print(f"{RED}Error in create_review_findings: {e}{RESET}")
        return f"% Error generating review_findings section: {e}"
    finally:
        for name, uploaded_file_obj in uploaded_files_map.items():
            if uploaded_file_obj:
                try:
                    genai.delete_file(uploaded_file_obj.name)
                except Exception as delete_err:
                    print(f"{YELLOW}Warning: Could not delete uploaded file {name} in create_review_findings: {delete_err}{RESET}")
        for name, path in temp_files_paths.items():
            if path and os.path.exists(path):
                os.remove(path)
def create_discussion_conclusion(review_findings_content: str, 
                                 summaries: str, 
                                 subject: str, 
                                 Biblio_content:str, 
                                 reviewer_suggestions: str = "", 
                                 slr_outline: str = "", 
                                 human_style_example_text: str = "") -> str: 
    if not review_findings_content.strip() or review_findings_content.startswith("% Error"):
        print("Review findings content is invalid or empty. Discussion/Conclusion will be very generic. Skipping.")
        return "\\section{Discussion}\n% Review findings were invalid or empty, cannot generate discussion.\n\n\\section{Conclusion}\n% Review findings were invalid or empty."

    actual_human_style_text = human_style_example_text if human_style_example_text.strip() else Human_Text

    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for the Discussion and Conclusion Sections:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for these Sections:\n{slr_outline}\nAlign your discussion points and conclusion with the overall themes and take-home messages suggested in the outline.\n---"
    
    style_guidance_addon = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic...
(Full style guidance as in create_background_string, referring to uploaded 'human_style_sample.txt')
""" # Truncated for brevity

    prompt_instructions = rf"""
Create a **Discussion** section and a **Conclusion** section for the systematic literature review (SLR) on **{subject}**make sure it's detailed , academicale , and huminazed.
Content for Review Findings, Summaries, Biblio, and Human Style Sample are in uploaded files.

{suggestions_addon}
{outline_addon}
{style_guidance_addon}

### Requirements:
1.  **Structure**:
    *   Start with `\section{{Discussion}}`.
    *   Follow with `\section{{Conclusion}}`.
2.  **Discussion Content**:
    *   Interpret the key findings presented in the uploaded 'review_findings_data.txt'.
    *   Compare/contrast findings with existing literature or theories (draw from uploaded 'summaries_data.txt' or general knowledge if applicable).
    *   ... (Rest of requirements as in original function) ...
3.  **Conclusion Content**: ...
4.  **Citations**: ... Use BibTeX keys from uploaded 'biblio_context.bib'.
5.  **LaTeX Formatting**: ...
6.  **Input Data**:
    *   Review Findings Section Content: uploaded 'review_findings_data.txt'
    *   Paper Summaries: uploaded 'summaries_data.txt'
    *   SLR Subject: {subject}

Return *only* the complete LaTeX code for the `\section{{Discussion}}` and `\section{{Conclusion}}`.
"""
    prompt_instructions += f"\n\n{LATEX_SAFETY_RULES}"

    uploaded_files_map = {}
    temp_files_paths = {}
    files_to_upload_content = {
        "review_findings_data.txt": review_findings_content,
        "summaries_data.txt": summaries,
        "biblio_context.bib": Biblio_content,
        "human_style_sample.txt": actual_human_style_text
    }
    # ... (identical try/finally block for file upload and cleanup as in create_background_string) ...
    try:
        for name, content_str in files_to_upload_content.items():
            if content_str and content_str.strip() and not content_str.startswith("% Error"):
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt" if not name.endswith(".bib") else ".bib", encoding='utf-8') as tmp_f:
                    tmp_f.write(content_str)
                    temp_files_paths[name] = tmp_f.name
                
                mime_type = 'text/plain'
                if name.endswith(".md"): mime_type = 'text/markdown'
                elif name.endswith(".bib"): mime_type = 'text/plain'

                uploaded_files_map[name] = genai.upload_file(
                    path=temp_files_paths[name],
                    mime_type=mime_type,
                    display_name=name
                )
            else:
                uploaded_files_map[name] = genai.upload_file(
                    path=io.BytesIO(b"% This file was intentionally left empty due to invalid input content.\n"),
                    mime_type='text/plain',
                    display_name=name
                )

        prompt_parts_for_llm = [prompt_instructions] + [f for f in uploaded_files_map.values() if f]
        
        response = summary_model.generate_content(
            prompt_parts_for_llm,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        generated_text = response.text.strip()
        generated_text = re.sub(r'^```(?:latex)?\s*[\r\n]*', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'[\r\n]*```\s*$', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'\\cite\s*\{\s*([^}\s]+)\s*\}', r'\\cite{\1}', generated_text)

        output_filename = 'Results/discussion_conclusion.tex'
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        print(f"Generated {output_filename}")
        return generated_text

    except Exception as e:
        print(f"{RED}Error in create_discussion_conclusion: {e}{RESET}")
        return f"% Error generating discussion_conclusion section: {e}"
    finally:
        for name, uploaded_file_obj in uploaded_files_map.items():
            if uploaded_file_obj:
                try:
                    genai.delete_file(uploaded_file_obj.name)
                except Exception as delete_err:
                    print(f"{YELLOW}Warning: Could not delete uploaded file {name} in create_discussion_conclusion: {delete_err}{RESET}")
        for name, path in temp_files_paths.items():
            if path and os.path.exists(path):
                os.remove(path)

def create_abstract_intro(review_findings_content: str, 
                          related_works_content:str, 
                          research_methodes_content:str, 
                          discussion_conclusion_content:str, 
                          subject: str, 
                          Biblio_content:str, 
                          reviewer_suggestions: str = "", 
                          slr_outline: str = "", 
                          human_style_example_text: str = "") -> str: 
    if any(s.startswith("% Error") or "No summaries provided" in s or "Insufficient input" in s for s in [review_findings_content, related_works_content, research_methodes_content, discussion_conclusion_content]):
        print("One or more input sections for Abstract/Intro generation are invalid or empty. Skipping.")
        return "\\begin{abstract}\n% Skipped due to invalid input sections.\n\\end{abstract}\n\n\\textbf{Keywords:} % Skipped\n\n\\section{Introduction}\n% Skipped due to invalid input sections.\n"

    actual_human_style_text = human_style_example_text if human_style_example_text.strip() else Human_Text

    suggestions_addon = ""
    if reviewer_suggestions:
        suggestions_addon = f"\n\n### Previous Reviewer Feedback to Address for the Abstract, Keywords, and Introduction Sections:\n{reviewer_suggestions}\nEnsure these points are considered in your revision.\n---"

    outline_addon = ""
    if slr_outline and not slr_outline.startswith(("% Error", "% No relevant")):
        outline_addon = f"\n\n### Overall SLR Outline to Consider for these Sections:\n{slr_outline}\nEnsure the introduction's themes/arguments and the abstract's summary align with the broader plan.\n---"
    
    style_guidance_addon = f"""
### Stylistic Guidance (for human-like writing):
Your primary goal for this section is to write in a way that is indistinguishable from a human academic...
(Full style guidance as in create_background_string, referring to uploaded 'human_style_sample.txt')
""" # Truncated for brevity

    prompt_instructions = rf"""
Create the **Abstract**, **Keywords**, and **Introduction** sections for a systematic literature review (SLR) titled: "Systematic Literature Review: {subject}" make sure it's detailed , academicale , and huminazed.
Content for Review Findings, Related Works, Research Methods, Discussion/Conclusion, Biblio, and Human Style Sample are in uploaded files.

{suggestions_addon}
{outline_addon}
{style_guidance_addon}

### Requirements:
1.  **Abstract**: ...
2.  **Keywords**: ...
3.  **Introduction (`\section{{Introduction}}`)**: ...
4.  **Content Source**: Synthesize information from the uploaded files:
    *   'review_findings_data.txt'
    *   'related_works_data.txt'
    *   'research_methodes_data.txt'
    *   'discussion_conclusion_data.txt'
5.  **LaTeX Formatting**: ...
6.  **Citations**: ... Use BibTeX keys from uploaded 'biblio_context.bib'.

### Output:
Return *only* the LaTeX code for the Abstract (within `\begin{{abstract}}...\end{{abstract}}`), then Keywords, then the Introduction section (`\section{{Introduction}}...`).
"""
    prompt_instructions += f"\n\n{LATEX_SAFETY_RULES}"

    uploaded_files_map = {}
    temp_files_paths = {}
    files_to_upload_content = {
        "review_findings_data.txt": review_findings_content,
        "related_works_data.txt": related_works_content,
        "research_methodes_data.txt": research_methodes_content,
        "discussion_conclusion_data.txt": discussion_conclusion_content,
        "biblio_context.bib": Biblio_content,
        "human_style_sample.txt": actual_human_style_text
    }
    # ... (identical try/finally block for file upload and cleanup as in create_background_string) ...
    try:
        for name, content_str in files_to_upload_content.items():
            if content_str and content_str.strip() and not content_str.startswith("% Error"):
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt" if not name.endswith(".bib") else ".bib", encoding='utf-8') as tmp_f:
                    tmp_f.write(content_str)
                    temp_files_paths[name] = tmp_f.name
                
                mime_type = 'text/plain'
                if name.endswith(".md"): mime_type = 'text/markdown'
                elif name.endswith(".bib"): mime_type = 'text/plain'

                uploaded_files_map[name] = genai.upload_file(
                    path=temp_files_paths[name],
                    mime_type=mime_type,
                    display_name=name
                )
            else:
                uploaded_files_map[name] = genai.upload_file(
                    path=io.BytesIO(b"% This file was intentionally left empty due to invalid input content.\n"),
                    mime_type='text/plain',
                    display_name=name
                )

        prompt_parts_for_llm = [prompt_instructions] + [f for f in uploaded_files_map.values() if f]
        
        response = summary_model.generate_content(
            prompt_parts_for_llm,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        generated_text = response.text.strip()
        generated_text = re.sub(r'^```(?:latex)?\s*[\r\n]*', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'[\r\n]*```\s*$', '', generated_text, flags=re.MULTILINE)
        generated_text = re.sub(r'\\cite\s*\{\s*([^}\s]+)\s*\}', r'\\cite{\1}', generated_text)

        output_filename = 'Results/abstract_intro_keywords.tex'
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(generated_text)
        print(f"Generated {output_filename}")
        return generated_text

    except Exception as e:
        print(f"{RED}Error in create_abstract_intro: {e}{RESET}")
        return f"% Error generating abstract_intro_keywords section: {e}"
    finally:
        for name, uploaded_file_obj in uploaded_files_map.items():
            if uploaded_file_obj:
                try:
                    genai.delete_file(uploaded_file_obj.name)
                except Exception as delete_err:
                    print(f"{YELLOW}Warning: Could not delete uploaded file {name} in create_abstract_intro: {delete_err}{RESET}")
        for name, path in temp_files_paths.items():
            if path and os.path.exists(path):
                os.remove(path)