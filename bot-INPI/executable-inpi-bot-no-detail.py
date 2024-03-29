from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains 

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from PIL import Image
from io import BytesIO
import time
import csv
import os
import base64
import concurrent.futures
import random
import selenium
print("versión selenium:", selenium.__version__)

# -------- File parsing CSV functions --------
denomination_file = "-actas-vigentes.csv"
denomination_images = "-images"
initial_data = ["NRO ACTA", 
                "TITULAR", 
                "FECHA INGRESO",
                "CLASE",
                "DENOMINACION",
                "TIPO DE MARCA",
                "NRO RESOLUCION",
                "ESTADO",
                "VENCIMIENTO"]

def routeFile(number):
    name = "class" + str(number) + denomination_file
    return os.path.join(os.getcwd(), "data-simple", name)

def routeFolderImages(number):
    name = "class" + str(number) + denomination_images
    return os.path.join(os.getcwd(), "data-simple", name)

def createFile(number):
    with open(routeFile(number), mode='w', newline='') as archivo_csv:
        escritor_csv = csv.writer(archivo_csv)
        escritor_csv.writerow(initial_data)

def appendLines(number, data):
    with open(routeFile(number), mode='a', newline='') as archivo_csv:
        escritor_csv = csv.writer(archivo_csv)
                
        for line in data:
            escritor_csv.writerow(line)

def storeImage(number, url, act_number):
    route = routeFolderImages(number)
    base64_image = url.split(",")[1]
    image_bytes = base64.b64decode(base64_image)
    image = Image.open(BytesIO(image_bytes))
    if not os.path.exists(route):
        os.makedirs(route)
    image.save(os.path.join(route, act_number + ".jpg"))


# -------- Selenium Bot entry --------
def botClass(classNumber):
    # Functions
    def makeCell(line):
        aLine = []
        for cell in line:
            aLine.append(cell.text)
        aLine.pop()
        return aLine

    def wait_for_element_to_hide(driver, locator, timeout=10):
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((locator))
        )
    
    def CreateChromeDriver(classNumber):
        try:
            options = Options()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-extensions')

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get('https://portaltramites.inpi.gob.ar/marcasconsultas/busqueda/?Cod_Funcion=NQA0ADEA')
            return driver, False
        except Exception as e:
            print("Error while creating driver for class: ", classNumber)
            print(e)
            time.sleep(5)
            return None, True
    
    def MakeSearch(driver, classNumber):
        try:
            collapsables = driver.find_elements(By.CLASS_NAME, "accordion-toggle");
            desiredText = "BUSCADOR"
            for collapsable in collapsables:
                if desiredText in collapsable.text:
                    collapsable.click()
                
            time.sleep(1)
            class_dropdown = Select(driver.find_element(By.ID, "clase"));
            class_dropdown.select_by_value(str(classNumber))

            checkbox = driver.find_element(By.CLASS_NAME, "glyphicon-ok")
            checkbox.click()
            
            search_button = driver.find_element(By.ID, "BtnBuscarAvanzada")
            search_button.click()
            return driver, False
        except Exception as e:
            print("Error while making search for class: ", classNumber)
            print(e)
            time.sleep(5)
            return driver, True

    def GetLine(driver, classNumber):
            try:
                table = driver.find_element(By.ID, "tblGrillaMarcas")
                tbody = table.find_element(By.TAG_NAME, 'tbody')
                tableElements = tbody.find_elements(By.TAG_NAME, "tr")
                line = makeCell(tableElements[n].find_elements(By.TAG_NAME, "td"))
                return driver, line, False
            except Exception as e: 
                print("Error while making search for class: ", classNumber)
                print(e)
                time.sleep(5)
                return driver, [], True
    # First search
    print("Building driver for class ", classNumber)
    hasDriverError = True
    while hasDriverError:
        driver, hasDriverError = CreateChromeDriver(classNumber)

    WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.ID, "BtnBuscarAvanzada"))
    )
    time.sleep(15)

    print("generating search for class ", classNumber)
    hasSearchError = True
    while hasSearchError:
        driver, hasSearchError = MakeSearch(driver, classNumber)

    createFile(classNumber)
    print("Created folder for class", classNumber)
    
    print("Go to table", classNumber)
    wait_for_element_to_hide(driver, (By.CSS_SELECTOR, ".fixed-table-loading"), timeout=300)
    time.sleep(15)

    print("loading first entry for class", classNumber)
    tab_original = driver.current_window_handle
    last_page_number = driver.find_element(By.CLASS_NAME, "page-last").text

    for i in range(1, int(last_page_number)):
        for n in range(0,10):
            time.sleep(random.uniform(1,2))
            line = [".",".",".",".",".",".",".",".","."]
            hasDetailPageError = True
            while hasDetailPageError:
                driver, line ,hasDetailPageError = GetLine(driver, classNumber)
            appendLines(number=classNumber, data=[line])
        print("I finished page: " + str(i) + " for class: ", classNumber)
        WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.CLASS_NAME, "page-next"))
        )
        next = driver.find_element(By.CLASS_NAME, "page-next")
        clickeablePage = next.find_element(By.TAG_NAME, "a")
        clickeablePage.click()
        wait_for_element_to_hide(driver, (By.CSS_SELECTOR, ".fixed-table-loading"), timeout=300)
        time.sleep(1)
        driver.switch_to.window(tab_original)
    driver.close()

def classSearcher(number):
    botClass(str(number))

veces_totales = 45
veces_en_paralelo = 9

with concurrent.futures.ThreadPoolExecutor(max_workers=veces_en_paralelo) as executor:
    for i in range(1, veces_totales + 1, veces_en_paralelo):
        time.sleep(random.uniform(2,20) + i)
        numeros = range(i, min(i + veces_en_paralelo, veces_totales + 1))
        futures = [executor.submit(classSearcher, num) for num in numeros]
        concurrent.futures.wait(futures)
