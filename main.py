import requests
from terminaltables import AsciiTable
import os
from dotenv import load_dotenv


def get_city_id(url, user_agent, city_name):
    base_url = f'{url}suggests/areas'
    headers = {'User-Agent': user_agent}
    params = {
        'text': city_name
    }
    response = requests.get(base_url, headers=headers, params=params)
    response.raise_for_status()
    areas_data = response.json()
    city_id = None
    for area in areas_data['items']:
        if area['text'] == city_name:
            city_id = area['id']
            break
    return city_id


def get_vacancies(url, head, api_key, language, city, site_name):
    base_url = url
    headers = {head: api_key}
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
    base_url += 'vacancies/'
    response = requests.get(base_url, headers=headers, params=params)
    response.raise_for_status()
    vacancies_data = response.json()
    if site_name == 'SuperJob':
        return vacancies_data['objects']
    elif site_name == 'HeadHunter':
        return vacancies_data['items']


def predict_salary(vacancy, site_name):
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
    return average_salaries


def print_statistics_table(average_salaries, site_name, city):
    headers = ["Язык программирования", "Вакансий найдено", "Вакансий обработано", "Средняя зарплата"]
    table_data = [headers]
    for language, data in average_salaries.items():
        table_data.append([
            language,
            data['vacancies_found'],
            data['vacancies_processed'],
            data['average_salary']
        ])
    table = AsciiTable(table_data, title=f'{site_name} {city}')
    print(table.table)


if __name__ == "__main__":
    load_dotenv()
    superjob_head = 'X-Api-App-Id'
    hh_head = "User-Agent"
    hh_api_key = "api-test-agent"
    superjob_api_key = os.getenv('SUPERJOB_API_KEY')
    programming_languages = ['Python', 'JavaScript', 'Java', 'C++', 'Ruby']
    superjob_url = 'https://api.superjob.ru/2.0/'
    hh_url = "https://api.hh.ru/"
    city = 'Москва'
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
