import requests
from terminaltables import AsciiTable
import os
from dotenv import load_dotenv
import argparse


def get_city_id(url, user_agent, city_name):
    base_url = f'{url}suggests/areas'
    headers = {'User-Agent': user_agent}
    params = {
        'text': city_name
    }
    response = requests.get(base_url, headers=headers, params=params)
    response.raise_for_status()
    areas = response.json()
    city_id = None
    for area in areas['items']:
        if area['text'] == city_name:
            city_id = area['id']
            break
    return city_id


def get_params(base_url, site_name, language, city):
    if site_name == 'HeadHunter':
        city_id = get_city_id(base_url, "api-test-agent", city_name=city)
        params = {
            "area": city_id,
            "text": language,
            "per_page": 100
        }
    elif site_name == 'SuperJob':
        params = {
            'keyword': language,
            'town': city,
            'count': 100,
        }
    else:
        params = {}
    return params


def get_vac_items(site_name, vacancies):
    if site_name == 'SuperJob':
        return vacancies['objects']
    elif site_name == 'HeadHunter':
        return vacancies['items']


def get_vacancies(url, head, api_key, language, city, site_name):
    params = get_params(url, site_name, language, city)
    headers = {head: api_key}
    base_url = url + 'vacancies/'
    response = requests.get(base_url, headers=headers, params=params)
    response.raise_for_status()
    vacancies = response.json()
    return get_vac_items(site_name, vacancies)


def get_salary_period(vacancy, site_name):
    if site_name == 'HeadHunter':
        salary = vacancy.get("salary")
        if not salary:
            return None
        salary_from = salary.get("from")
        salary_to = salary.get("to")
    elif site_name == 'SuperJob':
        salary_from = vacancy.get('payment_from')
        salary_to = vacancy.get('payment_to')
    else:
        salary_from = None
        salary_to = None
    return salary_from, salary_to


def predict_salary(vacancy, site_name):
    salary_period = get_salary_period(vacancy, site_name)
    if salary_period is not None:
        salary_from, salary_to = salary_period
        if salary_from and salary_to:
            return (salary_from + salary_to) // 2
        elif salary_from:
            return salary_from * 1.2
        elif salary_to:
            return salary_to * 0.8
    else:
        return None


def calculate_average_salary(url, head, api_key, languages, city, site_name):
    average_salaries = {}
    for language in languages:
        vacancies = get_vacancies(url, head, api_key, language, city, site_name)
        if not vacancies:
            continue
        salaries = []
        vacancies_processed = 0
        for vacancy in vacancies:
            salary = predict_salary(vacancy, site_name)
            if salary:
                salaries.append(salary)
                vacancies_processed += 1
        if salaries:
            average_salary = sum(salaries) // len(salaries)
            average_salaries[language] = {
                'vacancies_found': len(vacancies),
                'average_salary': average_salary,
                'vacancies_processed': vacancies_processed
            }
        else:
            average_salaries[language] = {
                'vacancies_found': len(vacancies),
                'average_salary': None,
                'vacancies_processed': vacancies_processed
            }
    return average_salaries


def print_statistics_table(average_salaries, site_name, city):
    headers = ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
    table = [headers]
    for language, salary in average_salaries.items():
        table.append([
            language,
            salary['vacancies_found'],
            salary['vacancies_processed'],
            salary['average_salary']
        ])
    table = AsciiTable(table, title=f'{site_name} {city}')
    print(table.table)


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(description='Город для вакансий')
    parser.add_argument(
        '--city',
        '-d',
        type=str,
        default='Москва',
        help='Город для вакансий'
    )
    args = parser.parse_args()

    city = args.city
    superjob_head = 'X-Api-App-Id'
    hh_head = "User-Agent"
    hh_api_key = "api-test-agent"
    superjob_api_key = os.getenv('SUPERJOB_API_KEY')
    programming_languages = ['Python', 'JavaScript', 'Java', 'C++', 'Ruby']

    superjob_url = 'https://api.superjob.ru/2.0/'
    average_salaries = calculate_average_salary(
        superjob_url,
        superjob_head,
        superjob_api_key,
        programming_languages,
        city,
        site_name='SuperJob'
    )
    print_statistics_table(
        average_salaries,
        site_name='SuperJob',
        city=city
    )

    hh_url = "https://api.hh.ru/"
    average_salaries = calculate_average_salary(
        hh_url,
        hh_head,
        hh_api_key,
        programming_languages,
        city,
        site_name='HeadHunter'
    )
    print_statistics_table(
        average_salaries,
        site_name='HeadHunter',
        city=city
    )
