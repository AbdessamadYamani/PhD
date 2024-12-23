from crewai_tools import ScrapeWebsiteTool
from crewai_tools import SerperDevTool
import os
import re
from langchain.tools import tool

os.environ["SERPER_API_KEY"] = "7e4dd3b3d7522086ec4f742aec40d4fe269f855a"

class Scrapping:

    @tool("Search tool")
    def search_and_scrape(search_query:str):
      """
      use this tool if you want to search about anythnig through internet using keywords as parameter.
      """

      def serper():
        """
        This function extracts links from the search results for the given search query.

        Returns:
            list: A list containing the extracted website URLs.
        """
        tool = SerperDevTool(n_results=2).run(search_query=search_query)
        output = str(tool)  # Convert the tool object to a string
        links = []  # List to store extracted links
        # Split the output based on the link separator
        split_output = output.split("Link: ")

        # Skip the first element (title) and extract links from the rest
        link_regex = r"^(.*?)\n"  # This pattern captures everything up to the first newline

        for element in split_output[1:]:
          match = re.search(link_regex, element)
          if match:
            link = match.group(1).strip()  # Extract and remove leading/trailing whitespace
            links.append(link)
        print(links)
        return links

      def web_scrapping(urls):
        """
        This function scrapes the content of each website provided in the list of URLs.

        Args:
            urls (list): A list of website URLs to scrape.

        Returns:
            list: A list containing the scraped content from each website.
        """
        scraped_content = []
        for url in urls:
          # Initialize the tool with the specific website URL for each iteration
          tool = ScrapeWebsiteTool(website_url=url)

          # Extract the text from the site and append it to the list
          text = tool.run()
          scraped_content.append(text)

        return scraped_content

      # Get links from search
      search_results = serper()
      print(search_results)
      # Check if any links were found
      if search_results:
        # Scrape content from each link
        scraped_data = web_scrapping(search_results)

        # Print or process the scraped data list
        return scraped_data
      else:
        print("No links found in the search results.")

