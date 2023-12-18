import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from pyotp import TOTP
import time
from kiteconnect import KiteConnect
import pandas as pd
import pandas_ta as ta
import mplfinance as fplt
import math

# Clear the log file by overwriting it (filemode='w')
logging.basicConfig(filename='Neeraj.log', filemode='w', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def autologin():
    try:
        # Read API key and user credentials from a file
        token_path = "api_key.txt"
        key, secret, username, password, totp_secret = open(token_path, 'r').read().split()

        # Create a Chrome WebDriver instance
        driver = webdriver.Chrome()
        logging.info("WebDriver instance created")

        # Initialize KiteConnect with your API key
        kite = KiteConnect(api_key=key)
        logging.info("KiteConnect initialized")

        # Open the Kite login page
        driver.get(kite.login_url())
        driver.implicitly_wait(10)
        logging.info("Kite login page opened")

        # Fill in the username and password fields
        username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="userid"]')))
        password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="password"]')))

        logging.info("Username and password fields located")

        username_input.send_keys(username)
        password_input.send_keys(password)

        # Click the "Login" button
        login_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="container"]/div/div/div/form/div[4]/button')))
        login_button.click()
        logging.info("Clicked the 'Login' button")
        time.sleep(2)

        # Generate TOTP
        totp = TOTP(totp_secret)
        token = totp.now()

        # Locate the TOTP input field and submit button
        totp_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="userid"]')))
        submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div/div[1]/div[2]/div/div/form/div[2]/button')))

        totp_input.send_keys(token)
        submit_button.click()
        logging.info("Filled TOTP and clicked 'Submit'")
        time.sleep(5)

        # Wait for successful login  # Replace with the URL you expect after login
        logging.info("Successfully logged in")

        # Extract the request token from the URL
        url = driver.current_url
        initial_token = url.split('request_token=')[1]
        request_token = initial_token.split('&')[0]
        print(request_token)

        # Close the WebDriver
        driver.quit()
        logging.info("WebDriver closed")

        # Initialize KiteConnect again with your API key and the new access token
        kite = KiteConnect(api_key=key)
        data = kite.generate_session(request_token,secret)
        kite.set_access_token(data["access_token"])
        print(data)
        logging.info("Jarvis Enabled")
        return kite

       
    except StaleElementReferenceException:
        logging.error("Stale element reference: The element is no longer valid.")
    except Exception as e:
        logging.error(f"Error during login: {str(e)}")

# Call the autologin function
kite = autologin()
print(kite)
nse = kite.instruments('NSE')
nse_data = pd.DataFrame(nse)
print(nse_data)


# Fetch LTP for NIFTY BANK on NSE
def get_renko(timestamps, close, step):
    prices = close
    first_brick = {
        'timestamp': timestamps.iloc[0],
        'open': math.floor(prices.iloc[0] / step) * step,
        'close': math.floor((prices.iloc[0] / step)+1) * step
    }
    bricks = [first_brick]
    for price, timestamp in zip(prices, timestamps):
        if price > (bricks[-1]['close'] + step):
            step_mult = math.floor((price - bricks[-1]['close']) / step)
            next_bricks = [{
                'timestamp': timestamp,
                'open': bricks[-1]['close'] + (mult * step),
                'close': bricks[-1]['close'] + ((mult + 1) * step)
            } for mult in range(1, step_mult)]
            bricks += next_bricks

        elif price < bricks[-1]['close'] - step:
            step_mult = math.ceil((bricks[-1]['close'] - price) / step)
            next_bricks = [{
                'timestamp': timestamp,
                'open': bricks[-1]['close'] - (mult * step),
                'close': bricks[-1]['close'] - ((mult + 1) * step)
            } for mult in range(1, step_mult-1)]
            bricks += next_bricks

        else:
            continue

    return pd.DataFrame(bricks)

def get_instrument_token(tradingsymbol, df):
    try:
        row = df[df['tradingsymbol'] == tradingsymbol].iloc[0]
        instrument_token = row['instrument_token']
        return instrument_token
    except IndexError:
        print(f"Tradingsymbol '{tradingsymbol}' not found in the DataFrame.")
        return None

# Example usage
tradingsymbol_to_search = 'NIFTY 50'
instrument_token_result = get_instrument_token(tradingsymbol_to_search, nse_data)

if instrument_token_result is not None:
    print(f"Instrument Token for {tradingsymbol_to_search}: {instrument_token_result}")


# Assuming you have already authenticated and obtained the kite object

# Corrected instrument token
instrument_token = 256265

# Corrected date format and removed extra space in the date range
start_date = '2023-11-01'
end_date = '2023-12-15'

# Corrected interval to 'minute' (assuming you want minute-wise historical data)
interval = 'day'

# Fetch historical data
data = kite.historical_data(instrument_token, start_date, end_date, interval)

# Convert the historical data to a Pandas DataFrame
df = pd.DataFrame(data)
print(df)



# def generate_renko_atr(data):
#     atr_period = 14
#     atr_multiplier = 1.5

#     # Calculate ATR
#     data['atr'] = ta.atr(data['high'], data['low'], data['close'], atr_period)

#     renko_data = []
#     current_brick = {'date': data['date'].iloc[0], 'open': data['close'].iloc[0], 'close': data['close'].iloc[0]}

#     for _, row in data.iterrows():
#         price_move = row['close'] - current_brick['close']
#         atr_value = row['atr'] * atr_multiplier

#         # Check if a new brick needs to be created
#         if abs(price_move) >= atr_value:
#             brick_direction = 'up' if price_move > 0 else 'down'
#             renko_data.append({
#                 'date': current_brick['date'],
#                 'type': 'first' if not renko_data else brick_direction,
#                 'open': current_brick['close'],
#                 'high': max(current_brick['close'], row['close']),
#                 'low': min(current_brick['close'], row['close']),
#                 'close': row['close']
#             })

#             current_brick['open'] = row['close']
#             current_brick['close'] += atr_value if brick_direction == 'up' else -atr_value
#             current_brick['date'] = row['date']

#     # Add the last brick
#     renko_data.append({
#         'date': current_brick['date'],
#         'type': 'first' if not renko_data else brick_direction,
#         'open': current_brick['close'],
#         'high': max(current_brick['close'], data['close'].iloc[-1]),
#         'low': min(current_brick['close'], data['close'].iloc[-1]),
#         'close': data['close'].iloc[-1]
#     })

#     return pd.DataFrame(renko_data)

# Call the autologin function


# Fetch historical data

# Convert 'date' column to datetime
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S').dt.tz_convert('Asia/Kolkata')

# Fetch the latest timestamp
latest_timestamp = df['date'].max()

# Assuming your data is up to date, set the 'date' column to the latest timestamp

df.loc[df['date'].isnull(), 'date'] = latest_timestamp

# Generate Renko chart based on ATR
# renko_df = generate_renko_atr(df)
# print(renko_df)





# Calculate Awesome Oscillator
df['ao'] = ta.ao(df['high'], df['low'])

# Print the DataFrame with Awesome Oscillator values
print(df)

# Reset the index to make 'date' a regular column
df.reset_index(inplace=True)

# Calculate Donchian Channels
donchian_df = ta.donchian(df['high'], df['low'],10,10)

# Merge the calculated Donchian Channels with the original DataFrame
df = pd.concat([df, donchian_df], axis=1)

# Print the DataFrame with Donchian Channels
print(df)

