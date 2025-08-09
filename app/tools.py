from db import get_connection
from langchain.tools import tool
import math
def get_onboarding_data():
    """Helper function to retrieve financial data (not a tool)"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            product_dev_expenses,
            manpower_expenses,
            marketing_expenses,
            operations_expenses,
            current_cash,
            target_runway_months
        FROM "cashflow-guardian".onboarding_data
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    return {
        "product_dev_expenses": float(row[0]),
        "manpower_expenses": float(row[1]),
        "marketing_expenses": float(row[2]),
        "operations_expenses": float(row[3]),
        "current_cash": float(row[4]),
        "target_runway_months": row[5]
    }

@tool
def get_financial_summary():
    """Retrieve and display all financial data of the company. The money are in Philippine Pesos"""
    data = get_onboarding_data()
    
    return f"""Financial Data Retrieved:
- Product Development: ₱{data['product_dev_expenses']:,.2f}
- Manpower: ₱{data['manpower_expenses']:,.2f}
- Marketing: ₱{data['marketing_expenses']:,.2f}
- Operations: ₱{data['operations_expenses']:,.2f}
- Current Cash: ₱{data['current_cash']:,.2f}"""

@tool
def compute_burn_rate():
    """Compute the monthly burn rate (total expenses) of the company. The money are in Philippine Pesos"""
    data = get_onboarding_data()
    burn_rate = (data['product_dev_expenses'] + data['manpower_expenses'] + 
                data['marketing_expenses'] + data['operations_expenses'])
    return f"Monthly burn rate: ₱{burn_rate:,.2f}"

@tool
def compute_runway(simulated_expense = None):
    """Compute the runway in months (how long current cash will last).The money are in Philippine Pesos"""
    data = get_onboarding_data()
    if simulated_expense is None:
        burn_rate = (data['product_dev_expenses'] + data['manpower_expenses'] + 
                data['marketing_expenses'] + data['operations_expenses'])
        runway = math.floor(data['current_cash'] / burn_rate)
    
        return f"Your current runway is {runway} months (₱{data['current_cash']:,.2f} ÷ ₱{burn_rate:,.2f}/month)"
    runway = math.floor(data['current_cash'] / simulated_expense)
    return f"Your current runway is {runway} months (₱{data['current_cash']:,.2f} ÷ ₱{simulated_expense:,.2f}/month)"

tools = [get_financial_summary, compute_burn_rate, compute_runway]