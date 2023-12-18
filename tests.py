import logging
import math
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from pyotp import TOTP
import pandas as pd
import pandas_ta as ta
from kiteconnect import KiteConnect

logging.basicConfig(filename='Neeraj.log', filemode='w', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
print(kite)
nse = kite.instruments('NSE')
nse_data = pd.DataFrame(nse)
print(nse_data)

def get_renko(timestamps, close, step):
    prices = close
    first_brick = {
        'timestamp': timestamps.iloc[0],
        'open': math.floor(prices.iloc[0] / step) * step,
        'high': math.floor((prices.iloc[0] / step) + 1) * step,
        'low': math.floor(prices.iloc[0] / step) * step,
        'close': math.floor((prices.iloc[0] / step) + 1) * step
    }
    bricks = [first_brick]
    for price, timestamp in zip(prices, timestamps):
        if price > (bricks[-1]['close'] + step):
            step_mult = math.floor((price - bricks[-1]['close']) / step)
            next_bricks = [{
                'timestamp': timestamp,
                'open': bricks[-1]['close'] + (mult * step),
                'high': bricks[-1]['close'] + ((mult + 1) * step),
                'low': bricks[-1]['close'] + (mult * step),
                'close': bricks[-1]['close'] + ((mult + 1) * step)
            } for mult in range(1, step_mult)]
            bricks += next_bricks
        elif price < bricks[-1]['close'] - step:
            step_mult = math.ceil((bricks[-1]['close'] - price) / step)
            next_bricks = [{
                'timestamp': timestamp,
                'open': bricks[-1]['close'] - (mult * step),
                'high': bricks[-1]['close'] - ((mult + 1) * step),
                'low': bricks[-1]['close'] - (mult * step),
                'close': bricks[-1]['close'] - ((mult + 1) * step)
            } for mult in range(1, step_mult-1)]
            bricks += next_bricks
        else:
            continue
    return pd.DataFrame(bricks)

# tradingsymbol_to_search = 'NIFTY 50'
# instrument_token_result = get_instrument_token(tradingsymbol_to_search, nse_data)

# if instrument_token_result is not None:
#     print(f"Instrument Token for {tradingsymbol_to_search}: {instrument_token_result}")

instrument_token = 256265
start_date = '2023-11-01'
end_date = '2023-12-15'
interval = 'day'
data = kite.historical_data(instrument_token, start_date, end_date, interval)
df = pd.DataFrame(data)

df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S').dt.tz_convert('Asia/Kolkata')
latest_timestamp = df['date'].max()
df.loc[df['date'].isnull(), 'date'] = latest_timestamp
df['ao'] = ta.ao(df['high'], df['low'])
print(df)
df.reset_index(inplace=True)
donchian_df = ta.donchian(df['high'], df['low'], 10, 10)
df = pd.concat([df, donchian_df], axis=1)
print(df)

# Use the get_renko function
renko_df = get_renko(df['date'], df['close'], step=20)
print("RENKO DF IS")
print(renko_df)
