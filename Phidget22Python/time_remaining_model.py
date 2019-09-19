import pandas as pd
import numpy as np

from pmdarima.arima import auto_arima
from statsmodels.nonparametric.smoothers_lowess import lowess
from warnings import filterwarnings; filterwarnings("ignore")

# set readings per minute
readings_per_minute = 2


# NOTE TO DAVID
"""
The variable "data" needs to be a pandas dataframe with data from from the phidget with the following columns:
    DATETIME: a datetime
    INTERNAL_TEMP: a float
    CHEWS: a float

The variable "doneness_goal" needs to be an integer input from the user.

The variable ideal cook length needs to be a timedelta input from the user.

The print statements at the bottom will ideally be displayed in the UI.
"""

# set doneness goal
doneness_goal = int(input("Please enter doneness goal (700-999): "))

# time goal
ideal_cook_length = pd.Timedelta(hours=12)

# data
data = pd.DataFrame()


# change DATETIME column to datetime
data['DATETIME'] = pd.to_datetime(data['DATETIME'])

data['DATETIME'] = data.apply(lambda x: x.DATETIME +
                                        pd.Timedelta(
                                            seconds=60 / readings_per_minute) if x.COOK_INDEX % 2 != 0 else x.DATETIME,
                              axis=1)

# create TIME_PASSED column
data['TIME_PASSED'] = data.apply(lambda x: (x.DATETIME - data.DATETIME.iloc[0]).seconds,
                                 axis=1)

# set index to date and del datetime column
data.index = data['DATETIME']
del data['DATETIME']

# define start time, last time, finish time, and number of periods
start_time = data.index[0]
last_time = data.index[-1]
finish_time = start_time + ideal_cook_length
n_periods = int(((finish_time - last_time).seconds / 60) * readings_per_minute)

# run smoothing on data
df_loess_15 = pd.DataFrame(lowess(data.INTERNAL_TEMP,
                                  np.arange(len(data.INTERNAL_TEMP)),
                                  frac=0.15)[:, 1],
                           index=data.index,
                           columns=['INTERNAL_TEMP'])

# auto_arima model
model = auto_arima(df_loess_15.INTERNAL_TEMP,
                   start_p=0, start_q=0,
                   max_p=3, max_q=3,
                   d=1, trace=False,
                   seasonal=False,
                   error_action='ignore',
                   suppress_warnings=True,
                   stepwise=True)
# fit model
model.fit(df_loess_15)


def predict_chews(n_periods):
    # generate predictions five minutes ahead
    pred = model.predict(n_periods=n_periods)

    # calculate chews
    total_doneness = data['CHEWS'].iloc[-1]
    velocity = 0

    # create dictionary of chews forecasts
    pred_dict = dict()
    for record in pred:
        velocity = 0.00000000000000007048 * (float(record) ** 7.29007299056)

        total_doneness += (
                velocity / readings_per_minute
        )

        pred_dict[record] = total_doneness

    # create dataframe of results
    results = pd.DataFrame(list(pred_dict.items()),
                           columns=['PRED_INTERNAL_TEMP', 'CHEWS'],
                           index=list(i for i in range(1, n_periods + 1)))

    results.reset_index(inplace=True)
    results = results.rename(columns={'index': 'PERIOD_NUMBER'})

    # create sub data frame of times that achieve doneness goal
    sub_results = results[results['CHEWS'] >= doneness_goal]

    return results, sub_results


results, sub_results = predict_chews(n_periods)
last_chew = results.CHEWS.iloc[-1]

# define acceptable doneness range, 20 minutes on either side of finish_time
finish_time_hi = finish_time + pd.Timedelta(minutes=20)
finish_time_lo = finish_time - pd.Timedelta(minutes=20)


if last_chew < doneness_goal:

    while last_chew < doneness_goal:
        n_periods += 1
        results, sub_results = predict_chews(n_periods)
        last_chew = results.CHEWS.iloc[-1]

    projected_time = last_time + pd.Timedelta(
        minutes=n_periods / readings_per_minute)  # datetime the cook will reach doneness goal
    missing_goal = n_periods / readings_per_minute  # how many minutes are you off
    mins_until_finish_time = (finish_time - last_time).seconds / 60  # minutes until finish time

    if missing_goal > 20:

        print("\nPlease increase heat, not currently achieving doneness goal in time.")
        print(f"Cook will finish at {projected_time} - {int(missing_goal)} minutes late.")

    else:
        print(f"\nCook is on track! It will be finished at {projected_time} in {mins_until_finish_time} minutes.")


elif len(sub_results) > 0:
    goal_achieved_period = sub_results.PERIOD_NUMBER.iloc[0]
    projected_time = (last_time + pd.Timedelta(minutes=goal_achieved_period / readings_per_minute))
    missing_goal = (finish_time - projected_time).seconds / 60

    if missing_goal > 20:

        print("\nPlease decrease heat, currently riding too hot.")
        print(f"Cook will finish at {projected_time} - {int(missing_goal)} minutes early.")

    else:
        print(
            f"\nCook is on track! It will be finished at {projected_time} in {goal_achieved_period / readings_per_minute} minutes.")