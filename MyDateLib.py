#!/usr/bin/env python3
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. It is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

"""Модуль для работы с датами."""

__all__ = ['correct_date', 'date_plus_months', 'days_in_year', 'months']

import calendar
import datetime


def correct_date(year, month, day):
    """Проверяет и устанавливает корректную дату.

    Дата корректируется относительно календарных ограничений
    и ограничений объекта datetime.date .

    >>> correct_date(2014, 3, 9)
    (True, (2014, 3, 9))
    >>> correct_date(2014, 2, 31)
    (False, (2014, 2, 28))
    >>> correct_date(2014, 35, 31)
    (False, (2014, 12, 31))
    >>> correct_date(2014, 5, -31)
    (False, (2014, 5, 1))    
    """
    f_date = (year, month, day)
    if year < 1:
        year = 1
    elif year > 9999:
        year = 9999
    if day < 1:
        day = 1
    if month < 1:
        month = 1
    elif month > 12:
        month = 12
    if month == 2:
        if calendar.isleap(year):
            if day > 29:
                day = 29
        else:
            if day > 28:
                day = 28
    elif month in {1, 3, 5, 7, 8, 10, 12}:
        if day > 31:
            day = 31
    else:
        if day > 30:
            day = 30
    ok = (f_date == (year, month, day))
    return ok, (year, month, day)


def date_plus_months(date, months, initdate=None):
    """Прибавляет месяцы к объекту datetime, возврашает новую дату

    Для вычитания использовать отрицательное число во втором
    аргументе. Если есть дата инициализации, функция всегда
    будет пытаться выставить день месяца равный дню месяца
    инициализации. Если день выходит за пределы месяца,
    метод сдвигает день у новой даты в сторону первой приемлемой
    минимальной даты.

    >>> date_plus_months(datetime.date(2013, 7, 31), 7)
    datetime.date(2014, 2, 28)
    >>> date_plus_months(datetime.date(2013, 7, 31), -5)
    datetime.date(2013, 2, 28)
    >>> initdate = datetime.date(2012, 12, 31)
    >>> date = date_plus_months(datetime.date(2013, 7, 31), -5, initdate)
    >>> date_plus_months(date, 1, initdate=initdate)
    datetime.date(2013, 3, 31)
    """

    years = date.year + months // 12
    months_ = months % 12
    months_ = date.month + months_
    if months_ > 12:
        years += 1
        months_ -= 12
    elif months_ < 1:
        years -= 1
        months_ += 12

    date = datetime.date(
        *correct_date(
            years, months_, date.day if initdate is None else initdate.day
            )[1]
        )
    return date


def days_in_year(year):
    """Возвращает кол-во дней в году

    >>> days_in_year(2016)
    366
    >>> days_in_year(1000)
    365
    """
    return 366 if calendar.isleap(year) else 365


def months(first_date, second_date):
    """Считает кол-во месяцев между двумя датами

    >>> months(datetime.date(2013, 3, 31), datetime.date(2010, 12, 3))
    -27
    >>> months(datetime.date(2013, 3, 31), datetime.date(2019, 1, 21))
    70
    """
    return (second_date.year - first_date.year)*12 + \
           (second_date.month - first_date.month)
