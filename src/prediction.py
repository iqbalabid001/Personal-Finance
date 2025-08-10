# Prediction module for the "Personal Finance Project" in Python, by: Tim Döring (68973)

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
import numpy as np

def prediction(database_name, fact_balance, nr_years):
     
    # nr_years must be a positive integer number
    
    if not isinstance(nr_years, int) or nr_years <= 0:
        print("Error: The number of years must be a positive integer.")
        return
    
    # Limit the prediction period to 5 years max
    if nr_years > 5:
        print("Attention: The prediction duration has been limited to 5 years.")
        nr_years = 5  # Sets nr_years to 5 if the user inputs a number greater than 5
    
    # Database connection, database_name is the first input argument of the prediction fucntion
    # Import of necessary tables from the database
    
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    Transactions = pd.read_sql_query(f"SELECT * FROM {'Transactions'}", conn)
    TransactionItems = pd.read_sql_query(f"SELECT * FROM {'TransactionItems'}", conn)
    Subcategories = pd.read_sql_query(f"SELECT * FROM {'Subcategories'}", conn)
    conn.close()

    # There are duplicate rows in the TransactionItems table, which are deleted here
    TransactionItems = TransactionItems.drop_duplicates(subset='transactionID')
    
    # Merging the Transactions and the TransactionItems tables to have all necessary data in one dataframe
    transactions_merge = pd.merge(Transactions, TransactionItems, how='inner', on='transactionID')

    # Creating a dataframe with the necessary columns for all transactions
    
    transactions = pd.DataFrame()
    transactions['date'] = transactions_merge['date']
    transactions['date'] = pd.to_datetime(Transactions['date'], format='%d.%m.%Y')
    transactions['description'] = transactions_merge['description']
    transactions['subcategoryID'] = transactions_merge['subcategoryID']
    transactions['repeatInterval'] = transactions_merge['repeatInterval'].str.lower()
    transactions['baseAmount'] = transactions_merge['baseAmount']

    # Setting the time frame for the prediction
    
    prediction_start_date = datetime.today() # prediction starts on day of running the code
    
    try: # prediction ends on the same day in selected future year.
        prediction_end_date = prediction_start_date.replace(year=prediction_start_date.year + nr_years) 
    except ValueError:  # If the code is run on a February 29th, the prediction ends on February 28th of the selected future year.
        prediction_end_date = prediction_start_date.replace(year=prediction_start_date.year + nr_years, day=28)

    # Creating an object with all the dates within the prediction time frame
    
    future_dates = pd.date_range(start=prediction_start_date, end=prediction_end_date, freq='D')
    future_dates = future_dates.strftime("%d.%m.%Y")

    # Creating a dataframe with all the future dates as rows and the necessary columns to predict a balance for each date
    
    prediction = pd.DataFrame()
    prediction['date'] = future_dates
    prediction['date'] = pd.to_datetime(prediction['date'], format='%d.%m.%Y')
    prediction['incomes'] = [0] * len(future_dates)
    prediction['expenses'] = [0] * len(future_dates)
    prediction['balance'] = [0] * len(future_dates)
    
    # Setting type to "float" for the columns that will be including monetary values
    prediction['expenses'] = prediction['expenses'].astype(float)
    prediction['incomes'] = prediction['incomes'].astype(float)
    prediction['balance'] = prediction['balance'].astype(float)  

    # Creating two lists with subcategory IDs based on whether they are incomes or expenses.
    # All expense subcatogry IDs are between 1 and 99, all income subcategory IDs above 100.
    
    expenses = []
    incomes = []

    for i in range(len(Subcategories)):
        subcategoryID = Subcategories.iloc[i]['subcategoryID']
        
        if 1 <= subcategoryID <= 99:
            expenses.append(subcategoryID)
        elif 100 <= subcategoryID <= 200:
            incomes.append(subcategoryID)

    # Inserting transactions row by row based on their "repeatInterval" category.
    
    for _, row in transactions.iterrows():
        transaction_date = row['date']
        subcategoryID = row['subcategoryID']
        baseAmount = row['baseAmount']
        repeatInterval = row['repeatInterval']

        # Inserting "weekly" transaction amounts into the prediction dataframe
        
        if repeatInterval == 'weekly':
            while transaction_date <= prediction['date'].max():
                if transaction_date in prediction['date'].values:
                    index = prediction.index[prediction['date'] == transaction_date][0]
                    if subcategoryID in expenses:
                        prediction.loc[index, 'expenses'] += baseAmount
                    elif subcategoryID in incomes:
                        prediction.loc[index, 'incomes'] += baseAmount
                        
                transaction_date += timedelta(weeks=1)

        # Inserting "fortnightly" transaction amounts into the prediction dataframe
        
        elif repeatInterval == 'fortnightly':
            while transaction_date <= prediction['date'].max():
                if transaction_date in prediction['date'].values:
                    index = prediction.index[prediction['date'] == transaction_date][0]
                    if subcategoryID in expenses:
                        prediction.loc[index, 'expenses'] += baseAmount
                    elif subcategoryID in incomes:
                        prediction.loc[index, 'incomes'] += baseAmount
                        
                transaction_date += timedelta(weeks=2)

        # Inserting "monthly" transaction amounts into the prediction dataframe

        elif repeatInterval == 'monthly':
            while transaction_date <= prediction['date'].max():
                if transaction_date in prediction['date'].values:
                    index = prediction.index[prediction['date'] == transaction_date][0]
                    if subcategoryID in expenses:
                        prediction.loc[index, 'expenses'] += baseAmount
                    elif subcategoryID in incomes:
                        prediction.loc[index, 'incomes'] += baseAmount
        
                next_month = transaction_date.month + 1 if transaction_date.month < 12 else 1
                next_year = transaction_date.year if transaction_date.month < 12 else transaction_date.year + 1
                
                try:
                    transaction_date = transaction_date.replace(year=next_year, month=next_month)
                # If transaction date is f. ex. the 31st and the next month has fewer days, the amount is inserted on the 28th. 
                # The 28th is chosen as it is the smallest possible month length.
                except ValueError: 
                    transaction_date = transaction_date.replace(year=next_year, month=next_month, day=28)
        
        # Inserting "yearly" transaction amounts into the prediction dataframe

        elif repeatInterval == 'yearly':
            while transaction_date <= prediction['date'].max():
                # Adjust for February 29th (in case of leap year)
                if transaction_date.month == 2 and transaction_date.day == 29:
                    transaction_date = transaction_date.replace(day=28)
                
                if transaction_date in prediction['date'].values:
                    index = prediction.index[prediction['date'] == transaction_date][0]
                    column = 'expenses' if subcategoryID in expenses else 'incomes'
                    prediction.loc[index, column] += baseAmount
        
                transaction_date = transaction_date.replace(year=transaction_date.year + 1)

    # Calculating every row of the balance column of the prediction dataframe
    
    prediction.loc[0, 'balance'] = fact_balance # fact_balance as the start for the prediction (first row). fact_balance is an input argument.
    
    # predicted balance is the predicted balance of the day before plus all repeated incomes and minus all repeated expenses occuring that day.
    for i in range(1, len(prediction)): 
        prediction.loc[i, 'balance'] = (
            prediction.loc[i - 1, 'balance'] + prediction.loc[i, 'incomes'] - prediction.loc[i, 'expenses'])

    
    # Creation of the prediction plot
    # x-axis labels on start and end date as well as the same days as the start date in every future year.
    
    prediction_start = prediction['date'].iloc[0]
    x_axis_labels = [prediction_start]
    current_label = prediction_start
    while current_label <= prediction['date'].max():
        try:
            next_label = current_label.replace(year=current_label.year + 1)
        except ValueError: # If x-axis label would fall on a February 29th that doesn't exist. It will be set to Feb 28th.
            next_label = current_label.replace(year=current_label.year + 1, month=2, day=28)
        if next_label <= prediction['date'].max():
            x_axis_labels.append(next_label)
        current_label = next_label

    # Plotting the predicted balance over time
    
    plt.figure(figsize=(12, 6))
    plt.plot(prediction['date'], prediction['balance'], color='red', label='Predicted Balance')
    plt.xticks(x_axis_labels, [date.strftime('%d.%m.%Y') for date in x_axis_labels], rotation=45)
    plt.xlabel('Date')
    plt.ylabel('Balance')
    plt.title('Prediction of the Balance Over Time')
    plt.legend()

    # Creation of a prediction dataframe with selected rows (start and end date as well as all 1st days of every month)
    
    prediction_start = prediction[['date', 'balance']].iloc[[0]]
    first_of_every_month = prediction[['date', 'balance']][prediction['date'].dt.day == 1]
    prediction_end = prediction[['date', 'balance']].iloc[[-1]]
    prediction_selection = pd.concat([prediction_start,  first_of_every_month, prediction_end])
    prediction_selection['date'] = prediction_selection['date'].dt.strftime('%d.%m.%Y')
    prediction_selection['balance'] = prediction_selection['balance'].round(2)

    # Creating the .pdf file
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f"{current_time}_prediction.pdf"
    
    with PdfPages(filename) as pdf:
        plt.tight_layout()
        pdf.savefig()
        plt.close()
    
        # Figure size depends on the number of rows as the number of rows varies based on chosen nr_years.
        # Setting minimum figure height as 35, because with small numbers of rows the table "squeezed".
        fig, ax = plt.subplots(figsize=(6, max(35, len(prediction_selection) * 0.6 + 2)))
        ax.axis('tight')
        ax.axis('off')
    
        table = ax.table(
            cellText=prediction_selection.values,
            colLabels=prediction_selection.columns,
            loc='center',
            cellLoc='center')
    
        # Some aesthetic adjustments for displaying the table (different row heights and font sizes for header and other rows)
        table.set_fontsize(14)
        num_rows = len(prediction_selection)
        row_height = 0.015
        for (row, col), cell in table.get_celld().items():
            if row == 0:  # Header row
                cell.set_fontsize(16)  # Slightly larger font for headers
                cell.set_height(row_height * 1.5)  # Slightly taller header
            else:
                cell.set_height(row_height)
    
        pdf.savefig(fig)
        plt.close()
        plt.show()

    
    print(f"Your .pdf file has been created and saved as: {filename}")

prediction("98754612.sqlite", 18000, 3)