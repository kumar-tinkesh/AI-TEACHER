import os
from dotenv import load_dotenv
from ollama import Client
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")

class OllamaCloudClient:
    def __init__(self):
        self.client = Client(
            host=os.getenv("OLLAMA_BASE_URL"),
            headers={
                "Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"
            }
        )

        self.model = os.getenv("OLLAMA_MODEL")

    def query(self, message: str, system_prompt: str = SYSTEM_PROMPT):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        response = self.client.chat(
            model=self.model,
            messages=messages
        )
        # print("row response from ollama cloud: ", response)

        return response.message.content


class GroqCloudClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("GROQ_BASE_URL"),
            api_key=os.getenv("GROQ_API_KEY")
        )

        self.model = os.getenv("GROQ_MODEL")

    def query(self, message: str, system_prompt: str = SYSTEM_PROMPT):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=float(os.getenv("TEMPERATURE", 0.7)),
            max_tokens=int(os.getenv("MAX_TOKENS", 512)),
            messages=messages
        )
        # print("row response from groq cloude : ", response)
        
        return response.choices[0].message.content

# # ================================
# # Usage
# # ================================
# if __name__ == "__main__":

#     # Ollama Cloud
#     ollama_ai = OllamaCloudClient()

#     ollama_reply = ollama_ai.query("Hello")
#     print("Ollama Cloud Response:")
#     print(ollama_reply)

#     print("\n" + "=" * 50 + "\n")

#     # Groq
#     groq_ai = GroqCloudClient()

#     groq_reply = groq_ai.query("Hello")
#     print("Groq Response:")
#     print(groq_reply)
