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


def get_sj_params(language, city):
    params = {
            'keyword': language,
            'town': city,
            'count': 100,
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
    params = get_sj_params(language, city)
    headers = {'X-Api-App-Id': api_key}
    base_url = 'https://api.superjob.ru/2.0/vacancies/'
    response = requests.get(base_url, headers=headers, params=params)
    response.raise_for_status()
    vacancies = response.json()
    return vacancies['objects']


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


def predict_hh_salary(vacancy):
    salary_period = get_hh_period(vacancy)
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


def predict_sj_salary(vacancy):
    salary_period = get_sj_period(vacancy)
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


def calculate_hh_average_salary(languages, city):
    average_salaries = {}
    for language in languages:
        vacancies = get_hh_vacancies(language, city)
        if not vacancies:
            continue
        salaries = []
        vacancies_processed = 0
        for vacancy in vacancies:
            salary = predict_hh_salary(vacancy)
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


def calculate_sj_average_salary(api_key, languages, city):
    average_salaries = {}
    for language in languages:
        vacancies = get_sj_vacancies(api_key, language, city)
        if not vacancies:
            continue
        salaries = []
        vacancies_processed = 0
        for vacancy in vacancies:
            salary = predict_sj_salary(vacancy)
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
    superjob_api_key = os.getenv('SUPERJOB_API_KEY')
    programming_languages = ['Python', 'JavaScript', 'Java', 'C++', 'Ruby']

    average_salaries = calculate_sj_average_salary(
        superjob_api_key,
        programming_languages,
        city,
    )
    print_statistics_table(
        average_salaries,
        site_name='SuperJob',
        city=city
    )

    average_salaries = calculate_hh_average_salary(
        programming_languages,
        city,
    )
    print_statistics_table(
        average_salaries,
        site_name='HeadHunter',
        city=city
    )
