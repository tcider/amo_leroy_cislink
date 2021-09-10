"""
Zakaz part of Cislink-MS integration
"""

import json
import sys
import time
from ftplib import FTP
import ms
import csv
import xml.etree.ElementTree as ET


from settings import CL_NUM_DB, URL_FTP, TRY, CL_USER, CL_PASSWD, CL_ZAKAZ_FOLDER, DIR, CL_RESERVE, \
    CL_PRIKAT_NAME, CL_DELIVERY_POINTS_DICT, CL_VI_MS_META, CL_ZAKAZ_DIR


def save_last(last_id):
    if not last_id:
        return
    tmp = {'num': last_id}
    with open(CL_NUM_DB, "w") as f:
        json.dump(tmp, f)


def get_last():
    try:
        with open(CL_NUM_DB) as f:
            try:
                tmp = json.load(f)
            except:
                return []
        return tmp['num']
    except FileNotFoundError:
        return []


def get_price_dict_from_csv(csv_file_name):
    res = dict()
    with open(csv_file_name, "r", encoding="utf-8-sig") as csv_file:
        rows = csv.reader(csv_file, delimiter=';')
        for row in rows:
            res[row[4]] = float(row[26])
    return res


def covert_date(date_tmp):
    if len(date_tmp) == 8:
        delivery_date = date_tmp[6:8] + '.' + date_tmp[4:6] + '.' + date_tmp[0:4]
    else:
        delivery_date = date_tmp
    return delivery_date


def get_products_from_zakaz(file):
    csv_file = DIR + CL_PRIKAT_NAME + ".csv"
    price_dict = get_price_dict_from_csv(csv_file)
    root = ET.parse(file).getroot()

    zakaz_id = root.find("DocumentNumber").text
    delivery_point = root.find("DeliveryPointGLN").text
    if delivery_point in CL_DELIVERY_POINTS_DICT:
        delivery_point = CL_DELIVERY_POINTS_DICT[delivery_point]
    delivery_date = covert_date(root.find("DeliveryDate").text)
    zakaz_date = covert_date(root.find("DocumentDate").text)
    delivery_time = root.find("DeliveryTime").text
    comment = f"Заказ №{zakaz_id} от {zakaz_date}\nДата и время доставки: {delivery_date} {delivery_time}\nТочка доставки: {delivery_point}\n"
    flag = 1
    res = []
    for order in root.findall("DocDetail"):
        elem_dict = {}
        product_code = order.find('ReceiverPrdCode').text
        product_quantity = int(float(order.find('QTY').text))
        product_id = ms.get_id_by_code(product_code)
        if product_code in price_dict:
            product_price = price_dict[product_code]
        else:
            product_price = 0
        if not product_id:
            if flag:
                comment += "В Заказ необходимо добавить следующие позиции(не найдены в МС):\n"
                flag = 0
            product_name = order.find('ProductName').text
            comment += f"Код: {product_code}, Наименование: {product_name}, Кол-во: {product_quantity}"
            if product_price:
                comment += f", Цена: {product_price}"
            comment += "\n"
        else:
            elem_dict['href'] = product_id
            elem_dict['quantity'] = product_quantity
            elem_dict['price'] = product_price
            res.append(elem_dict)
    # print(res)
    # print(comment)
    return res, comment, zakaz_id


def main(): #FIXME Разкомментировать все кроме Print!
    zakaz_files = []
    res_last= get_last()
    error = 0
    i = 0
    while i < TRY:
        try:
            ftp = FTP(URL_FTP)
            ftp.login(user=CL_USER, passwd=CL_PASSWD)
            ftp.cwd(CL_ZAKAZ_FOLDER)
        except:
            error = 1
            i += 1
        else:
            error = 0
            break
    if error:
        print("Error ftp login")
        sys.exit()
    zakaz_files_all = ftp.nlst()
    for elem in zakaz_files_all:
        if elem not in res_last:
            zakaz_files.append(elem)
    if zakaz_files:
        tm = time.strftime('%d.%m.%Y_%H.%M', time.localtime())
        print(tm, "Обработка заказов", zakaz_files)
    for file in zakaz_files:
        i = 0
        error = 0
        while i < TRY:
            try:
                with open(DIR + CL_ZAKAZ_DIR + file, 'wb') as local_file:
                    ftp.retrbinary('RETR ' + file, local_file.write)
            except:
                error = 1
                i += 1
            else:
                error = 0
                break
        if error:
            print("Error ftp uploading zakaz")
            continue
        products, comment, zakaz_id = get_products_from_zakaz(DIR + CL_ZAKAZ_DIR + file)
        if zakaz_id in res_last:
            continue
        # print(products)
        # print(comment)
        products_meta = ms.make_products_meta(products, CL_RESERVE)
        order_id = ms.post_order(CL_VI_MS_META, products_meta, comment, zakaz_id)
        if order_id:
            print(f"Заказ {order_id} по файлу {file} размещен в МС")
            res_last.append(file)
        else:
            print(f"МС ошибка размещения заказа по файлу {file}")

    ftp.quit()
    save_last(res_last)
    sys.exit()

if __name__ == "__main__":
    main()