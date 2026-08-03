from openai import AsyncOpenAI
from .prompt_loader import load_prompt
from backend.config import settings
import asyncio

async def generate_report_full(ticker: str, context_markdown: str, llm_provider: str, api_key: str, system_prompt: str, language: str = "en") -> str:
    """
    Generates a full report (non-streaming) using the given system prompt.
    Used for the parallel Optimistic and Pessimistic agents.
    """
    user_prompt = f"Target Company: {ticker}\n\nHere is the collected context data:\n{context_markdown}\n\n"
    if language == "it":
        user_prompt += "IMPORTANTE: Scrivi l'intera analisi ESCLUSIVAMENTE in lingua ITALIANA."
    else:
        user_prompt += "Please proceed with the analysis."
    
    if llm_provider == "openai":
        key = api_key if api_key else settings.openai_api_key
        if not key:
            return "Error: No OpenAI API key provided."
            
        client = AsyncOpenAI(api_key=key, base_url="https://api.deepseek.com")
        
        try:
            response = await client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error during generation: {str(e)}"
            
    else:
        # Fallback / mock for unsupported MVP providers
        await asyncio.sleep(2)
        return f"Mock full report for {ticker} using {llm_provider}.\n\nContext length: {len(context_markdown)}"


async def generate_arbiter_report(ticker: str, context_markdown: str, optimistic_report: str, pessimistic_report: str, llm_provider: str, api_key: str, language: str = "en"):
    """
    Streams the final synthesized report from the Arbiter agent.
    """
    prompt_file = "arbiter_prompt_it.md" if language == "it" else "arbiter_prompt.md"
    system_prompt = load_prompt(prompt_file)
    
    # Construct the specialized arbiter user prompt
    user_prompt = f"Target Company: {ticker}\n\n"
    user_prompt += f"--- RAW FINANCIAL DATA CONTEXT ---\n{context_markdown}\n\n"
    user_prompt += f"--- OPTIMISTIC AGENT REPORT ---\n{optimistic_report}\n\n"
    user_prompt += f"--- PESSIMISTIC AGENT REPORT ---\n{pessimistic_report}\n\n"
    if language == "it":
        user_prompt += "IMPORTANTE: Genera l'INTERO report finale, tutte le sezioni, le tabelle e la scorecard ESCLUSIVAMENTE IN LINGUA ITALIANA."
    else:
        user_prompt += "Please proceed with the adjudication and synthesis."
    
    if llm_provider == "openai":
        key = api_key if api_key else settings.openai_api_key
        if not key:
            yield "Error: No OpenAI API key provided."
            return
            
        client = AsyncOpenAI(api_key=key, base_url="https://api.deepseek.com")
        
        try:
            stream = await client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n\nError during generation: {str(e)}"
            
    else:
        # Fallback / mock for unsupported MVP providers
        yield f"Generating Arbiter report for {ticker} using {llm_provider}...\n\n"
        await asyncio.sleep(1)
        yield "\nDone."

