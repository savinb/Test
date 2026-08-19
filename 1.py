import os
from pathlib import Path

def check_remote_report(self, r_list: list, t_list: list, o_d: str, c_h: str):
    fileutils = self.fileutils
    datadir = Path(self.datadir)

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
                        fileutils.replace_in_file({r'source-filename="\d{8}_\w{8}_ZONE5_\d{8}_A\d{1}_FRSBR_NCZ_PART_AVANS_REESTR.xls"': 'source-filename="s-f"'}, report)
                        fileutils.replace_in_file({r'timestamp="\d{14}"': 'timestamp="timestamp"'}, report)
                        fileutils.replace_in_file({r'report-session-id="FRSBR_NCZ_EE_\d{17}"': 'report-session-id="report-session-id"'}, report)
                        fileutils.replace_in_file({r'id="FRSBR_NCZ_EE_\d{17}"': 'id="id"'}, report)

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

                    if fileutils.find_in_file('комиссии в НЦЗ (5)', report) or fileutils.find_in_file('class="FRSBR_NCZ_CFR_ITOG_REESTR_XML"', report):
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

                    if fileutils.find_in_file('электроэнергии в НЦЗ (5)', report) or fileutils.find_in_file('class="FRSBR_NCZ_CFR_REESTR_DD_XML"', report):
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
