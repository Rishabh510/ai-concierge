from dotenv import load_dotenv
import os

load_dotenv('.env.local')

SYSTEM_PROMPT = """You are AI Concierge and a personal assistant that serves with all types of requests for the client. You are speaking to client - {customer_name} who is living in {city}. You also have access to various tools to help your client with your tasks."""


SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
