import os
import google.generativeai as genai
import json

def init_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)

def parse_expense(text):
    # Find the best available model dynamically
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # Prefer flash models as they are fast and cheap
    flash_models = [m for m in available_models if 'flash' in m]
    model_name = flash_models[0] if flash_models else available_models[0]
    
    model = genai.GenerativeModel(model_name)
    prompt = f"""
    You are a finance assistant. Extract the details from the user's message.
    Message: "{text}"
    
    Respond ONLY with a valid JSON object containing the following keys:
    - amount: (float) the amount mentioned. If no amount is mentioned, return null.
    - category: (string) the type of expense (e.g., taxi, food). If not found, return "other".
    - payment_source: (string) the payment method (e.g., UPI, Credit Card, Cash).
    - description: (string) a brief summary.
    - is_expense: (boolean) true if the message is reporting a standard expense.
    - is_debt: (boolean) true if the message is about owing money or someone owing the user money.
    - is_debt_clear: (boolean) true if the message is about clearing or paying off an existing debt.
    - debt_type: (string) "i_owe" if the user owes money to someone else, "owed_to_me" if someone owes the user money.
    - person_name: (string) the name of the person involved in the debt (e.g., "Aditya").
    """
    
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Strip markdown json blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:-3].strip()
            
        return json.loads(result_text)
    except Exception as e:
        print(f"Failed to parse LLM response: {e}")
        return None

def get_finance_advice(user_id, user_message, current_monthly_total, recent_expenses):
    # Find the best available model dynamically
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    flash_models = [m for m in available_models if 'flash' in m]
    model_name = flash_models[0] if flash_models else available_models[0]
    
    model = genai.GenerativeModel(model_name)
    expenses_str = "\n".join([f"- {e[0]} for {e[1]} via {e[2]} on {e[4]}" for e in recent_expenses])
    prompt = f"""
    You are a helpful and friendly personal finance agent. 
    The user is asking a question or seeking advice: "{user_message}"
    
    Here is their recent financial context:
    - Total spent this month: {current_monthly_total}
    - Recent expenses:
    {expenses_str}
    
    Provide a concise, helpful response. You can give budgeting advice, analyze their spending, or just answer their question. Keep it brief and suitable for a chat message on Telegram/WhatsApp. Use emojis where appropriate.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Failed to generate advice: {e}")
        return "I'm having trouble analyzing your request right now. Let's try again later!"
