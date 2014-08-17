#!/usr/bin/env python3
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. It is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

"""Расчёт платежей по ипотечному кредиту и хранение ипотечной истории."""

__all__ = ['Calculation', 'Storage']

import datetime
import calendar
from MyDateLib import date_plus_months, correct_date, months, days_in_year


class Storage:
    """Класс, экземпляры которого содержат информацию о платеже."""

    __slots__ = ('payment', 'recalc', 'loan_sum',
                 'loan_payment', 'bank_interest', 'annuity',
                 'period', 'the_rest', 'overpayment', 'profit_bp')

    def __init__(self, payment, recalc, loan_sum=None, loan_payment=None,
                 bank_interest=None, annuity=None, period=None, the_rest=None,
                 overpayment=None, profit_bp=None):
        self.payment = payment # кортеж с платежами каждого плательщика
        self.recalc = recalc
        self.loan_sum = loan_sum # сумма долга на данный момент
        self.loan_payment = loan_payment
        self.bank_interest = bank_interest
        self.annuity = annuity
        self.period = period
        self.the_rest = the_rest
        self.overpayment = overpayment
        self.profit_bp = profit_bp # экономия относительно банковского периода


    def __str__(self):
        """Для печати тестовых значений"""
        return ("  ".join([str(i) for i in (self.loan_payment, \
                                            self.bank_interest, self.annuity,
                                            self.recalc, self.loan_sum)]) + \
                "\n" + "  ".join([str(i) for i in (self.overpayment,
                                                   self.profit_bp,
                                                   self.period)]))


class Calculation:
    """Класс делает расчёт платежей, экономии и т.д.

    Класс обрабатывает три основных случая: новый платеж, редактирование,
    расчет запланированного периода/платежа.
    """

    def __init__(self, first_date, loan_sum, percent, period):
        """Ипотечная история: начальные данные, платежы, переплаты и т.д."""
        self.first_date = first_date
        self.date = first_date
        self.loan_sum = loan_sum
        self.first_loan_sum = loan_sum
        self.percent = percent / 100
        self.first_period = period
        self.period = period
        self.data = {}
        self.first_annuity = self.annuity_payment()
        self.actualy_annuity = self.first_annuity


    def advanced_repayment_date(self, payment):
        """Ежемесячный платёж -> дата последнего платежа."""

        assert payment > self.actualy_annuity, \
               "Платеж не может быть меньше аннуитетного."

        date = self.date
        loan_sum = self.loan_sum
        while loan_sum > payment:
            interest_on_the_loan = round(loan_sum * self.percent * \
                                         self._ratio(date), 2)
            loan_sum -= (payment - interest_on_the_loan)
            date = self._next_date(date)
        plan_period = self._next_date(date)
        return plan_period


    def advanced_repayment_payment(self, finally_date):
        """Дата последнего платежа -> ежемесячный платёж."""

        assert finally_date > self.date, \
               "Запланированная дата уже прошла"

        date = datetime.date(*correct_date(
            finally_date.year, finally_date.month, self.first_date.day)[1])
        if finally_date > date:
            finally_date = self._next_date(date)
        elif finally_date < date:
            finally_date = date

        date = self.date
        months_ = months(date, finally_date)

        r1 = 1 + self.percent * self._ratio(date)
        numerator = r1
        x = 1
        date = self._next_date(date)
        for ign in range(months_ - 1):
            r = 1 + self.percent * self._ratio(date)
            numerator *= r
            x = 1 + r*x
            date = self._next_date(date)
        denominator = x
        plan_payment = round(self.loan_sum * numerator / denominator, 2)
        return plan_payment


    def annuity_payment(self):
        """Считает аннуитетный платеж"""
        i = self.percent/12 # проценты / месяцев_в_году
        n = self.period
        annuity = round(self.loan_sum * (i*(1+i)**n)/(((1+i)**n) - 1), 2)
        return annuity


    def new_payment(self, data):
        """Считает информацию по каждому платежу."""
        for date, storage in sorted(data.items()):
            storage = self._calculation(date, storage)
            self.data[date] = storage
        self.date = max(self.data)


    def remove_payment(self, date):
        """Удаляет все платежи начиная с указанной даты (включая саму дату)."""
        for key in sorted(self.data, reverse=True):
            if key < date:
                break
            del self.data[key]

        if self.data:
            max_date = max(self.data)
            self.loan_sum = self.data[max_date].loan_sum
            self.period = self.data[max_date].period
            self.actualy_annuity = self.annuity_payment()
            self.date = max_date
        else:
            self.loan_sum = self.first_loan_sum
            self.period = self.first_period
            self.actualy_annuity = self.annuity_payment()
            self.date = self.first_date


    def _calculation(self, date, storage):
        """Метод считает ежемесячные изменения."""
        storage.annuity = self.actualy_annuity
        last_date = self._last_date(date)
        storage.bank_interest = self._interest_on_the_loan(last_date)
        storage.loan_payment = round(storage.annuity - storage.bank_interest, 2)
        self.loan_sum = storage.loan_sum = round(
            self.loan_sum - storage.loan_payment, 2)
        if storage.recalc:
            storage.overpayment = round(
                sum(storage.payment) - storage.annuity + \
                (self.data[last_date].the_rest if last_date != self.first_date \
                 else 0)*1.005, 2)
            self.loan_sum = storage.loan_sum = self.loan_sum - \
                            storage.overpayment
            self.period = storage.period = self.first_period - \
                          months(self.first_date, date)
            storage.profit_bp = self._profit_bp(date, storage.overpayment)
            self.actualy_annuity = self.annuity_payment()
            storage.the_rest = 0
        else:
            storage.period = self.period
            storage.the_rest = round(
                sum(storage.payment) - storage.annuity + \
                (self.data[last_date].the_rest if last_date != self.first_date \
                 else 0)*1.005, 2)
            storage.overpayment = 0
            storage.profit_bp = 0
        self.date = date
        return storage


    def _interest_on_the_loan(self, date):
        """Сумма, которую забирает банк (за пользование кредитом).

        date - датой последнего платежа
        """
        return round(self.loan_sum * self.percent * self._ratio(date), 2)


    def _last_date(self, date):
        """Возвращает дату предыдущего платежа платежа"""
        return date_plus_months(date, -1, initdate=self.first_date)


    def _next_date(self, date):
        """Возвращает дату следующего платежа"""
        return date_plus_months(date, 1, initdate=self.first_date)


    def _profit_bp(self, date, overpayment):
        """Экономия от каждой переплаты.

        Экономия отсчитывается относительно оставшегося банковского
        периода кредита.
        """
        profit = Calculation(
            first_date=date, loan_sum=overpayment, percent=self.percent*100,
            period=self.period).actualy_annuity * self.period - overpayment
        return round(profit, 2)


    def _ratio(self, date):
        """Принимает дату прошлого платежа и возвращает коэффициент.

        Коэффициент - это отношение дней в следующем платежном периоде
        к дней в году, учитывая стык с високосным годом. Дата должна
        быть датой последнего платежа.
        """

        next_date = self._next_date(date)
        if next_date.month == 1 and calendar.isleap(next_date.year):
            break_date = date.replace(day=31)
            k = (break_date - date).days / days_in_year(date.year) + \
                (next_date - break_date).days / days_in_year(next_date.year)
        else:
            days = (next_date - date).days
            k = days / days_in_year(next_date.year)
        return k


def main():
    """Для тестирования"""
    d = {datetime.date(2013, 8, 3): (65000, 0),
         datetime.date(2013, 9, 3): (18000, 0),
         datetime.date(2013, 10, 3): (13373, 0),
         datetime.date(2013, 11, 3): (19637, 0),
         datetime.date(2013, 12, 3): (47400, 10000),
         datetime.date(2014, 1, 3): (30000, 40000),
         datetime.date(2014, 2, 3): (32000, 10000),
         datetime.date(2014, 3, 3): (30000, 50000),
         datetime.date(2014, 4, 3): (14000, 10000),
         datetime.date(2014, 5, 3): (10000, 0),
         datetime.date(2014, 6, 3): (0, 11000)}
    d_new = {}
    for date, payment in d.items():
        d_new[date] = Storage(payment, recalc=(
            True if date.month in {8, 9, 11, 12, 1, 2, 3, 4, 6} else False))

    d_new[datetime.date(2014, 6, 3)] = Storage((14000, 11000), recalc=True)
    d = d_new

    calculation = Calculation(
        datetime.date(2013, 7, 3), 900000, 14.5, 120)
    calculation.new_payment(d)
    calculation.new_payment(
        {datetime.date(2014, 7, 3): Storage((30000, 0), recalc=True)})
    for k, v in sorted(calculation.data.items()):
        print(k, end=": ")
        print(v)

    print(calculation.advanced_repayment_payment(datetime.date(2015, 8, 3)))
    print(calculation.advanced_repayment_date(46156.36))
    print(calculation.actualy_annuity)


if __name__ == "__main__":
    main()
