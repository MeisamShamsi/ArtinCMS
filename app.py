from flask import Flask, render_template, request
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend suitable for servers
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import base64

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Get inputs from the form
            initial_backup_fund = float(request.form['initial_backup_fund'])
            initial_fixed_income_fund = float(request.form['initial_fixed_income_fund'])
            initial_chance_fund = float(request.form['initial_chance_fund'])
            success_probability = float(request.form['success_probability'])
            chance_fund_profit_percentage = float(request.form['chance_fund_profit_percentage']) / 100
            total_months = int(request.form['total_months'])
            chance_fund_update_interval = int(request.form['chance_fund_update_interval'])
            
            # Validate that the update interval is at least 1
            if chance_fund_update_interval < 1:
                error_message = "Chance Fund update interval must be at least 1."
                return render_template('index.html', error_message=error_message)
            
            # Store initial balances
            initial_backup_fund_balance = initial_backup_fund
            initial_fixed_income_fund_balance = initial_fixed_income_fund
            initial_chance_fund_balance = initial_chance_fund

            # Initialize funds
            backup_fund_investments = []  # List to hold investments in the Backup Fund
            fixed_income_fund_balance = initial_fixed_income_fund
            chance_fund_balance = initial_chance_fund
            saving_fund_balance = 0.0

            # Interest rates
            backup_fund_annual_rate = 0.42
            fixed_income_fund_annual_rate = 0.26

            # Monthly rates
            fixed_income_monthly_rate = fixed_income_fund_annual_rate / 12

            # Data storage for plotting
            data = {
                'Month': [],
                'Backup Fund Balance': [],
                'Fixed Income Fund Balance': [],
                'Chance Fund Balance': [],
                'Saving Fund Balance': [],
                'Saving Fund Profit': [],
                'Total Backup and Fixed Income Balance': []
            }

            # Initialize profits
            fixed_income_profits_available = 0.0
            backup_fund_profits_available = 0.0

            # Add initial investment to backup fund investments
            backup_fund_investments.append({
                'amount': initial_backup_fund,
                'months_left': 12,
                'next_interest_in': 3
            })

            # Calculate total updates and number of successes
            # Updates start from the first interval
            update_months = list(range(chance_fund_update_interval, total_months + 1, chance_fund_update_interval))
            total_updates = len(update_months)
            number_of_successes = int(round(success_probability * total_updates))
            number_of_failures = total_updates - number_of_successes

            # Create a schedule of updates
            update_results = ['success'] * number_of_successes + ['failure'] * number_of_failures

            # Shuffle the schedule to distribute successes and failures
            np.random.shuffle(update_results)

            # Create a dictionary to map update months to results
            update_schedule = dict(zip(update_months, update_results))

            # Simulation loop
            for month in range(1, total_months + 1):
                # Reset monthly saving fund profit
                saving_fund_profit = 0.0

                # Fixed Income Fund - Monthly interest
                fixed_income_interest = fixed_income_fund_balance * fixed_income_monthly_rate
                fixed_income_fund_balance += fixed_income_interest
                fixed_income_profits_available += fixed_income_interest

                # Backup Fund - Process investments
                new_backup_investments = []
                for investment in backup_fund_investments:
                    investment['months_left'] -= 1
                    investment['next_interest_in'] -= 1

                    if investment['next_interest_in'] == 0:
                        # Pay interest every 3 months
                        interest = investment['amount'] * (backup_fund_annual_rate / 4)
                        backup_fund_profits_available += interest
                        investment['next_interest_in'] = 3

                    if investment['months_left'] == 0:
                        # Return principal after 12 months
                        backup_fund_profits_available += investment['amount']
                    else:
                        new_backup_investments.append(investment)

                backup_fund_investments = new_backup_investments

                # Reinvest profits in Backup Fund
                if backup_fund_profits_available > 0:
                    backup_fund_investments.append({
                        'amount': backup_fund_profits_available,
                        'months_left': 12,
                        'next_interest_in': 3
                    })
                    backup_fund_profits_available = 0.0

                # Chance Fund - Update at specified intervals
                if month in update_schedule:
                    result = update_schedule[month]
                    if result == 'success':
                        # Chance Fund makes a profit
                        profit = chance_fund_balance * chance_fund_profit_percentage

                        # Calculate amount needed to bring Chance Fund balance back to initial balance
                        amount_needed_to_initial = initial_chance_fund_balance - chance_fund_balance

                        if amount_needed_to_initial > 0:
                            # Use profit to bring Chance Fund balance back to initial balance
                            amount_to_chance_fund = min(profit, amount_needed_to_initial)
                            chance_fund_balance += amount_to_chance_fund
                            profit -= amount_to_chance_fund
                        else:
                            amount_to_chance_fund = 0  # No need to add to Chance Fund balance

                        # Transfer remaining profit to Saving Fund
                        saving_fund_balance += profit
                        saving_fund_profit += profit  # Record profit for this month

                    else:
                        # Chance Fund loses all money
                        chance_fund_balance = 0.0
                        # Recharge the Chance Fund
                        recharge_needed = initial_chance_fund_balance
                        recharge_amount = 0.0

                        # Use Fixed Income Fund profits
                        amount_from_fixed_income_profits = min(fixed_income_profits_available, recharge_needed)
                        fixed_income_profits_available -= amount_from_fixed_income_profits
                        recharge_amount += amount_from_fixed_income_profits
                        recharge_needed -= amount_from_fixed_income_profits

                        # Use Backup Fund profits
                        if recharge_needed > 0:
                            amount_from_backup_fund_profits = min(backup_fund_profits_available, recharge_needed)
                            backup_fund_profits_available -= amount_from_backup_fund_profits
                            recharge_amount += amount_from_backup_fund_profits
                            recharge_needed -= amount_from_backup_fund_profits

                        # Use Fixed Income Fund principal, but not below initial balance
                        if recharge_needed > 0:
                            max_amount_from_fixed_income_principal = fixed_income_fund_balance - initial_fixed_income_fund_balance
                            amount_from_fixed_income_principal = min(max_amount_from_fixed_income_principal, recharge_needed)
                            fixed_income_fund_balance -= amount_from_fixed_income_principal
                            recharge_amount += amount_from_fixed_income_principal
                            recharge_needed -= amount_from_fixed_income_principal

                        # Use Backup Fund principal, but not below initial balance
                        if recharge_needed > 0:
                            current_backup_fund_balance = sum(inv['amount'] for inv in backup_fund_investments)
                            max_amount_from_backup_fund_principal = current_backup_fund_balance - initial_backup_fund_balance
                            amount_from_backup_fund_principal = min(max_amount_from_backup_fund_principal, recharge_needed)
                            # Adjust backup fund investments
                            investments_removed = 0.0
                            new_backup_investments = []
                            for investment in backup_fund_investments:
                                if investments_removed < amount_from_backup_fund_principal:
                                    amount_needed = amount_from_backup_fund_principal - investments_removed
                                    if investment['amount'] <= amount_needed:
                                        investments_removed += investment['amount']
                                        # Skip adding this investment to new list
                                    else:
                                        # Reduce the amount of this investment
                                        investment['amount'] -= amount_needed
                                        investments_removed += amount_needed
                                        new_backup_investments.append(investment)
                                else:
                                    new_backup_investments.append(investment)
                            backup_fund_investments = new_backup_investments
                            recharge_amount += amount_from_backup_fund_principal
                            recharge_needed -= amount_from_backup_fund_principal

                        # Now, set the chance fund balance
                        chance_fund_balance += recharge_amount

                # Calculate total balance of Backup Fund and Fixed Income Fund
                total_backup_and_fixed_income = sum(inv['amount'] for inv in backup_fund_investments) + fixed_income_fund_balance

                # Record data for plotting
                data['Month'].append(month)
                data['Backup Fund Balance'].append(sum(inv['amount'] for inv in backup_fund_investments))
                data['Fixed Income Fund Balance'].append(fixed_income_fund_balance)
                data['Chance Fund Balance'].append(chance_fund_balance)
                data['Saving Fund Balance'].append(saving_fund_balance)
                data['Saving Fund Profit'].append(saving_fund_profit)
                data['Total Backup and Fixed Income Balance'].append(total_backup_and_fixed_income)

            # Create DataFrame
            df = pd.DataFrame(data)

            # Calculate final balances
            final_backup_fund_balance = df['Backup Fund Balance'].iloc[-1]
            final_fixed_income_fund_balance = df['Fixed Income Fund Balance'].iloc[-1]
            final_saving_fund_balance = df['Saving Fund Balance'].iloc[-1]
            total_balance = final_backup_fund_balance + final_fixed_income_fund_balance

            # Prepare data for the additional table
            final_balances = {
                'Backup Fund': final_backup_fund_balance,
                'Fixed Income Fund': final_fixed_income_fund_balance,
                'Saving Fund': final_saving_fund_balance,
                'Total of Backup and Fixed Income Funds': total_balance
            }

            # Format numbers with commas
            pd.options.display.float_format = '{:,.2f}'.format
            table_html = df.to_html(index=False, classes='table table-striped table-bordered', border=0)

            # Generate the plot
            plt.figure(figsize=(10, 6))
            plt.plot(df['Month'], df['Backup Fund Balance'], label='Backup Fund Balance')
            plt.plot(df['Month'], df['Fixed Income Fund Balance'], label='Fixed Income Fund Balance')
            plt.plot(df['Month'], df['Chance Fund Balance'], label='Chance Fund Balance')
            plt.plot(df['Month'], df['Saving Fund Balance'], label='Saving Fund Balance')
            plt.plot(df['Month'], df['Total Backup and Fixed Income Balance'], label='Total Backup and Fixed Income Fund Balance', linestyle='--', color='purple')
            # Remove 'Saving Fund Profit' from the chart
            # plt.bar(df['Month'], df['Saving Fund Profit'], color='orange', alpha=0.5, label='Saving Fund Profit')
            plt.xlabel('Month')
            plt.ylabel('Amount')
            plt.title('Capital Management Simulation')
            plt.legend()
            plt.grid(True)
            ax = plt.gca()
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))

            # Save the plot to a PNG image in memory
            img = io.BytesIO()
            plt.savefig(img, format='png', bbox_inches='tight')
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode()
            plt.close()  # Close the figure to free memory

            # Render the results template
            return render_template('results.html', table_html=table_html, plot_url=plot_url, final_balances=final_balances)
        except ValueError:
            error_message = "Please enter valid numerical values."
            return render_template('index.html', error_message=error_message)
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
