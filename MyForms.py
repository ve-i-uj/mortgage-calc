#!/usr/bin/env python3
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. It is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

"""Две формы ввода: плательщиков и ежемесячногых платежей."""

__all__ = ['AddEditForm', 'PayerNames']

import collections
import copy
import datetime
import functools
import locale
import sys
from tkinter import *

from Calculation import Calculation, Storage
from MyWidgets import IntegerEntry
from MyDateLib import date_plus_months


def setlocal_ru(func):
    """Для установления локальных настроек компьютера на время работы функции"""
    @functools.wraps(func)
    def wrapper(*arg, **kw):
        loc = locale.getlocale()
        if sys.platform == 'win32':
            locale.setlocale(locale.LC_ALL, ('Russian_Russia', '1251'))
        else:
            locale.setlocale(locale.LC_ALL, ('RU', 'UTF8'))
        result = func(*arg, **kw)
        locale.setlocale(locale.LC_ALL, loc)
        return result
    return wrapper


class AddEditForm(Toplevel):
    """Графическая форма для введения сумм платежей.

    Так же используется для редактирования платежей
    (параметр self.reduct).
    """

    def rollback(func):
        """Откатывает экз. класса Calculation на начальное состояние."""
        @functools.wraps(func)
        def wrapper(self, *arg, **kw):
            date = self.calculation.date
            result = func(self, *arg, **kw)
            self.calculation.remove_payment(date_plus_months(
                date, 1, initdate=self.calculation.first_date))
            return result
        return wrapper


    def __init__(self, parent, names, calculation=None, reduct=False):
        """Метод инициализации"""
        super(AddEditForm, self).__init__(parent)
        self.parent = parent
        self.transient(self.parent)
        self.title("Добавить новый платеж" if not reduct else \
                   'Редактировать платеж')
        self.reduct = reduct
        self.result = {}

        self.__names = names
        self.calculation = copy.deepcopy(calculation)
        self.date = self.calculation.date

        self.debt_is_end = False

        self.message = StringVar()
        self.message_lst = {}
        self.message_lst[self.__next_date(self.date)] = [
            "" for i in self.__names
            ]
        self.data_error_message = ["" for i in ['YEAR', 'MONTH', "DAY"]]
        self.ok_button = False

        self.configure(bg='light goldenrod')


        frame1 = Frame(self, bg='light goldenrod')
        periodLabel = Label(
            frame1, text="Дата списания: ", width=23,
            anchor=CENTER, bg='light goldenrod')
        currentperiodLabel = Label(
            frame1, text=str(self.__next_date(self.date)),
            relief=SUNKEN, bg='cornsilk', width=23, justify=CENTER)
        periodLabel.grid(row=2, column=0, padx=2, pady=4, sticky=W)
        currentperiodLabel.grid(row=2, column=1, padx=0, pady=4, sticky=EW)
        frame1.grid(row=1, column=0, padx=15, pady=4, sticky=EW)

        self.frame2 = Frame(self, bg='light goldenrod')
        paymentLabel = Label(self.frame2, text="Платеж{0}".format(
            "и" if len(names) > 1 else ""), bg='goldenrod1')
        paymentLabel.grid(row=0, column=0, columnspan=999,
                          padx=2, pady=2, sticky=EW)

        # head
        Label(self.frame2, text='Пересчёт', width=15, bg='yellow').grid(
            row=1, column=0, padx=2, pady=2, sticky=W)
        for i, name in enumerate(self.__names):
            Label(self.frame2, text=name, bg='cornsilk').grid(
                row=1, column=i+1, padx=2, pady=8, sticky=EW)

        # payments row
        self.widget_rows = collections.defaultdict(list)
        self.reculcVars = collections.defaultdict(IntVar)

        date = self.__next_date(self.date)
        self.__create_new_row(date)
        messageLabel = Label(
            self.frame2, textvariable=self.message,
            relief=GROOVE, anchor=W, justify=LEFT, bg='white')
        messageLabel.grid(row=999, column=0,
                          columnspan=len(self.__names)+1, padx=2,
                          pady=8, sticky=EW)
        self.frame2.grid(row=2, column=0, padx=15, pady=4, sticky=W)

        frame3 = Frame(self, bg='light goldenrod')
        if not self.reduct:
            anotherButton = Button(frame3, text='Еще один платеж', height=1,
                                   bg='aliceblue', fg='black')
            deletePayment = Button(frame3, text='Удалить последний платеж',
                                   height=1, bg='aliceblue', fg='black')
            anotherButton.pack(padx=0, pady=2, side=LEFT)
            deletePayment.pack(padx=0, pady=2, side=LEFT)
            anotherButton.bind("<Button-1>", self.anotherPayment)
            deletePayment.bind("<Button-1>", self.deleteLastPayment)
        okButton = Button(frame3, text='Ok', height=1,
                          bg='aliceblue', fg='black')
        cancelButton = Button(frame3, text="Cancel", height=1,
                              bg="aliceblue", fg='black')
        okButton.bind("<Button-1>", self.ok)
        cancelButton.bind("<Button-1>", self.cancel)
        okButton.pack(padx=0, pady=2, side=RIGHT)
        cancelButton.pack(padx=0, pady=2, side=RIGHT)
        frame3.grid(row=3, column=0, padx=15, pady=4,
                    sticky=E if self.reduct else EW)

        self.bind("<Control-q>", self.close)
        self.bind("<Escape>", self.close)
        self.bind("<Return>", self.ok)

        self.protocol("WM_DELETE_WINDOW", self.close)

        self.focus_set()
        while True:
            try:
                self.grab_set()
            except TclError:
                pass
            else:
                break
        self.wait_window()


    def anotherPayment(self, *ign):
        """Метод для создания еще одного поля для ввода платежа"""
        if len(self.widget_rows) == 12:
            self.message_lst[datetime.date(2100, 1, 1)] = [
                'Вводить платежи за один раз можно только за 12 месяцев'
                ]
            self.__update_message()
            return
        date = self.__next_date(max(self.widget_rows))
        self.__create_new_row(date)

        self.message_lst[date] = ["" for i in range(len(self.__names) + 1)]


    def cancel(self, *ignore):
        """Метод для закрытия формы"""
        self.close()


    @rollback
    def check(self):
        """Проверяет вхождение платежа в имеющиеся границы.

        Метод проверяет, чтобы введенный платеж был не меньше
        аннуитетного ежемесячного платежа и не больше суммы долга.
        Проверяет каждый платеж в отдельности. Если какой-то не верный -
        дальше не считает. И в любом случае всегда откатывает
        self.calculation  на начальное состояние после проверки.
        """

        def error(annuity, date):
            """Сообщение об ошибке"""
            messagebox.showinfo(
                'Невозможное значение',
                'Месяц: {1}. Платеж меньше возможного ({0})'.format(
                    annuity, date.strftime('%B')))

        if [(k, v) for k, v in self.message_lst.items() if not \
            (''.join(v) == '' or k >= datetime.date(2100, 1, 1))]:
            messagebox.showinfo(
                'Введены неприавильные значения!',
                'Необходимо исправить указанные недочёты.',
                parent=self)
            self.__update_message()
            return False
        # проверяет каждый платеж в отдельности.
        # если какой-то не верный - дальше считать нет смысла.
        # и в любом случае всегда откатывает self.calculation
        # на начальное состояние после проверки
        self.debt_is_end = False
        for date, widgets_row in sorted(self.widget_rows.items()):
            annuity = self.calculation.actualy_annuity
            payments = [float(widget.get()) for widget in widgets_row[1:]]
            if sum(payments) < annuity:
                last_date = date_plus_months(
                    date, -1, initdate=self.calculation.first_date)
                # если это первый платеж - нет остатка в прошлом месяце
                if last_date == self.calculation.first_date:
                    error(annuity, date)
                    return False
                # проверяем есть ли остаток в прошлом месяце
                info = self.calculation.data[last_date]
                if info.the_rest > 0:
                    if info.the_rest >= annuity:
                        replay = messagebox.askyesno(
                            '{}. Оплата из остатка'.format(date.strftime('%B')),
                            ('В прошлом месяце ({2}) остаток денег на '
                             'вашем счёте составил: {0}.\n'
                             'Это позволит в этом месяце '
                             'не вносить платеж ({1}), а недостающую сумму'
                             'вычесть из остатка. \n\nВычетаем?').format(
                                 info.the_rest, annuity,
                                 last_date.strftime('%B')),
                            parent=self)
                        if not replay:
                            error(annuity, date)
                            return False
                    else:
                        # если платеж + остаток > ежемесячного
                        if sum(payments) + info.the_rest >= annuity:
                            replay = messagebox.askyesno(
                                '{}. Оплата из остатка'.format(
                                    date.strftime('%B')),
                                ('В прошлом месяце ({2}) остаток денег на '
                                 'вашем счёте составил: {0}.\n'
                                 'Это позволит в этом месяце внести денег '
                                 'меньше ежемесячного платежа ({1}), '
                                 'а недостающую часть вычесть из остатка. \n\n'
                                 'Вычетаем?').format(
                                     info.the_rest, annuity,
                                     last_date.strftime('%B')),
                                parent=self)
                            if not replay:
                                error(annuity, date)
                                return False
                        else:
                            messagebox.showinfo(
                                'Невозможное значение',
                                ('Месяц: {1}. Платеж меньше ежемесячного ({0})'
                                 '\n.С учетом остатка на счету в прошлом '
                                 'месяце, платеж в этом месяце должен быть'
                                 'не менее {2}').format(
                                     annuity, date.strftime('%B'),
                                     annuity - info.the_rest),
                                parent=self)
                            return False
                else:
                    error(annuity, date)
                    return False

            # считаем calc с учётом нового платежа
            self.calculation.new_payment(
                {date: Storage(
                    payment=payments, recalc=bool(
                        int(self.reculcVars[date].get())))}
                )
            # задолженность до платежа
            last_date = date_plus_months(
                date, -1, initdate=self.calculation.first_date)
            loan = self.calculation.data[last_date].loan_sum if \
                   last_date != self.calculation.first_date else \
                   self.calculation.first_loan_sum
            # плата банку за пользование
            bank_interest = self.calculation.data[date].bank_interest
            # остаток в прошлом месяце
            the_rest = self.calculation.data[last_date].the_rest if \
                       last_date != self.calculation.first_date else 0
            if sum(payments) + the_rest > loan + bank_interest:
                messagebox.showinfo(
                    'Невозможное значение',
                    ('Месяц: {1}. \nПлатеж {2}больше'
                     ' оставшейся задолженности: {0}').format(
                         round(loan + bank_interest, 2), date.strftime('%B'),
                         '' if the_rest == 0 else \
                         '(вместе с остатком за прошлый месяц) '),
                    parent=self)
                return False
            # сравниваю целые числа, т.к. аннуитетный платеж не считает
            # настолько маленькие числа (1 рубль на 10 лет)
            if int(sum(payments)) == int(loan + bank_interest):
                messagebox.showinfo(
                    'Кредит закрыт',
                    ('Месяц: {0}. \nВ этом месяце кредит закрыт.\n'
                     'Поздравляем =).').format(date.strftime('%B')),
                    parent=self)
                self.debt_is_end = True
                # долг закрыт, удаляем все нижние строки
                for i in (date_ for date_ in self.widget_rows.keys() \
                          if date_ > date):
                    self.deleteLastPayment()
                return True
        return True


    def check_weekend(self, date):
        """Предупреждает о попадании даты следующего платежа на выходные."""
        if date.isoweekday() in {6, 7}:
            messagebox.showwarning(
                "ВНИМАНИЕ!",
                ("Следующая дата списания {1} выпадает на выходной ({0}).\n\n"
                 "Возможно стоит пополнить счет зарание.").format(
                     'Субботу' if date.isoweekday() == 6 else 'Воскресенье',
                     date.isoformat()),
                parent=self)


    def close(self, event=None):
        """Закрывает форму."""
        self.parent.focus_set()
        self.destroy()


    def deleteLastPayment(self, *ign):
        """Удаляет последнюю строку ввода для платежа"""
        if len(self.widget_rows) == 1:
            return
        max_date, widgets_row = max(self.widget_rows.items())
        for wiget in widgets_row:
            wiget.grid_forget()
        del self.reculcVars[max_date]
        del self.widget_rows[max_date]


    def ok(self, *ignore):
        """Запоминает результаты ввода платежей."""
        if not self.check():
            return
        for date, widgets_row in self.widget_rows.items():
            payments = tuple([float(i.get()) for i in widgets_row[1:]])
            self.result[date] = Storage(
                payment=payments, recalc=bool(int(self.reculcVars[date].get())))
        if not self.reduct and not self.debt_is_end:
            self.check_weekend(self.__next_date(max(self.result)))
        self.close()


    def payment_control(self, i, date, *ignore):
        """Проверяет корректность введеного платежа."""

        payment = self.widget_rows[date][i].get()
        if payment == "":
            self.widget_rows[date][i]['bg'] = "pink"
            self.message_lst[date][i-1] = (
                "Месяц {0}, Столбец {1}: "
                "Поле платежа не должно быть пустым.").format(
                    date.strftime('%B'), i)
            self.__update_message()
        else:
            try:
                float(payment)
            except ValueError:
                for j, char in enumerate(payment):
                    try:
                        int(char)
                    except ValueError:
                        self.message_lst[date][i-1] = (
                            "Месяц {2}, Столбец {1}: "
                            "Ошибка в {0} символе "
                            "(должны быть только цифры)").format(
                                j+1, i, date.strftime('%B'))
                        self.__update_message()
                        self.widget_rows[date][i]['bg'] = "pink"
                        break
            else:
                self.widget_rows[date][i]['bg'] = 'aliceblue'
                self.message_lst[date][i-1] = ""
                self.__update_message()
        if [(k, v) for k, v in self.message_lst.items() \
            if not (''.join(v) == '' or k >= datetime.date(2100, 1, 1))]:
            self.message_lst[datetime.date(2200, 1, 1)] = [""]


    @setlocal_ru
    def __create_new_row(self, date):
        """Создает в форме еще одну строку ввода"""
        row = 2 + len(self.widget_rows)
        reculcCheck = Checkbutton(self.frame2, text=str(date.strftime('%B')),
                                  variable=self.reculcVars[date],
                                  onvalue=1, offvalue=0, bg='yellow2')
        reculcCheck.grid(row=row, column=0, padx=2, pady=8, sticky=EW)
        self.widget_rows[date].append(reculcCheck)
        for i, payer in enumerate(self.__names, start=1):
            paymentEntry = Entry(self.frame2, relief=RIDGE)
            paymentEntry.insert(0, 0)
            paymentEntry.bind("<Any-KeyRelease>",
                              functools.partial(self.payment_control, i, date))
            paymentEntry.grid(row=row, column=i, padx=2, pady=8, sticky=EW)
            self.widget_rows[date].append(paymentEntry)
        self.widget_rows[date][0].focus_set()


    def __update_message(self):
        """Обновляет поле вывода ошибок"""
        messages = []
        for month in sorted(self.message_lst):
            strings = "\n".join([i for i in self.message_lst[month] if i != ''])
            if strings.strip() != '':
                messages.append(strings)
        self.message.set('\n'.join(messages).strip())


    def __next_date(self, date):
        """Прибавляет к дате один месяц"""
        return date_plus_months(date, 1, initdate=self.calculation.first_date)


class PayerNames(Toplevel):
    """Класс-форма для получения имен плательщиков."""

    def __init__(self, parent, count, loan_sum):
        """Форма ввода имен плательщиков и сумм их займов."""
        super(PayerNames, self).__init__(parent)
        self.parent = parent
        self.transient(self.parent)
        self.title("Имена плательщиков")
        self.config(bg='light goldenrod')

        self.count = count
        self.loan_sum = loan_sum
        self.__names = []
        self.__loans = []
        self.block = False

        self.varNames = []
        self.varLoans = []
        for i in range(self.count):
            self.varNames.append(StringVar())
            self.varLoans.append(StringVar())

        frame = Frame(self, bg='light goldenrod')
        headerLabel = Label(
            frame, text='Введите {0}{1}'.format(
                'имена плательщиков' if self.count > 1 else 'имя плательщика',
                ' и сумму долга\n для каждого плательщика' if \
                self.count > 1 else ''),
            bg='light goldenrod')
        headerLabel.grid(row=0, column=0, columnspan=4,
                         padx=2, pady=10, sticky=EW)

        for i, (text, width) in enumerate(zip(('Имя', 'Сумма'), (14, 8))):
            Label(frame, text=text, width=width, bg='goldenrod1').grid(
                row=1, column=1+i, padx=2, pady=2, sticky=EW)

        self.groupEntries = []
        for i in range(self.count):
            label = Label(frame, text="Плательщик № {0}:".format(i+1),
                          bg='light goldenrod')
            label.grid(row=i+2, column=0, padx=2, pady=2, sticky=W)
            nameEntry = Entry(frame, relief=RIDGE,
                              textvariable=self.varNames[i], justify=CENTER)
            nameEntry.grid(row=2+i, column=1, padx=2, pady=2, sticky=EW)
            loanEntry = IntegerEntry(frame, to=self.loan_sum,
                                     relief=RIDGE, justify=CENTER,
                                     textvariable=self.varLoans[i])
            self.varLoans[i].set(int(loan_sum/self.count))
            loanEntry.grid(row=2+i, column=2, padx=2, pady=2, sticky=EW)
            self.varLoans[i].trace('w', functools.partial(self._change_loan, i))
            self.groupEntries.append(loanEntry)

        Label(frame,
              text=('Сумма займов для всех плательщиков'
                    'должна быть равна: {0}').format(self.loan_sum),
              bg='pink',
              justify=CENTER).grid(row=i+2+1, column=0, columnspan=10, pady=20)

        self.groupEntries[0].focus_set()

        frame.grid(row=0, column=0, padx=15, pady=2, sticky=NSEW)

        button_frame = Frame(self, bg='light goldenrod')
        okButton = Button(button_frame, text='Ok',
                          bg='aliceblue', fg='black')
        cancelButton = Button(button_frame, text="Cancel",
                              bg="aliceblue", fg='black')
        okButton.bind("<Button-1>", self.ok)
        cancelButton.bind("<Button-1>", self.cancel)
        okButton.grid(row=0, column=2, padx=2, pady=2, sticky=EW)
        cancelButton.grid(row=0, column=3, padx=2, pady=2, sticky=EW)
        button_frame.grid(row=3, column=0, padx=15, pady=4, sticky=E)

        list(frame.grid_slaves(row=2, column=1))[0].focus_set()

        frame.columnconfigure(1, weight=1)
        window = self.winfo_toplevel()
        window.columnconfigure(0, weight=1)

        self.bind("<Control-q>", self.close)
        self.bind("<Escape>", self.close)
        self.bind("<Return>", self.ok)

        self.protocol("WM_DELETE_WINDOW", self.close)

        self.focus_set()
        while True:
            try:
                self.grab_set()
            except TclError:
                pass
            else:
                break
        self.wait_window()


    @property
    def loans(self):
        """Свойство для получения задолженности каждого из плательщиков"""
        return tuple(self.__loans)


    @property
    def names(self):
        """Свойство для получения имён плательщиков"""
        return tuple(self.__names)


    def cancel(self, *ignore):
        """Закрывает форму"""
        self.close()


    def close(self, event=None):
        """Закрывает форму"""
        self.parent.focus_set()
        self.destroy()


    def ok(self, *ignore):
        """Записывает в атрибуты экземпляра имена и задолженности"""
        for i, var in enumerate(self.varLoans):
            if var.get() == '':
                messagebox.showinfo(
                    'Внимание!',
                    ('Поле "Сумма" Плательщика № {0} '
                     'не должно быть пустым.').format(i+1),
                    parent=self)
                return
        total_loan = sum(
            int(var.get()) for var in self.varLoans if var.get() != '')
        if not total_loan == self.loan_sum:
            messagebox.showinfo(
                'Внимание!', ('Сумма кредитов сейчас: {1}\n\n'
                              'А должна быть: {0}   ').format(
                                  self.loan_sum, total_loan),
                parent=self)
            return
        payer_names = [var_name.get() for var_name in self.varNames]
        if not all(payer_names):
            reply = messagebox.askyesno(
                "Пустое имя", "Чьё-то имя осталось пустым.\n\nВы уверены?",
                parent=self)
            if reply:
                temp_lst = []
                for i, name in enumerate(payer_names, start=1):
                    if name == "":
                        name = 'Плательщик №{0}'.format(i)
                    temp_lst.append(name)
                payer_names = temp_lst
            else:
                return
        s = 'Имена плательщиков:' if self.count > 1 else 'Имя плательщика'
        reply = messagebox.askyesno(
            "{s}".format(s=s),
            "{s}:\n\n{0}".format("\n".join(payer_names), s=s),
            parent=self)
        if reply:
            self.__names.extend(payer_names)
            self.__loans.extend([int(var.get()) for var in self.varLoans])
            self.close()


    def _change_loan(self, i, *ign):
        """Автоматически пересчитывает задолженность плательщиков в ниже."""
        if self.block:
            return
        try:
            next_ = i + 1
            if not next_ == self.count:
                value = int(
                    (self.loan_sum - sum(int(var.get()) for var in \
                                         self.varLoans[:i+1] if \
                                         var.get() != ''))/(self.count - (i+1)))
                self.block = True
                for var in self.varLoans[next_:]:
                    if value >= 0:
                        var.set(value)
        except ValueError:
            pass
        finally:
            self.block = False
