#!/usr/bin/env python3
import requests
from selenium import webdriver
from bs4 import BeautifulSoup
import time

start_url = 'https://manage.hut.shefcompsci.org.uk/timesheet_entries?week_commencing_date=2018-02-12'
clone_user = 'user_369'

class Epimanage:
    def __init__(self):
        self.driver = webdriver.Chrome()

    def login(self, username, password):
        self.driver.get(start_url)
        self.driver.find_element_by_id('username').send_keys(username)
        self.driver.find_element_by_id('password').send_keys(password)

        self.driver.find_element_by_xpath('//*[@id="fm1"]/div[3]/input[4]').click()

    def timetable(self):
        self.driver.get(start_url)

    def get_timetable_entry(self, url):
        self.driver.get(url)
        
        data = {
            'description': self.driver.find_element_by_id('timesheet_entry_description').text,
            'act': self.driver.find_element_by_id('timesheet_entry_activity_type').get_attribute('value'),
            'hours': self.driver.find_element_by_id('timesheet_entry_hours').get_attribute('value'),
        }
        
        return data

    def get_user_entries(self):
        self.timetable()

        entries = []

        for day in self.driver.find_element_by_id(clone_user).find_elements_by_tag_name('td'):
            day_entries = []
            for link in day.find_elements_by_tag_name('a'):
                if "Edit this entry" in link.get_attribute('title'):
                    day_entries.append(link.get_attribute('href'))
            entries.append(day_entries)

        return entries

    def new_entry(self, day, activity='development', hours=1, description=''):
        self.timetable()
        dateBoxes = self.driver.find_element_by_id('user_404')
        dateBoxes.find_elements_by_tag_name('td')[day].find_elements_by_class_name('add-timesheet-entry-btn')[0].click()
        time.sleep(2)

        self.driver.find_element_by_id('timesheet-project-select').find_elements_by_tag_name('option')[1].click()
        
        type_select = self.driver.find_element_by_id('timesheet_entry_activity_type')
        for act in type_select.find_elements_by_tag_name('option'):
            if act.get_attribute("value") == activity:
                act.click()

        hour_box = self.driver.find_element_by_id('timesheet_entry_hours')
        hour_box.clear()
        hour_box.send_keys(str(hours))

        self.driver.find_element_by_id('timesheet_entry_description').send_keys(description)

        self.driver.find_element_by_xpath('//*[@id="new_timesheet_entry"]/div[3]/button[1]').click()

if __name__ == '__main__':
    em = Epimanage()
    em.login('username', 'password')
    entries = em.get_user_entries()

    for i, day in enumerate(entries):
        for entry in day:
            details = em.get_timetable_entry(entry)
            print(details)
            em.new_entry(day=i, activity=details['act'], hours=details['hours'], description=details['description'])
