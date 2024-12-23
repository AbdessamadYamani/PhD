from crewai import Task
from tools import arxive_search_tool
from tools import web_scrapping_tool



Subject = "LLM serious games"

class AllTasks():
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key

    def create_related_works(self, agent):
        description = f"""
Create the seaction [Related works] where you should search for the literature reviews relevant to the subject , the more details fo give is the best and you should respect these things:
1- Change the keywords each time you search for new papers.
2- For each paper you should summarize it and provide what is the main idea of the paper and how it is related to the subject.
your results should be in Overleaf code and you should add a table at the end that summarize for each paper the main idea and how it is related to the subject, and for each of them give the link to the paper.
Subject : {Subject}

        """   
        return Task(
            description=description,
            expected_output="""
Related works :
---------------
The Related Works section of an academic article is crucial for situating your research within the existing body of knowledge. Here’s a detailed overview of what this section should include:
Purpose of the Related Works Section
Contextualization: This section helps readers understand the background and context of your research problem by reviewing relevant literature.
Comparison: It highlights how your work differs from or builds upon previous studies, emphasizing its novelty and significance.
Key Components to Include
Overview of the Field:
Start with a brief introduction to the broader research area. This sets the stage for more specific discussions about related works.
For example, if your paper focuses on machine learning applications, mention foundational works in machine learning before diving into specifics.
Selection of Relevant Studies:
Choose key papers that are directly related to your work. Avoid an exhaustive list; instead, focus on those that provide substantial insights or contrast with your findings.
Each selected paper should be accompanied by a concise summary that explains its relevance to your research.
Critical Analysis:
Discuss the strengths and weaknesses of the related works. This analysis should clarify how these studies contribute to your understanding of the topic and where they fall short.
Highlight gaps in the literature that your research aims to address.
Connection to Your Work:
Clearly articulate how each piece of referenced work relates to your own research. This could involve discussing how you are building on their findings, addressing their limitations, or exploring different methodologies.
Use phrases like "In contrast to [Author's] findings..." or "Building upon [Author's] approach..." to establish these connections.
Organizational Structure:
Consider organizing the section thematically or chronologically. A thematic structure allows for grouping studies by topic, while a chronological approach can illustrate the evolution of research in your area.
Ensure that the flow of information is logical and contributes to a coherent narrative throughout the paper.
Writing Style
Aim for clarity and conciseness while providing enough detail to inform readers about each study's contributions.
Avoid overly technical jargon unless necessary, as this can alienate readers unfamiliar with specific terms.
Conclusion
The Related Works section should not merely enumerate previous studies but instead create a narrative that integrates these works into a cohesive framework supporting your research. By critically engaging with existing literature, you position your study as a meaningful contribution to the field, paving the way for future research directions.

""",
            output_file="Related_works.md",
            tools=[arxive_search_tool.fetch_arxiv_papers],
            agent=agent        )
    def create_research_string(self, agent,context):
        description = f"""You should create the research string based on what each data base  prefrences, the string should be based on the subject {Subject} and the context you have  following these steps :
        1- Check for each data base how the search string is the data bases are the following : Research gate , Arxive , Scopus.
        2- for each data base create the search string based on the subject and the context you have.
        
        """   
        return Task(
            description=description,
            expected_output="the results should be in overleaf code , it should be in a table that have 2 columns the name of the database and its search string.",
            output_file="search_string.md",
            tools=[web_scrapping_tool.Scrapping.search_and_scrape],
            agent=agent ,
                   context=context  )
    def create_research_questions_and_mappings(self, agent,context):
        description = f"""based on the context you have and the subject you should provide the research questions and the mappings question, each research question may have some sub-questions if needed and a motivation that answer the question "how the result of this qiestion will help us" , the mapping question should be quantitative 
        each search strgin should have many keywords related to the subject {Subject} and the context you have.
        """   
        return Task(
            description=description,
            expected_output="the results should be in overleaf code , it should be in a 2 tables one for the research questions and the other for the mapping question.The one for research questions should have 4 columns one for the reference of the question , the second for the question, the third for the sub-questions and the last for the motivation. The one for the mapping question should have 2 columns one for the question and the other for the mapping.",
            output_file="research_questions_and_mappings.md",
            tools=[],
            agent=agent ,
                   context=context  )
    