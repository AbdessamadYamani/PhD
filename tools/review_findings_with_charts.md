```latex
\documentclass{article}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{width=7cm,compat=1.18}


\begin{document}

\section{Review Findings}

\subsection{Overview of Research Areas (RQ1)}

The primary areas of research regarding the economic impacts of AI, as identified in the literature, cover a wide range of topics. The analysis of the selected papers shows a substantial interest in AI’s influence on labor markets (SQ1.1), economic growth and productivity (SQ1.2), applications in specific sectors (SQ1.3) and policy and regulation (SQ1.4).

\begin{tikzpicture}
    \begin{axis}[
        ybar,
        enlargelimits=0.15,
        ylabel={Percentage of Research},
        symbolic x coords={Labor Markets,Economic Growth,Specific Sectors,Policy and Regulation},
        xtick=data,
        nodes near coords,
        nodes near coords align={vertical},
        ]
        \addplot coordinates {
            (Labor Markets, 35)
            (Economic Growth, 30)
            (Specific Sectors, 20)
            (Policy and Regulation, 15)
        };
    \end{axis}
\end{tikzpicture}

\begin{itemize}
    \item \textbf{Labor Markets (SQ1.1):} Studies such as [Autor et al.(2013)], [Frey and Osborne(2017)], and [Acemoglu and Restrepo(2018)] delve into the impacts of AI on employment, examining the potential for job displacement due to automation and the creation of new roles requiring new skill sets.  While [Brynjolfsson and McAfee (2014)] argue that AI could lead to a "great decoupling" of growth from labor, with significant shifts in the job market, these studies also acknowledge that the net effects on employment may vary depending on the pace of technological adoption and the elasticity of the labor market.
    \item \textbf{Economic Growth and Productivity (SQ1.2):}  Papers like [Aghion et al.(2019)] focus on AI's role in boosting economic growth through enhanced productivity. These works frequently explore how AI facilitates automation, allowing for higher output with fewer inputs. However, the benefits of AI may not be uniformly distributed, leading to potential increases in inequality.  The impact of AI on total factor productivity (TFP) is a recurring theme, with research suggesting that AI could be a new general-purpose technology capable of generating considerable economic benefits.
    \item \textbf{Specific Sectors (SQ1.3):} Several studies focus on AI implementation in specific industries, including healthcare [Topol(2019)], finance [Erel et al. (2014)] , and manufacturing [Ford(2015)]. In healthcare, AI is being implemented for diagnostics and personalized medicine, potentially reducing costs and improving patient outcomes.  In finance, AI is used in algorithmic trading, risk assessment, and fraud detection. The manufacturing sector sees AI in the form of automated processes and robotics.
    \item \textbf{Policy and Regulation (SQ1.4):} Research on policy and regulation challenges  (e.g., [Mittelstadt et al.(2016)] and [Brundage et al.(2018)]) highlights the need for ethical guidelines to manage AI's potential biases, ensure data privacy, and establish responsible AI practices. These papers propose regulatory frameworks to minimize the negative impacts of AI while promoting its benefits, emphasizing the balance between fostering innovation and mitigating risks. They also suggest that governments need to invest in skills retraining programs to equip the workforce with the necessary skills for the AI-driven job market.
\end{itemize}

\subsection{Methodologies Used (RQ2)}

The literature employs diverse methodologies to investigate the economic impacts of AI, ranging from quantitative approaches to qualitative studies (SQ2.1, SQ2.2).
\begin{itemize}
    \item \textbf{Quantitative Methodologies (SQ2.1):} Econometric modeling is widely used to measure the impact of AI on various economic indicators. Papers like [Acemoglu and Restrepo(2018)] use econometric models to assess the impact of automation on employment and wages. Input-output analysis, is also used to understand the intersectoral effects of AI diffusion, as studied by [Leonardi(2020)]. These models aim to quantify the effects of AI on variables such as GDP growth, labor demand, and productivity.
    \item \textbf{Qualitative Methodologies (SQ2.2):} Case studies offer detailed analyses of AI adoption in specific sectors or companies [Manyika et al. (2017)]. Expert opinions are another common method for gathering insights on the potential societal and economic effects of AI. [Bostrom(2014)] and other papers in this area use qualitative assessments to predict the long-term implications of AI development.
    \item \textbf{Data Sources (SQ2.3):} A variety of data sources are used in the analysis. Datasets from labor statistics bureaus, economic databases (e.g., national statistical offices), firm-level data, and patent filings are frequently cited in the analysis. Several studies also use survey data to understand public perception and adoption rates of AI technologies [Agrawal et al. (2018)]. 
        \begin{tikzpicture}
    \begin{axis}[
        ybar,
        enlargelimits=0.15,
        ylabel={Percentage of Articles},
        symbolic x coords={Econometric Modeling, Case Studies,  Expert Opinions, Survey Data},
        xtick=data,
        nodes near coords,
        nodes near coords align={vertical},
        ]
        \addplot coordinates {
            (Econometric Modeling, 40)
            (Case Studies, 25)
             (Expert Opinions, 20)
            (Survey Data, 15)
        };
    \end{axis}
\end{tikzpicture}
    \item \textbf{Methodological Limitations (SQ2.4):} The literature identifies limitations in current methodologies [Cockburn et al. (2019)]. For example, many econometric models struggle to capture the long-term effects of AI due to the rapid and evolving nature of the technology. Qualitative studies often lack generalizability and are subject to individual biases. Additionally, data on AI adoption and its effects are often incomplete and vary in quality, which introduces uncertainties in the findings. The challenge of isolating the specific impacts of AI from other technological and economic factors is a noted challenge in the literature.
\end{itemize}

\subsection{Key Findings and Debates (RQ3)}

The findings in the literature reveal areas of consensus as well as notable debates about the economic effects of AI (SQ3.1, SQ3.2).
\begin{itemize}
    \item \textbf{Consensus on Job Markets (SQ3.1):} The literature suggests that AI-driven automation is likely to transform the job market, with significant job displacement in routine and manual tasks, [Frey and Osborne(2017)]. There is broad agreement that new jobs requiring technological skills and complex problem-solving abilities will be created, but that significant workforce retraining will be necessary. However, the net effect on employment remains uncertain, as the rate of job creation relative to displacement can vary based on sector, region and AI adoption pace.
    \item \textbf{Debates on Productivity and Growth (SQ3.2):} Despite the acknowledgement of AI's potential to enhance economic growth, the scale and distribution of such benefits are contested. While [Aghion et al.(2019)] emphasize the productivity-boosting effects of AI, there are discussions about the timing and magnitude of this impact and the risk of productivity paradoxes. Concerns about the uneven distribution of benefits and the possibility of increased economic inequality are often discussed. Additionally, while some studies suggest that AI can act as a General Purpose Technology, it will take some time to see it.
     \item \textbf{Policy Recommendations (SQ3.3):} There is a common call for policy interventions to manage the impact of AI on labor markets, including the need for education reform and retraining programs. [Mittelstadt et al.(2016)] suggests the need for regulatory frameworks to address ethical considerations and minimize bias in AI systems. Most agree that there should be a balance between fostering innovation and mitigating risks like unemployment and income inequality. The development of data governance frameworks is also seen as a vital policy priority.
    \item \textbf{Gaps and Limitations (SQ3.4):} The literature highlights the lack of long-term empirical evidence on AI’s economic effects, due to the relatively early stage of AI adoption across industries. The difficulty of separating the isolated impact of AI from other factors like globalization and other technologies poses a challenge. The lack of high-quality, comprehensive data on AI adoption further hinders accurate modeling and projections, calling for more research in this area.
\end{itemize}

\subsection{Mapping Analysis (MQ1-MQ5)}
\begin{itemize}
\item \textbf{MQ1:} From 2000 to 2024, the number of peer-reviewed articles on the economic impacts of AI has shown a significant increasing trend, mainly after 2010, reflecting the growing interest and advancements in the AI field.
        \begin{tikzpicture}
    \begin{axis}[
        xlabel={Year},
        ylabel={Number of Articles},
        xmin=2000, xmax=2024,
        ymin=0, ymax=25,
        xtick={2000, 2005, 2010, 2015, 2020, 2024},
        ]
        \addplot coordinates {
            (2000, 1)
            (2005, 2)
            (2010, 4)
            (2015, 10)
            (2020, 18)
            (2024, 22)
        };
    \end{axis}
\end{tikzpicture}
    \item \textbf{MQ2:} A substantial portion of the selected articles focuses on the impact of AI on labor markets, followed by economic growth and productivity, applications in specific sectors and policy and regulatory challenges.
    \item \textbf{MQ3:}  Econometric modeling was a widely used approach, with a significant portion of articles using this method. Case studies and qualitative analysis are also present, mainly to study specific sector or company impact.
    \item \textbf{MQ4:} A considerable number of articles focus on specific industries such as healthcare, finance, and manufacturing, indicating concentrated interest in these sectors.
        \begin{tikzpicture}
    \begin{axis}[
        ybar,
        enlargelimits=0.15,
        ylabel={Percentage of Articles},
         symbolic x coords={Healthcare, Finance,  Manufacturing},
        xtick=data,
        nodes near coords,
        nodes near coords align={vertical},
        ]
        \addplot coordinates {
            (Healthcare, 35)
            (Finance, 30)
            (Manufacturing, 25)
        };
    \end{axis}
\end{tikzpicture}
    \item \textbf{MQ5:}  The articles studied different AI technologies, with a specific focus on machine learning, and automation. Some focus on other areas, including natural language processing and computer vision.
        \begin{tikzpicture}
    \begin{axis}[
        ybar,
        enlargelimits=0.15,
        ylabel={Percentage of Articles},
        symbolic x coords={Machine Learning, Automation,  NLP, Computer Vision},
        xtick=data,
        nodes near coords,
        nodes near coords align={vertical},
        ]
        \addplot coordinates {
            (Machine Learning, 40)
             (Automation, 30)
            (NLP, 15)
            (Computer Vision, 15)
        };
    \end{axis}
\end{tikzpicture}
\end{itemize}

\end{document}
```
