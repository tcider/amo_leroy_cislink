"""
MoySklad lib
"""

from typing import Dict, Union, List, Tuple, Any
import requests
import time
import json
from settings import TRY, SLEEP_TIME, MS_HEADERS, SKLAD, SKLAD2, MS_FIELD_RECOM_PRICE, MS_FIELD_ZAKUP_PRICE, \
    MS_FIELD_GROUP_VI, MS_FIELD_BRAND, MS_FIELD_GLUBINA, MS_FIELD_SHIRINA, MS_FIELD_VISOTA, MS_FIELD_SROK, \
    CL_OUR_MS_META, CL_STORE, CL_PROJECT


def requests_get(url):
    i = 0
    resp = None
    while i < TRY:
        try:
            resp = requests.get(url, headers=MS_HEADERS)
        except:
            time.sleep(SLEEP_TIME)
            i += 1
        else:
            break
    return resp


def get_all_stock() -> List:
    """
    Поулчение всех всех товаров из МС с лвоарем нужных данных
    """
    limit = 1000
    offset = 0
    size = 1001
    res = []
    while limit + offset < size:
        request_url = f"https://online.moysklad.ru/api/remap/1.2/entity/product?filter=https://online.moysklad.ru/api/remap/1.2/entity/product/metadata/attributes/{MS_FIELD_GROUP_VI}!=&limit={limit}&offset={offset}"
        resp = requests_get(request_url)
        try:
            res_dict = json.loads(str(resp.text))
        except:
            continue
        size = res_dict['meta']['size']
        # print(size)
        for elem in res_dict['rows']:
            # print(elem)
            elem_dict = {}
            if 'name' not in elem:
                continue
            elem_dict['name'] = elem['name']

            # Еденица имзерения
            # elem_dict['ed'] = ''
            # if 'uom' in elem:
            #     uom_href = elem['uom']['meta']['href']
            #     uom_resp = requests_get(uom_href)
            #     try:
            #         elem_dict['ed'] = json.loads(str(uom_resp.text))['name']
            #     except:
            #         pass

            elem_dict['group'] = ''
            elem_dict['brand'] = ''
            elem_dict['glubina'] = ''
            elem_dict['shirina'] = ''
            elem_dict['visota'] = ''
            elem_dict['srok'] = ''
            if 'attributes' in elem:
                for atr in elem['attributes']:
                    if atr['id'] == MS_FIELD_GROUP_VI:
                        elem_dict['group'] = atr['value']
                    if atr['id'] == MS_FIELD_BRAND:
                        elem_dict['brand'] = atr['value']
                    if atr['id'] == MS_FIELD_GLUBINA:
                        elem_dict['glubina'] = round(atr['value'], 2)
                    if atr['id'] == MS_FIELD_SHIRINA:
                        elem_dict['shirina'] = round(atr['value'], 2)
                    if atr['id'] == MS_FIELD_VISOTA:
                        elem_dict['visota'] = round(atr['value'], 2)
                    if atr['id'] == MS_FIELD_SROK:
                        elem_dict['srok'] = atr['value']

            # Вес и Обьем
            elem_dict['weight'] = 0
            elem_dict['volume'] = 0
            if 'weight' in elem:
                elem_dict['weight'] = round(elem['weight'], 2)
            if 'volume' in elem:
                elem_dict['volume'] = elem['volume']

            # Страна
            elem_dict['country'] = ''
            if 'country' in elem:
                country_href = elem['country']['meta']['href']
                country_resp = requests_get(country_href)
                try:
                    elem_dict['country'] = json.loads(str(country_resp.text))['name']
                except:
                    pass

            # Price
            elem_dict['rec_price'] = 0
            elem_dict['zak_price'] = 0
            for el in elem['salePrices']:
                if el['priceType']['id'] == MS_FIELD_RECOM_PRICE:
                    elem_dict['rec_price'] = el['value'] / 100
                if el['priceType']['id'] == MS_FIELD_ZAKUP_PRICE:
                    elem_dict['zak_price'] = el['value'] / 100

            # Получаю остаток
            product = elem['meta']['href']
            url2 = f"https://online.moysklad.ru/api/remap/1.2/report/stock/bystore?filter=product={product}"
            resp2 = requests_get(url2)
            res_dict2 = json.loads(str(resp2.text))
            stock = 0
            if res_dict2['rows']:
                for el in res_dict2['rows'][0]['stockByStore']:
                    if el['name'] == SKLAD:
                        stock += int(el['stock']) - int(el['reserve'])
                    elif el['name'] == SKLAD2:
                        stock += int(el['stock']) - int(el['reserve'])
            elem_dict['stock'] = stock

            # Код поставщика
            elem_dict['code'] = ''
            if 'code' in elem:
                elem_dict['code'] = elem['code']

            # Barcode
            elem_dict['barcode'] = ''
            if 'barcodes' in elem:
                for el in elem['barcodes']:
                    if 'ean13' in el:
                        try:
                            elem_dict['barcode'] = int(el['ean13'])
                        except:
                            elem_dict['barcode'] = el['ean13']

            # print(elem_dict)
            res.append(elem_dict)

        offset += 1000
    return res


def get_id_by_code(code: Any) -> str:
    request_url = f"https://online.moysklad.ru/api/remap/1.2/entity/assortment?filter=code={code}"
    resp = requests_get(request_url)
    if resp.ok:
        try:
            res_dict = json.loads(str(resp.text))['rows'][0]
        except:
            print("Товар не найден в МС")
            return None
        # print(res_dict)
        return res_dict['id']
    print("Ошибка запроса в МС")
    return None


def modify_product(ms_id: str, res: List):
    url = f"https://online.moysklad.ru/api/remap/1.2/entity/product/{ms_id}"
    data = {
        "attributes": [{
            "meta": {
                "href": f"https://online.moysklad.ru/api/remap/1.2/entity/product/metadata/attributes/{MS_FIELD_GROUP_VI}",
                "type": "attributemetadata",
                "mediaType": "application/json"
            },
            "id": MS_FIELD_GROUP_VI,
            "value": res[8]
            },
            {
                "meta": {
                    "href": f"https://online.moysklad.ru/api/remap/1.2/entity/product/metadata/attributes/{MS_FIELD_BRAND}",
                    "type": "attributemetadata",
                    "mediaType": "application/json"
                },
                "id": MS_FIELD_BRAND,
                "value": res[9]
            },
            {
                "meta": {
                    "href": f"https://online.moysklad.ru/api/remap/1.2/entity/product/metadata/attributes/{MS_FIELD_GLUBINA}",
                    "type": "attributemetadata",
                    "mediaType": "application/json"
                },
                "id": MS_FIELD_GLUBINA,
                "value": float(res[13])
            },
            {
                "meta": {
                    "href": f"https://online.moysklad.ru/api/remap/1.2/entity/product/metadata/attributes/{MS_FIELD_SHIRINA}",
                    "type": "attributemetadata",
                    "mediaType": "application/json"
                },
                "id": MS_FIELD_SHIRINA,
                "value": float(res[15])
            },
            {
                "meta": {
                    "href": f"https://online.moysklad.ru/api/remap/1.2/entity/product/metadata/attributes/{MS_FIELD_VISOTA}",
                    "type": "attributemetadata",
                    "mediaType": "application/json"
                },
                "id": MS_FIELD_VISOTA,
                "value": float(res[17])
            }
        ]
    }
    resp = requests.put(url, headers=MS_HEADERS, json=data)
    if resp.ok:
        print("MS ok modify product")
        return True
    print("MS NO modify product", resp.text)
    return False


def make_products_meta(products: List[Dict], reserve):
    """
    "positions": [{
                "quantity": 10,
                "price": 100,
                "discount": 0,
                "vat": 0,
                "assortment": {
                  "meta": {
                    "href": "https://online.moysklad.ru/api/remap/1.2/entity/product/8b382799-f7d2-11e5-8a84-bae5000003a5",
                    "type": "product",
                    "mediaType": "application/json"
                  }
                },
                "reserve": 10
              }]
    """
    for i in range(len(products)):
        mshref = "https://online.moysklad.ru/api/remap/1.2/entity/product/" + products[i]['href']
        price = products[i]['price'] * 100
        quantity = products[i]['quantity']
        if reserve:
            reserve_num = quantity
        else:
            reserve_num = 0
        products[i] = {
                "quantity": quantity,
                "price": price,
                "discount": 0,
                "vat": 0,
                "assortment": {
                  "meta": {
                    "href": mshref,
                    "type": "product",
                    "mediaType": "application/json"
                  }
                },
                "reserve": reserve_num
        }
    return products


def post_order(contragent_meta, products_meta, comment, name) -> (str, str):
    url = "https://online.moysklad.ru/api/remap/1.2/entity/customerorder"

    data = {
        "name": name,
        "description": comment,
        "positions": products_meta,
        "organization": {"meta": CL_OUR_MS_META},
        "agent": {"meta": contragent_meta},
        "store": CL_STORE,
        "project": CL_PROJECT
    }

    resp = requests.post(url, headers=MS_HEADERS, json=data)
    res_dict = json.loads(resp.text)
    if resp.ok:
        print("MS ok add lead", res_dict['name'])
        return res_dict['name']
    print("MS NO add lead", res_dict)
    return None