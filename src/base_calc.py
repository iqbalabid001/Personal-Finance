import sqlite3
import requests
from datetime import datetime

def update_base_amounts(database):
    """Recalculate and update baseAmount (EUR equivalent) for each transaction using Frankfurter API."""
    try:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        # Step 1: Fetch transaction data
        cursor.execute("""
            SELECT ti.transactionID, ti.amount, t.date, t.currency 
            FROM TransactionItems ti
            JOIN Transactions t ON ti.transactionID = t.transactionID
        """)
        transactions = cursor.fetchall()

        # Step 2: Store fetched rates to avoid duplicate API calls
        historical_rates = {}

        for transaction_id, amount, date, currency in transactions:
            if currency == "EUR":
                base_amount = round(amount, 2)
                print(f"Transaction ID {transaction_id} is already in EUR. BaseAmount set to {base_amount:.2f}")
            else:
                # Convert date to YYYY-MM-DD for API
                formatted_date = datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")

                # Check if we already have the rate for this currency and date
                if (currency, formatted_date) not in historical_rates:
                    try:
                        url = f"https://api.frankfurter.app/{formatted_date}"
                        params = {"from": currency, "to": "EUR"}
                        response = requests.get(url, params=params)

                        if response.status_code != 200:
                            raise ValueError(f"HTTP {response.status_code}: {response.text}")

                        data = response.json()
                        rate = data.get("rates", {}).get("EUR")

                        if rate is None:
                            raise ValueError(f"No EUR rate found for {currency} on {formatted_date}")

                        historical_rates[(currency, formatted_date)] = rate
                        print(f"Fetched {currency} → EUR rate for {formatted_date}: {rate}")

                    except Exception as e:
                        print(f"Error fetching rate for {currency} on {formatted_date}: {e}")
                        continue

                # Convert amount to EUR
                rate = historical_rates.get((currency, formatted_date))
                if rate:
                    base_amount = round(amount * rate, 2)  # rate is from currency → EUR
                    print(f"Updated transaction ID {transaction_id} with baseAmount {base_amount:.2f}")
                else:
                    print(f"Missing rate for {currency} on {formatted_date}")
                    continue

            # Step 3: Update database
            cursor.execute("""
                UPDATE TransactionItems
                SET baseAmount = ?
                WHERE transactionID = ? AND amount = ?
            """, (base_amount, transaction_id, amount))

        conn.commit()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"General error: {e}")
    finally:
        conn.close()
        print("Base amounts updated successfully!")

if __name__ == "__main__":
    database = "98754612.sqlite"
    update_base_amounts(database)