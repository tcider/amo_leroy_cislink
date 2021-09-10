from typing import Dict, List, Tuple
import requests
#pip install requests
import time
import json
from settings import TRY, SLEEP_TIME, LEROY_URL, LEROY_TOKEN_FILE, \
    LEROY_API_KEY, LEROY_DAY_EXP, LEROY_PASW, LEROY_LOGIN, MS_HEADERS, SKLAD, SKLAD2


def requests_get(url, headers=None):
    """
    Вспомогательная безопасная обертка над request
    """
    i = 0
    while i < TRY:
        try:
            resp = requests.get(url, headers=headers)
        except:
            time.sleep(SLEEP_TIME)
            i += 1
        else:
            return resp
    print("Get request Error")
    return None


def leroy_init_token() -> Dict:
    """
    Получение в тч обновление токена(срок 60дней)
    """
    header = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "apikey": LEROY_API_KEY
    }
    response = requests.get(LEROY_URL + "/user/authbypassword" + f"?login={LEROY_LOGIN}&password={LEROY_PASW}", headers=header)
    if response.ok:
        try:
            res_dict = json.loads(str(response.text))
        except:
            pass
        else:
            res_dict['expires_in'] += time.time()
            with open(LEROY_TOKEN_FILE, "w") as f:
                json.dump(res_dict, f)
            print("Получен новый токен Леруа")
            return res_dict
    print("Ошибка получения нового токена Леруа")
    return {}


def leroy_get_header() -> Dict:
    """
    Вспом метод для всех запросов, готовит заголовок для запроса, вставляя туда токен, обновляя его при необходимости
    """
    try:
        with open(LEROY_TOKEN_FILE, 'r') as f:
            token_dict = json.load(f)
    except:
        token_dict = leroy_init_token()
    if token_dict['expires_in'] - time.time() <= LEROY_DAY_EXP * 24 * 60 * 60:
        token_dict = leroy_init_token()
    if not len(token_dict):
        return {}

    header = {
        "Content-Type": "application/json",
        "apikey": LEROY_API_KEY,
        "Authorization": f"Bearer {token_dict['access_token']}"
    }
    return header


def leroy_get_assortment() -> Dict[str, Tuple]:
    """
    Возвращает словарь с ключами code: str по моему складу и значениями tuple(marketplaceId: int, price: float, stock: int)
    """
    res = {}
    header = leroy_get_header()
    response = requests.get(LEROY_URL + f"/api/v1/products/assortment?login={LEROY_LOGIN}&password={LEROY_PASW}", headers=header)
    if not response.ok:
        return res
    try:
        res_dict = json.loads(str(response.text))
    except:
        return res
    for elem in res_dict['result']['products']:
        if not elem['removedFromSale']:
            res[elem['productId']] = (elem['marketplaceId'], elem['price'], elem['stock'])
    return res


def leroy_change_price(marketplaceId: int, price: float) -> None:
    """
    Меняет цену на товар
    """
    header = leroy_get_header()
    data = {
        "data": {
            "products": [
                {
                    "marketplaceId": marketplaceId,
                    "price": price
                }
            ]
        }
    }
    response = requests.post(LEROY_URL + f"/api/v1/products/price?login={LEROY_LOGIN}&password={LEROY_PASW}", headers=header, json=data)
    if response.ok:
        return True
    return False


def leroy_change_stock(marketplaceId: int, stock: int) -> None:
    """
    Меняет остаток товара в Леруа
    """
    header = leroy_get_header()
    data = {
        "data": {
            "products": [
                {
                    "marketplaceId": marketplaceId,
                    "stock": stock
                }
            ]
        }
    }
    response = requests.post(LEROY_URL + f"/api/v1/products/stock?login={LEROY_LOGIN}&password={LEROY_PASW}", headers=header, json=data)
    if response.ok:
        return True
    return False


def ms_get_stock(code: str) -> (float, int):
    """
    Поулчение остатка И цены по товарам МойСклад под полю Код
    """
    request_url = f"https://online.moysklad.ru/api/remap/1.2/entity/assortment?filter=code={code}"
    resp = requests_get(request_url, headers=MS_HEADERS)
    if resp:
        try:
            res_dict = json.loads(str(resp.text))
        except:
            return (None)
        try:
            price = round(res_dict['rows'][0]['salePrices'][0]['value'] / 100, 2)
        except:
            price = None
        try:
            stock = int(res_dict['rows'][0]['quantity'])
            if stock < 0:
                stock = 0
        except:
            stock = None
        if not price and not stock:
            return None
        return (price, stock)
    return (None)


def ms_get_stock_bystore(code: str) -> (float, int):
    """
    Поулчение остатка И цены по товарам МойСклад под полю Код по конкретному слкаду!
    """
    request_url = f"https://online.moysklad.ru/api/remap/1.2/entity/assortment?filter=code={code}"
    resp = requests_get(request_url, headers=MS_HEADERS)
    product = None
    stock = None
    if resp:
        try:
            res_dict = json.loads(str(resp.text))
            product = res_dict['rows'][0]['meta']['href']
        except:
            return None
        try:
            price = round(res_dict['rows'][0]['salePrices'][0]['value'] / 100, 2)
        except:
            price = None
    else:
        return None

    request_url = f"https://online.moysklad.ru/api/remap/1.2/report/stock/bystore?filter=product={product}"
    resp = requests_get(request_url, headers=MS_HEADERS)
    if resp:
        try:
            res_dict = json.loads(str(resp.text))
            stock_list = res_dict['rows'][0]['stockByStore']
        except:
            stock = None
        else:
            stock = 0
            for elem in stock_list:
                if elem['name'] == SKLAD:
                    stock += int(elem['stock']) - int(elem['reserve'])
                elif elem['name'] == SKLAD2:
                    stock += int(elem['stock']) - int(elem['reserve'])
    if not price and not stock:
        return None
    return (price, stock)


def main():

    ########### Запуск ###########
    leroy_assortment = leroy_get_assortment()
    #print(leroy_assortment)
    for key in leroy_assortment:
        #print(key)
        #data = ms_get_stock(str(key).strip()) # По всем складам
        data = ms_get_stock_bystore(str(key).strip())

        # Проверка если в коде в начале стояли 0 и в экселе они пропали
        if not data and len(str(key).strip()) < 6:
            new_key = str(key).strip()[:]
            while len(new_key) < 6:
                new_key = "0" + new_key
            data = ms_get_stock_bystore(new_key)

        if data:
            if data[0] is not None and int(data[0]) != int(leroy_assortment[key][1]):
                leroy_change_price(leroy_assortment[key][0], data[0])
                print("Price for %s changed from %s to %s" % (key, leroy_assortment[key][1], data[0]))
            if data[1] is not None and data[1] != int(leroy_assortment[key][2]):
                leroy_change_stock(leroy_assortment[key][0], data[1])
                print("Stock for %s changed from %s to %s" % (key, leroy_assortment[key][2], data[1]))
        else:
            print("%s don't found in MS" % key)

    ###############################
    sys.exit()


if __name__ == "__main__":
    main()
