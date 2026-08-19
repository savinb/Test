    def check_remote_report(self, r_list: list, t_list: list, o_d: str, c_h: str):
        fileutils = self.fileutils
        datadir = self.datadir
        with (allure.step(f'Проверка отчётов в каталоге выгрузки {o_d}')):
            for i in range(1, r_list.__len__()):
                with allure.step('Проверка отчёта ' + r_list[i]):
                    fileutils.download_report_from_server(r_list[i], o_d, c_h)
                    if 'BRS_' in r_list[i]:
                        with open(os.path.join(datadir, r_list[1]), 'r', encoding='windows-1251') as file:
                            lines = file.readlines()
                            first_10 = lines[:10]
                            last_line = lines[-1:] if lines else []
                            result_lines = first_10 + last_line
                            with open(os.path.join(datadir, r_list[1]), 'w', encoding='windows-1251') as file:
                                file.writelines(result_lines)
                    if 'FRSBR_MTNCZ_GTPP_5' in r_list[i]:
                        with open(os.path.join(datadir, r_list[1]), 'r', encoding='windows-1251') as file:
                            lines = file.readlines()
                            first_10 = lines[:10]
                            last_line = lines[-50:] if lines else []
                            result_lines = first_10 + last_line
                            with open(os.path.join(datadir, r_list[1]), 'w', encoding='windows-1251') as file:
                                file.writelines(result_lines)
                    if r_list[i].find('xls') > 0:
                        if r_list[i].find('_BR_BAN_') > 0:
                            fileutils.xls_compare(r_list[i], t_list[i - 1], skip_columns=['C'], skip_order=True)
                        elif r_list[i].find('_FRSBR_BANKRUPT_POVER_REPORT') > 0:
                            fileutils.xls_compare(r_list[i], t_list[i - 1], skip_columns=['E'],skip_cells=['A9'] ,skip_order=True)
                        else:
                            try:
                                fileutils.xls_compare(r_list[i], t_list[i - 1], skip_order=True)
                            except:
                                self.compare_excel_files(datadir / r_list[i], datadir / t_list[i - 1])

                    if r_list[i].find('xml') > 0:
                        # Общие
                        fileutils.replace_in_file({r'source="\d{8}_ZONE5_\d{8}_A\d{1}_FRSBR_NCZ_CFR_AVANS_\w{4,5}_XLS.xls"': 'source="source"'}, r_list[i])
                        # fileutils.replace_in_file({r'<subject>\d{8}_ZONE5_\d{8}_A\d{1}_FRSBR_NCZ_CFR_AVANS_\w{4,5}_XLS.xls': '<subject>subject'}, r_list[i])
                        fileutils.replace_in_file({r'<subject>\d{8}_ZONE5_\d{8}_A\d{1}_FRSBR_NCZ_CFR_AVANS_\w{4,5}_XLS': '<subject>subject'}, r_list[i])
                        fileutils.replace_in_file({r'created-date="\d{14}"': 'created="YYYYMMDDhhmmss"'}, r_list[i])
                        fileutils.replace_in_file({r'guid="\{.*\}"': 'guid = "guid"' }, r_list[i])

                        # 1.5. Участнику: Реестр обязательств/требований по авансовым платежам по ДКП/КМ НЦЗ
                        if fileutils.find_in_file('type="FRSBR_NCZ_PART_AVANS_REESTR"',r_list[i]) != '':
                            fileutils.replace_in_file({r'source-filename="\d{8}_\w{8}_ZONE5_\d{8}_A\d{1}_FRSBR_NCZ_PART_AVANS_REESTR.xls"': 'source-filename="s-f"'}, r_list[i])
                            fileutils.replace_in_file({r'timestamp="\d{14}"': 'timestamp="timestamp"'}, r_list[i])
                            fileutils.replace_in_file({r'report-session-id="FRSBR_NCZ_EE_\d{17}"': 'report-session-id="report-session-id"'}, r_list[i])
                            fileutils.replace_in_file({r'id="FRSBR_NCZ_EE_\d{17}"': 'id="id"'}, r_list[i])
                        # 9.XX
                        str9XX = ['_PART_MAIL"', '_BANKRUPT"', 'REESTR_DOG"', 'POVER_REPORT"', 'REESTR_OBYAZ_CFR"', 'REESTR_TREB_CFR"']
                        for j in range(0, str9XX.__len__()):
                            if fileutils.find_in_file(str9XX[j], r_list[i]):
                                fileutils.replace_in_file({r'source-filename=".*.xl.*"': 'source-filename="s-f"'}, r_list[i])
                                fileutils.replace_in_file({r'source=".*.xl.*"': 'source="s-f"'}, r_list[i])
                                fileutils.replace_in_file({r'timestamp="\d{14}"': 'timestamp="timestamp"'}, r_list[i])
                                fileutils.replace_in_file({r'report-session-id="\d{1,4}"': 'report-session-id="report-session-id"'}, r_list[i])
                                fileutils.replace_in_file({r'id=.*': 'id="id"'}, r_list[i])
                                fileutils.replace_in_file({r'<subject>.*': '<subject>subject</subject>'}, r_list[i])
                        # ЦФР | XML: Реестр в ЦФР для банкротов
                        if fileutils.find_in_file('Обязательства на БР за период', r_list[i]) or fileutils.find_in_file('Реестр обязательств по договорам купли-продажи', r_list[i]) or fileutils.find_in_file('Обязательства на БР ДВ за период', r_list[i]):
                            fileutils.replace_in_file({r'<package id=".{32}"': '<package id="id"'}, r_list[i])
                            fileutils.replace_in_file({r'package-date="\d{8}"': 'package-date="YYYYMMDD"'}, r_list[i])
                            fileutils.replace_in_file({r'contract-number="BR-.*" ': 'contract-number="contract-number" '}, r_list[i])
                            fileutils.replace_in_file({r'contract-date="\d{8}"': 'contract-date="YYYYMMDD"'}, r_list[i])
                            fileutils.replace_in_file({r'fss-id="BRSB\d{5}"': 'fss-id="BRSB-id"'}, r_list[i])
                        # ЦФР | XML: Реестр в ЦФР
                        if fileutils.find_in_file('признанных банкротами', r_list[i]) != '' or 'BRS_' in r_list[i]:
                            fileutils.replace_in_file({r'contract-date="\d{8}"': 'contract-date="YYYYMMDD"'}, r_list[i])
                            fileutils.replace_in_file({r'fss-id="BRS.{6}"': 'fss-id="BRSXXXXXX"'}, r_list[i])
                            fileutils.replace_in_file({r'<subject>.*': '<subject>subject</subject>'}, r_list[i])
                            fileutils.replace_in_file({r'source=".*.xml"': 'source="s-f"'}, r_list[i])
                        # XML в ЦФР: авансовые реестры по ДКП/КМ в НЦЗ
                        if fileutils.find_in_file('class="FRSBR_NCZ_CFR_AVANS_REESTR_XML"', r_list[i]) != '':
                            fileutils.replace_in_file({r'source="BRNCZ_ZONE5_AVANS\d{1}_\d{8}_\d{8}_\d{1,3}.xml"': 'source="source"'}, r_list[i])
                            # fileutils.replace_in_file({r'<subject>BRNCZ_ZONE5_AVANS\d{1}_\d{8}_\d{8}_\d{1,3}.xml': '<subject>subject'}, r_list[i])
                            fileutils.replace_in_file({r'<subject>BRNCZ_ZONE5_AVANS\d{1}_\d{8}_\d{8}_\d{1,3}': '<subject>subject'}, r_list[i])
                        if fileutils.find_in_file('Реестр обязательств/требований по авансовым платежам по договорам купли-продажи', r_list[i]) != '':
                            fileutils.replace_in_file({r'^  id=.*': '  id="id"'}, r_list[i])
                            fileutils.replace_in_file({r'^  package-date=               "\d{8}"': '  package-date=               "YYYYMMDD"'}, r_list[i])
                        # 5.04 | Приложение 1 к финансовому отчету 202501_AEMZENER_E_20260402_FRSBR_PRIL_FINO.info.xml
                        if fileutils.find_in_file('FRSBR_PRIL_FINO', r_list[i]) != '':
                            fileutils.replace_in_file({r'id="[^"]*_FRSBR_PRIL_FINO"': 'id="id"'}, r_list[i])
                            fileutils.replace_in_file({r'source-filename="[A-Z0-9_]*_FRSBR_PRIL_FINO\.xls"': 'source-filename="source-filename"'}, r_list[i])
                            fileutils.replace_in_file({r'timestamp="\d{14}"': 'timestamp="timestamp"'}, r_list[i])
                            fileutils.replace_in_file({r'report-session-id="\d{1,4}"': 'report-session-id="report-session-id"'}, r_list[i])
                        # Участникам | XML (по узлам, ГТП, РГЕ)'
                        if fileutils.find_in_file('class="FOREM"', r_list[i]) != '':
                            fileutils.replace_in_file({r'id="[^"]*"': 'id="32s"'}, r_list[i])
                            fileutils.replace_in_file({r'local-id="[^"]*"': 'local-id="NNNN"'}, r_list[i])
                            fileutils.replace_in_file({r'created="\d{8}"': 'created="YYYYMMDD"'}, r_list[i])
                        # Отчёт XML-отчет для систем ОРЦТ
                        if fileutils.find_in_file('class="FRSBR_ORCT_MONTH_FACT"', r_list[i]) != '':
                            fileutils.replace_in_file({r'created="\d{14}"': 'created="YYYYMMDDHHmmss"'}, r_list[i])
                            fileutils.replace_in_file({r'p-version-id="\d{1,3}"': 'p-version-id="ID"'}, r_list[i])
                            fileutils.replace_in_file({r'ver-rio="\d{1,6}"': 'ver-rio="vRIO"'}, r_list[i])
                            fileutils.replace_in_file({r'p-calc-db-name="[^"]*"': 'p-calc-db-name="p-calc-db-name="'}, r_list[i])
                        # Участникам | Формирование договоров с банкротами (DOC)
                        if fileutils.find_in_file('class="ASUD_PART_BR_BANKRUPT"', r_list[i]) or fileutils.find_in_file('class="FRSBR_CFR_REESTR_OBYAZ_BANKRUPT"', r_list[i])!= '':
                            fileutils.replace_in_file({r'  id="[^"]*"': '  id="32s"'}, r_list[i])
                            fileutils.replace_in_file({r'  source-filename="[^"]*"': '  source-filename="source-filename"'}, r_list[i])
                            fileutils.replace_in_file({r'source=".*.xml"': 'source="s-f"'}, r_list[i])
                            fileutils.replace_in_file({r'  timestamp="[^"]*"': '  timestamp="14d"'}, r_list[i])
                            fileutils.replace_in_file({r'  report-session-id="[^"]*"': '  report-session-id="report-session-id"'}, r_list[i])
                        # Отчет поверенного по договорам с банкротами
                        if fileutils.find_in_file('class="FRSBR_PART_DOG_BANKRUPT_POVER_REPORT"', r_list[i]):
                            fileutils.replace_in_file({r'date-from="\d{8}"': 'date-from="YYYYMMDD"'}, r_list[i])
                            fileutils.replace_in_file({r'date-to="\d{8}"': 'date-to="YYYYMMDD"'}, r_list[i])
                        # 11.01 | Отчет по цене ДДПР
                        if fileutils.find_in_file('class="FRSBR_PRICE_DDPR"', r_list[i])!= '':
                            fileutils.replace_in_file({r'  id="[^"]*"': '  id="32s"'}, r_list[i])
                            fileutils.replace_in_file({r'  source-filename="[^"]*"': '  source-filename="source-filename"'}, r_list[i])
                            fileutils.replace_in_file({r'source=".*.xml"': 'source="s-f"'}, r_list[i])
                            fileutils.replace_in_file({r'  timestamp="[^"]*"': '  timestamp="14d"'}, r_list[i])
                            fileutils.replace_in_file({r'  report-session-id="[^"]*"': '  report-session-id="report-session-id"'}, r_list[i])
                        # 4.10 Участнику: Итоговый реестр обязательств/требований по ДПМ/КМ НЦЗ
                        # 4.11 Реестры в ЦФР: Итоговый реестр по ДКП в НЦЗ
                        if fileutils.find_in_file('class="FRSBR_NCZ_PART_ITOG_REESTR"', r_list[i]) != '' or fileutils.find_in_file('NCZ_CFR_ITOG', r_list[i])!= '':
                            fileutils.replace_in_file({r'  id="[^"]*"': '  id="32s"'}, r_list[i])
                            fileutils.replace_in_file({r'  source-filename="[^"]*"': '  source-filename="source-filename"'}, r_list[i])
                            fileutils.replace_in_file({r'source=".*.xls"': 'source="s-f"'}, r_list[i])
                            fileutils.replace_in_file({r'timestamp="\d{14}"': 'timestamp="timestamp"'}, r_list[i])
                            fileutils.replace_in_file({r'report-session-id="FRSBR_NCZ_EE_\d{17}"': 'report-session-id="report-session-id"'}, r_list[i])
                            fileutils.replace_in_file({r'  report-session-id="[^"]*"': '  report-session-id="report-session-id"'}, r_list[i])
                            fileutils.replace_in_file({r'<subject>\d{8}_ZONE5_\d{8}_FRSBR_NCZ_CFR_ITOG_\w{4,5}_XLS.xls': '<subject>subject'}, r_list[i])
                        # 4.xml01 Реестры в ЦФР: Итоговый реестр по ДКП/КМ в НЦЗ
                        if fileutils.find_in_file('комиссии в НЦЗ \(5\)', r_list[i]) != '' or fileutils.find_in_file('class="FRSBR_NCZ_CFR_ITOG_REESTR_XML"', r_list[i]) != '':
                            fileutils.replace_in_file({r'<package id=".{32}"': '<package id="id"'}, r_list[i])
                            fileutils.replace_in_file({r'package-date="\d{8}"': 'package-date="YYYYMMDD"'}, r_list[i])
                            fileutils.replace_in_file({r'source=".*.xm.*"': 'source="s-f"'}, r_list[i])
                            fileutils.replace_in_file({r'<subject>\w{5}_ZONE5_ITOG_\d{8}_\d{8}_\d{2,4}.xml': '<subject>subject'}, r_list[i])
                            fileutils.replace_in_file({r'fss-id="[^"]*"': 'fss-id="fss-id"'}, r_list[i])
                        # 4.xml02 Данные для МТ НЦЗ
                        if fileutils.find_in_file('class="FRSBR_MTNCZ"', r_list[i]) != '':
                            fileutils.replace_in_file({r'created="\d{14}"': 'created="YYYYMMDDhhmmss"'}, r_list[i])
                            fileutils.replace_in_file({r'num="\d{1,4}"': 'num="NNNN"'}, r_list[i])
                            fileutils.replace_in_file({r'version-id="\d{1,4}"': 'version-id="version-id"'}, r_list[i])
                            fileutils.replace_in_file({r'calc-version="\d{1,4}"': 'calc-version="calc-version"'}, r_list[i])
                            fileutils.replace_in_file({r'calc-db-name="[^"]*"': 'calc-db-name="calc-db-name"'}, r_list[i])
                            fileutils.replace_in_file({r'stand-name="[^"]*"': 'stand-name="stand-name"'}, r_list[i])
                            fileutils.replace_in_file({r'ver-rio="[^"]*"': 'ver-rio="ver-rio"'}, r_list[i])
                        # 4.xml03 Данные для ОРЦТ
                        if fileutils.find_in_file('class="FRSBR_ORCT_NCZ_MONTH_FACT"', r_list[i]) != '':
                            fileutils.replace_in_file({r'ver-rio="\d{1,6}"': 'ver-rio="ver-rio"'}, r_list[i])
                            fileutils.replace_in_file({r'p-version-id="\d{1,4}"': 'p-version-id="p-version-id"'}, r_list[i])
                            fileutils.replace_in_file({r'p-calc-db-name="[^"]*"': 'p-calc-db-name="p-calc-db-name" '}, r_list[i])
                            fileutils.replace_in_file({r'p-calc-schema="[^"]*"': 'p-calc-schema="p-calc-schema"'}, r_list[i])
                            fileutils.replace_in_file({r'created="\d{14}"': 'created="YYYYMMDDhhmmss"'}, r_list[i])
                        # 4.xml03 Данные для ОРЦТ
                        if fileutils.find_in_file('электроэнергии в НЦЗ \(5\)', r_list[i]) != '' or fileutils.find_in_file('class="FRSBR_NCZ_CFR_REESTR_DD_XML"', r_list[i]) != '':
                            fileutils.replace_in_file({r'<package id=".{32}"': '<package id="id"'}, r_list[i])
                            fileutils.replace_in_file({r'package-date="\d{8}"': 'package-date="YYYYMMDD"'}, r_list[i])
                            fileutils.replace_in_file({r'source=".*.xm.*"': 'source="s-f"'}, r_list[i])
                            fileutils.replace_in_file({r'<subject>.*': '<subject>subject</subject>'}, r_list[i])
                        # 5.5 Участнику: Отчет о стоимости покупки электроэнергии в объемах по двусторонним договорам
                        if fileutils.find_in_file('UPZ_dd_buy', r_list[i]) != '' or fileutils.find_in_file('UPZ_dd_sell', r_list[i]) != '':
                            fileutils.replace_in_file({r'id="[^"]*"': 'id="id"'}, r_list[i])
                            fileutils.replace_in_file({r'source-filename="[^"]*"': 'source-filename="source-filename"'}, r_list[i])
                            fileutils.replace_in_file({r'timestamp="[^"]*"': 'timestamp="timestamp"'}, r_list[i])
                        # 7.xml01 Отчет (месяц) по величинам для расчета коэффициента снижения
                        if r_list[i].find('param_for_koef_snizh_month.xml') > 0:
                            fileutils.replace_in_file({r'stand-name=".*"': 'stand-name="stand-name"'}, r_list[i])
                        # 6.xml01 Отчет (год 2025) по величинам для расчета коэффициента снижения
                        if r_list[i].find('param_for_koef_snizh_year.xml') or r_list[i].find('param_for_koef_snizh_month.xml')> 0:
                            fileutils.replace_in_file({r'stand-name=".*"': 'stand-name="stand-name"'}, r_list[i])
                            fileutils.replace_in_file({r'calc-type="[^"]*"': 'calc-type="calc-type"'}, r_list[i])
                            fileutils.replace_in_file({r'calc-id="[^"]*"': 'calc-id="calc-id"'}, r_list[i])
                            fileutils.replace_in_file({r'stand-name="[^"]*"': 'stand-name="stand-name"'}, r_list[i])
                            fileutils.replace_in_file({r'stand-name="[^"]*"': 'stand-name="stand-name"'}, r_list[i])

                        fileutils.xml_compare(r_list[i], t_list[i - 1], skip_order=True)

            with (allure.step('Проверка формирования по БД:')):
                # SQL = (f"SELECT * FROM frsbr3.frs_event_detail_log "
                #        f"where event_id=(SELECT max(event_id) FROM frsbr3.frs_event_detail_log) and type_id = 'INFO'")
                SQL = (f"SELECT * FROM frsbr3.frs_event_detail_log "
                       f"where event_id=(SELECT max(event_id) FROM frsbr3.frs_event_detail_log)")
                log_text = self.dbutils.run_sql(SQL)
                a = ''
                for k in range(1, log_text.__len__()):
                    a += log_text[k][5]
                with (allure.step(f'{a}')):
                    return log_text