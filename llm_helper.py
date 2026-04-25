import os
import google.generativeai as genai
import json

MODEL_NAME = None

def init_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)

def get_model_name():
    global MODEL_NAME
    if MODEL_NAME is None:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in available_models if 'flash' in m]
        MODEL_NAME = flash_models[0] if flash_models else available_models[0]
    return MODEL_NAME

def parse_expense(text):
    model = genai.GenerativeModel(get_model_name())
    prompt = f"""
    You are a finance assistant. Extract the details from the user's message.
    Message: "{text}"
    
    Respond ONLY with a valid JSON object containing the following keys:
    - amount: (float) the amount mentioned. Return null if none.
    - category: (string) the type of expense.
    - payment_source: (string) the payment method.
    - description: (string) a brief summary.
    - is_expense: (boolean) true if it's a standard expense.
    - is_debt: (boolean) true if owing or owed money.
    - is_debt_clear: (boolean) true if clearing a debt.
    - debt_type: (string) "i_owe" or "owed_to_me".
    - person_name: (string) name of person for debt.
    - is_recurring_setup: (boolean) true if setting up a new recurring expense/subscription (e.g., "paying 37000 to landlord every month").
    - is_recurring_update: (boolean) true if updating the amount of an existing recurring expense (e.g., "rent increased to 39000").
    - is_recurring_payment: (boolean) true if the user is mentioning they have paid a recurring expense.
    - is_autopay: (boolean) true if the recurring expense is auto-debited / autopay.
    - payee: (string) who is receiving the recurring payment (e.g., "landlord", "Netflix", "Gemini").
    - day_of_month: (integer) The specific day of the month (1-31) the recurring expense happens or is due. Null if not specified.
    """
    
    try:
        # Request native JSON from Gemini to guarantee perfect formatting
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"Failed to parse LLM response: {e}")
        return None

def get_finance_advice(user_id, user_message, current_monthly_total, recent_expenses, recurring_expenses):
    model = genai.GenerativeModel(get_model_name())
    expenses_str = "\n".join([f"- {e[0]} for {e[1]} via {e[2]} on {e[4]}" for e in recent_expenses])
    recurring_str = "\n".join([f"- {e[4]} ({e[1]}) to {e[3]} | Autopay: {e[5]} | Last Paid: {e[7]}" for e in recurring_expenses])
    
    prompt = f"""
    You are an AI personal finance agent on Telegram. 
    Your capabilities: You track daily expenses, manage debts/IOUs, handle recurring subscriptions/rent (with custom dates and autopay), and give budgeting advice.
    
    User message: "{user_message}"
    
    Context:
    - Total spent this month: {current_monthly_total}
    - Recent expenses:
    {expenses_str}
    - Recurring Expenses & Subscriptions (Autopay info and Paid status):
    {recurring_str}
    
    If the user asks what you can do or how to use you, cheerfully explain your capabilities with simple examples.
    If the user asks what subscriptions they have running, list them nicely from the context.
    If they ask what recurring expenses are unpaid, identify those where Last Paid is NOT the current month, and Autopay is False.
    Keep the response concise, helpful, and use emojis!
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Failed to generate advice: {e}")
        return "I'm having trouble analyzing your request right now. Let's try again later!"
