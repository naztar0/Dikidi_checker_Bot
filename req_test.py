import requests
import json
import datetime


def masters():
    url = "https://beauty.dikidi.net/ru/ajax/newrecord/to_master_get_masters/?company_id=14998"
    json_get = requests.get(url)
    data = json.loads(json_get.text)
    result = {}
    for master in data["masters"]:
        result[master] = data["masters"][master]["username"]
    return result


def services(master):
    url = "https://beauty.dikidi.net/mobile/ajax/newrecord/company_services/?lang=ru&company=14998&master={master}&share="
    json_get = requests.get(url.format(master=master))
    data = json.loads(json_get.text)
    result = {}
    list_num = None
    for service_id in data["data"]["list"]:
        list_num = service_id
    for service_id in data["data"]["list"][list_num]["services"]:
        result[service_id["id"]] = service_id["name"]
    return result


def get_date(service, master):
    now_date = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
    next_date = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=70), "%Y-%m-%d")
    url = "https://beauty.dikidi.net/en/ajax/newrecord/get_dates_true/?company_id=14998&services_id%5B%5D={service_id}&master_id={master}&date_from={f}&date_to={n}"
    json_get = requests.get(url.format(service_id=service, master=master, f=now_date, n=next_date))
    data = json.loads(json_get.text)
    result = []
    try:
        for date in data["dates_true"]:
            result.append(date)
    except KeyError:
        result = False
    return result


def get_time(date, service, master):
    url = "https://beauty.dikidi.net/ru/ajax/newrecord/get_masters/?company_id=14998&date={date}&services_id%5B%5D={service_id}&master_id={master}&is_show_all_times=0"
    json_get = requests.get(url.format(date=date, service_id=service, master=master))
    data = json.loads(json_get.text)
    result = []
    for time in data["times"][str(master)]:
        result.append(time)
    return result
