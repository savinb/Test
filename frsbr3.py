import datetime
import os
import time
import pandas as pd
import pytest
from allure_commons.types import AttachmentType
from selenium.webdriver.common.by import By
import shared
import allure
import re
from babel.dates import format_date, format_datetime, format_time
import zipfile
import xml.etree.ElementTree as ET

class FRSBR3:
    """Класс реализующий методы для работы с функционалом ФРС БР 3.
    """

    def __init__(self, variables, datadir, dbutils, fileutils, frs, pytestconfig):
        self.browser = frs.browser
        self.variables = variables
        self.datadir = datadir
        self.dbutils = dbutils
        self.fileutils = fileutils
        self.frs = frs
        self.pytestconfig = pytestconfig

    @staticmethod
    def get_month_name(date: datetime, genitive_case: bool = False):
        if genitive_case:
            # января
            return format_datetime(date, format="MMMM", locale='ru')
        else:
            # январь
            return format_datetime(date, format="LLLL", locale='ru')

    def calc_do(self, calc_name: str):
        browser = self.browser
        with allure.step('Выполнение расчёта ' + calc_name):
            all_done = False
            timeout = 10
            time.sleep(10)
            browser.find_element(by=By.XPATH, value="//span[contains(.,'Рассчитать')]").click()
            if not shared.is_element_exists(browser, by=By.XPATH, value=f"//tr[contains(., '{calc_name}')]", timeout=20):
                assert False, 'Не найден расчёт '+ calc_name
            while (not all_done) and (timeout < 21600):
                gettext = browser.find_element(by=By.XPATH, value=f"//tr[contains(., '{calc_name}')]").text
                with allure.step('Десятисекундная итерация ' + str(timeout) + '. Состояние: '+ gettext):
                    if 'Удачно рассчитана' in gettext:
                        all_done = True
                    else:
                        if 'Прервана' in gettext:
                            all_done = True
                        time.sleep(10)
                        timeout = timeout + 10
            if 'Удачно рассчитана' not in gettext:
                assert False, "Не расcчиталось за " + str(timeout) + ' Состояние: ' + gettext
            else:
                self.check_DB_op('Расчет окончен')
                return gettext.split('@')[0].rstrip()

    def calc_check_log(self, calc_log: str):
        fileutils = self.fileutils
        calc_log_origin = calc_log
        calc_hour = datetime.datetime.now().strftime('%d.%m.%Y %H')
        # Заменяем время
        calc_log = re.sub(r'\d{2}.\d{2}.\d{4} \d{2}:\d{2}:\d{2}', 'DD.MM.YYYY HH:mm:SS', calc_log)
        calc_log = re.sub(r'\d{2}.\d{2}.\d{4} \d{2}:\d{2}', 'DD.MM.YYYY HH:mm', calc_log)
        calc_log = re.sub(r'\d{2}.\d{2}.\d{4}', 'DD.MM.YYYY', calc_log)
        # Заменяем номер версии РИО
        calc_log = re.sub(r'Версия РИО: \d{1,6}', 'Версия РИО: NNNNNN', calc_log)
        # Заменяем номер расчета
        calc_log = re.sub(r'\d{1,5} DD.MM.YYYY', 'NNNN DD.MM.YYYY', calc_log)
        calc_log = re.sub(r'\d{1,5}\nDD.MM.YYYY', 'NNNN DD.MM.YYYY', calc_log)
        # calc_log = re.sub(r' \d{1,4} сек. ', ' N сек. ', calc_log)
        # calc_log = re.sub(r' \d{1,3} \d{1,3} сек. ', ' N сек. ', calc_log)
        calc_log = re.sub(r'\( .* сек. \)', '( N сек. )', calc_log)
        calc_log = re.sub(r'номером: \d{1,4}', 'номером: NNNN', calc_log)
        calc_log = re.sub(r'\n\d{1,5}\n', '\nNNNN\n', calc_log)
        calc_log = re.sub(r'Создана версия загрузки: \d{1,4}', 'Создана версия загрузки: NNNN', calc_log)
        calc_log = re.sub(r'Версия РИО \(xml\): \d{1,6}', 'Версия РИО (xml): V_RIO_XML', calc_log)
        calc_log = re.sub(r'Локальная версии РИО: \d{1,6}', 'Локальная версии РИО: V_RIO_Local', calc_log)
        # Заменяем id
        calc_log = re.sub(r' id=\d{1,4}. ', ' id=XXXX. ', calc_log)
        calc_log = re.sub(r' Версия: \d{1,4}. ', ' Версия: VVVV. ', calc_log)
        calc_log = re.sub(r' Окончательная версия: \d{1,4}', '  Окончательная версия: VVVV', calc_log)
        #данные по РГЕ "будет использована версия загрузки файла XML по ГТПГ из МФО БР: 61"
        calc_log = re.sub(r'XML по ГТПГ из МФО БР: \d{1,4}', 'XML по ГТПГ из МФО БР: NN', calc_log)
        # Новое обязательство: BRSB15339
        calc_log = re.sub(r'BRSB\d{1,5}', 'BRSBNNNNN', calc_log)
        # NNNN DD.MM.YYYY HH:mm:SS 1. Создан договор: BR-F00001-VOBLKOME-TELMAGES-0424
        calc_log = re.sub(r'Создан договор: .*', 'Создан договор: (Номер договора)', calc_log)

        test_id_full = os.environ.get('PYTEST_CURRENT_TEST').split('/')[-1]
        test_name = test_id_full.split(' ')[0].replace('.py::', '__')
        # TODO Если не закомментарено то сравнение с шаблоном не выполняется!#######
        with open(test_name + '_calc_log_template', 'w',encoding='windows-1251') as file:
            file.write(calc_log)
        ############################################################################
        calc_log_template = fileutils.read_file(test_name + '_calc_log_template')
        difference = set(calc_log.split('\n')).symmetric_difference(set(calc_log_template.split('\n')))
        if len(difference) > 0:
            print(str(difference))
            allure.attach(calc_log_origin, name=f"Лог расчёта", extension='txt')
            allure.attach(calc_log, name=f"Лог расчёта после замен", extension='txt')
            allure.attach(calc_log_template, name=f"Шаблон лога", extension='txt')
            allure.attach(str(difference), name=f"Разница", extension=AttachmentType.TEXT)
            pytest.fail(f"Лог выполнения расчёта не совпадает с эталоном!")
        else:
            allure.attach('Файл лога совпадает с шаблоном', name=f"Результат проверки", extension='txt')

    def calc_load_file_listner(self, server_parameter: str, files_to_load: list, l_name: str, timeout: int = 1200):
        browser = self.browser
        fileutils = self.fileutils
        frs = self.frs
        pytestconfig = self.pytestconfig
        server_name = frs.get_server_name()
        listner_path = frs.get_server_parameter(server_parameter, True) + '/'
        id_list = []

        copy_time = time.time()
        time.sleep(1)

        with allure.step('Остановка tomcat'):
            if pytestconfig.getoption('remote'):
                shared.run_ansible_playbook('tomcat-stop.yml', {})
            else:
                shared.manage_remote_service_by_jenkins(server_name, 'tomcat', 'Stop')

        with allure.step('Очистка каталогов литнера'):
            fileutils.delete_files_on_server(listner_path)
            fileutils.delete_files_on_server(listner_path + 'err/')
            fileutils.delete_files_on_server(listner_path + 'arch/')

        with allure.step(f'Копирование файлов {files_to_load}  в каталог {listner_path}'):
            file_name = fileutils.copy_files_to_server(files_to_load, listner_path, False)[0]
            if len(fileutils.find_files_on_server(files_to_load, copy_time, listner_path)) != len(files_to_load):
                assert False, f'Файлы {files_to_load} не скопировались'

        with allure.step('Запуск tomcat'):
            if pytestconfig.getoption('remote'):
                shared.run_ansible_playbook('tomcat-start.yml', {})
            else:
             shared.manage_remote_service_by_jenkins(server_name, 'tomcat', 'Start')

        with allure.step('Контроль успешности загрузки'):
            start = datetime.datetime.now()
            wait_sec = 0

            while len(fileutils.find_files_on_server(files_to_load, copy_time, listner_path)) > 0 and (datetime.datetime.now() - start).total_seconds() < timeout:
                time.sleep(10)
                wait_sec = wait_sec + 10

            if len(fileutils.find_files_on_server(['.*'], copy_time, listner_path+ 'arch/', regexp=True)) < len(files_to_load):
                if len(fileutils.find_files_on_server(['.*'], copy_time, listner_path + 'err/', regexp=True)) > 0:
                    assert False, f'Файлы находятся в каталоге неуспешных загрузок: ({len(fileutils.find_files_on_server(files_to_load, copy_time, listner_path + "err/"))}) штук'
                if server_parameter == 'listener.BrXmlMfoNodeEurService.in':
                    time.sleep(600)
                if len(fileutils.find_files_on_server(files_to_load, copy_time, listner_path)) > 0:
                    assert False, f'Файлы не обнаружены в каталоге успешных загрузок, остались валяться необработанные в каталоге {listner_path}'
                assert False, f'Файлы не обнаружены в каталоге успешных загрузок (ушли в никуда)'
            else:
                assert True, f'Файлы успешно загружены за {str(wait_sec)} секунд'
                self.check_DB_op('успешно завершена.')

            #if server_parameter != 'listener.BrXmlMfoNodeEurService.in' and server_parameter != 'listener.BrXmlMfoNodeSibService.in':
            with allure.step('Логин после рестарта tomcat'):
                frs.login('adm', 'adm')
                browser.find_element(by=By.XPATH, value="//*[contains(text(),'Журнал расчётов')]").click()
            # gettext = frs.get_webelement(by=By.XPATH, value=f"//tr[contains(., '{l_name}')]").text
            # return gettext.split('@')[0].rstrip()
            # SELECT max(id) FROM frsbr3.frs_event_log where source='BrXmlMfoNodeEurFileListener'
            for i in range(files_to_load.__len__()):
                SQL = f"SELECT max(version_id) FROM frsbr3.frs_file_load_log where file_name = '{files_to_load[i]}'"
                load_id = str(self.dbutils.run_sql(SQL)[0][0])
                id_list.append(load_id)

            # Ждём по БД окончательного завершения загрузки
                sql_success = f'''SELECT 1 FROM frsbr3.frs_event_detail_log ed, frsbr3.frs_event_log e, frsbr3.frs_file_load_log_event fle, frsbr3.frs_file_load_log fll
                            where e.id = fle.event_id and fle.load_id=fll.id and ed.event_id=e.id and fll.version_id={load_id}
                            and ed.detail_text like 'Загрузка файла%успешно завершена.' '''
                while len(self.dbutils.run_sql(sql_success)) == 0 and (datetime.datetime.now() - start).total_seconds() < timeout:
                    time.sleep(10)
            return id_list

    def set_journal_period(self):
        browser = self.browser
        fileutils = self.fileutils
        frs = self.frs
        with allure.step('Установка периода в журнале расчётов'):
            frs.get_webelement(by=By.XPATH, value="//input[contains(@id,'version-calc-select-start-date')]").click()
            time.sleep(1)
            frs.get_webelement(by=By.XPATH, value="(//div[@class='v-btn__content'])[1]").click()
            time.sleep(1)
            frs.get_webelement(by=By.XPATH, value="(//i[contains(@class,'right')])[2]").click()
            time.sleep(1)
            frs.get_webelement(by=By.XPATH, value="(//div[@class='v-btn__content'])[1]").click()
            frs.get_webelement(by=By.XPATH, value="//i[@class='v-icon notranslate mdi mdi-refresh theme--light']").click()

    def select_graph_node(self, node: str):
        if node == 'МОДУЛЬ РАСЧЕТА БР':
            return None
        browser = self.browser
        frs = self.frs
        with allure.step('Отркрытие графа расчётов'):
            frs.get_webelement(by=By.XPATH, value="//input[contains(@id,'clc-graph-category-select')]").click()

        with allure.step('Снятие отметок со всех узлов графа расчётов'):
            if frs.is_webelement_exists(by=By.XPATH, value="//*[@id='clc-graph-category-leafs-win']", timeout=5):
                frs.get_webelement(by=By.XPATH, value="//*[@id='clc-graph-category-leafs-win']/div[1]/div/button").click()
            else:
                assert False, 'Не найден узел МОДУЛЬ РАСЧЕТА БР'

        with allure.step('Выбор узла ' + node):
            if frs.is_webelement_exists(by=By.XPATH, value="//div[text() ='" + node + "']/ancestor::div[@class = 'v-treeview-node__content']/preceding-sibling::button[1]", timeout=15):
                frs.get_webelement(by=By.XPATH, value=f"//div[text() ='" + node + "']/ancestor::div[@class = 'v-treeview-node__content']/preceding-sibling::button[1]").click()
            else:
                assert False, f'Не найдены отметки узлов графа расчётов {node}'

    def select_operation(self, op_name: str):
        browser = self.browser
        frs = self.frs
        with allure.step(f'Поиск операции {op_name}'):
            frs.get_webelement(by=By.XPATH, value=f"//i[@class='v-icon notranslate mdi mdi-text-search theme--light']").click()
            frs.get_webelement(by=By.XPATH, value=f"//input[contains(@id,'input')]").send_keys(f'{op_name}')
            frs.get_webelement(by=By.XPATH, value=f"//button[@aria-label='append icon']").click()
            if frs.is_webelement_exists(by=By.XPATH, value=f"//div[@class='v-list-item__title'][contains(.,'{op_name}')]", timeout=15):
                frs.get_webelement(by=By.XPATH, value=f"//div[@class='v-list-item__title'][contains(.,'{op_name}')]").click()
            else:
                assert False, f'Не найдена операция {op_name}'

            if "Загрузка" in op_name:
                frs.get_webelement(by=By.XPATH, value=f"//div[@class='d-flex align-center pointer ml-8'][contains(.,'{op_name}')]/parent::div/child::button").click()
            else:
                frs.get_webelement(by=By.XPATH, value=f"//div[@class='d-flex align-center pointer'][contains(.,'{op_name}')]/parent::div/child::div").click()

    def control_count(self, c_id: str):
        browser = self.browser
        frs = self.frs
        with allure.step(f'Контроль выполненного расчёта {c_id}'):
            frs.get_webelement(by=By.XPATH, value=f"//span[@class='pointer underline version-calc-get-id'][text() = '{c_id}']").click()
            if frs.is_webelement_exists(by=By.XPATH, value=f"(//div[@class='v-select__selections'][contains(.,'30')])[2]", timeout=15):
                frs.get_webelement(by=By.XPATH, value=f"(//div[@class='v-select__selections'][contains(.,'30')])[2]").click()
                frs.get_webelement(by=By.XPATH, value=f"//div[@class='v-list-item__title'][contains(.,'100')]").click()

            frs.get_webelement(by=By.XPATH, value=f"(//div[contains(@class,'ripple')])[4]").click()
            if frs.is_webelement_exists(by=By.XPATH, value=f"//tbody[contains(.,'Отсутствуют данные')]", timeout=15):
                with allure.step(f'В отчете об операции {c_id} ошибок не найдено'):
                    frs.get_webelement(by=By.XPATH, value=f"(//div[contains(@class,'ripple')])[4]").click()
                with allure.step(f'Перемотка лога на последнюю страницу'):
                    if frs.is_webelement_exists(by=By.XPATH, value=f"//*[@id='evnt-detail-pagination']/ul", timeout=5):
                        c_pages = frs.get_webelement(by=By.XPATH, value=f"//*[@id='evnt-detail-pagination']/ul").text.split('\n').__len__()+1
                        s_pages = str(c_pages)
                        if c_pages > 3:
                            frs.get_webelement(by=By.XPATH, value=f"//button[@type='button'][contains(.,'{s_pages}')]").click()
                        if c_pages == 3:
                            frs.get_webelement(by=By.XPATH, value=f"(//i[contains(@class,'v-icon notranslate mdi mdi-chevron-right theme--light')])[2]").click()
            else:
                assert False, f'Обнаружены ошибки в операции {c_id}!'

    def get_text_log(self, id: str, num_file: int = None):
        fileutils = self.fileutils
        frs = self.frs
        datadir = fileutils.datadir
        with allure.step(f'Получение Excel файла лога и преобразование его в текст'):
            frs.get_webelement(by=By.XPATH, value="(//i[@class='v-icon notranslate mdi mdi-download theme--light'])[2]").click()
            if 'Реестр_участников' in self.datadir.name:
                report_list = f'events[{id}].xlsx'
            else:
                report_list = f'version-details[{id}].xlsx'
            frs.reports.download_single_report(report_list)
            value = fileutils.xls_read(report_list)
            rows = value.values.shape[0]
            cols = value.values.shape[1]

            if num_file != None:
                fname = f'version-details_log_{str(num_file+1)}.txt'
            else:
                fname = f'version-details_log.txt'
            with open(datadir/fname, 'w', encoding='windows-1251') as file:
                for i in range(0, rows):
                    for j in range(0, cols):
                        log_str = str(value.values[i, j])
                        # Заменяем время
                        # if log_str.find('CMAX ') > 0:

                        log_str = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', 'YYYY-MM.DD HH:mm:SS', log_str)
                        log_str = re.sub(r'(\d{2})\.(\d{2})\.(\d{4})', 'DD.MM.YYYY', log_str)
                        log_str = re.sub(r'ZONE\d{1}_\d{5}_\d{14}_', 'ZONEN_NNNNN_YYYYMMDDHHmmss_', log_str)

                        log_str = re.sub(r'загружен: \d{2}.\d{2}.\d{4} \d{2}:\d{2}', 'загружен: DD.MM.YYYY HH:mm', log_str)
                        log_str = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', 'YYYY-MM.DD HH:mm', log_str)
                        log_str = re.sub(r'\d{4}-\d{2}-\d{2} ', 'YYYY-MM-DD', log_str)
                        log_str = re.sub(r'\d{2}:\d{2}:\d{2}', 'HH:mm:SS', log_str)
                        log_str = re.sub(r'\d{2}:\d{2}', 'HH:mm', log_str)
                        # Заменяем номер версии РИО
                        log_str = re.sub(r'Версия РИО: \d{1,6}', 'Версия РИО: NNNNNN', log_str)
                        # Заменяем номер расчета
                        log_str = re.sub(r'\d{1,5} DD.MM.YYYY', 'NNNN DD.MM.YYYY', log_str)
                        # log_str = re.sub(r' \d{1,4} сек. ', ' N сек. ', log_str)
                        # log_str = re.sub(r' \d{1,3} \d{1,3} сек. ', ' N сек. ', log_str)
                        log_str = re.sub(r'\( .* сек. \)', '( N сек. )', log_str)
                        log_str = re.sub(r'номером: \d{1,4}', 'номером: NNNN', log_str)
                        if j == 0: log_str = re.sub(r'\d{1,5}', 'NNNNN', log_str)
                        log_str = re.sub(r'Создана версия загрузки: \d{1,4}', 'Создана версия загрузки: NNNN', log_str)
                        log_str = re.sub(r'Версия РИО \(xml\): \d{1,6}', 'Версия РИО (xml): V_RIO_XML', log_str)
                        log_str = re.sub(r'Локальная версии РИО: \d{1,6}', 'Локальная версии РИО: V_RIO_Local', log_str)
                        # Заменяем id
                        log_str = re.sub(r' id=\d{1,4}. ', ' id=XXXX. ', log_str)
                        log_str = re.sub(r' Версия: \d{1,4}. ', ' Версия: VVVV. ', log_str)
                        log_str = re.sub(r' Окончательная версия: \d{1,4}', '  Окончательная версия: VVVV', log_str)
                        # данные по РГЕ "будет использована версия загрузки файла XML по ГТПГ из МФО БР: 61"
                        log_str = re.sub(r'XML по ГТПГ из МФО БР: \d{1,4}', 'XML по ГТПГ из МФО БР: NN', log_str)
                        # Новое обязательство: BRSB15339
                        log_str = re.sub(r'BRSB\d{1,5}', 'BRSBNNNNN', log_str)
                        # NNNN DD.MM.YYYY HH:mm:SS 1. Создан договор: BR-F00001-VOBLKOME-TELMAGES-0424
                        log_str = re.sub(r'Создан договор: .*', 'Создан договор: (Номер договора)', log_str)
                        file.write(log_str + '|')
                    file.write('\n')

            frs.get_webelement(by=By.XPATH, value=f"//i[contains(@class,'v-icon notranslate mdi mdi-close theme--light black--text')]").click()

            with open(datadir/fname, 'r', encoding='windows-1251') as file:
                return file.read()

    def goto_report(self, c_name: str, r_name: str, FSK_flag: bool = False, autostart: bool = True, t_limit: int = 600):
        frs = self.frs
        with allure.step('Отркрытие журнала расчётов, получение id, переход в форму "Информация об операции"'):
            frs.get_webelement(by=By.XPATH, value="//span[@class='v-btn__content'][contains(.,'Журнал расчётов')]").click()
            if frs.is_webelement_exists(by=By.XPATH, value=f"//div[@class='v-select__selections'][contains(.,'30')]", timeout=15):
                frs.get_webelement(by=By.XPATH, value=f"//div[@class='v-select__selections'][contains(.,'30')]").click()
                frs.get_webelement(by=By.XPATH, value=f"//div[@class='v-list-item__title'][contains(.,'1000')]").click()
            # if frs.is_webelement_exists(by=By.XPATH, value=f"(//i[@class='v-icon notranslate mdi mdi-menu-down theme--light'])[2]", timeout=15):
            #     frs.get_webelement(by=By.XPATH, value=f"(//i[@class='v-icon notranslate mdi mdi-menu-down theme--light'])[2]").click()
            #     frs.get_webelement(by=By.XPATH, value=f"//i[@class='v-icon notranslate mdi mdi-menu-down theme--light primary--text']//following::div[@class='v-list-item__title'][contains(text(),'{c_name}')]").click()

            id = frs.get_webelement(by=By.XPATH, value=f"//tr[contains(.,'{c_name}')]").text.split('@')[0].rstrip()
            frs.get_webelement(by=By.XPATH, value=f"//span[@class='pointer underline version-calc-get-id'][text() = '{id}']").click()

        with allure.step(f'Получение отчётов "{r_name}"'):
            frs.click_webelement(by=By.XPATH, value=f"//div[@class='link-alike'][contains(.,'{r_name}')]")

            if FSK_flag:
                frs.get_webelement(by=By.XPATH, value=f"(//div[contains(@class,'v-input--selection-controls__ripple')])[6]").click()
            if not autostart:
                frs.get_webelement(by=By.XPATH, value="//span[@class='v-btn__content'][contains(.,'Сформировать')]").click()
            all_done = False
            timeout = 0
            while (not all_done) and (timeout < t_limit):
                if frs.is_webelement_exists(by=By.XPATH, value="//div[@class='v-card__title'][contains(.,'Формирование завершено')]", timeout=10):
                    all_done = True
                else:
                    if frs.is_webelement_exists(by=By.XPATH, value=f"//div[@class='v-card__title'][contains(.,'Отчеты не сформированы')]", timeout=10):
                        all_done = True
                with allure.step('Десятисекундная итерация ' + str(timeout)):
                    if not all_done:
                        if frs.is_webelement_exists(by=By.XPATH, value=f"//div[contains(@class,'notification error')]", timeout=10):
                            assert False, 'Упало с красной рамкой'
                        timeout = timeout + 10
            assert timeout < t_limit, f'Превышен таймаут ожидания отчётов {t_limit} сек'

    def check_report(self, r_list: list, t_list: list, ignored_cols: list = None, ignored_rows: list = None):
        fileutils = self.fileutils
        datadir = self.datadir
        frs = self.frs
        with (allure.step('Проверка отчётов')):
            for i in range(1, r_list.__len__()):
                with allure.step('Проверка отчёта ' + r_list[i]):
                    frs.get_webelement(by=By.XPATH, value=f"//td[contains(.,'{r_list[i]}')]").click()
                    frs.reports.download_single_report(r_list[i])
                    if r_list[i].find('xml') > 0:
                        # frs.get_webelement(by=By.XPATH, value=f"//td[contains(.,'{r_list[i]}')]").click()
                        strFSK = ['fsk_sum_pok_', 'ORCT_MONTH_FACT_FSK', '_FACT_FSK_CFR', '_FSK_FACT_CFR', '_fsk_finance', '_sum_fsc_bez_gq', '_fsc_analytics']
                        for j in range(0, strFSK.__len__()):

                            if r_list[i].find(strFSK[j]) > 0:
                                fileutils.replace_in_file({r'created="[^"]*"': 'created="created"'}, r_list[i])
                                fileutils.replace_in_file({r'id="[^"]*"': 'id="id"'}, r_list[i])
                                fileutils.replace_in_file({r'p-calc-version="[^"]*"': 'p-calc-version="p-calc-version"'}, r_list[i])
                                fileutils.replace_in_file({r'p-calc-db-name="[^"]*"': 'p-calc-db-name="p-calc-db-name"'}, r_list[i])
                                fileutils.replace_in_file({r'p-calc-instance-name="[^"]*"': 'p-calc-instance-name="p-calc-instance-name"'}, r_list[i])
                                fileutils.replace_in_file({r'ver-rio="[^"]*"': 'ver-rio="ver-rio"'}, r_list[i])
                                fileutils.replace_in_file({r'source="[^"]*"': 'source="source"'}, r_list[i])
                                fileutils.replace_in_file({r'<subject>.*': '<subject>subject</subject>'}, r_list[i])
                                fileutils.replace_in_file({r'timestamp="\d{14}"': 'timestamp="timestamp"'}, r_list[i])
                                fileutils.replace_in_file({r'source-filename="[^"]*"': 'source-filename="source-filename"'}, r_list[i])
                        fileutils.xml_compare(r_list[i], t_list[i - 1], skip_order=True)
                    else:
                        if ignored_cols != None:
                            fileutils.xls_compare(r_list[i], t_list[i - 1], skip_order=True, skip_columns=ignored_cols)
                        if  ignored_rows != None:
                            fileutils.xls_compare(r_list[i], t_list[i - 1], skip_order=True, skip_cells=ignored_rows)
                        if ignored_rows == None and ignored_cols == None:
                            try:
                                fileutils.xls_compare(r_list[i], t_list[i - 1], skip_order=True)
                            except:
                                self.compare_excel_files(datadir / r_list[i], datadir / t_list[i - 1])
                with (allure.step('Проверка формирования по БД:')):
                    # SQL = (f"SELECT * FROM frsbr3.frs_event_detail_log "
                    #        f"where event_id=(SELECT max(event_id) FROM frsbr3.frs_event_detail_log) and type_id = 'INFO'")
                    SQL = (f"SELECT * FROM frsbr3.frs_event_detail_log "
                           f"where event_id=(SELECT max(event_id) FROM frsbr3.frs_event_detail_log)")
                    log_text = self.dbutils.run_sql(SQL)
                    a = ''
                    for k in range(0, log_text.__len__()):
                        a += log_text[k][5]+'\n'
                    with (allure.step(f'{a}')):
                        return log_text

    def check_remote_report(self, r_list: list, t_list: list, o_d: str, c_h: str):
        fileutils = self.fileutils
        datadir = self.datadir

        def trim_file(name: str, head: int = 10, tail: int = 1):
            path = datadir / name
            try:
                with path.open('r', encoding='windows-1251') as f:
                    lines = f.readlines()
            except FileNotFoundError:
                return
            result = lines[:head] + (lines[-tail:] if lines else [])
            with path.open('w', encoding='windows-1251') as f:
                f.writelines(result)

        # Общие XML-паттерны, применяемые всегда к XML-файлам
        common_xml_repls = [
            (r'source="\d{8}_ZONE5_\d{8}_A\d{1}_FRSBR_NCZ_CFR_AVANS_\w{4,5}_XLS.xls"', 'source="source"'),
            (r'<subject>\d{8}_ZONE5_\d{8}_A\d{1}_FRSBR_NCZ_CFR_AVANS_\w{4,5}_XLS', '<subject>subject'),
            (r'created-date="\d{14}"', 'created="YYYYMMDDhhmmss"'),
            (r'guid="\{.*\}"', 'guid = "guid"'),
        ]

        # Повторяющиеся наборы замен вынесены в списки для удобного применения
        replacements_9xx = [
            (r'source-filename=".*.xl.*"', 'source-filename="s-f"'),
            (r'source=".*.xl.*"', 'source="s-f"'),
            (r'timestamp="\d{14}"', 'timestamp="timestamp"'),
            (r'report-session-id="\d{1,4}"', 'report-session-id="report-session-id"'),
            (r'id=.*', 'id="id"'),
            (r'<subject>.*', '<subject>subject</subject>'),
        ]

        # Проходим по списку отчётов (начиная с индекса 1, как в оригинале)
        with allure.step(f'Проверка отчётов в каталоге выгрузки {o_d}'):
            for idx, report in enumerate(r_list[1:], start=1):
                target = t_list[idx - 1] if idx - 1 < len(t_list) else None
                with allure.step(f'Проверка отчёта {report}'):
                    fileutils.download_report_from_server(report, o_d, c_h)

                    # Обрезки для текстовых отчётов
                    if 'BRS_' in report:
                        trim_file(r_list[1], head=10, tail=1)
                    elif 'FRSBR_MTNCZ_GTPP_5' in report:
                        trim_file(r_list[1], head=10, tail=50)

                    # Excel-сравнения
                    lower = report.lower()
                    if lower.endswith(('.xls', '.xlsx')):
                        try:
                            if '_BR_BAN_' in report:
                                fileutils.xls_compare(report, target, skip_columns=['C'], skip_order=True)
                            elif '_FRSBR_BANKRUPT_POVER_REPORT' in report:
                                fileutils.xls_compare(report, target, skip_columns=['E'], skip_cells=['A9'], skip_order=True)
                            else:
                                fileutils.xls_compare(report, target, skip_order=True)
                        except Exception:
                            # fallback на внутреннюю функцию сравнения
                            self.compare_excel_files(datadir / report, datadir / target)

                    # XML-обработка и сравнение
                    if lower.endswith('.xml'):
                        # общие замены
                        for pat, repl in common_xml_repls:
                            fileutils.replace_in_file({pat: repl}, report)

                        # Специфичные случаи
                        if fileutils.find_in_file('type="FRSBR_NCZ_PART_AVANS_REESTR"', report):
                            self.replace_all_in_file({
                                r'source-filename="\d{8}_\w{8}_ZONE5_\d{8}_A\d{1}_FRSBR_NCZ_PART_AVANS_REESTR.xls"': 'source-filename="s-f"',
                                r'timestamp="\d{14}"': 'timestamp="timestamp"',
                                r'report-session-id="FRSBR_NCZ_EE_\d{17}"': 'report-session-id="report-session-id"',
                                r'id="FRSBR_NCZ_EE_\d{17}"': 'id="id"',
                            }, report)

                        # 9.XX группы
                        str9XX = ['_PART_MAIL"', '_BANKRUPT"', 'REESTR_DOG"', 'POVER_REPORT"', 'REESTR_OBYAZ_CFR"', 'REESTR_TREB_CFR"']
                        for marker in str9XX:
                            if fileutils.find_in_file(marker, report):
                                for pat, repl in replacements_9xx:
                                    fileutils.replace_in_file({pat: repl}, report)

                        # ЦФР | Реестры и другие условные замены
                        if any(fileutils.find_in_file(s, report) for s in (
                                'Обязательства на БР за период',
                                'Реестр обязательств по договорам купли-продажи',
                                'Обязательства на БР ДВ за период'
                        )):
                            fileutils.replace_in_file({r'<package id=".{32}"': '<package id="id"'}, report)
                            fileutils.replace_in_file({r'package-date="\d{8}"': 'package-date="YYYYMMDD"'}, report)
                            fileutils.replace_in_file({r'contract-number="BR-.*" ': 'contract-number="contract-number" '}, report)
                            fileutils.replace_in_file({r'contract-date="\d{8}"': 'contract-date="YYYYMMDD"'}, report)
                            fileutils.replace_in_file({r'fss-id="BRSB\d{5}"': 'fss-id="BRSB-id"'}, report)

                        if fileutils.find_in_file('признанных банкротами', report) or 'BRS_' in report:
                            fileutils.replace_in_file({r'contract-date="\d{8}"': 'contract-date="YYYYMMDD"'}, report)
                            fileutils.replace_in_file({r'fss-id="BRS.{6}"': 'fss-id="BRSXXXXXX"'}, report)
                            fileutils.replace_in_file({r'<subject>.*': '<subject>subject</subject>'}, report)
                            fileutils.replace_in_file({r'source=".*.xml"': 'source="s-f"'}, report)

                        if fileutils.find_in_file('class="FRSBR_NCZ_CFR_AVANS_REESTR_XML"', report):
                            fileutils.replace_in_file({r'source="BRNCZ_ZONE5_AVANS\d{1}_\d{8}_\d{8}_\d{1,3}.xml"': 'source="source"'}, report)
                            fileutils.replace_in_file({r'<subject>BRNCZ_ZONE5_AVANS\d{1}_\d{8}_\d{8}_\d{1,3}': '<subject>subject'}, report)

                        if fileutils.find_in_file('Реестр обязательств/требований по авансовым платежам по договорам купли-продажи', report):
                            fileutils.replace_in_file({r'^  id=.*': '  id="id"'}, report)
                            fileutils.replace_in_file({r'^  package-date=               "\d{8}"': '  package-date=               "YYYYMMDD"'}, report)

                        # Приложение 1 к финансовому отчету
                        if fileutils.find_in_file('FRSBR_PRIL_FINO', report):
                            fileutils.replace_in_file({r'id="[^"]*_FRSBR_PRIL_FINO"': 'id="id"'}, report)
                            fileutils.replace_in_file({r'source-filename="[A-Z0-9_]*_FRSBR_PRIL_FINO\.xls"': 'source-filename="source-filename"'}, report)
                            fileutils.replace_in_file({r'timestamp="\d{14}"': 'timestamp="timestamp"'}, report)
                            fileutils.replace_in_file({r'report-session-id="\d{1,4}"': 'report-session-id="report-session-id"'}, report)

                        # Различные классы/форматы
                        if fileutils.find_in_file('class="FOREM"', report):
                            fileutils.replace_in_file({r'id="[^"]*"': 'id="32s"'}, report)
                            fileutils.replace_in_file({r'local-id="[^"]*"': 'local-id="NNNN"'}, report)
                            fileutils.replace_in_file({r'created="\d{8}"': 'created="YYYYMMDD"'}, report)

                        if fileutils.find_in_file('class="FRSBR_ORCT_MONTH_FACT"', report):
                            fileutils.replace_in_file({r'created="\d{14}"': 'created="YYYYMMDDHHmmss"'}, report)
                            fileutils.replace_in_file({r'p-version-id="\d{1,3}"': 'p-version-id="ID"'}, report)
                            fileutils.replace_in_file({r'ver-rio="\d{1,6}"': 'ver-rio="vRIO"'}, report)
                            fileutils.replace_in_file({r'p-calc-db-name="[^"]*"': 'p-calc-db-name="p-calc-db-name"'}, report)

                        if fileutils.find_in_file('class="ASUD_PART_BR_BANKRUPT"', report) or fileutils.find_in_file('class="FRSBR_CFR_REESTR_OBYAZ_BANKRUPT"', report):
                            fileutils.replace_in_file({r'  id="[^"]*"': '  id="32s"'}, report)
                            fileutils.replace_in_file({r'  source-filename="[^"]*"': '  source-filename="source-filename"'}, report)
                            fileutils.replace_in_file({r'source=".*.xml"': 'source="s-f"'}, report)
                            fileutils.replace_in_file({r'  timestamp="[^"]*"': '  timestamp="14d"'}, report)
                            fileutils.replace_in_file({r'  report-session-id="[^"]*"': '  report-session-id="report-session-id"'}, report)

                        if fileutils.find_in_file('class="FRSBR_PART_DOG_BANKRUPT_POVER_REPORT"', report):
                            fileutils.replace_in_file({r'date-from="\d{8}"': 'date-from="YYYYMMDD"'}, report)
                            fileutils.replace_in_file({r'date-to="\d{8}"': 'date-to="YYYYMMDD"'}, report)

                        if fileutils.find_in_file('class="FRSBR_PRICE_DDPR"', report):
                            fileutils.replace_in_file({r'  id="[^"]*"': '  id="32s"'}, report)
                            fileutils.replace_in_file({r'  source-filename="[^"]*"': '  source-filename="source-filename"'}, report)
                            fileutils.replace_in_file({r'source=".*.xml"': 'source="s-f"'}, report)
                            fileutils.replace_in_file({r'  timestamp="[^"]*"': '  timestamp="14d"'}, report)
                            fileutils.replace_in_file({r'  report-session-id="[^"]*"': '  report-session-id="report-session-id"'}, report)

                        if fileutils.find_in_file('class="FRSBR_NCZ_PART_ITOG_REESTR"', report) or fileutils.find_in_file('NCZ_CFR_ITOG', report):
                            fileutils.replace_in_file({r'  id="[^"]*"': '  id="32s"'}, report)
                            fileutils.replace_in_file({r'  source-filename="[^"]*"': '  source-filename="source-filename"'}, report)
                            fileutils.replace_in_file({r'source=".*.xls"': 'source="s-f"'}, report)
                            fileutils.replace_in_file({r'timestamp="\d{14}"': 'timestamp="timestamp"'}, report)
                            fileutils.replace_in_file({r'report-session-id="FRSBR_NCZ_EE_\d{17}"': 'report-session-id="report-session-id"'}, report)
                            fileutils.replace_in_file({r'  report-session-id="[^"]*"': '  report-session-id="report-session-id"'}, report)
                            fileutils.replace_in_file({r'<subject>\d{8}_ZONE5_\d{8}_FRSBR_NCZ_CFR_ITOG_\w{4,5}_XLS.xls': '<subject>subject'}, report)

                        if fileutils.find_in_file('комиссии в НЦЗ \(5\)', report) or fileutils.find_in_file('class="FRSBR_NCZ_CFR_ITOG_REESTR_XML"', report):
                            fileutils.replace_in_file({r'<package id=".{32}"': '<package id="id"'}, report)
                            fileutils.replace_in_file({r'package-date="\d{8}"': 'package-date="YYYYMMDD"'}, report)
                            fileutils.replace_in_file({r'source=".*.xm.*"': 'source="s-f"'}, report)
                            fileutils.replace_in_file({r'<subject>\w{5}_ZONE5_ITOG_\d{8}_\d{8}_\d{2,4}.xml': '<subject>subject'}, report)
                            fileutils.replace_in_file({r'fss-id="[^"]*"': 'fss-id="fss-id"'}, report)

                        if fileutils.find_in_file('class="FRSBR_MTNCZ"', report):
                            fileutils.replace_in_file({r'created="\d{14}"': 'created="YYYYMMDDhhmmss"'}, report)
                            fileutils.replace_in_file({r'num="\d{1,4}"': 'num="NNNN"'}, report)
                            fileutils.replace_in_file({r'version-id="\d{1,4}"': 'version-id="version-id"'}, report)
                            fileutils.replace_in_file({r'calc-version="\d{1,4}"': 'calc-version="calc-version"'}, report)
                            fileutils.replace_in_file({r'calc-db-name="[^"]*"': 'calc-db-name="calc-db-name"'}, report)
                            fileutils.replace_in_file({r'stand-name="[^"]*"': 'stand-name="stand-name"'}, report)
                            fileutils.replace_in_file({r'ver-rio="[^"]*"': 'ver-rio="ver-rio"'}, report)

                        if fileutils.find_in_file('class="FRSBR_ORCT_NCZ_MONTH_FACT"', report):
                            fileutils.replace_in_file({r'ver-rio="\d{1,6}"': 'ver-rio="ver-rio"'}, report)
                            fileutils.replace_in_file({r'p-version-id="\d{1,4}"': 'p-version-id="p-version-id"'}, report)
                            fileutils.replace_in_file({r'p-calc-db-name="[^"]*"': 'p-calc-db-name="p-calc-db-name" '}, report)
                            fileutils.replace_in_file({r'p-calc-schema="[^"]*"': 'p-calc-schema="p-calc-schema"'}, report)
                            fileutils.replace_in_file({r'created="\d{14}"': 'created="YYYYMMDDhhmmss"'}, report)

                        if fileutils.find_in_file('электроэнергии в НЦЗ \(5\)', report) or fileutils.find_in_file('class="FRSBR_NCZ_CFR_REESTR_DD_XML"', report):
                            fileutils.replace_in_file({r'<package id=".{32}"': '<package id="id"'}, report)
                            fileutils.replace_in_file({r'package-date="\d{8}"': 'package-date="YYYYMMDD"'}, report)
                            fileutils.replace_in_file({r'source=".*.xm.*"': 'source="s-f"'}, report)
                            fileutils.replace_in_file({r'<subject>.*': '<subject>subject</subject>'}, report)

                        if fileutils.find_in_file('UPZ_dd_buy', report) or fileutils.find_in_file('UPZ_dd_sell', report):
                            fileutils.replace_in_file({r'id="[^"]*"': 'id="id"'}, report)
                            fileutils.replace_in_file({r'source-filename="[^"]*"': 'source-filename="source-filename"'}, report)
                            fileutils.replace_in_file({r'timestamp="[^"]*"': 'timestamp="timestamp"'}, report)

                        if 'param_for_koef_snizh_month.xml' in report or 'param_for_koef_snizh_year.xml' in report:
                            fileutils.replace_in_file({r'stand-name=".*"': 'stand-name="stand-name"'}, report)
                            fileutils.replace_in_file({r'calc-type="[^"]*"': 'calc-type="calc-type"'}, report)
                            fileutils.replace_in_file({r'calc-id="[^"]*"': 'calc-id="calc-id"'}, report)

                        # Финальное сравнение XML
                        fileutils.xml_compare(report, target, skip_order=True)

    def check_db_generation(self):
        with allure.step('Проверка формирования по БД:'):
            SQL = (
                "SELECT * FROM frsbr3.frs_event_detail_log "
                "where event_id=(SELECT max(event_id) FROM frsbr3.frs_event_detail_log)"
            )
            log_text = self.dbutils.run_sql(SQL)
            # Собираем текст логов (начиная со второй строки, как в оригинале)
            combined = ''.join(row[5] for row in log_text[1:]) if len(log_text) > 1 else ''
            with allure.step(combined):
                return log_text

    def check_DB_op(self, final_str:str):
        with allure.step('Проверка лога операции по БД'):
            SQL = (f"SELECT * FROM frsbr3.frs_event_detail_log "
                   f"where event_id=(SELECT max(event_id) FROM frsbr3.frs_event_detail_log) and type_id = 'INFO'")
            log_text = self.dbutils.run_sql(SQL)
            if str(log_text).__contains__(final_str):
                with allure.step(f'Проверка лога операции по БД выполнена успешно, признак: {final_str}'):
                    None
            else:
                with allure.step(f'Проверка лога операции по БД выполнена c ошибкой!, признак: {final_str} не найден'):
                    None
            return log_text

    def allure_rep_log(self):
        pytestconfig = self.pytestconfig
        frs = self.frs
        server_name = frs.get_server_name()
        test_id_full = os.environ.get('PYTEST_CURRENT_TEST').split('/')[-1]
        test_name = test_id_full.split(' ')[0].replace('.py::', '__')
        dirname = os.environ.get('PYTEST_CURRENT_TEST').split('/')[-1].split(' ')[0].split('.py')[0]
        if dirname == 'test_Реестр_участников' or dirname == 'test_Проверка_системы':
            procname = os.environ.get('PYTEST_CURRENT_TEST').split('/')[1].split('::')[1].split(' ')[0]
        else:
            procname = os.environ.get('PYTEST_CURRENT_TEST').split('/')[2].split('::')[1].split(' ')[0]
        print(f'\n■■■■■\n{dirname}\n■■■■■')
        with allure.step(f'{dirname}'):
            allure.attach(dirname, name=f'{dirname}')
            allure.attach(procname, name=f'{procname}')
        if 'test_load_' in procname:
            with allure.step('Запуск tomcat'):
                if pytestconfig.getoption('remote'):
                    shared.run_ansible_playbook('tomcat-start.yml', {})
                else:
                 shared.manage_remote_service_by_jenkins(server_name, 'tomcat', 'Start')
            return test_name
        if self.variables['debug_mode']:
            import subprocess
            proc = subprocess.Popen(['explorer', frs.datadir])
            # os.system(f"TASKKILL /F /PID {proc.pid}")

    def get_load_id(self, fname : str):
        SQL = f"SELECT max(version_id) FROM frsbr3.frs_file_load_log where file_name = '{fname}'"
        load_id = str(self.dbutils.run_sql(SQL)[0][0])
        return load_id

    def login_m(self, search_str: str = None, login: str = None, password: str = None):
        browser = self.browser
        frs = self.frs
        browser.get('http://vm-ot-docker:19000/login')
        frs.get_webelement(by=By.XPATH, value=f"//input[contains(@id,'accessKey')]").send_keys('minioadmin')
        frs.get_webelement(by=By.XPATH, value=f"//input[contains(@id,'secretKey')]").send_keys('minioadmin')
        frs.get_webelement(by=By.XPATH, value=f"//*[@id='do-login']").click()
        browser.get('http://vm-ot-docker:19000/buckets/frsbr3/browse')
        frs.get_webelement(by=By.XPATH, value=f'//*[@id="search-resource"]').send_keys(search_str)

        return browser

    def select_rep_param(self, c_name: str, r_name: str, subj_name: str = None, GTP_name: str = None, autostart: bool = False):
        frs = self.frs
        with allure.step('Отркрытие журнала расчётов, получение id, переход в форму "Информация об операции"'):
            frs.get_webelement(by=By.XPATH, value="//span[@class='v-btn__content'][contains(.,'Журнал расчётов')]").click()
            id = frs.get_webelement(by=By.XPATH, value=f"//tr[contains(.,'{c_name}')]").text.split('@')[0].rstrip()
            frs.get_webelement(by=By.XPATH, value=f"//span[@class='pointer underline version-calc-get-id'][text() = '{id}']").click()

        with allure.step(f'Получение отчётов "{r_name}"'):
            frs.click_webelement(by=By.XPATH, value=f"//div[@class='link-alike'][contains(.,'{r_name}')]")

            if subj_name != None:
                with allure.step(f'Выбор Участника {subj_name}'):
                    frs.get_webelement(by=By.XPATH, value="//input[contains(@id,'report-param-fstTraderIdList')]").click()
                    frs.get_webelement(by=By.XPATH, value=f"//input[contains(@id,'report-param-fstTraderIdList')]").send_keys(subj_name)
                    frs.get_webelement(by=By.XPATH, value=f"//div[@class='v-list-item__title'][contains(.,'{subj_name}')]").click()
                    frs.get_webelement(by=By.XPATH, value="//i[contains(@class,'v-icon notranslate mdi mdi-menu-down theme--light primary--text')]").click()

            if GTP_name != None:
                with allure.step(f'Выбор ГТП {GTP_name}'):
                    frs.get_webelement(by=By.XPATH, value="//input[contains(@id,'report-param-gtpIdList')]").click()
                    frs.get_webelement(by=By.XPATH, value="//input[contains(@id,'report-param-gtpIdList')]").send_keys(GTP_name)
                    frs.get_webelement(by=By.XPATH, value=f"//div[@class='v-list-item__title'][contains(.,'{GTP_name}')]").click()
                    frs.get_webelement(by=By.XPATH, value="//i[contains(@class,'v-icon notranslate mdi mdi-menu-down theme--light primary--text')]").click()

            with allure.step(f'Ожидание окончания формирования отчётов'):
                if not autostart:
                    frs.get_webelement(by=By.XPATH, value="//span[@class='v-btn__content'][contains(.,'Сформировать')]").click()
                all_done = False
                timeout = 0
                while (not all_done) and (timeout < 600):
                    all_done = frs.is_webelement_exists(by=By.XPATH, value="//table[contains(.,'Файл(ы) доступные для скачивания')]", timeout=10)
                    with allure.step('Десятисекундная итерация ' + str(timeout)):
                        if all_done:
                            report_list = frs.get_webelement(by=By.XPATH, value=f"//table[contains(.,'Файл(ы) доступные для скачивания')]").text.split('\n')
                        else:
                            timeout = timeout + 10

        with allure.step(f'Список отчётов: {report_list[1:]}'):
            return report_list

    def extract_text_from_docx(self, s:str):
        with allure.step(f'Преобразование {s} в текстовый файл'):
            with zipfile.ZipFile(s, 'r') as docx:
                xml_content = docx.read('word/document.xml')
                root = ET.fromstring(xml_content)
            # Пространство имён для Word XML
            word_namespace = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            text_elements = []
            # # Извлекаем текст из всех <w:t> элементов
            for text_node in root.iter(f'{word_namespace}t'):
                text_elements.append(text_node.text)
            return ''.join(text_elements)

    def get_cell_address(self, row_idx, col_idx):
        """
        Преобразует числовые индексы строки и столбца в адрес ячейки Excel (A1, B2 и т.д.).
        """
        # Создаем строку из букв столбцов (0 -> A, 1 -> B, ..., 25 -> Z, 26 -> AA)
        letters = ''
        col_idx_copy = col_idx
        while col_idx_copy >= 0:
            letters = chr(ord('A') + (col_idx_copy % 26)) + letters
            col_idx_copy = (col_idx_copy // 26) - 1
        return f"{letters}{row_idx + 1}"

    def compare_excel_files(self, file1_path, file2_path):
        """
        Сравнивает два файла Excel и выводит список различий.
        """
        try:
            # Читаем файлы Excel. По умолчанию читается первый лист ('Sheet1').
            df1 = pd.read_excel(file1_path)
            df2 = pd.read_excel(file2_path)

            # Проверяем, совпадают ли размеры таблиц
            if df1.shape != df2.shape:
                print("Размеры таблиц не совпадают. Сравнение по ячейкам невозможно.")
                print(f"Размер Таблицы1: {df1.shape} (строк, столбцов)")
                print(f"Размер Таблицы2: {df2.shape} (строк, столбцов)")
                return

            # Находим индексы ячеек, где значения различаются
            diff_df = df1.compare(df2, keep_shape=True)
            if diff_df.empty:
                print("Различий между таблицами не обнаружено.")
                return

            compare_text = ''

            for row_idx in diff_df.index:
                for col_name in diff_df.columns.get_level_values(0):
                    # Проходим по базовым именам столбцов (без суффиксов '_self'/'_other')

                    # Проверяем, действительно ли в этой ячейке есть отличие
                    # Это нужно, так как keep_shape=True заполняет несуществующие отличия NaN
                    val_self = diff_df.at[row_idx, (col_name, 'self')]
                    val_other = diff_df.at[row_idx, (col_name, 'other')]

                    if pd.notna(val_self) or pd.notna(val_other):
                        # Вычисляем адрес ячейки для вывода
                        col_idx_original = df1.columns.get_loc(col_name)
                        address = self.get_cell_address(row_idx, col_idx_original)

                    if pd.notna(val_self) or pd.notna(val_other):
                        compare_text += f"Отчёт: {val_self} ({address}) отличается от шаблон: {val_other} ({address})" + '\n'
            allure.attach(compare_text, name=f"Отличия", extension=AttachmentType.TEXT)

        except FileNotFoundError:
            print(f"Ошибка: один из файлов не найден по пути {file1_path} или {file2_path}")
        except Exception as e:
            print(f"Произошла непредвиденная ошибка: {e}")
        assert compare_text == '', f"Файл {file1_path} не совпадает с образцом {file2_path}"

    def replace_all_in_file(self, replacements: dict, file_name: str, encoding: str = None, new_file_name: str = None):
        datadir = self.datadir
        if encoding is None:
            encoding = 'windows-1251'

        with open(str(datadir / file_name), 'r', encoding=encoding) as f:
            content = f.read()

        for pattern, repl in replacements.items():
            content = re.sub(pattern, repl, content, flags=re.M)

        if new_file_name is not None:
            file_name = new_file_name

        with open(str(datadir / file_name), 'w', encoding=encoding) as f:
            f.write(content)
