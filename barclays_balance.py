#!/usr/bin/env python3
import time
import secretstorage
import json
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup

def get_credentials():
    bus = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(bus)
    collection.unlock()
    secret = next(collection.search_items({'application': 'barclays'})).get_secret()
    return json.loads(secret)

def login(driver):
    driver.get('https://bank.barclays.co.uk')
    details = get_credentials()
    
    surname_field = driver.find_element_by_id('surname0')
    surname_field.send_keys(details['surname'])

    card_radio = driver.find_element_by_xpath('//*[@id="login-bootstrap"]/div/div[1]/div/div[1]/div[1]/div[1]/div[4]/section/form/div/div/div/div[4]/div/div/span/div/label')
    card_radio.click()

    cardNumber = details['cardNumber'].split('-')
    driver.find_element_by_id('cardNumber0').send_keys(cardNumber[0])
    driver.find_element_by_id('cardNumber1').send_keys(cardNumber[1])
    driver.find_element_by_id('cardNumber2').send_keys(cardNumber[2])
    driver.find_element_by_id('cardNumber3').send_keys(cardNumber[3])

    driver.find_element_by_xpath('//*[@id="login-bootstrap"]/div/div[1]/div/div[1]/div[1]/div[1]/div[4]/section/form/div/div/div/div[11]/div/button').click()

    time.sleep(3)
    
    driver.find_element_by_id('passcode0').send_keys(details['passcode'])

    secret_word_question = driver.find_element_by_id('label-memorableCharacters').text
    ch1, ch2 = secret_word_question.split(' ')[1][0], secret_word_question.split(' ')[3][0]
    ch1, ch2 = int(ch1), int(ch2)

    box1 = driver.find_element_by_name('firstMemorableCharacter').find_element_by_id('selectedCharacter')
    box1.click()
    ActionChains(driver).send_keys(details['secretWord'][ch1-1]).perform()

    box2 = driver.find_element_by_name('secondMemorableCharacter').find_element_by_id('selectedCharacter')
    box2.click()
    ActionChains(driver).send_keys(details['secretWord'][ch2-1]).perform()

    driver.find_element_by_id('btn-login-authSFA').click()

def get_balances(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    accounts = soup.find(id='account-list')

    for account in accounts.find_all(class_='personal'):
        try:
            name = account.find(class_='account-name').text
            balance = account.find(class_='balance').text

            yield (name, balance)
        except:
            pass

if __name__ == '__main__':
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')

    driver = webdriver.Chrome(chrome_options=options)

    login(driver)
    time.sleep(3)

    for account in get_balances(driver):
        print(account)

    driver.close()
