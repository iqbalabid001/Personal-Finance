import os
import sqlite3
from datetime import datetime
from splitwise import Splitwise

def read_settings(settings_file="settings.txt"): #get the credentials
    settings = {} #dictionary to store and make the credentials accessible
    try:
        with open(settings_file, 'r') as file:
            for line in file:
                if '=' in line: #as stored in settings.txt, check for '=' to prevent ValueError
                    key, value = line.strip().split('=', 1) #just split for the current one
                    settings[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"Error: {settings_file} not found. Please make sure the file exists in current directory.")
        return None
    return settings

def create_tables(conn): #takes connection obj as argument
    cursor = conn.cursor() #cursor object to execute the queries here
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS "Groups" (groupID INTEGER PRIMARY KEY, "group" TEXT);
        CREATE TABLE IF NOT EXISTS Users (userID INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE IF NOT EXISTS Transactions (
            transactionID INTEGER PRIMARY KEY,
            date TEXT,
            groupID INTEGER,
            subcategoryID INTEGER,
            description TEXT,
            currency TEXT,
            repeatInterval TEXT,
            updated TEXT,
            FOREIGN KEY (subcategoryID) REFERENCES Subcategories (subcategoryID)
        );
        CREATE TABLE IF NOT EXISTS TransactionItems (
            itemID INTEGER PRIMARY KEY AUTOINCREMENT,
            transactionID INTEGER,
            userID INTEGER,
            amount FLOAT,
            baseAmount FLOAT
        );
        CREATE TABLE IF NOT EXISTS Categories (categoryID INTEGER PRIMARY KEY, category TEXT);
        CREATE TABLE IF NOT EXISTS Subcategories (subcategoryID INTEGER PRIMARY KEY, subcategory TEXT);
    """)
    conn.commit()  #save the creation of tables

def sync_splitwise_data():
    settings = read_settings()
    if settings is None:
        return

    try:
        consumer_key = settings['consumer_key']
        consumer_secret = settings['consumer_secret']
        access_token = settings['access_token']
        access_token_secret = settings['access_token_secret']
    except KeyError as e:
        print(f"Error: Missing key '{e}' in settings.txt.")
        return

    s = Splitwise(settings['consumer_key'], settings['consumer_secret'])
    s.setAccessToken({'oauth_token': settings['access_token'], 'oauth_token_secret': settings['access_token_secret']})
    user = s.getCurrentUser()  #get the current user
    print(f"Authenticated user ID: {user.id}") #current user ID

    wise_db = f"{user.id}.sqlite" #db name
    conn = sqlite3.connect(wise_db) #create the file, get a connection and store the connection in a variable
    create_tables(conn) #pass the connection to create_tables() to create specified tables
    cursor = conn.cursor()  #cursor object for subsequent database operations

    print("Fetching data from Splitwise...")

    try:
        groups = s.getGroups()
        print(f"Fetched {len(groups)} groups")
        for group in groups:
            cursor.execute('''INSERT OR IGNORE INTO "Groups" (groupID, "group") VALUES (?, ?)''', (group.id, group.name))

        friends = s.getFriends()
        print(f"Fetched {len(friends)} friends")
        for friend in friends:
            cursor.execute('''INSERT OR IGNORE INTO Users (userID, name) VALUES (?, ?)''', (friend.id, f"{friend.first_name} {friend.last_name}"))

        categories = s.getCategories() #returns a list of categories (including top-level categories and their potential subcategories)
        print(f"Fetched {len(categories)} categories")
        subcategory_dict = {}  #dictionary to map subcategory names to IDs
        for category in categories: #get and store the catagories
            cursor.execute('''INSERT OR IGNORE INTO Categories (categoryID, category) VALUES (?, ?)''', (category.id, category.name))
            for subcategory in category.subcategories: #get and store the subcatagories
                cursor.execute('''INSERT OR IGNORE INTO Subcategories (subcategoryID, subcategory) VALUES (?, ?)''', (subcategory.id, subcategory.name))
                subcategory_dict[subcategory.name] = subcategory.id  #store the subcategory ID with name for later use

        expenses = s.getExpenses(limit=50, offset=0)    #variable will contain a list of Expense objects, such as id, date etc
        current_expense_ids = {expense.id for expense in expenses if expense.deleted_at is None}   #create a set of IDs of all current or undeleted expenses
        cursor.execute("SELECT transactionID FROM Transactions")   #all transaction IDs (expense IDs) from the local Transactions table
        stored_expenses = cursor.fetchall()   #fetche all results from the previous query ans store in variable
        stored_expense_ids = {row[0] for row in stored_expenses}   #another set with the IDs of all expenses in the local database
        deleted_expense_ids = stored_expense_ids - current_expense_ids   #use the sets to get the IDs that are no longer in Splitwise

        for id in deleted_expense_ids:  #iterate over the set of deleted IDs
            cursor.execute("DELETE FROM TransactionItems WHERE transactionID = ?", (id,)) #remove associated transaction items (user shares)
            cursor.execute("DELETE FROM Transactions WHERE transactionID = ?", (id,)) #remove the actual deleted expense entry
            print(f"Deleted transaction ID: {id}")

        for expense in expenses:  #format the date from ISO 8601 to dd.mm.yyyy
            if expense.deleted_at is not None:  #skip deleted expenses
                continue
            formatted_date = datetime.fromisoformat(expense.date.replace("Z", "")).strftime("%d.%m.%Y")

            subcategory_id = None
            if expense.category:
                subcategory_name = expense.category.name  #gets subcatagory as catagory category.name returned by getExpenses method is also subcatagory
                if subcategory_name in subcategory_dict:
                    subcategory_id = subcategory_dict[subcategory_name]  #lookup and assign the subcategory ID

            repeat_interval = expense.repeat_interval if expense.repeat_interval else "One-time" #get the repeat interval if available

            cursor.execute('''INSERT OR REPLACE INTO Transactions (transactionID, date, groupID, subcategoryID, description, currency, repeatInterval, updated) 
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (expense.id, formatted_date, expense.group_id, subcategory_id, expense.description, expense.currency_code, repeat_interval, expense.updated_at))

            cursor.execute("DELETE FROM TransactionItems WHERE transactionID = ?", (expense.id,)) #prevent duplicate and clear old exp information

            for user_share in expense.users: #populate the TransactionItems table
                cursor.execute('''INSERT INTO TransactionItems (transactionID, userID, amount, baseAmount) VALUES (?, ?, ?, ?)''', (expense.id, user_share.id, user_share.paid_share, None))
                print(f"Updated transaction ID: {expense.id}")

    except Exception as e:
        print(f"Error fetching data: {e}")
    finally:
        conn.commit()
        conn.close()
        print("Data synchronization complete!")

if __name__ == "__main__":
    sync_splitwise_data()

#The function below was added by Tim for use in later tasks
def get_user_id():
    settings = read_settings()
    if settings is None:
        return

    try:
        consumer_key = settings['consumer_key']
        consumer_secret = settings['consumer_secret']
        access_token = settings['access_token']
        access_token_secret = settings['access_token_secret']
    except KeyError as e:
        print(f"Error: Missing key '{e}' in settings.txt.")
        return

    s = Splitwise(settings['consumer_key'], settings['consumer_secret'])
    s.setAccessToken({'oauth_token': settings['access_token'], 'oauth_token_secret': settings['access_token_secret']})
    user = s.getCurrentUser()  #get the current user
    return user.id