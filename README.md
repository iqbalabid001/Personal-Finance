To run this project, a valid Splitwise account is needed to obtain the necessary API credentials, consumer key, and consumer secret. In addition, 2 to 3 more accounts for createing groups and transactions.

Create a New Splitwise Account: Sign up for a new account on Splitwise. 
Get API Keys: Go to the Splitwise developer page to register a new application and get your unique Consumer Key and Consumer Secret. 
Set Up the create_settings script accordingly for the settings.txt to be successfully created:

After setup:
1. Run the create_settings script and click the authorization URL in the output
2. Log in to the main user account and click Authorize
3. Although the page will not load, an authorization code will be generated. The code is at the end of the URL (oauth_verifier)
4. Copy the code at the end of the url and paste it as input in the code. After it is entered, the setting.txt file with required keys and tokens will be created in the current directory.

Task 1: Splitwise sync (sync.py)
For sync.py to work, we just need to make sure that the settings.txt file exists in the current directory. Then the script should run and create the database without any input or issue.

Database Details:
Categories Table stores the “income” category.
Subcategories Table defines different sources of income such as Salary, Business, Gifts, Grants, and Other.
Transactions Table keeps track of detailed transactions of income.
TransactionItems Table connects users and income amounts to track balances.

Task 2: Income Input (income.py)
With the Income Input module, users can record different types of income in the system. The database allows users to categorize sources of income, define amounts and make sure the database is properly storing the data.
It asks users for the following details:

1.	Choose an income category by name or by its ID.
2.	Enter the amount of income.
3.	Provide the date in DD.MM.YYYY format.
4.	Select a repeat interval (One-time, Weekly, Fortnightly, Monthly, Yearly).

The code will ask the user to reenter one of these inputs until it is received in the correct format. If the format is correct, a confirmation message will be generated and the transaction will be added to the database. Any errors regarding the database will also be caught.

Task 3: Default Currency (base_cacl.py)
For this code to work we need to make sure the API is not used up. The base amounts cannot be calculated and some of the modules (for example the prediction.py) won’t work as they use the baseAmount column of the database for their calculations.


Task 4: Unrecorded Transactions (unrec_transact.py)
This part of the project automates the process of identifying transactions not recorded in the user's financial tracking tool (Splitwise) and inserts these as income or expenses into the database using the formula Unrecorded amount = Incomes - Expenses + Net Debt - Fact Balance

Prerequisites:
Requests library for API calls
A valid API key for currency conversion rates
Access to Splitwise API including consumer key and secret
The sync module containing necessary user authentication functions

Task 5:The Prediction Module (prediction.py)
Input Arguments:
The main function prediction() requires three input arguments:
The database name (.sqlite file)
The fact balance (user’s current balance)
A number of years (positive integer number)

When the code is run, the database name is extracted via the get_user_id() function from the sync module.
The fact balance is globally saved while running the unrec_transact module and accessed like this: unrec_transact.factbalance.
The only input argument thus is the number of years that the prediction should run. It must be a positive integer and cannot exceed 5 years because I don’t think a longer time frame is sensible. Every integer number higher than 5 is automatically reduced to 5 by the function.
In the user interface, the user is required to enter a number during an input request. This number then is saved as nr_years and used as the third input argument.

Task 6: Reporting (reporting.py)
Goal: Generate financial report for user transactions over the last three months.

Input:
user ID (automatic)

Output:
Visual charts (bar and pie charts).
The code generates PDF report with detailed financial analysis.
