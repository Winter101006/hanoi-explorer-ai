import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def create_driver(headless=False):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        options=options
    )

    driver.set_page_load_timeout(40)

    return driver


def scroll_page(
    driver,
    max_scrolls=8,
    wait_seconds=1
):
    last_height = driver.execute_script(
        "return document.body.scrollHeight"
    )

    for _ in range(max_scrolls):
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

        time.sleep(wait_seconds)

        new_height = driver.execute_script(
            "return document.body.scrollHeight"
        )

        if new_height == last_height:
            break

        last_height = new_height


def load_page(
    driver,
    url,
    scroll=True
):
    driver.get(url)

    WebDriverWait(
        driver,
        20
    ).until(
        EC.presence_of_element_located(
            (
                By.TAG_NAME,
                "body"
            )
        )
    )

    if scroll:
        scroll_page(driver)

    time.sleep(1)

    return driver.page_source


def close_driver(driver):
    if driver is None:
        return

    try:
        driver.quit()
    except Exception:
        pass