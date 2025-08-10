import os
import sqlite3
import sync
from datetime import datetime
from splitwise import Splitwise
from requests_oauthlib import OAuth1Session


def input_category(conn):

    cursor = conn.cursor()

    #Inserting income category to keep track of money
    cursor.execute(
        "INSERT OR IGNORE INTO Categories (categoryID, category) VALUES (?, ?)", (100, 'Income')
    )

    #list of specific types of income
    income_subcategories = [
        (101, 'Salary'),
        (102, 'Business'),
        (103, 'Gifts'),
        (104, 'Grants'),
        (105, 'Other')
    ]
    #loops through subcategories and adds them into our database
    for subcategory_id, subcategory_name in income_subcategories:
        cursor.execute(
            "INSERT OR IGNORE INTO Subcategories (subcategoryID, subcategory) VALUES (?, ?)",
            (subcategory_id, subcategory_name)
        )

    conn.commit()


def input_data(user_id):
    #opens the database or create one if does not exist
    db_name = f"{user_id}.sqlite"

    if not os.path.exists(db_name):
        print(f"Database '{db_name}' not found. Please create it using the sync module first.")
        return

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

    #assigns ID's to each subcategory for easy reference later on
    income_subcategories = {
        'Salary': 101,
        'Business': 102,
        'Gifts': 103,
        'Grants': 104,
        'Other': 105
    }

    repeat_intervals = ['One-time', 'Weekly', 'Fortnightly', 'Monthly', 'Yearly'] #defines repeated intervals

    try:
        input_category(conn) #makes sure the categories are in place
        subcategory_id = None
        subcategory_name = None
        while subcategory_id is None:
            choice = input(f"Choose a category (by name or ID): \n" +
               "\n".join([f"{id_}: {name}" for id_, name in income_subcategories.items()]) +
               "\n").strip() #user picks a category whether its ID or name
            if choice.isdigit() and int(choice) in income_subcategories.values():
                subcategory_id = int(choice)
                subcategory_name = [name for name, id_ in income_subcategories.items() if id_ == subcategory_id][0]
            elif choice.capitalize() in income_subcategories:
                subcategory_id = income_subcategories[choice.capitalize()]
            else:
                print("Invalid choice. Please try again.")

        # input for amount
        while True:
            try:
                amount = float(input("Enter amount of income: "))
                break
            except ValueError:
                print("Please enter a numeric value.")

        # input for Date
        while True:
            date_input = input("Enter the date (DD.MM.YYYY): ")
            try:
                date = datetime.strptime(date_input, "%d.%m.%Y").strftime("%d.%m.%Y")
                break
            except ValueError:
                print("Invalid date format. Please use DD.MM.YYYY.")

        # input for repeated interval
        repeat_interval = None
        while repeat_interval not in repeat_intervals:
            repeat_interval = input(f"Select repeated interval:\nOptions: {', '.join(repeat_intervals)}\n").capitalize()
            if repeat_interval not in repeat_intervals:
                print("Invalid repeat interval. Please try again.")

        #inserts the transaction details into the database
        cursor.execute('''INSERT INTO Transactions (transactionID, date, groupID, subcategoryID, description, currency, repeatInterval, updated)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (None, date, None, subcategory_id, subcategory_name, 'EUR', repeat_interval, datetime.now().isoformat()))
        transaction_id = cursor.lastrowid

        #inserting transaction items to the database
        cursor.execute('''INSERT INTO TransactionItems (transactionID, userID, amount, baseAmount)
                          VALUES (?, ?, ?, ?)''',
                       (transaction_id, user_id, amount, amount))

        conn.commit()
        print(f"Income has been added to the database!")

    except Exception as e:
        print(f"An error occurred while inserting income data: {e}")

    finally:
        conn.close()


if __name__ == "__main__":
    user_id = sync.get_user_id()
    input_data(user_id)


