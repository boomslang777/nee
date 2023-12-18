import pandas as pd
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
import math
import pandas_ta as ta
from datetime import datetime
def autologin():
    try:
        token_path = "api_key.txt"
        key, secret, username, password, totp_secret = open(token_path, 'r').read().split()
        driver = webdriver.Chrome()
        logging.info("WebDriver instance created")
        kite = KiteConnect(api_key=key)
        logging.info("KiteConnect initialized")
        driver.get(kite.login_url())
        driver.implicitly_wait(10)
        logging.info("Kite login page opened")
        username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="userid"]')))
        password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="password"]')))
        logging.info("Username and password fields located")
        username_input.send_keys(username)
        password_input.send_keys(password)
        login_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="container"]/div/div/div/form/div[4]/button')))
        login_button.click()
        logging.info("Clicked the 'Login' button")
        time.sleep(2)
        totp = TOTP(totp_secret)
        token = totp.now()
        totp_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="userid"]')))
        submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div/div[1]/div[2]/div/div/form/div[2]/button')))
        totp_input.send_keys(token)
        submit_button.click()
        logging.info("Filled TOTP and clicked 'Submit'")
        time.sleep(5)
        logging.info("Successfully logged in")
        url = driver.current_url
        initial_token = url.split('request_token=')[1]
        request_token = initial_token.split('&')[0]
        print(request_token)
        driver.quit()
        logging.info("WebDriver closed")
        kite = KiteConnect(api_key=key)
        data = kite.generate_session(request_token, secret)
        kite.set_access_token(data["access_token"])
        print(data)
        logging.info("Jarvis Enabled")
        return kite
    except StaleElementReferenceException:
        logging.error("Stale element reference: The element is no longer valid.")
    except Exception as e:
        logging.error(f"Error during login: {str(e)}")
kite = autologin()



def get_renko(timestamps, close, step):
    prices = close
    first_brick = {
        'timestamp': timestamps[0],
        'open': math.floor(prices.iloc[0] / step) * step,
        'close': math.floor((prices.iloc[0] / step) + 1) * step
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
            } for mult in range(1, step_mult - 1)]
            bricks += next_bricks

        else:
            continue

    return pd.DataFrame(bricks)

# Fetch Renko values every minute and update the DataFrame
instrument_token = 256265
interval = 'minute'
step = 20

while True:
    # Fetch historical data
    data = kite.historical_data(instrument_token, datetime.now().strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'), interval)

    # Create DataFrame from historical data
    df = pd.DataFrame(data)
    print(df)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # Update the DataFrame with Renko values
    renko_values = get_renko(df.index, df['close'], step)
    df = pd.concat([df, renko_values], axis=1)

    # Compute Awesome Oscillator
    df['ao'] = ta.ao(df['high'], df['low'])

    # Calculate Donchian Channels
    donchian_df = ta.donchian(df['high'], df['low'], 10, 10)

    # Merge the calculated Donchian Channels with the original DataFrame
    df = pd.concat([df, donchian_df], axis=1)

    # Print the updated DataFrame
    print(df)

    # Sleep for 60 seconds before fetching data again
    time.sleep(60)