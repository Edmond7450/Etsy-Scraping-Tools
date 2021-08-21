import copy
import csv
import datetime
import glob
import json
import os
import requests
import time

from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sys import platform

import my_settings

server_status = ''
flag_stop = False


class HomeView(TemplateView):
    template_name = 'index.html'
    driver = None

    def get(self, request, *args, **kwargs):
        files = list(filter(os.path.isfile, glob.glob("static/result/*.csv")))
        files.sort(key=lambda x: os.path.getatime(x), reverse=True)
        files = [os.path.basename(file) for file in files]

        return render(request, self.template_name, {'files': files})

    def post(self, request, *args, **kwargs):
        param = {}
        param['urls'] = request.POST['urls'].strip()
        param['pages'] = request.POST['pages'].strip()
        param['shop_keywords'] = request.POST['shop_keywords'].strip()
        param['product_ids'] = request.POST['product_ids'].strip()
        param['product_keywords'] = request.POST['product_keywords'].strip()
        param['analyze_shops'] = request.POST['analyze_shops'].strip()
        param['ckb_product'] = request.POST.get('ckb_product')
        param['analyze_keywords'] = request.POST['analyze_keywords'].strip()

        urls = param['urls'].split(',')
        try:
            pages = int(param['pages'])
        except:
            pages = 10000

        shop_keywords = param['shop_keywords'].split(',')
        product_ids = param['product_ids'].split(',')
        product_keywords = param['product_keywords'].split(',')
        analyze_shops = param['analyze_shops'].split(',')
        analyze_keywords = param['analyze_keywords'].split(',')
        if param['ckb_product'] == 'on':
            ckb_product = True
        else:
            ckb_product = False

        chrome_options = Options()
        chrome_options.add_argument("window-size=1024,1000")
        chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("user-data-dir=selenium")
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
        chrome_options.add_argument(f'user-agent={user_agent}')
        # chrome_options.add_argument('--proxy-server=%s' % proxy)

        # if platform == "win32" or platform == "win64":
        #     chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(options=chrome_options)
        url = 'https://www.etsy.com/'
        self.driver.get(url)
        time.sleep(2)

        try:
            setting = self.driver.find_element_by_xpath('//button[@data-gdpr-single-choice-accept=""]')
            setting.click()
            time.sleep(1)

            # setting = self.driver.find_element_by_xpath('//button[@data-gdpr-open-full-settings=""]')
            # setting.click()
            # time.sleep(1)
            #
            # if self.driver.find_element_by_xpath('//div[@data-section="personalization_consent"]//label[contains(@class, "privacySettings__toggleLabel")]').text.strip() == 'Off':
            #     ckb = self.driver.find_element_by_xpath('//div[@data-section="personalization_consent"]//div[@class="privacySettings__toggle"]')
            #     self.driver.execute_script("arguments[0].scrollIntoView()", ckb)
            #     ckb.click()
            #     time.sleep(1)
            #
            # if self.driver.find_element_by_xpath('//div[@data-section="third_party_consent"]//label[contains(@class, "privacySettings__toggleLabel")]').text.strip() == 'Off':
            #     ckb = self.driver.find_element_by_xpath('//div[@data-section="third_party_consent"]//div[@class="privacySettings__toggle"]')
            #     self.driver.execute_script("arguments[0].scrollIntoView()", ckb)
            #     ckb.click()
            #     time.sleep(1)
            #
            # btn = self.driver.find_element_by_xpath('//*[@id="gdpr-privacy-settings"]//button')
            # self.driver.execute_script("arguments[0].scrollIntoView()", btn)
            # btn.click()

            time.sleep(1)
            self.driver.find_element_by_xpath('//button[@data-etsy-promo-banner-dismiss=""]').click()
        except:
            pass

        global server_status
        global flag_stop
        server_status = ''
        flag_stop = False

        if urls != ['']:
            self.find_shops_by_urls(urls, pages)

        if shop_keywords != ['']:
            self.find_shops_by_keywords(shop_keywords)

        if product_ids != ['']:
            self.find_products_by_id(product_ids)

        if product_keywords != ['']:
            self.find_products_by_keyword(product_keywords)

        if analyze_shops != ['']:
            self.analyze_shops(analyze_shops, ckb_product)

        if analyze_keywords != ['']:
            self.analyze_keywords(analyze_keywords)

        self.driver.close()

        files = list(filter(os.path.isfile, glob.glob("static/result/*.csv")))
        files.sort(key=lambda x: os.path.getatime(x), reverse=True)
        files = [os.path.basename(file) for file in files]

        param['files'] = files

        return render(request, self.template_name, param)

    def find_shops_by_urls(self, urls, pages):
        global server_status
        global flag_stop

        output_filename = "static/result/shop_urls_output"
        fileIndex = 1
        fname = output_filename
        while os.path.isfile(fname + ".csv") == True:
            fname = "%s_%06d" % (output_filename, fileIndex)
            fileIndex = fileIndex + 1
        output_filename = fname

        with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
            of.write(','.join(['InputURL', 'Rank', 'Shop', 'ProductID', 'Price', 'Title', 'Tags']) + '\n')

        for url in urls:
            if flag_stop:
                break

            url = url.strip()
            self.driver.get(url)
            print(url)
            server_status = server_status + '\n\n' + url
            time.sleep(3)

            current_page = 1
            while current_page <= pages:
                if flag_stop:
                    break

                server_status = server_status + '\ncurrent page: ' + str(current_page)

                try:
                    WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
                except:
                    pass

                rank = 0
                rows = self.driver.find_elements_by_xpath('//div[@data-search-results-region=""]//li//a')
                for row in rows:
                    if flag_stop:
                        break

                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView()", row)
                        time.sleep(1)
                    except:
                        pass

                    rank += 1
                    item = {}
                    tags = []
                    item['InputURL'] = self.driver.current_url
                    item['Rank'] = rank
                    try:
                        shop = row.find_element_by_xpath('.//div[@class="v2-listing-card__shop"]/p[contains(@class, "screen-reader-only")]').text.strip()
                        if shop.find('Ad from shop ') != -1:
                            item['Shop'] = shop[13:]
                            tags.append('Ad')
                        else:
                            item['Shop'] = shop[10:]
                    except:
                        continue
                    if item['Shop'] == '':
                        continue
                    item['ProductID'] = row.get_attribute('data-listing-id')
                    try:
                        item['Price'] = row.find_element_by_xpath('.//span[contains(@class, "n-listing-card__price")]//span[@class="currency-value"]').text.strip()
                    except:
                        continue
                    if item['Price'] == '':
                        continue
                    item['Title'] = row.get_attribute('title')

                    try:
                        row.find_element_by_xpath('.//span[contains(@class, "promotion-price")]')
                        tags.append('Discounted')
                    except:
                        pass
                    try:
                        row.find_element_by_xpath('.//span[contains(@class, "wt-badge")]/span[@class="display-inline-block"]')
                        tags.append('Bestseller')
                    except:
                        pass
                    item['Tags'] = ', '.join(tags)

                    with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
                        writer = csv.DictWriter(of, fieldnames=['InputURL', 'Rank', 'Shop', 'ProductID', 'Price', 'Title', 'Tags'])
                        writer.writerow(item)

                page_links = self.driver.find_elements_by_xpath('//nav[@class="search-pagination"]//li/a')
                self.driver.execute_script("arguments[0].scrollIntoView()", page_links[-1])
                time.sleep(1)
                page_links[-1].click()
                time.sleep(3)
                current_page += 1

    def find_shops_by_keywords(self, shop_keywords):
        global server_status
        global flag_stop

        output_filename = "static/result/shop_keywords_output"
        fileIndex = 1
        fname = output_filename
        while os.path.isfile(fname + ".csv") == True:
            fname = "%s_%06d" % (output_filename, fileIndex)
            fileIndex = fileIndex + 1
        output_filename = fname

        with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
            of.write(','.join(['Keyword', 'ShopName']) + '\n')

        for keyword in shop_keywords:
            if flag_stop:
                break

            url = f"https://www.etsy.com/search/shops?search_query={keyword.strip()}"
            self.driver.get(url)
            print(url)
            server_status = server_status + '\n' + url
            time.sleep(3)

            current_page = 1
            while 1:
                if flag_stop:
                    break

                server_status = server_status + '\ncurrent page: ' + str(current_page)

                try:
                    WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
                except:
                    pass

                rows = self.driver.find_elements_by_xpath('//span[contains(@class, "shopname")]/a')
                for row in rows:
                    if flag_stop:
                        break

                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView()", row)
                        time.sleep(1)
                    except:
                        pass

                    item = {}
                    item['Keyword'] = keyword.strip()
                    shop_url = row.get_attribute('href')
                    item['ShopName'] = shop_url[26:shop_url.find('?')]

                    with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
                        writer = csv.DictWriter(of, fieldnames=['Keyword', 'ShopName'])
                        writer.writerow(item)

                next_page = self.driver.find_element_by_xpath('//a[@id="pager-next"]')
                self.driver.execute_script("arguments[0].scrollIntoView()", next_page)
                time.sleep(1)
                if next_page.is_enabled() and next_page.get_attribute('class') != 'next-disabled':
                    next_page.click()
                    time.sleep(3)
                else:
                    break

                current_page += 1

    def find_products_by_id(self, product_ids):
        global server_status
        global flag_stop

        output_filename = "static/result/product_ids_output"
        fileIndex = 1
        fname = output_filename
        while os.path.isfile(fname + ".csv") == True:
            fname = "%s_%06d" % (output_filename, fileIndex)
            fileIndex = fileIndex + 1
        output_filename = fname

        with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
            of.write(','.join(['ProductID', 'Tags']) + '\n')

        for product_id in product_ids:
            if flag_stop:
                break

            url = f"https://www.etsy.com/listing/{product_id.strip()}"
            self.driver.get(url)
            print(url)
            server_status = server_status + '\n' + url
            time.sleep(3)

            item = {}
            item['ProductID'] = product_id.strip()
            tags = []

            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
            except:
                pass

            rank = 0
            tag_rows = self.driver.find_elements_by_xpath('//ul[contains(@class, "tag-cards-with-image")]//*[contains(@class, "tag-with-image-text-internal")]')
            for tag_row in tag_rows:
                if rank == 0:
                    rank += 1
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView()", tag_row)
                        time.sleep(1)
                    except:
                        pass

                if tag_row.get_attribute('title').islower():
                    tags.append(tag_row.get_attribute('title'))

            rank = 0
            tag_rows = self.driver.find_elements_by_xpath('//*[@id="wt-content-toggle-tags-read-more"]//li/a')
            for tag_row in tag_rows:
                if rank == 0:
                    rank += 1
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView()", tag_row)
                        time.sleep(1)
                    except:
                        pass

                if tag_row.text.islower():
                    tags.append(tag_row.text.strip())

            item['Tags'] = ', '.join(tags)

            with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
                writer = csv.DictWriter(of, fieldnames=['ProductID', 'Tags'])
                writer.writerow(item)

    def find_products_by_keyword(self, product_keywords):
        global server_status
        global flag_stop

        output_filename = "static/result/product_keywords_output"
        fileIndex = 1
        fname = output_filename
        while os.path.isfile(fname + ".csv") == True:
            fname = "%s_%06d" % (output_filename, fileIndex)
            fileIndex = fileIndex + 1
        output_filename = fname

        with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
            of.write(','.join(['MainKeyword', 'Tags']) + '\n')

        url = 'https://www.etsy.com/'
        self.driver.get(url)
        print(url)
        server_status = server_status + '\n' + url
        time.sleep(3)

        for keyword in product_keywords:
            if flag_stop:
                break

            server_status = server_status + '\n' + 'Search: ' + keyword

            item = {}
            item['MainKeyword'] = keyword.strip()
            tags = []

            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
            except:
                pass

            input = self.driver.find_element_by_xpath('//*[@id="global-enhancements-search-query"]')
            try:
                self.driver.execute_script("arguments[0].scrollIntoView()", input)
                time.sleep(1)
            except:
                pass
            input.click()
            input.clear()
            time.sleep(1)
            input.send_keys(item['MainKeyword'])
            time.sleep(2)

            rows = self.driver.find_elements_by_xpath('//*[@id="global-enhancements-search-suggestions"]//li')
            for row in rows:
                tags.append(row.get_attribute("textContent").strip())

            item['Tags'] = ', '.join(tags)

            with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
                writer = csv.DictWriter(of, fieldnames=['MainKeyword', 'Tags'])
                writer.writerow(item)

    def analyze_shops(self, analyze_shops, ckb_product):
        global server_status
        global flag_stop

        output_filename = "static/result/analyze_shops_output"
        fileIndex = 1
        fname = output_filename
        while os.path.isfile(fname + ".csv") == True:
            fname = "%s_%06d" % (output_filename, fileIndex)
            fileIndex = fileIndex + 1
        output_filename = fname

        with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
            of.write(','.join(['ShopName', 'ShopCreatedDaysAgo', 'ShopBIO', 'ShopCountry', 'ShopOwner', 'ShopOwnerResponse', 'ShopHasFAQ', 'SaleMessage',
                                'ShopCategories', 'ShopSales', 'ShopFavorites', 'ShopAnnouncement', 'ShopItems', 'ShopReviews', 'ShopRating',
                                'ListingID', 'ListingTitle', 'ListingCategory', 'ListingTags', 'ListingMedia', 'ListingPrice', 'ListingViews', 'ListingFavorites',
                                'ListingReviews', 'ListingSales', 'ListingKeywords', 'ListingDescriptionLengthWords', 'ListingCreatedDaysAgo', 'ListingUpdatedDaysAgo']) + '\n')

        for shop in analyze_shops:
            if flag_stop:
                break

            url = f"https://www.etsy.com/shop/{shop.strip()}"
            self.driver.get(url)
            print(url)
            server_status = server_status + '\n\n' + url
            time.sleep(3)

            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
            except:
                pass

            item = {}
            try:
                item['ShopName'] = self.driver.find_element_by_xpath('//div[contains(@class, "shop-name-and-title-container")]/h1').text.strip()
            except:
                item['ShopName'] = shop.strip()
                item['ShopCreatedDaysAgo'] = ''
                item['ShopBIO'] = 'Sorry, the page you were looking for was not found.'
                with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
                    writer = csv.DictWriter(of, fieldnames=['ShopName', 'ShopCreatedDaysAgo', 'ShopBIO'])
                    writer.writerow(item)
                continue
            try:
                item['ShopBIO'] = self.driver.find_element_by_xpath('//div[contains(@class, "shop-name-and-title-container")]/span').text.strip()
            except:
                item['ShopBIO'] = ''
            try:
                item['ShopCountry'] = self.driver.find_element_by_xpath('//span[contains(@class, "shop-location ")]').text.split(',')[-1].strip()
            except:
                item['ShopCountry'] = ''
            item['ShopOwner'] = self.driver.find_element_by_xpath('//div[contains(@class, "shop-owner ")]//a/p').text.strip()
            try:
                faq = self.driver.find_element_by_xpath('//*[@id="faq"]')
                self.driver.execute_script("arguments[0].scrollIntoView()", faq)
                time.sleep(1)
                item['ShopHasFAQ'] = 'yes'
            except:
                item['ShopHasFAQ'] = 'no'

            item['ShopCategories'] = len(self.driver.find_elements_by_xpath('//button[contains(@class, "wt-tab__item")]')) - 1
            try:
                item['ShopSales'] = self.driver.find_element_by_xpath('//div[contains(@class, "shop-info")]//a[@rel="nofollow"]').text.split()[0].replace(',', '')
                has_sold = True
            except:
                try:
                    item['ShopSales'] = self.driver.find_element_by_xpath('//div[contains(@class, "shop-info")]/div[2]/span[1]').text.split()[0].replace(',', '')
                except:
                    item['ShopSales'] = ''
                has_sold = False
            try:
                item['ShopFavorites'] = self.driver.find_element_by_xpath('//div[contains(@class, "shop-info")]//span[@data-region="num-favorers"]').text.replace(',', '')
            except:
                item['ShopFavorites'] = ''
            try:
                item['ShopAnnouncement'] = self.driver.find_element_by_xpath('//*[@data-inplace-editable-text="announcement"]').get_attribute("textContent")
            except:
                item['ShopAnnouncement'] = ''
            item['ShopItems'] = self.driver.find_element_by_xpath('//button[@data-section-id="0"]/span[2]').text.strip().replace(',', '')
            try:
                reviews = self.driver.find_element_by_xpath('//div[contains(@class, "reviews-total")]/div/div[3]')
                self.driver.execute_script("arguments[0].scrollIntoView()", reviews)
                time.sleep(1)
                item['ShopReviews'] = reviews.text.replace('(', '').replace(')', '').replace(',', '').strip()
            except:
                try:
                    shop_home_html = self.driver.find_element_by_xpath('//div[contains(@class, "shop-home")]').get_attribute('innerHTML')
                    start_pos = shop_home_html.find('"reviewCount": "')
                    if start_pos != -1:
                        start_pos += 16
                        end_pos = shop_home_html.find('"', start_pos)
                        item['ShopReviews'] = shop_home_html[start_pos:end_pos]
                    else:
                        item['ShopReviews'] = ''
                except:
                    item['ShopReviews'] = ''

            try:
                item['ShopRating'] = self.driver.find_element_by_xpath('//div[contains(@class, "shop-info")]//input[@name="initial-rating"]').get_attribute('value')
            except:
                item['ShopRating'] = ''

            try:
                url = f"https://openapi.etsy.com/v2/shops/{item['ShopName']}?api_key={my_settings.API_KEY}"
                response = requests.get(url, timeout=5)
                results = json.loads(response.content)['results'][0]
                item['ShopCreatedDaysAgo'] = (datetime.datetime.now() - datetime.datetime.fromtimestamp(results['creation_tsz'])).days
                if results['sale_message']:
                    item['SaleMessage'] = results['sale_message']
                else:
                    item['SaleMessage'] = results['digital_sale_message']
            except:
                pass
            item['ShopOwnerResponse'] = ''

            if ckb_product and int(item['ShopItems']) > 0:
                solds = {}
                if has_sold:
                    solds = self.parse_sold(item['ShopName'])

                categories = self.driver.find_elements_by_xpath('//button[contains(@class, "wt-tab__item")]')
                category_index = 0
                for category in categories:
                    if flag_stop:
                        break

                    category_index += 1
                    category_name = category.find_element_by_xpath('.//span[1]').text.strip()
                    if (category_name == 'All' or category_name == 'On sale') and category_index < len(categories):
                        continue
                    server_status = server_status + '\ncategory: ' + category_name
                    self.driver.execute_script("arguments[0].scrollIntoView()", category)
                    time.sleep(1)
                    category.click()
                    time.sleep(3)

                    try:
                        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
                    except:
                        pass

                    product_index = 0
                    current_page = 1
                    while 1:
                        if flag_stop:
                            break

                        server_status = server_status + '\ncurrent page: ' + str(current_page)

                        rows = self.driver.find_elements_by_xpath('//div[contains(@class, "responsive-listing-grid")]/div')
                        if len(rows) == 0:
                            rows = self.driver.find_elements_by_xpath('//ul[contains(@class, "listing-cards")]/li[contains(@class, "v2-listing-card position-relative")]')

                        main_window = self.driver.current_window_handle
                        for row in rows:
                            product_index += 1
                            self.driver.execute_script("arguments[0].scrollIntoView()", row)
                            time.sleep(1)

                            product_item = copy.deepcopy(item)
                            product_item['ListingID'] = row.get_attribute('data-listing-id')
                            product_item['ListingTitle'] = row.find_element_by_xpath('./a').get_attribute('title')
                            product_item['ListingCategory'] = category_name
                            product_item['ListingPrice'] = row.find_element_by_xpath('.//span[@class="currency-value"]').text.strip()
                            tags = []

                            try:
                                row.find_element_by_xpath('.//span[contains(@class, "through")]')
                                tags.append('discounted')
                            except:
                                pass
                            try:
                                row.find_element_by_xpath('.//span[contains(@class, "wt-badge--sale-01")]')
                                tags.append('free shipping')
                            except:
                                pass
                            try:
                                red_text = row.find_element_by_xpath('.//div[contains(@class, "wt-text-brick")]').text
                            except:
                                try:
                                    red_text = row.find_element_by_xpath('.//div[contains(@class, "text-danger")]').text
                                except:
                                    red_text = ''
                            if red_text.find(' have this in their cart') != -1:
                                tags.append('in peoples carts')
                            if red_text.find(' left') != -1:
                                tags.append('limited quantity')

                            row.find_element_by_xpath('.//a').click()
                            time.sleep(3)
                            self.driver.switch_to.window(self.driver.window_handles[1])
                            time.sleep(3)
                            try:
                                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
                            except:
                                pass
                            server_status = server_status + '\n' + self.driver.current_url

                            try:
                                self.driver.find_element_by_xpath('//*[@id="listing-page-cart"]//span[contains(@class, "wt-badge--status-03")]')
                                tags.insert(0, 'bestseller')
                            except:
                                pass
                            # try:
                            #     limited_quantity = self.driver.find_element_by_xpath('//*[@id="nudge-copy-plural"]/span[@class="nudge-number"]').text.strip()
                            #     tags.append('limited quantity')
                            # except:
                            #     pass

                            product_item['ListingTags'] = ', '.join(tags)

                            if not product_item['ShopOwnerResponse']:
                                try:
                                    product_item['ShopOwnerResponse'] = self.driver.find_element_by_xpath('//div[contains(@class, "description-right")]//div/div[3]//p[2]/b').text
                                except:
                                    try:
                                        product_item['ShopOwnerResponse'] = self.driver.find_element_by_xpath('//div[contains(@class, "description-right")]//div/div[3]//p[2]/strong').text
                                    except:
                                        product_item['ShopOwnerResponse'] = ''
                                item['ShopOwnerResponse'] = product_item['ShopOwnerResponse']

                            product_item['ListingMedia'] = len(self.driver.find_elements_by_xpath('//*[@id="listing-right-column"]//div[contains(@class, "wt-overflow-scroll")]/ul/li'))
                            # try:
                            #     product_item['ListingRating'] = self.driver.find_element_by_xpath('//*[@id="reviews"]//h3//input[@name="rating"]').get_attribute('value')
                            # except:
                            #     product_item['ListingRating'] = ''
                            try:
                                favorites = self.driver.find_element_by_xpath('//a[contains(@href, "/favoriters?")]').text.strip()
                                if favorites == 'One favorite' or favorites == 'One favourite':
                                    product_item['ListingFavorites'] = '1'
                                else:
                                    product_item['ListingFavorites'] = favorites.replace('favorites', '').replace('favourite', '').strip()
                            except:
                                product_item['ListingFavorites'] = ''
                            try:
                                product_item['ListingReviews'] = self.driver.find_element_by_xpath('//*[@id="same-listing-reviews-tab"]/span').text.strip()
                            except:
                                double_review = self.driver.find_elements_by_xpath('//*[@id="reviews"]//div[contains(@class, "wt-grid")]//a[contains(@href, "/listing/' + product_item['ListingID'] + '/")]')
                                product_item['ListingReviews'] = int(len(double_review) / 2)
                                pass
                            try:
                                product_item['ListingSales'] = solds[product_item['ListingID']]
                            except:
                                product_item['ListingSales'] = ''

                            rank = 0
                            tags = []
                            tag_rows = self.driver.find_elements_by_xpath('//ul[contains(@class, "tag-cards-with-image")]//*[contains(@class, "tag-with-image-text-internal")]')
                            for tag_row in tag_rows:
                                if rank == 0:
                                    rank += 1
                                    try:
                                        self.driver.execute_script("arguments[0].scrollIntoView()", tag_row)
                                        time.sleep(1)
                                    except:
                                        pass

                                if tag_row.get_attribute('title').islower():
                                    tags.append(tag_row.get_attribute('title'))

                            rank = 0
                            tag_rows = self.driver.find_elements_by_xpath('//*[@id="wt-content-toggle-tags-read-more"]//li/a')
                            for tag_row in tag_rows:
                                if rank == 0:
                                    rank += 1
                                    try:
                                        self.driver.execute_script("arguments[0].scrollIntoView()", tag_row)
                                        time.sleep(1)
                                    except:
                                        pass

                                if tag_row.text.islower():
                                    tags.append(tag_row.text.strip())

                            product_item['ListingKeywords'] = ', '.join(tags)
                            try:
                                description = self.driver.find_element_by_xpath('//*[@id="wt-content-toggle-product-details-read-more"]').text.strip()
                                product_item['ListingDescriptionLengthWords'] = len(description.split())
                            except:
                                product_item['ListingDescriptionLengthWords'] = ''

                            try:
                                listed_on = self.driver.find_element_by_xpath('//div[contains(@class, "wt-align-items-baseline")]/div[contains(@class, "wt-align-items-baseline")]/div[1]').text.replace('Listed on ', '').strip()
                                product_item['ListingUpdatedDaysAgo'] = (datetime.datetime.now() - datetime.datetime.strptime(listed_on, '%b %d, %Y')).days
                            except:
                                product_item['ListingUpdatedDaysAgo'] = ''

                            time.sleep(3)
                            self.driver.close()
                            # self.driver.switch_to.window(self.driver.window_handles[0])
                            self.driver.switch_to.window(main_window)
                            time.sleep(3)

                            try:
                                url = f"https://openapi.etsy.com/v2/listings/{product_item['ListingID']}?api_key={my_settings.API_KEY}"
                                response = requests.get(url, timeout=5)
                                results = json.loads(response.content)['results'][0]
                                product_item['ListingViews'] = results['views']
                                product_item['ListingCreatedDaysAgo'] = (datetime.datetime.now() - datetime.datetime.fromtimestamp(results['creation_tsz'])).days
                            except:
                                pass

                            with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
                                writer = csv.DictWriter(of, fieldnames=['ShopName', 'ShopCreatedDaysAgo', 'ShopBIO', 'ShopCountry', 'ShopOwner', 'ShopOwnerResponse', 'ShopHasFAQ', 'SaleMessage',
                                                                        'ShopCategories', 'ShopSales', 'ShopFavorites', 'ShopAnnouncement', 'ShopItems', 'ShopReviews', 'ShopRating',
                                                                        'ListingID', 'ListingTitle', 'ListingCategory', 'ListingTags', 'ListingMedia', 'ListingPrice', 'ListingViews', 'ListingFavorites',
                                                                        'ListingReviews', 'ListingSales', 'ListingKeywords', 'ListingDescriptionLengthWords', 'ListingCreatedDaysAgo', 'ListingUpdatedDaysAgo'])
                                writer.writerow(product_item)

                        pages = self.driver.find_elements_by_xpath('//div[@data-item-pagination=""]/div[3]//li/a')
                        if len(pages) > 0:
                            next_page = pages[-1]
                            self.driver.execute_script("arguments[0].scrollIntoView()", next_page)
                            time.sleep(1)
                            if next_page.is_enabled() and next_page.get_attribute('class').find('wt-is-disabled') == -1:
                                next_page.click()
                                time.sleep(3)
                            else:
                                break
                        else:
                            break

                        current_page += 1

                if flag_stop:
                    break
            else:
                try:
                    try:
                        row = self.driver.find_element_by_xpath('//div[contains(@class, "responsive-listing-grid")]/div')
                    except:
                        row = self.driver.find_element_by_xpath('//ul[contains(@class, "listing-cards")]/li[contains(@class, "v2-listing-card position-relative")]')

                    self.driver.execute_script("arguments[0].scrollIntoView()", row)
                    time.sleep(1)
                    row.click()
                    time.sleep(3)
                    self.driver.switch_to.window(self.driver.window_handles[1])
                    time.sleep(3)

                    try:
                        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
                        item['ShopOwnerResponse'] = self.driver.find_element_by_xpath('//div[contains(@class, "description-right")]//div/div[3]//p[2]/b').text
                    except:
                        try:
                            item['ShopOwnerResponse'] = self.driver.find_element_by_xpath('//div[contains(@class, "description-right")]//div/div[3]//p[2]/strong').text
                        except:
                            item['ShopOwnerResponse'] = ''

                    time.sleep(3)
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    time.sleep(3)
                except:
                    item['ShopOwnerResponse'] = ''

                with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
                    writer = csv.DictWriter(of, fieldnames=['ShopName', 'ShopCreatedDaysAgo', 'ShopBIO', 'ShopCountry', 'ShopOwner', 'ShopOwnerResponse', 'ShopHasFAQ', 'SaleMessage',
                                                            'ShopCategories', 'ShopSales', 'ShopFavorites', 'ShopAnnouncement', 'ShopItems', 'ShopReviews', 'ShopRating'])
                    writer.writerow(item)

    def parse_sold(self, shop):
        global server_status
        global flag_stop
        solds = {}

        url = f'https://www.etsy.com/shop/{shop}/sold'
        self.driver.execute_script('''window.open(arguments[0],"_blank");''', url)
        time.sleep(3)
        self.driver.switch_to.window(self.driver.window_handles[-1])
        server_status = server_status + '\n\n' + url
        time.sleep(3)

        current_page = 0
        while 1:
            if flag_stop:
                break

            current_page += 1
            server_status = server_status + '\nsold page: ' + str(current_page)

            rows = self.driver.find_elements_by_xpath('//a[contains(@class, "listing-link")]')
            for row in rows:
                listing_id = row.get_attribute('data-listing-id')
                if listing_id in solds.keys():
                    solds[listing_id] += 1
                else:
                    solds[listing_id] = 1

            pages = self.driver.find_elements_by_xpath('//li[contains(@class, "btn-list-item")]')
            if len(pages) > 0:
                next_page = pages[-1]
                self.driver.execute_script("arguments[0].scrollIntoView()", next_page)
                time.sleep(1)
                if next_page.is_enabled() and next_page.get_attribute('class').find('is-disabled') == -1:
                    next_page.find_element_by_xpath('./a').click()
                    time.sleep(3)
                else:
                    break
            else:
                break

        time.sleep(3)
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        time.sleep(3)

        return solds

    def analyze_keywords(self, analyze_keywords):
        global server_status
        global flag_stop

        output_filename = "static/result/analyze_keywords_output"
        fileIndex = 1
        fname = output_filename
        while os.path.isfile(fname + ".csv") == True:
            fname = "%s_%06d" % (output_filename, fileIndex)
            fileIndex = fileIndex + 1
        output_filename = fname

        with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
            of.write(','.join(['ProductID', 'Tags']) + '\n')

        for analyze_keyword in analyze_keywords:
            if flag_stop:
                break

            url = f"https://www.etsy.com/search?q={analyze_keyword.strip()}"
            self.driver.get(url)
            print(url)
            server_status = server_status + '\n' + url
            time.sleep(3)

            item = {}
            item['Keyword'] = analyze_keyword.strip()

            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//body')))
            except:
                pass
            try:
                row = self.driver.find_element_by_xpath('//div[contains(@class, "search-listings-group")]//div[contains(@class, "clearfix")]//span[@class="wt-display-inline-flex-lg"]/span[2]').text.strip()
                item['Results'] = row.split()[0].replace('(', '').replace(',', '')
            except:
                try:
                    row = self.driver.find_element_by_xpath('//div[contains(@class, "search-listings-group")]//span[contains(@class, "wt-text-link-no-underline")]').text.strip()
                    item['Results'] = row.split()[0].replace('(', '').replace(',', '')
                except:
                    item['Results'] = ''

            with open(output_filename + '.csv', 'a+', encoding='utf-8', newline='') as of:
                writer = csv.DictWriter(of, fieldnames=['Keyword', 'Results'])
                writer.writerow(item)

    def get_status(request, *args, **kwargs):
        global server_status
        status = {'status': server_status[1:]}
        server_status = ''
        return JsonResponse(status)

    def stop_search(srequest, *args, **kwargs):
        global flag_stop
        flag_stop = True

        return JsonResponse({'status': 'success'})
