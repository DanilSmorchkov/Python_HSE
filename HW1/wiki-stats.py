import argparse
import random
import re
from time import sleep
from bs4 import BeautifulSoup
import requests
from tqdm.auto import tqdm


def compute_pause(pause: str) -> float:
    """
    Calculation of the pause duration taking into account the strategy chosen
    by the user.
    :param pause: pause calculation strategy and numerical characteristics.
    :return: duration of the pause.
    """
    if 'gauss' in pause:  # Обработка нормального распределения
        params_gauss = re.split('[:/]', pause)
        mean, sigma = params_gauss[1:]
        sigma = float(sigma)
        mean_sec = to_sec(mean)
        if sigma < 0:
            raise argparse.ArgumentTypeError('Sigma should be a positive')
        return abs(random.gauss(mean_sec, sigma))
    elif '-' in pause:  # Обработка равномерного распределения
        if '-' == pause[0] or '' in pause.split('-'):
            raise argparse.ArgumentTypeError('Time should be a positive value')
        left, right = pause.split('-')
        left_sec = to_sec(left)
        right_sec = to_sec(right)
        if left_sec > right_sec:
            raise argparse.ArgumentTypeError('The left border must be less '
                                             'than or equal to the right')
        return random.uniform(left_sec, right_sec)
    else:  # Обработка дискретной паузы
        return to_sec(pause)


def to_sec(time: str) -> float:
    """
    Auxiliary function for converting time to seconds
    :param time: The string with the specified units of measurement
    :return: Time converted to seconds
    """

    if 'ms' in time:
        if (ml_sec := float(time[:-2])) <= 0:
            raise argparse.ArgumentTypeError('Time should be a positive value')
        return ml_sec / 1000
    elif 's' in time:
        if (sec := float(time[:-1])) <= 0:
            raise argparse.ArgumentTypeError('Time should be a positive value')
        return sec
    else:
        if (ml_sec := float(time)) <= 0:
            raise argparse.ArgumentTypeError('Time should be a positive value')
        return ml_sec / 1000


def go_to_wiki(page: str, lang: str, links_file: str, nearest_file: str,
               pause: str) -> None:
    """
    On request, it finds a wiki page, checks the correctness of the request
    and accesses functions get_external_links, information_pages_test,
    get_category_neighbours if necessary
    :param pause: Time of the pause
    :param page: request
    :param lang: National Wiki Section
    :param links_file: file for external links
    :param nearest_file: file for category neighbors

    :return: None
    """
    url = f'http://{lang}.wikipedia.org/wiki/{page}'
    try:
        resp = requests.get(url)
        # Ошибка, если неправильный национальный раздел вики
        # или в случае, если нет интернета, но здесь ничего не поделать
    except requests.exceptions.ConnectionError:
        print('Wrong national wiki section!')
    else:
        if resp.status_code == requests.codes['ok']:
            print(f'Successful request {url}')
            desambig = information_pages_test(resp, page, lang)
            if desambig:
                get_external_links(resp, lang, links_file)
                get_category_neighbours(resp, lang, nearest_file, pause)
        elif resp.status_code == requests.codes['not_found']:
            print(f'The page on the link {url} was not found.'
                  f' Error {resp.status_code}.')
        else:
            print(f'Mistake {resp.status_code} ({resp.reason}).'
                  f' Request rejected')


def information_pages_test(response: requests.Response, page: str, lang: str) \
        -> bool:
    """
    Checks  the page is ambiguous. If yes, it displays all links on the screen
    Checks the page is disambiguation page
    :param response:
    :param page: request
    :param lang: National Wiki Section
    :return: True if disambiguous else False
    """
    flag_page_is_disambig = True
    # Словарь для хранения названий категории, характерной
    # для всех "плохих" страниц
    dict_names_page = {'en': 'Disambiguation pages', 'ru': 'Страницы значений',
                       'fr': 'Homonymie', 'pt': 'Desambiguação',
                       'de': 'Begriffsklärung', 'es': 'Desambiguación',
                       'it': 'Pagine di disambiguazione', 'zh': '消歧义'}
    soup = BeautifulSoup(response.text, 'html.parser')
    category_a_tags = (soup.find('div', id='mw-normal-catlinks').
                       find('ul').find_all('a'))
    for a_tag in category_a_tags:
        if dict_names_page[lang] in a_tag.text:
            print('This page is ambiguous. All links to unambiguous '
                  'wiki pages will be displayed below.')
            flag_page_is_disambig = False
            break
    if not flag_page_is_disambig:
        new_links: [str] = []
        for paragraph in tqdm(soup.find_all(
                'div', class_='mw-parser-output'),
                position=0, colour='red'):
            for value in tqdm(paragraph.find_all('li'),
                              leave=False, position=1, colour='red'):
                for tag_a in value.find_all('a'):
                    # Сразу откидываем не вики-страницы
                    if '/wiki/' == tag_a.get('href')[:6]:
                        link = (f'http://{lang}.wikipedia.org'
                                f'{tag_a.get("href")}')
                        request = requests.get(link)
                        soup_new_link = BeautifulSoup(request.text,
                                                      'html.parser')
                        new_link_have_categories = soup_new_link.find(
                            'div', id='mw-normal-catlinks') \
                            # Если страница вики и у нее нет категорий,
                        # то это странная страница, нам такая не нужна
                        if not new_link_have_categories:
                            continue
                        flag_ambig = False
                        for a_tag in new_link_have_categories.find(
                                'ul').find_all('a'):
                            # Проверим, что ссылки на
                            # не "неоднозначные" страницы
                            if dict_names_page[lang] in a_tag.text:
                                flag_ambig = True
                                continue
                        if flag_ambig:
                            continue
                        if link not in new_links:
                            new_links.append(link)
    if not flag_page_is_disambig:
        print(*new_links, sep='\n')
    return flag_page_is_disambig


def get_external_links(response: requests.Response, lang: str,
                       links_file: str) -> None:
    """
    The function writes external links in links_file
    :param response: response to a request from the wiki
    :param lang: National Wiki Section
    :param links_file: the name of the file to write
    :return: None
    """
    external_links_diff_lang: dict[str: str] = {'en': 'External_links',
                                                'ru': 'Ссылки',
                                                'de': 'Weblinks',
                                                'es': 'Enlaces_externos',
                                                'it': 'Collegamenti_esterni',
                                                'fr': 'Liens_externes',
                                                'pt': 'Ligações_externas',
                                                'nl': 'Externe_links',
                                                'hi': 'सन्दर्भ',
                                                'zh': '外部連接'}
    # Опять же создаем словарь, в котором храним названия шапки модуля,
    # где хранятся внешние ссылки на разных языках
    external_links: list[str] = []
    soup = BeautifulSoup(response.text, 'html.parser')
    external_tag = soup.find(id=external_links_diff_lang[lang])
    if external_tag:
        external_header = external_tag.parent
        uls_for_links = external_header.find_next_siblings('ul')
        for ul in uls_for_links:
            for a_tags in ul.find_all('a', class_='external text'):
                external_links.append(a_tags.get('href'))
        with open(links_file, mode='w') as f:
            print(*external_links, sep='\n', file=f)
    else:
        open(links_file, mode='w').close()


def get_category_neighbours(response: requests.Response, lang: str,
                            nearest_file: str, pause: str) -> None:
    """
    The function searches for all neighbors by category and writes their name,
    the number of intersected categories and the names of these categories to
    a file
    :param pause: Pause time between requests
    :param response: response to a request from the wiki
    :param lang: National Wiki Section
    :param nearest_file: the name of the file to write
    :return: None
    """
    soup = BeautifulSoup(response.text, 'html.parser')
    list_category_names: [str] = []
    list_category_links: [str] = []
    list_for_write_in_file: [tuple[str, int, [...]]] = []
    category_tags_a = soup.find('div', class_='mw-normal-catlinks').find(
        'ul').find_all('a')
    # Собираем все ссылки из раздела с категориями
    for tag_a in category_tags_a:
        list_category_names.append(tag_a.text)
        list_category_links.append(
            f'http://{lang}.wikipedia.org{tag_a.get("href")}')
    for num_category_link, category_link in enumerate(
            tqdm(list_category_links, position=0, colour='red')):
        category_response = requests.get(
            category_link)  # Ходим по всем категориям страницы
        flag_for_next_page = True
        # Если в категории много страниц, ходим по каждой из них
        # (обновление флага внизу)
        while flag_for_next_page:
            category_soup = BeautifulSoup(category_response.text,
                                          'html.parser')
            category_header_all = category_soup.find_all('h2')
            for header2 in category_header_all:
                if list_category_names[num_category_link] in header2.text:
                    header_category = header2
                    break
            category_dir_tag = (header_category.find_next_sibling(
                'div', class_='mw-content-ltr').
                                find('div', class_='mw-category '
                                                   'mw-category-columns'))
            for tag_a in tqdm(category_dir_tag.find_all('a'), leave=False,
                              position=1, colour='red'):
                sleep(pause)  # Ходим по всем ссылкам в определенной категории
                link_in_category = (f'http://{lang}.wikipedia.org'
                                    f'{tag_a.get("href")}')
                resp_link = requests.get(link_in_category)
                soup_for_neighbour = BeautifulSoup(resp_link.text,
                                                   'html.parser')
                neighbour_category_names: set[str] = set()
                neighbour_a_tags_in_category = (
                    soup_for_neighbour.find('div',
                                            class_='mw-normal-catlinks').find(
                        'ul').find_all('a'))
                for a_tag in neighbour_a_tags_in_category:
                    neighbour_category_names.add(a_tag.text)
                intersec_neighbours_and_base = set(
                    list_category_names).intersection(neighbour_category_names)
                list_for_write_in_file.append(
                    (tag_a.text, len(intersec_neighbours_and_base),
                     [*intersec_neighbours_and_base]))
            next_page_tags_a = (category_dir_tag.
                                find_parent().find_next_siblings('a'))
            # Смотрим, есть ли ссылка на следующую страницу с категориями
            if next_page_tags_a:
                for tags_a in next_page_tags_a:
                    link = tags_a.get('href')
                    if 'pagefrom' in link:
                        flag_for_next_page = True
                        category_response = requests.get(
                            f'http://{lang}.wikipedia.org{link}')
                    else:
                        flag_for_next_page = False
            else:
                flag_for_next_page = False
    unique_value: list[tuple[str, int, ...]] = []
    for x in list_for_write_in_file:  # Убираем повторы
        if x not in unique_value:
            unique_value.append(x)
    unique_value.sort(key=lambda key: key[0])
    unique_value.sort(key=lambda key: key[1], reverse=True)
    with open(nearest_file, mode='w') as f:
        print(*unique_value, file=f, sep='\n')


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='wiki-stats',
        description='A program that makes automatic queries in Wikipedia and '
                    'records external links and relationships with neighbors '
                    'by category in files upon successful connection')
    parser.add_argument('page', type=str,
                        help='The query of interest in the wiki')
    parser.add_argument('--pause', type=compute_pause,
                        default='3s',
                        help='Pause between requests. There are three '
                             'different strategies: just set a number in '
                             'seconds (1s) or milliseconds (1000 or 1000ms) '
                             'or a uniformly distributed pause - two time'
                             ' values separated by a hyphen, then this is the '
                             'range from which you need to give a'
                             ' new timeout every time with a uniform '
                             'distribution in a given range (1s-2000) or'
                             ' a normally distributed pause: It is set like '
                             'this: gauss:1000/2.0 or gauss:200ms/3.0, '
                             'where between the colon and the slash is the '
                             'center of the normal distribution, after the'
                             ' slash is the standard deviation.')
    parser.add_argument('--lang', type=str, default='en',
                        help='National wikipedia section (fr, de, etc.).'
                             ' Default = en')
    parser.add_argument('--links_file', type=str,
                        default='links.txt',
                        help='The file to which external links will '
                             'be written.'
                             ' Default = links.txt')
    parser.add_argument('--nearest_file', type=str,
                        default='nearest.txt',
                        help='The file in which relationships with neighbors '
                             'by category will be recorded.'
                             ' Default = nearest.txt')
    args = parser.parse_args()
    page = args.page
    print(args.page)
    pause = args.pause
    lang = args.lang
    links_file = args.links_file
    nearest_file = args.nearest_file
    go_to_wiki(page, lang, links_file, nearest_file, pause)


if __name__ == '__main__':
    main()
