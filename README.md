# AI Expense Tracker Bot

An AI-powered expense tracker agent for Telegram that allows you to log expenses using natural language. It uses the Gemini API to extract details like amount, category, and payment source, and it keeps a running total of your monthly spending. It also acts as a financial agent, offering budgeting advice based on your history.

## Setup Instructions

1. **Install dependencies:**
   Make sure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your API keys:**
   - Rename `.env.example` to `.env`
   - **Telegram Bot Token**: Go to Telegram, search for `@BotFather`, send `/newbot`, follow the instructions, and paste the API token in your `.env` file.
   - **Gemini API Key**: Go to [Google AI Studio](https://aistudio.google.com/app/apikey), create a new API key, and paste it in your `.env` file.

3. **Run the bot:**
   ```bash
   python bot.py
   ```

## Usage
Once the bot is running, go to your bot on Telegram and send a message like:
- "taxi 300"
- "bought groceries for 1200 using UPI"
- "How much have I spent on food this month?"

The bot will automatically process the expense, save it to a local SQLite database (`expenses.db`), and respond with your total spending for the current month.
