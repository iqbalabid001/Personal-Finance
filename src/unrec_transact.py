import sqlite3
import requests
from sync import get_user_id, read_settings
from splitwise import Splitwise
from datetime import datetime


# sum of base_amount from Income and Expenses (database)
def income_expenses(database_name):
    try:
        conn = sqlite3.connect(database_name)  # connection to database
        cursor = conn.cursor()
        # income transactions with description 'Income' or subCategoryId between 100 and 106
        cursor.execute("""
            SELECT SUM(baseAmount)
            FROM TransactionItems
            WHERE transactionID IN (
                SELECT transactionID
                FROM Transactions
                WHERE description = 'Income'
                OR subcategoryId BETWEEN 100 AND 106
            )
        """)
        income = cursor.fetchone()[0]
        if income is None:
            income = 0.0

        # calculating expenses
        cursor.execute("""
            SELECT SUM(baseAmount)
            FROM TransactionItems
            WHERE transactionID IN (
                SELECT transactionID
                FROM Transactions
                WHERE description != 'Income'
                AND (subcategoryId < 100 OR subcategoryId > 106)
            )
        """)
        expenses = cursor.fetchone()[0]
        if expenses is None:
            expenses = 0.0

        conn.close()
        return income, expenses
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return 0.0, 0.0


# Exchange Rate to convert currency to Euro using Frankfurter API
def exchange_rate(base_currency, target_currency="EUR"):
    try:
        if base_currency == target_currency:
            return 1.0
        url = f"https://api.frankfurter.app/latest?from={base_currency}&to={target_currency}"
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code}: {response.text}")
        data = response.json()
        rate = data.get("rates", {}).get(target_currency)
        if rate is None:
            raise ValueError(f"Exchange rate not available for {base_currency} to {target_currency}")
        return rate
    except Exception as e:
        raise ValueError(str(e))


# calculating Net Debt, access balances from friends, take currencies into account
def net_debt():
    try:
        settings = read_settings("settings.txt")  # settings file with access information
        s = Splitwise(settings["consumer_key"], settings["consumer_secret"])
        s.setAccessToken(
            {"oauth_token": settings["access_token"], "oauth_token_secret": settings["access_token_secret"]}
        )
        balances = {}
        for friend in s.getFriends():
            for balance in friend.getBalances() or []:
                currency = balance.getCurrencyCode()
                amount = float(balance.getAmount())
                if currency not in balances:
                    balances[currency] = {"owes": 0.0, "owed": 0.0}
                if amount < 0:
                    balances[currency]["owes"] += abs(amount)
                else:
                    balances[currency]["owed"] += amount

        total_net_debt_eur = 0.0
        for currency, amounts in balances.items():
            net_debt_value = amounts["owes"] - amounts["owed"]
            print(f"{currency}:")
            print(f"  User owes: {amounts['owes']:.2f}")
            print(f"  User is owed: {amounts['owed']:.2f}")
            print(f"  Net debt: {net_debt_value:.2f}")

            # Convert to EUR if necessary
            if currency != "EUR":
                try:
                    rate = exchange_rate(currency, "EUR")
                    net_debt_eur = net_debt_value * rate
                    print(f"  Net debt in EUR: {net_debt_eur:.2f}")
                except ValueError as ex:
                    print(f"  Could not fetch exchange rate for {currency} to EUR: {ex}")
                    net_debt_eur = 0.0
            else:
                net_debt_eur = net_debt_value

            total_net_debt_eur += net_debt_eur

        print(f"\nTotal Net Debt in EUR: {total_net_debt_eur:.2f}")
        return total_net_debt_eur
    except Exception as e:
        print(f"Error calculating net debt: {e}")
        return 0.0


# function to insert the unrecorded transaction into the database
def insert_transaction(database_name, amount):
    try:
        if abs(amount) < 0.00001:
            print("Unrecorded transactions not found")
            return

        user_id = get_user_id()
        conn = sqlite3.connect(database_name)
        cursor = conn.cursor()

        # Ensure subcategories exist
        cursor.executemany("""
            INSERT OR IGNORE INTO Subcategories (subcategoryID, subcategory)
            VALUES (?, ?)
        """, [(99, "Unrecorded Expense"), (106, "Unrecorded Income")])

        description, subcategory_id = (
            ("Unrecorded Income", 106) if amount < 0 else ("Unrecorded Expense", 99)
        )
        base_amount = abs(amount)
        current_date = datetime.now().strftime("%d.%m.%Y")

        # Insert transaction
        cursor.execute("""
            INSERT INTO Transactions (date, description, currency, subCategoryId, repeatInterval)
            VALUES (?, ?, 'EUR', ?, 'One-time')
        """, (current_date, description, subcategory_id))
        transaction_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO TransactionItems (transactionID, amount, baseAmount, userID)
            VALUES (?, ?, ?, ?)
        """, (transaction_id, base_amount, base_amount, user_id))

        conn.commit()
        conn.close()
        print(f"{description} of {base_amount:.2f} EUR is added to database.")

    except sqlite3.Error as e:
        print(f"Error recording transaction: {e}")


# variable to store factbalance
factbalance = None

# function to ask for account balance
def get_factbalance():
    while True:
        try:
            factbalance_value = float(input("Enter your Fact Balance in EUR: "))
            return factbalance_value
        except ValueError:
            print("Invalid input. Please enter a numeric value.")


# Main function
def unrecorded_transactions(database_name):
    global factbalance
    factbalance = None
    income, expenses = income_expenses(database_name)
    net_debt_eur = net_debt()
    factbalance = get_factbalance()

    # Calculate unrecorded amount
    unrecorded_amount = income - expenses + net_debt_eur - factbalance
    print("\nSummary:")
    print(f"Income: {income:.2f} EUR")
    print(f"Expenses: {expenses:.2f} EUR")
    print(f"Net Debt: {net_debt_eur:.2f} EUR")
    print(f"Fact Balance: {factbalance:.2f} EUR")
    print(f"Unrecorded Amount: {unrecorded_amount:.2f} EUR")

    insert_transaction(database_name, unrecorded_amount)


if __name__ == "__main__":
    import sync
    user_id = sync.get_user_id()
    database_name = str(user_id) + ".sqlite"
    unrecorded_transactions(database_name)
    print(factbalance)