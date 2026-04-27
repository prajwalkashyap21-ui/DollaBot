import os
import google.generativeai as genai
import json

MODEL_NAME = None

def init_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)

def parse_expense(text):
    # Hardcode the model to skip the slow list_models API check entirely!
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    prompt = f"""
    You are a finance assistant. Extract the details from the user's message.
    Message: "{text}"
    
    Respond ONLY with a valid JSON object containing the following keys:
    - amount: (float) the amount mentioned. Return null if none.
    - category: (string) the type of expense.
    - payment_source: (string) the payment method.
    - description: (string) a brief summary.
    - expense_date: (string) YYYY-MM-DD format if the user explicitly mentions a past date (e.g. "on 2nd April"). Null if not specified.
    - is_expense: (boolean) true if the user is logging a new, standard one-time expense.
    - is_expense_delete: (boolean) true if the user is explicitly asking to delete, remove, or undo an expense.
    - is_expense_update: (boolean) true if the user is asking to update or change the date of an existing, standard logged expense (e.g. "The 2500 payment was made on 5th April").
    - is_debt: (boolean) true if the user is logging a debt or someone owing money.
    - is_debt_clear: (boolean) true if clearing a debt.
    - debt_type: (string) "i_owe" or "owed_to_me".
    - person_name: (string) name of person for debt.
    - is_recurring_setup: (boolean) true if setting up a new recurring expense/subscription (ONLY if user explicitly mentions "monthly", "recurring", "subscription", or "every month").
    - is_recurring_update: (boolean) true if the user wants to update the amount or date of an existing recurring expense (e.g. "change my rent date to the 5th").
    - is_recurring_payment: (boolean) true if the user is mentioning they have paid a recurring expense.
    - is_autopay: (boolean) true if the recurring expense is auto-debited / autopay.
    - payee: (string) who is receiving the recurring payment (e.g., "electricity", "Netflix").
    - day_of_month: (integer) The specific day of the month (1-31) the recurring expense happens or is due (e.g. "5th April" -> 5). Null if not specified.
    """
    
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Robust JSON extraction: look for the opening and closing brackets
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                result_text = result_text[start_idx:end_idx+1]
                return json.loads(result_text)
            else:
                err = f"Could not find JSON block. Response was: {result_text}"
                print(err)
                return {"error": err}
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                import time
                print("Rate limited! Waiting 6 seconds before retrying...")
                time.sleep(6)
                continue
            err = f"Exception during LLM parse: {str(e)}"
            print(err)
            return {"error": err}

def get_finance_advice(user_id, user_message, current_monthly_total, recent_expenses, recurring_expenses):
    # Hardcode the model to skip the slow list_models API check entirely!
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
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
    Keep the response concise, helpful, and use emojis! DO NOT use markdown like **bold** or *italics*.
    """
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            return response.text.replace('**', '').replace('*', '')
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                import time
                print("Rate limited in advice engine! Waiting 6 seconds...")
                time.sleep(6)
                continue
            err = f"Exception during advice generation: {str(e)}"
            print(err)
            return f"🛠 *System Error in Advice Engine:*\n`{err}`"
