import time
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import csv


def get_system_prefix():
    if platform.system() == 'Linux':
        return 'linux'
    elif platform.system() == 'Darwin':
        return 'mac'
    return 'exe'


# Функция fill_csv была вынесена в начало, тк запись в файлы теперь происходит в функции scrape
def fill_csv(category, location, products):
    with open(f"{category}_{location}.csv", mode="w", encoding='utf-8') as w_file:
        file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
        file_writer.writerow(["id", "title", "price", "promo_price", "url"])
        for key, value in products.items():
            file_writer.writerow([key, value['title'], value['price'], value['promo_price'], value['url']])


def scrape(category, city):
    options = webdriver.ChromeOptions()
    options.add_argument('user-agent=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.headless = True
    options.add_argument('window-size=1920,1080')
    prefix = get_system_prefix()
    service = Service(f'./chromedriver.{prefix}')
    driver = webdriver.Chrome(
        service=service,
        options=options
    )

    products = {}
    try:
        driver.get(f"https://www.detmir.ru/catalog/index/name/{category}/")
        driver.implicitly_wait(5)
        # город выбирается нажатием на кнопку выбора региона, что надёжнее:
        # окно с вариантом подтвердить город или выбрать другой появляется не всегда
        print(f'Выбираем город {city}')
        region_button = driver.find_element(By.XPATH, "//*[@id='app-container']/div[2]/header/div/div[2]/div/div/div[1]/ul/li[2]/div/div/div[1]/div/span")
        driver.execute_script("arguments[0].click();", region_button)
        time.sleep(5)
        # выбор города теперь не по индексу (что ненадёжно), а перебором элементов с названием - те которые не нажимаются не кнопки, а нажатие
        # кнопки с городом влечёт закрытие модального окна, организована проверка видно ли оно пользователю - если нет, двигаемся дальше,город выбран
        city_buttons = driver.find_elements(By.XPATH, f"//span[contains(text(), '{city}')]")

        print('Нажимаем на кнопку и проверяем наличие модального окна')
        try:
            for elem in city_buttons:
                driver.execute_script("arguments[0].click();", elem)
                modal_close_button = driver.find_element(By.XPATH, "//*[@id='tw']/div[1]/div/div/div[2]/div/button")  # кнопка "закрыть модальное окно"
                if not modal_close_button.is_displayed():  # если кнопка не видна пользователю
                    break
        except (StaleElementReferenceException, NoSuchElementException):
            pass

        time.sleep(5)

        print('Пролистываем до конца...')
        while True:
            try:
                scroll_button = driver.find_element(By.XPATH, f"//div[contains(text(), 'Показать ещё')]")
                driver.execute_script("arguments[0].click();", scroll_button)
                driver.implicitly_wait(5)
            except (NoSuchElementException, StaleElementReferenceException):
                break

        print('Формируем словарь из продуктов')
        products_list = driver.find_elements(By.XPATH, '//a[contains(@href, "https://www.detmir.ru/product/index/id")]')

        for product in products_list:
            # добавлен try/except, а также блок else с continue, если возникнет проблема с элементом - программа не падает, переходит к следующему
            try:
                url = product.get_attribute('href')
                id = url.split('/')[-2]
                if id not in products:
                    stats = {}
                    driver.implicitly_wait(1)
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
                        print(f"Непредвиденное количество элементов {len(p_tags)} for id {id}:")
                        continue

                    stats['url'] = url
                    stats['city'] = city
                    products[id] = stats
                    print(f"  ...продукт {id} - {stats['title']} добавлен")
            except (NoSuchElementException, TimeoutException): #перехватываем ошибки, которые иногда происходили при запусках скрипта
                pass

    except (ConnectionError, ConnectionRefusedError) as ex:
        print(f'Не удалось подключиться: {ex}')
    except TimeoutException as ex:
        print(f'Команда не была выполнена вовремя: {ex}')
    except NoSuchElementException as ex:
        print(f'Элемент не был найден: {ex}')
    except Exception as ex:
        print(f'Исключение: {ex}')
    finally:
        driver.close()
        driver.quit()
        print(f'Получено {len(products)} продуктов из категории {category} в регионе {city}')
        print('Записываем в файл')
        #даже в случае исключения записываем данные, которые удалось собрать
        fill_csv(category, city, products)


if __name__ == '__main__':
    try:
        category = 'lego'

        msc_location = 'Москва и Московская область'
        spb_location = 'Санкт-Петербург и Ленинградская область'

        scrape(category, msc_location)
        scrape(category, spb_location)

        print('Done!')
    except Exception as ex:
        print(f'Неперехваченное исключение: {ex}')
