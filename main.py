import sys
from selenium.webdriver.support.wait import WebDriverWait
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import csv


def scrape(category, city):
    options = webdriver.ChromeOptions()
    options.add_argument('user-agent=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0')
    options.add_argument('--disable-blink-features=AutomationControlled')
    # options.headless = True
    options.add_argument('window-size=1920,1080')
    service = Service("./chromedriver")
    driver = webdriver.Chrome(
        service=service,
        options=options
    )
    try:
        driver.get("https://www.detmir.ru")
        driver.implicitly_wait(3)

        print(f'Выбираем город {city}')
        list_button = driver.find_element(By.XPATH, "//span[contains(text(), 'другой')]")
        wait = WebDriverWait(driver, 5)
        wait.until(EC.element_to_be_clickable(list_button)).click()
        city_button = driver.find_element(By.XPATH, f"//span[contains(text(), '{city}')]")
        driver.execute_script("arguments[0].click();", city_button)

        print('Выбираем категорию игрушки')
        shop_category_button = driver.find_element(By.XPATH,
                                                   '//a[(@href="https://www.detmir.ru/catalog/index/name/igry_i_igrushki/")]')
        driver.execute_script("arguments[0].click();", shop_category_button)

        print(f'Выбираем категорию {category}')
        lego_button = driver.find_element(By.XPATH,
                                          f'//a[(@href="https://www.detmir.ru/catalog/index/name/{category}/")]')
        driver.execute_script("arguments[0].click();", lego_button)

        driver.implicitly_wait(3)

        print(f'Пролистываем до конца...')
        while True:
            try:
                scroll_button = driver.find_element(By.XPATH, f"//div[contains(text(), 'Показать ещё')]")
                driver.execute_script("arguments[0].click();", scroll_button)
                driver.implicitly_wait(5)
            except (NoSuchElementException, StaleElementReferenceException):
                break

        print(f'Формируем словарь из продуктов')
        products = {}
        products_list = driver.find_elements(By.XPATH, '//a[contains(@href, "https://www.detmir.ru/product/index/id")]')
        for product in products_list:
            url = product.get_attribute('href')
            id = url.split('/')[-2]
            if id not in products:
                stats = {}
                p_tags = product.find_elements(By.TAG_NAME, 'p')
                if len(p_tags) == 3:
                    stats['title'] = p_tags[0].text
                    stats['price'] = p_tags[2].text
                    stats['promo_price'] = p_tags[1].text
                elif len(p_tags) == 2:
                    stats['title'] = p_tags[0].text
                    stats['price'] = p_tags[1].text
                    stats['promo_price'] = ''
                elif len(p_tags) == 1:
                    stats['title'] = p_tags[0].text
                    stats['price'] = 'Нет в наличии'
                    stats['promo_price'] = ''
                else:
                    raise Exception(f"Unexpected number of stats {len(p_tags)} for id {id}")

                stats['url'] = url
                stats['city'] = city
                products[id] = stats
                print(f'  ...продукт {id} добавлен')
        print(f'Получено {len(products)} продуктов из категории {category} в регионе {city}')
        return products

    except TimeoutException as ex:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f'{exc_tb.tb_lineno}: TimeoutException = {ex}')
    except NoSuchElementException as ex:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f'{exc_tb.tb_lineno}: NoSuchElementException = {ex}')
    except Exception as ex:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f'{exc_tb.tb_lineno}:{exc_type}: Exception = {ex}')
    finally:
        driver.close()
        driver.quit()


def fill_cbv(category, location, products):
    with open(f"{category}_{location}.csv", mode="w", encoding='utf-8') as w_file:
        file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
        file_writer.writerow(["id", "title", "price", "promo_price", "url"])
        for key, value in products.items():
            file_writer.writerow([key, value['title'], value['price'], value['promo_price'], value['url']])


if __name__ == '__main__':
    category = 'lego'
    spb_location = 'Санкт-Петербург и Ленинградская область'
    msc_location = 'Москва и Московская область'

    products_spb = scrape(category, spb_location)
    products_msc = scrape(category, msc_location)

    print('Сохраняем в файлы')
    fill_cbv(category, spb_location, products_spb)
    fill_cbv(category, msc_location, products_msc)

    print('Done!')
