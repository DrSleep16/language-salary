import requests
from terminaltables import AsciiTable
import os
from dotenv import load_dotenv
import argparse


def get_city_id(city_name):
    base_url = 'https://api.hh.ru/suggests/areas'
    headers = {'User-Agent': 'api-test-agent'}
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


def get_hh_params(language, city):
    city_id = get_city_id(city_name=city)
    params = {
        "area": city_id,
        "text": language,
        "per_page": 100
    }
    return params


def get_sj_params(language, city, page):
    params = {
            'keyword': language,
            'town': city,
            'page': page,
        }
    return params


def get_hh_vacancies(language, city):
    params = get_hh_params(language, city)
    headers = {"User-Agent": "api-test-agent"}
    base_url = 'https://api.hh.ru/vacancies/'
    all_vacancies = []
    page = 0

    while True:
        page_params = params.copy()
        page_params['page'] = page
        response = requests.get(base_url, headers=headers, params=page_params)
        response.raise_for_status()

        vacancies = response.json().get('items', [])
        if not vacancies:
            break

        all_vacancies.extend(vacancies)
        total_pages = int(response.headers.get('X-Pagination-Pages', 0))
        if page >= total_pages - 1:
            break

        page += 1
    return all_vacancies


def get_sj_vacancies(api_key, language, city):
    headers = {'X-Api-App-Id': api_key}
    base_url = 'https://api.superjob.ru/2.0/vacancies/'
    all_vacancies = []
    page = 0

    while True:
        params = get_sj_params(language, city, page)
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        vacancy = response.json()

        if not vacancy['objects']:
            break

        all_vacancies.extend(vacancy['objects'])
        page += 1

    return all_vacancies


def get_hh_period(vacancy):
    salary = vacancy.get("salary")
    if not salary:
        return None
    salary_from = salary.get("from")
    salary_to = salary.get("to")
    return salary_from, salary_to


def get_sj_period(vacancy):
    salary_from = vacancy.get('payment_from')
    salary_to = vacancy.get('payment_to')
    return salary_from, salary_to


def calculate_average_salary(salary_period):
    if salary_period is None:
        return None

    salary_from, salary_to = salary_period

    if salary_from and salary_to:
        return (salary_from + salary_to) // 2

    if salary_from:
        return salary_from * 1.2

    if salary_to:
        return salary_to * 0.8


def predict_hh_salary(vacancy):
    salary_period = get_hh_period(vacancy)
    return calculate_average_salary(salary_period)


def predict_sj_salary(vacancy):
    salary_period = get_sj_period(vacancy)
    return calculate_average_salary(salary_period)


def get_salaries_statistic(language, vacancies, salaries):
    salaries_statistic = {language: {
        'vacancies_found': len(vacancies),
        'average_salary': None,
        'vacancies_processed': len(salaries)
    }}
    if salaries:
        salaries_statistic[language]['average_salary'] = sum(salaries) // len(salaries)
    return salaries_statistic[language]


def calculate_hh_salaries_statistic(languages, city):
    salaries_statistic = {}
    for language in languages:
        vacancies = get_hh_vacancies(language, city)
        if not vacancies:
            continue
        salaries = []
        for vacancy in vacancies:
            salary = predict_hh_salary(vacancy)
            if salary:
                salaries.append(salary)
        salaries_statistic[language] = get_salaries_statistic(language, vacancies, salaries)
    return salaries_statistic


def calculate_sj_salaries_statistic(api_key, languages, city):
    salaries_statistic = {}
    for language in languages:
        vacancies = get_sj_vacancies(api_key, language, city)
        if not vacancies:
            continue
        salaries = []
        for vacancy in vacancies:
            salary = predict_sj_salary(vacancy)
            if salary:
                salaries.append(salary)
        salaries_statistic[language] = get_salaries_statistic(language, vacancies, salaries)
    return salaries_statistic


def print_statistics_table(salaries_statistic, site_name, city):
    headers = ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
    table = [headers]
    for language, salary in salaries_statistic.items():
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

    my_city = args.city
    superjob_api_key = os.getenv('SUPERJOB_API_KEY')
    programming_languages = ['Python', 'JavaScript', 'Java', 'C++', 'Ruby']

    sj_salaries_statistic = calculate_sj_salaries_statistic(
        superjob_api_key,
        programming_languages,
        my_city,
    )
    print_statistics_table(
        sj_salaries_statistic,
        site_name='SuperJob',
        city=my_city
    )

    hh_salaries_statistic = calculate_hh_salaries_statistic(
        programming_languages,
        my_city,
    )
    print_statistics_table(
        hh_salaries_statistic,
        site_name='HeadHunter',
        city=my_city
    )
