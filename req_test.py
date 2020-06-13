import requests
import json
import datetime
import constants as c


def masters():
    url = f"https://beauty.dikidi.net/ru/ajax/newrecord/to_master_get_masters/?company_id={c.service}"
    json_get = requests.get(url)
    data = json.loads(json_get.text)
    result = {}
    for master in data["masters"]:
        result[master] = data["masters"][master]["username"]
    return result


def services(master):
    url = f"https://beauty.dikidi.net/mobile/ajax/newrecord/company_services/?lang=ru&company={c.service}&master={master}&share="
    json_get = requests.get(url)
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
    url = f"https://beauty.dikidi.net/en/ajax/newrecord/get_dates_true/?company_id={c.service}" \
          f"&services_id%5B%5D={service}&master_id={master}&date_from={now_date}&date_to={next_date}"
    json_get = requests.get(url)
    data = json.loads(json_get.text)
    result = []
    try:
        for date in data["dates_true"]:
            result.append(date)
    except KeyError:
        result = False
    return result


def get_time(date, service, master):
    url = f"https://beauty.dikidi.net/ru/ajax/newrecord/get_masters/?company_id={c.service}&date={date}&services_id%5B%5D={service}&master_id={master}&is_show_all_times=0"
    json_get = requests.get(url)
    data = json.loads(json_get.text)
    result = []
    for time in data["times"][str(master)]:
        result.append(time)
    return result
