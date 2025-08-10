import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF
import sqlite3
from datetime import datetime
from sync import get_user_id
import numpy as np
# connecting to the db and create df
def prepare_transactions(user_id):
    conn = sqlite3.connect(f"{user_id}.sqlite")
    query = """
    SELECT 
        Transactions.transactionID,
        Transactions.date,
        Transactions.subcategoryID,
        TransactionItems.baseAmount AS amount,
        Subcategories.subcategory AS Subcategory
    FROM Transactions
    JOIN TransactionItems ON Transactions.transactionID = TransactionItems.transactionID
    JOIN Subcategories ON Transactions.subcategoryID = Subcategories.subcategoryID
    WHERE TransactionItems.amount > 0
    ORDER BY Transactions.date
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y')
    df['month'] = df['date'].dt.to_period('M').astype(str)  # new column for month
    df = df.sort_values('date', ascending=False)
    df['type'] = np.where((df['subcategoryID'] >= 101) & (df['subcategoryID'] <= 106), 'Income', 'Expense') # new column, assign type of transaction: income or expense
    df['amount'] = df['amount'].fillna(0) # fill NA with 0
    return df

import matplotlib.pyplot as plt
import pandas as pd

# function for visualization
def generate_charts(df):
    try:
        df_monthly = df.groupby(['month', 'type'])['amount'].sum().unstack()  # expenses and income by mponths
        last3months = df_monthly.tail(3).fillna(0)  # last three months, fill Na with 0

        plt.figure(figsize=(6, 4))  # size of bar chart
        last3months.plot(kind='bar', color=['red', 'green']) # 1 bar chart Income vs Expenses grouped by months, last 3
        plt.title('Income vs Expenses (Last 3 Months)')
        plt.xlabel('Month')
        plt.ylabel('Amount (€)')
        plt.xticks(rotation=0) # horizontal label
        plt.legend(title="Type")
        plt.tight_layout() # adjusts elements, should prevent overlapping
        plt.savefig("income_vs_expenses_last_3_months.png") # save 1 bar chart
        plt.close()
    except Exception as e:
        print("Failed to generate or save the income vs expenses bar chart:", e)
    finally:
        plt.close()

    try:
        plt.figure(figsize=(6, 4))
        summary = df_monthly.sum() # total expenses and income for last 3 months
        summary.plot(kind='bar', color=['red', 'green'])
        plt.title('Total Income vs Expenses (Last 3 Months)')
        plt.xlabel('Type')
        plt.ylabel('Amount (€)')
        plt.xticks(rotation=0)
        plt.tight_layout() # adjust elements
        plt.savefig("total_income_vs_expenses.png")
        plt.close()
    except Exception as e:  # handle errors
        print("Failed to generate or save the total income vs expenses bar chart:", e)
    finally:
        plt.close()

    months_3 = sorted(df['month'].unique())[-3:] # last three months names
    for month in months_3: # for every month in last three months, create pie chart
        try:
            monthly_expenses = df[(df['type'] == 'Expense') & (df['month'] == month)] # df with expenses and months
            if not monthly_expenses.empty:
                subcategory_data = monthly_expenses.groupby('Subcategory')['amount'].sum() #sum of expenses for every category
                total = subcategory_data.sum() # sum of all expenses
                threshold = 0.02 * total # 2% of expenses
                significant_subcategories = subcategory_data[subcategory_data >= threshold] # we want to have expenses categories, with sum bigger than 2% of total
                small_subcategories = subcategory_data[subcategory_data < threshold] # rest of expenses categories, less than 2%

                if not small_subcategories.empty:
                    significant_subcategories['Others'] = small_subcategories.sum() # sum of small categories in Others, and add to big categories

                plt.figure(figsize=(10, 6))
                wedges, texts, autotexts = plt.pie(significant_subcategories, labels=significant_subcategories.index,
                                                   autopct='%1.1f%%', startangle=90) # creating pie charts, assigns the index of sign. subcat. as labels,str percentage for slices, startby 90 degrees
                plt.title(f'Expenses by Subcategory - {month}') # title
                legend_labels = [f'{label}: {val:.1f}%' for label, val in (significant_subcategories / total * 100).items()] # legend, loop to show subcategory and its percentage of  total exp
                plt.legend(wedges, legend_labels, title="Subcategories", loc="center left", bbox_to_anchor=(1.2, 0.5))
                plt.subplots_adjust(right=0.8)
                plt.savefig(f"expense_pie_{month}.png", bbox_inches='tight') # save pie chart,all element included
        except Exception as e:
            print(f"Failed to generate or save the pie chart for {month}:", e)
        finally:
            plt.close()
# Creating pdf file with fpdf
def generate_pdf_report(df):
    pdf = FPDF() # instance of Fpdf, create pdf
    pdf.set_auto_page_break(auto=True, margin=15) # breaks autom., margin 15
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16) # fons sets
    pdf.cell(0, 10, "Financial Report", ln=1, align="C") # title, centered

    user_id = get_user_id() # function from sync module
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"User ID: {user_id}", ln=1) # print user id

    # Income vs Expenses overview monthly
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Income vs Expenses (Last 3 Months)", ln=1)
    pdf.set_font("Arial", size=12)

    for month_str in sorted(df['month'].unique())[-3:]: # iterates last 3 month
        month = pd.Period(month_str)
        formatted_month = month.strftime('%B %Y') # Month in word year format
        monthly_data = df[df['month'] == month_str] # filter for month
        income = monthly_data[monthly_data['type'] == 'Income']['amount'].sum() # sum income
        expenses = monthly_data[monthly_data['type'] == 'Expense']['amount'].sum() # sum expenses
        pdf.cell(0, 10, f"{formatted_month}: Income: {income:.2f} EUR, Expenses: {expenses:.2f} EUR", ln=1)
# bar charts
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Income & Expense Overview", ln=1, align="C")
    pdf.set_font("Arial", size=12)
    try:
        pdf.image("income_vs_expenses_last_3_months.png", x=10, y=None, w=120) # group by month
        pdf.image("total_income_vs_expenses.png", x=10, y=None, w=120) # totals last 3 months
    except FileNotFoundError:
        pdf.cell(0, 10, "Charts not found.", ln=1)

# pie charts monthly expenses
    last_3_months = sorted(df['month'].unique())[-3:] # list of months
    for month_str in last_3_months:
        month = pd.Period(month_str)
        formatted_month = month.strftime('%B %Y')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Financial Details - {formatted_month}", ln=1, align="C")
        pdf.set_font("Arial", size=12)

        try:
            pdf.image(f"expense_pie_{month_str}.png", x=10, y=None, w=180)  # Larger chart

        except FileNotFoundError:
            pdf.cell(0, 10, "Pie Chart not found.", ln=1)

# Print expenses by category with percentage
        monthly_expenses = df[(df['type'] == 'Expense') & (df['month'] == month_str)] # only expenses and month
        if not monthly_expenses.empty:
            subcategory_summary = monthly_expenses.groupby('Subcategory')['amount'].sum().reset_index() #group, sum by subcategory.
            total_amount = subcategory_summary['amount'].sum() # total for month
            subcategory_summary['Percentage'] = (subcategory_summary['amount'] / total_amount) * 100 # persentage for categories
            subcategory_summary = subcategory_summary.sort_values(by='Percentage', ascending=False)# sort, desc.

            pdf.set_font("Arial", size=10)  #  font sets
            for index, row in subcategory_summary.iterrows():
                pdf.cell(100, 10, row['Subcategory'], 0, 0, 'L') # list category
                pdf.cell(40, 10, f"{row['amount']:.2f} EUR", 0, 0, 'R') # amount
                pdf.cell(40, 10, f"{row['Percentage']:.1f}%", 0, 1, 'R') # percentage
            pdf.set_font("Arial", size=12) #  font sets
        else:
            pdf.cell(0, 10, "No expenses for this month.", ln=1) # if no expenses

    today = datetime.now().strftime("%Y-%m-%d") # current day date
    pdf.output(f"{today}.pdf") # save pdf under current date
    print(f"Report saved as {today}.pdf")

# Main function combines all the steps
def reporting():
    user_id = get_user_id() # from sync module
    df = prepare_transactions(user_id) #returns df
    if df is not None: # if df exists, creates pie and bar charts snd generation pdf named by current date
        generate_charts(df)
        generate_pdf_report(df)
    else:
        print("Failed to prepare transaction data.") # handle errors

if __name__ == "__main__":
    reporting()
