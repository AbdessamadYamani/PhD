from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
# from llamaapi import LlamaAPI
# from langchain_experimental.llms import ChatLlamaAPI




key = "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"
key1 = "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"
key2 = "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"
key3="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"
key4="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"
key5="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"
# llama-3.1-8b-instant	, llama3-8b-8192,llama-3.1-70b-versatile



# # Replace 'Your_API_Token' with your actual API token
# llama = LlamaAPI("LA-03cb897efa784c6ea5f265af4e9f25b3e035ece5b6614cc0af4ef813067b89fb")
# model = ChatLlamaAPI(client=llama,model="llama3.3-70b")





llmLlaMa0=ChatGroq(api_key=key,model="llama3-70b-8192")
llmLlaMa1=ChatGroq(api_key=key1,model="llama-3.1-70b-versatile")
llmLlaMa2=ChatGroq(api_key=key2,model="llama3-groq-8b-8192-tool-use-preview")
llmLlaMa3=ChatGroq(api_key=key3,model="llama-3.1-70b-versatile")
llmLlaMa4=ChatGroq(api_key=key4,model="llama-3.1-8b-instant")
llmLlaMa5=ChatGroq(api_key=key5,model="llama-3.1-70b-versatile")


# Gemini key : AIzaSyB5sRD6w4zFRswpCQnLt__h4hirhRzEQsI

# gemini
openai_api_key = "AIzaSyDB34rofMFLYfo0zwXnPZ6DLWHs3-I_rjM"
llmGemini = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=openai_api_key)


Subject="Exploring the Impact of the integration of  Large Language Models on Serious Game"