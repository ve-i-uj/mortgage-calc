#!/usr/bin/env python3
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. It is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

"""Классы для создания виджетов, используемых в ипотечном калькуляторе."""

__all__ = ['Display', 'PaymentTable', 'LoanData',
           'AdvancedRepayment', 'MySpinBoxDate', 'FloatEntry',
           'IntegerEntry', 'ValidatingEntry']

import abc
import collections
import datetime
import functools
from tkinter import *

from MyDateLib import correct_date, date_plus_months


class ValidatingEntry(Entry, metaclass=abc.ABCMeta):
    """Абстрактный класс для наследования.

    Интерфейс Entry + проверка введенного значения.
    """
    def __init__(self, parent, value=None, textvariable=None, **kw):
        super(ValidatingEntry, self).__init__(parent, **kw)
        self.__value = str(value) if value else ''
        assert isinstance(textvariable, (StringVar, type(None))), \
               ('виджет можно привязать только к '
                'переменной-экземпляру класса StringVar')
        self.variable = StringVar() if textvariable is None else textvariable
        self.config(textvariable=self.variable)
        self.variable.set(self.__value)
        self.variable.trace("w", self.__callback)
        self.block = False


    def __callback(self, *ign):
        """Запускает проверку и записывает изменения, если проверка пройдена"""
        # чтобы рекурсивный вызов при перезаписи переменной обрывался на входе
        if self.block:
            return
        try:
            self.block = True
            value = self.variable.get()
            newvalue = self.validate(value)
            if newvalue is None:
                self.variable.set(self.__value)
            elif newvalue != value:
                self.__value = newvalue
                self.variable.set(newvalue)
            else:
                self.__value = value
        finally:
            self.block = False


    @abc.abstractmethod
    def validate(self, value):
        """Метод производит проверку значения."""
        return value


class IntegerEntry(ValidatingEntry):
    """Класс для ввода целых чисел.

    Параметры from_ и to задают нижнюю и верхнюю границу числа для ввода.
    (числа выходящие за границу просто не получится ввести)
    """

    def __init__(self, parent, value=None, from_=None, to=None, **kw):
        super(IntegerEntry, self).__init__(parent, value=value, **kw)
        self.__from = from_
        self.__to = to
        self.__valid_value = value or from_ or to or None
        self.bind('<FocusOut>', lambda *ign: self.focusOutCheck())


    def validate(self, value):
        """Проверяет корректность ввода числа"""
        if self.__from is not None and self.__from >= 0 \
           and value.startswith('-'):
            return None
        if value in ('-', ''):
            return value
        value = self.__type_validate(value)
        if value is None:
            return None
        value = self.__border_validate(value)
        self.__valid_value = value
        return value


    def __border_validate(self, value):
        """Метод проверяет значение на вхождение в заданные границы"""
        val = int(value)
        if self.__from is not None and val < self.__from:
            return str(self.__from)
        if self.__to is not None and val > self.__to:
            return str(self.__to)
        return value


    def __type_validate(self, value):
        """Проверяет, чтобы значение было целой цифрой (тип integer)"""
        try:
            if value:
                int(value)
            return value
        except ValueError:
            return None


    def focusOutCheck(self):
        """Проверяет, чтобы значения были корректны для данного типа"""
        if self.variable.get() in ['', '-']:
            self.variable.set(self.__valid_value)


    def get(self):
        """Возвращает значение поля виджета.

        Если в поле ввода нет значения вернет последнее корректное.
        """
        self.focusOutCheck()
        return self.variable.get()


class FloatEntry(ValidatingEntry):
    """Класс для ввода чисел с точкой.

    Параметры from_ и to задают нижнюю и верхнюю границу числа для ввода.
    (числа выходящие за границу просто не получится ввести)
    """

    def __init__(self, parent, value=None, from_=None, to=None, **kw):
        super(FloatEntry, self).__init__(parent, value=value, **kw)
        self.__from = from_
        self.__to = to
        self.__valid_value = value or from_ or to or None
        self.bind('<FocusOut>', lambda *ign: self.focusOutCheck())


    def validate(self, value):
        """Проверяет корректность ввода числа"""
        if self.__from >= 0 and value.startswith('-'):
            return None
        if value in ('-', ''):
            return value
        value = self.__type_validate(value)
        if value is None:
            return None
        value = self.__border_validate(value)
        self.__valid_value = value
        return value


    def __border_validate(self, value):
        """Метод проверяет значение на вхождение в заданные границы."""
        val = float(value)
        if self.__from is not None and val < self.__from:
            return str(self.__from)
        if self.__to is not None and val > self.__to:
            return str(self.__to)
        return value


    def __type_validate(self, value):
        """Проверяет, чтобы значение было целой цифрой (тип integer)"""
        try:
            if value:
                float(value)
            return value
        except ValueError:
            return None


    def focusOutCheck(self):
        """Проверяет, чтобы значения были корректны для данного типа"""
        value = self.variable.get()
        if value in ['', '-']:
            value = self.__valid_value
        value = float(value)
        if value == 0 or (not (-1 < float(value) < 1) and \
                          int(value) == float(value)):
            value = str(int(value))
        else:
            value = str(float(value))
        self.variable.set(value)


    def get(self):
        """Возвращает значение поля виджета.

        Если в поле ввода нет значения вернет последнее корректное.
        """
        self.focusOutCheck()
        return self.variable.get()


class MySpinBoxDate(Frame):
    """Класс для создания виджетов для ввода даты через три Spinbox'а

    Виджет проверяет корректность ввода и не даёт вводить в поля
    посторонние символы (такие как буквы и знаки препинания),
    так же проверяет количество дней в месяце (в том числе с учетом
    високосных годов).
    t_date, b_date - верхняя и нижняя граница даты;
    first_date - первоначальная дата, если не задана,
    то выставляется текущая дата.

    Отключать поля ввода можно таким же способом, как и в обычных
    Spinbox'ах: передавая виджету параметр 'state' (со значением
    'disabled', или 'normal', или 'readonly') через конфигурационный
    метод configuration.

    check_changes(self, callback) - метод вызывает функцию переданную
    в аргумент callback при каждом изменении даты.

    set_border_date(self, bottom=None, top=None) - меняет значения
    ограничивающих дат.
    """

    def trace_variableOffOn(func):
        """На время работы поступившей функции отключает привязку к переменной.

        Чтобы не было рекурсивного вызова
        при выставлении значения в переменную.
        """
        @functools.wraps(func)
        def wrapper(self, *arg, **kw):
            traces = collections.defaultdict(list)
            for var in self.dateVars:
                traces[id(var)].extend(list(var.trace_vinfo()))
                for mode, name in traces[id(var)]:
                    var.trace_vdelete(mode, name)
            result = func(self)
            for var in self.dateVars:
                for mode, name in traces[id(var)]:
                    var.trace(mode, self.__callback)
            return result
        return wrapper


    def __init__(self, parent, first_date=None, b_date=None,
                 t_date=None, *arg, **kw):
        super(MySpinBoxDate, self).__init__(parent, *arg, **kw)
        self.parent = parent
        # переменная хранит последнюю корректную дату
        self.__date = first_date or b_date or t_date or datetime.date.today()
        self.b_date = b_date
        self.t_date = t_date
        self.borders_before_disable = (b_date, t_date)

        self.configure(bg='light goldenrod')
        # по этой переменной отслеживаются изменения
        self.dateVar = StringVar()

        self.dateVars = []
        for value in [str(int(v)) for v in str(self.__date).split('-')]:
            var = StringVar()
            var.set(value)
            self.dateVars.append(var)

        for i, text in enumerate(['год', 'месяц', 'день']):
            Label(self, text=text, font='Times 6', bg='light goldenrod').grid(
                row=0, column=i, sticky=EW)

        self.spinBoxes = []
        for column, (from_, to, width, var) in enumerate(zip(
            (0, 1, 1), (9999, 12, 31), (4, 2, 2), self.dateVars)):
            spb = Spinbox(
                self, from_=from_, to=to, width=width, textvariable=var,
                justify=RIGHT, readonlybackground='cornsilk')
            self.spinBoxes.append(spb)
            spb.grid(row=1, column=column)
            spb.bind("<FocusOut>", lambda *ign: self.__setup_date())

        self.bind("<FocusOut>", lambda *ign: self.__setup_date())

        for var in self.dateVars:
            var.trace("w", self.__callback)


    def __callback(self, *ign):
        """Метод запускает проверку.

        Если проверка пройдена, записывает изменения в переменную
        (засчёт которой отслеживаются изменения во всём виджете).
        """
        date = [var.get() for var in self.dateVars if var.get() != '']
        if len(date) != 3:
            return
        newdate = self.validate(date)
        if newdate is None:
            self.__setup_date()
        elif newdate != date:
            new_date = datetime.date(*[int(d) for d in newdate])
            if self.__date != new_date:
                self.__date = new_date
                self.dateVar.set(str(self.__date))
            self.__setup_date()
        else:
            self.__date = datetime.date(*[int(d) for d in date])
            self.dateVar.set(str(self.__date))


    @trace_variableOffOn
    def __setup_date(self):
        """Устанавливает дату в виджете."""
        [var.set(value) for var, value in zip(
            self.dateVars, [
                str(int(v)) for v in self.__date.isoformat().split('-')
                ]
            )
         ]


    def validate(self, date):
        """Метод запускает проверки."""
        date = self.__type_validate(date)
        if date is None:
            return None
        ok, date = correct_date(*date)
        date = self.__border_validate(datetime.date(*date))
        return date.isoformat().split('-')


    def __type_validate(self, date):
        """Проверяет, чтобы все значения были целыми числами"""
        try:
            date = [int(v) for v in date]
            return date
        except ValueError:
            return None


    def __border_validate(self, date):
        """Проверяет дату на вхождение в установленные пользователем границы"""
        if self.b_date is not None:
            if date < self.b_date:
                date = self.b_date
        if self.t_date is not None:
            if date > self.t_date:
                date = self.t_date
        return date


    def configure(self, cnf=None, **kw):
        """Устанавливает параметры виджета.

        Может принимать параметр Spinbox'а - 'state',
        в остальном аналогичен методу Frame.configure .
        """
        if kw.get('state') is not None:
            if kw.get('state') in {'disabled', 'normal', 'readonly'}:
                if kw.get('state') in {'disabled', 'readonly'}:
                    self.borders_before_disable = self.b_date, self.t_date
                    self.b_date = self.get_date()
                    self.t_date = self.get_date()
                else:
                    self.b_date, self.t_date = self.borders_before_disable
                for spinbox in self.spinBoxes:
                    spinbox.configure(state=kw.get('state'))
                kw.pop('state')
            else:
                raise TclError("bad state '%s': must be disabled,"
                               "normal, or readonly" %kw.pop('state'))
        super().configure(cnf=None, **kw)


    def check_changes(self, callback):
        """При изменении даты в виджете вызывает переданную функциюпри"""
        self.dateVar.trace('w', callback)


    def set_date(self, date):
        """Устанавливает дату в виджете (date - объект datetime)

        Если дата выходит за граничные условия,
        будет выставлена ближайшая граничная дата.
        """
        if not isinstance(date, datetime.date):
            TypeError('date - должен быть объектом datetime')
        date = self.__border_validate(date)
        self.__date = date
        # запускает пересчёт платежа, а мне это не нужно.
        # а так - это необходимое действие
        # (если его еще где-то применять)
        #self.dateVar.set(str(self.__date))
        self.__setup_date()


    def get_date(self):
        """Возвращает дату (экземпляр datetime.date)"""
        if len([var.get() for var in self.dateVars if var.get() != '']) != 3:
            self.__setup_date()
        return self.__date


    def set_border_date(self, bottom=None, top=None):
        """Устанавливает граничные даты."""
        if bottom is not None and top is not None:
            if not bottom <= top:
                raise ValueError('нижняя граница не должна быть больше верхней')
        if bottom is not None:
            if not isinstance(bottom, datetime.date):
                raise TypeError('bottom - должен быть объектом datetime')
            self.b_date = bottom
        if top is not None:
            if not isinstance(top, datetime.date):
                raise TypeError('bottom - должен быть объектом datetime')
            self.t_date = top
        date = self.__border_validate(self.__date)
        if self.__date != date:
            self.__date = date
            self.dateVar.set(str(self.__date))
            self.__setup_date()


class AdvancedRepayment(Frame):
    """Класс для создания формы досрочного погашения."""

    def __init__(self, parent, calc, *arg, **kw):
        """Графическая форма для получения платежа/даты досрочного погашения"""
        super(AdvancedRepayment, self).__init__(parent, *arg, **kw)
        self.calc = calc

        self.configure(bg='light goldenrod')

        self.plan_paymentVar = StringVar()

        planedLabel = Label(self, text="Досрочное погашение",
                            width=20, anchor=CENTER, bg='cornsilk')
        ppLabel = Label(self, text="Платеж:", width=20,
                        anchor=CENTER, bg='cornsilk')
        pdLabel = Label(self, text="Дата:", width=20,
                        anchor=CENTER, bg='cornsilk')
        planedLabel.grid(row=0, column=0, columnspan=2,
                         padx=2, pady=2, sticky=EW)
        ppLabel.grid(row=1, column=0, padx=2, pady=2, sticky=W)
        pdLabel.grid(row=1, column=1, padx=2, pady=2, sticky=W)

        self.ppVar = StringVar()
        self.ppEntry = FloatEntry(self, width=20, from_=0,
                                  textvariable=self.ppVar, justify=CENTER)
        self.ppEntry.bind(
            '<Any-KeyRelease>',
            lambda *ign: self.__calculation(initiator='pp_payment'))
        self.ppEntry.bind(
            '<FocusOut>',
            lambda *ign: self.__calculation(initiator='pp_date'))
        self.ppEntry.grid(row=2, column=0, padx=2, pady=2, sticky=SW)

        self.dateSpinBox = MySpinBoxDate(
            self, first_date=date_plus_months(calc.first_date, calc.period//2),
            t_date=date_plus_months(calc.first_date, calc.period),
            b_date=date_plus_months(calc.first_date, 1))
        self.dateSpinBox.check_changes(
            lambda *ign: self.__calculation(initiator='pp_date'))
        self.dateSpinBox.grid(row=2, column=1, padx=2, pady=2, sticky=E)

        self.__calculation(initiator='pp_date')


    def set_changes(self, calc):
        """Устанавливает новые данные для вычислений."""
        self.calc = calc
        self.dateSpinBox.set_border_date(
            bottom=date_plus_months(
                calc.first_date if not calc.data else max(calc.data), \
                1, initdate=calc.first_date),
            top=date_plus_months(calc.first_date, calc.first_period))
        self.__calculation(initiator='pp_date')


    def __calculation(self, initiator):
        """Вычисляет значения запланированной даты от платежа (и наоборот)"""

        if initiator == 'pp_date':
            payment = self.calc.advanced_repayment_payment(
                self.dateSpinBox.get_date())
            self.ppVar.set(int(payment))
            self.ppEntry['bg'] = 'white'
        elif initiator == 'pp_payment':
            payment = self.ppVar.get()
            if payment == '' or float(payment) < self.calc.actualy_annuity:
                self.ppEntry['bg'] = 'pink'
                return
            planed_date = self.calc.advanced_repayment_date(float(payment))
            self.ppEntry['bg'] = 'white'
            self.dateSpinBox.set_date(planed_date)


class LoanData(Frame):
    """Класс для создания форма ввода данных кредита."""

    def __init__(self, parent, *arg, **kw):
        """Форма основных данные займа."""
        super(LoanData, self).__init__(parent, *arg, **kw)
        self.__loan_data = []
        # к этой переменной привязывается отслеживание изменений
        self.checkVar = StringVar()

        self.configure(bg='light goldenrod')

        for i, text in enumerate(
            ("Сумма кредита (руб):", "Банковский процент (%):",
             "Кредитный период (мес.):")
            ):
            Label(
                self, text=text, underline=0,
                width=26, anchor=W, bg='light goldenrod'
                ).grid(row=i, column=0, padx=2, pady=0, sticky=W)

        self.loanVars = []
        self.loanEntries = []
        for i, (value, from_, to, var) in enumerate(zip(
            (1000000, 14.5, 120), (1, 0, 1), (100000000, 100, 600),
            (StringVar() for i in range(3))
            )):
            myEnrty = IntegerEntry if i != 1 else FloatEntry
            entry = myEnrty(
                self, value=value, from_=from_, to=to, textvariable=var,
                width=13, justify=CENTER, readonlybackground='cornsilk')
            entry.grid(row=i, column=1, padx=2, pady=0, sticky=W)
            self.loanVars.append(var)
            self.loanEntries.append(entry)
            entry.bind('<Any-KeyRelease>', lambda *ign: self.__set_loan_data())

        self.__set_loan_data()


    def check_changes(self, callback):
        """Вызывает переданную функцию при изменении данных в виджете"""
        self.checkVar.trace('w', callback)


    def configure(self, cnf=None, **kw):
        """Метод для конфигурирования виджета.

        Может принимать параметр Entry'а - 'state',
        в остальном аналогичен методу Frame.configure."""
        if kw.get('state') is not None:
            if kw.get('state') in {'disabled', 'normal', 'readonly'}:
                for entry in self.loanEntries:
                    entry.configure(state=kw.get('state'))
                kw.pop('state')
            else:
                raise TclError("bad state '%s': must be disabled,"
                               "normal, or readonly" %kw.pop('state'))
        super().configure(cnf=None, **kw)


    def get_loan_data(self):
        """Возвращает именнованный кортеж с данными кредита"""
        loanD = collections.namedtuple('LD', 'loan percent period')
        return loanD(*[int(var.get()) if i != 1 else float(var.get()) \
                       for i, var in enumerate(self.loanVars)])


    def set_loan_data(self, credit, interest, period):
        """Устанавливает данные кредита в форме."""
        values = [credit, interest, period]
        for ent, value in zip(self.loanEntries, values):
            ent.delete(0, END)
            ent.insert(0, str(round(value, 5)))


    def __set_loan_data(self):
        """Записывает данные в переменную, по которой отслеживаются изменения"""
        data = [var.get() for var in self.loanVars if var.get() != '']
        if len(data) == 3:
            new_data = ', '.join(data)
            if new_data != self.checkVar.get():
                self.checkVar.set(new_data)


class PaymentTable(Frame):
    """Класс для создания таблицы платежей"""

    def __init__(self, parent, names=None, *arg, **kw):
        """Таблица платежей."""
        super(PaymentTable, self).__init__(parent, *arg, **kw)
        self.canvas_width = 495 if sys.platform == 'win32' else 625
        self.canvas_height = 280
        self.canvas = Canvas(self, width=self.canvas_width,
                             height=self.canvas_height, bg='khaki')

        self.__names = names
        self.indicate_allVar = IntVar()
        self.view = 'together'
        self.changing_cells = collections.defaultdict(list)
        self.expend_rowVars = collections.defaultdict(IntVar)
        self.row_height = 19

        self.row_count = 0
        self.last_date = None
        self.first_date = None

        # first head
        headFr = Frame(self.canvas)
        dateCh = Checkbutton(
            headFr, text='', variable=self.indicate_allVar, width=1,
            bg='gold', onvalue=1, offvalue=0, command=self.__indicate_all)
        dateCh.grid(row=0, column=0, padx=0, pady=0, sticky=EW)
        for i, (text, width) in enumerate(
            zip(("№", "Дата списания:", "По кредиту:", "По процентам:",
                 "Платеж:", "Остаток долга:"), (6, 16, 11, 13, 11, 14))
            ):
            lb = Label(headFr, width=width, text=text, relief=GROOVE,
                       justify=LEFT, bg='gold')
            lb.grid(row=0, column=i+1, padx=0, pady=0, sticky=EW)
        self.canvas.create_window(0, 0, anchor=NW, window=headFr,
                                  width=self.canvas_width,
                                  height=self.row_height)

        self.canvas.pack(side="left")

        self.scr = Scrollbar(self, orient="vertical", takefocus=False,
                             width=15, bg='khaki')
        self.scr.pack(side="left", fill="y")
        self.scr["command"] = self.canvas.yview

        self.canvas.config(
            yscrollcommand=self.scr.set,
            scrollregion=(0, 0, 650, self.row_height))

        self.canvas.create_text(312 if not sys.platform == 'win32' else 240,
                                140, tags='init_text',
                                font=('New Roman', 12),
                                text=('Здесь будет таблица с'
                                      'информацией о Ваших '
                                      'платежах\n(после добавления платежа)'),
                                justify=CENTER)
#        self.bind_all("<MouseWheel>", func=self.__rollWheel)
        self.bind_all("<Button-4>", func=self.__rollWheel)
        self.bind_all("<Button-5>", func=self.__rollWheel)


    def expand_row(self, date):
        """Метод разворачивает строку с соответствующей датой."""
        if self.expend_rowVars[date].get():
            # сдвинули область скрола
            self.canvas.config(
                scrollregion=(
                    0, 0, self.canvas_width,
                    int(float(self.canvas['scrollregion'].split(' ')[3])) + \
                    self.row_height*(len(self.__names)+1)
                    )
                )
            # разварачиваем строку
            if date != self.last_date:
                x, y = self.canvas.coords(
                    str(date_plus_months(date, 1, initdate=self.first_date)))
                self.canvas.addtag_overlapping(
                    'move', int(x), int(y),
                    *[int(float(i)) for i in \
                      self.canvas['scrollregion'].split(' ')[2:4]]
                    )
                self.canvas.move(
                    'move', 0, self.row_height*(len(self.__names)+1))
                self.canvas.dtag('move')
            self.canvas.itemconfig(
                str(date), height=self.row_height*(len(self.__names)+2))
        else:
            if date != self.last_date:
                x, y = self.canvas.coords(
                    str(date_plus_months(date, 1, initdate=self.first_date)))
                self.canvas.addtag_overlapping(
                    'move', int(x), int(y),
                    *[int(float(i)) for i in \
                      self.canvas['scrollregion'].split(' ')[2:4]])
                self.canvas.move(
                    'move', 0, -self.row_height*(len(self.__names)+1))
                self.canvas.dtag('move')
            self.canvas.itemconfig(str(date), height=self.row_height)
            self.canvas.config(
                scrollregion=(
                    0, 0, self.canvas_width,
                    int(float(self.canvas['scrollregion'].split(' ')[3]) - \
                        self.row_height*(len(self.__names)+1))
                    )
                )


    def new_payments(self, calc, planning_mode=False):
        """Отображает информацию о новых платежах, как новые строки"""
        if self.first_date is None:
            self.first_date = calc['together'].first_date
        for date, info in sorted(calc['together'].data.items()):
            if self.last_date is not None and self.last_date >= date:
                continue
            self.__create_row(date, info, planning_mode=planning_mode)
            self.__view_together_or_once(date, calc, view=self.view)


    def remove_row(self, date):
        """Удаляет все нижние строки ничиная с указанной даты"""
        if self.last_date is not None:
            assert date <= self.last_date, 'Нет такой даты'
        else:
            return
        x, y = self.canvas.coords(str(date))
        self.canvas.addtag_overlapping(
            'delete', int(x), int(y),
            *[int(float(i)) for i in \
              self.canvas['scrollregion'].split(' ')[2:4]]
            )
        self.canvas.delete('delete')
        self.canvas.dtag('delete')
        self.canvas.config(
            scrollregion=(0, 0, self.canvas_width, int(y)))

        for d in sorted(self.expend_rowVars.keys(), reverse=True):
            if d < date:
                break
            del self.expend_rowVars[d]
            del self.changing_cells[d]

        self.last_date = date_plus_months(date, -1, initdate=self.first_date) \
                         if not len(self.expend_rowVars) == 0 else None
        if self.last_date is None:
            self.first_date = None
            self.canvas.create_text(
                312 if not sys.platform == 'win32' else 240,
                180 if sys.platform == 'win32' else 140, tags='init_text',
                font=('New Roman', 12),
                text=('Здесь будет таблица с информацией о Ваших платежах\n'
                      '(после добавления платежа)'),
                justify=CENTER)


    def set_names(self, names):
        """Устанавливает имена"""
        self.__names = names


    def view_extra_row(self, calc, view):
        """Меняет вид всех развернутых строк.

        Вид может быть: для всех вместе или для
        кажного плательщика в отдельности.
        """
        for date in calc['together'].data.keys():
            self.__view_together_or_once(date, calc, view)
        self.view = view


    def __view_together_or_once(self, date, calc, view='together'):
        """Меняет вид конкретной развернутой строки"""

        def break_list(lst, n):
            """Разбивает список на списки с заданным кол-вом элементов

            Если кол-во эл-тов не кратны заданному числу,
            в последнем списке будет меньше значений).
            """
            i = 0
            j = n
            while True:
                br_l = lst[i:j]
                if br_l:
                    yield lst[i:j]
                    i = j
                    j += n
                else:
                    break

        if self.last_date is None: return

        if view == 'together':
            info = calc['together'].data[date]
            for lb in self.changing_cells[date][2:]:
                # удаляем нижние строки
                lb.grid_remove()
            for i, (lb, text) in enumerate(
                zip(self.changing_cells[date][:2],
                    ('{0}'.format(round(info.overpayment, 2)),
                     '{0}'.format(round(info.profit_bp, 2)))),
                start=4):
                lb.config(text=text)
                lb.grid(row=2, column=i, rowspan=len(self.__names), sticky=NSEW)
            # в более старших версиях (>3.1) возвращается список, а не map
            list(lb.master.grid_slaves(column=6, row=1))[0].grid_remove()
        elif view == 'once':
            for lb in self.changing_cells[date][:2]:
                lb.grid_forget()
            for row, (name, payer_row) in enumerate(
                zip(self.__names, break_list(self.changing_cells[date], 3)),
                start=2):
                info = calc[name].data[date]
                for i, (lb, text) in enumerate(
                    zip(payer_row,
                        ('{0}'.format(round(info.overpayment, 2)),
                         '{0}'.format(round(info.profit_bp, 2)),
                         '{0}'.format(round(info.loan_sum)))),
                    start=4):
                    lb.config(text=text)
                    lb.grid(row=row, column=i, sticky=NSEW)
            Label(lb.master, text='Долг:', relief=GROOVE,
                  justify=LEFT, bg='moccasin').grid(
                      row=1, column=6, padx=0, pady=0, sticky=EW)


    def __create_row(self, date, info, planning_mode):
        """Метод создает строку в таблице"""

        if self.last_date is None:
            self.canvas.delete('init_text')
        rowFr = Frame(self.canvas, bg='khaki')
        dateCh = Checkbutton(
            rowFr, text='', variable=self.expend_rowVars[date], width=1,
            height=1, bg='cornsilk' if not planning_mode else 'pale green',
            onvalue=1, offvalue=0,
            command=functools.partial(self.expand_row, date=date))
        dateCh.grid(row=0, column=0, padx=0, pady=0, sticky=EW)
        for i, (text, width) in enumerate(
            zip(("{0}".format(len(self.expend_rowVars)),
                 "{0}".format(str(date)),
                 "{0}".format(info.loan_payment),
                 "{0}".format(info.bank_interest),
                 "{0}".format(info.annuity),
                 "{0}".format(round(info.loan_sum))),
                (6, 16, 11, 13, 11, 14))):
            lb = Label(
                rowFr, width=width, text=text, relief=GROOVE, justify=LEFT,
                bg='cornsilk' if not planning_mode else 'pale green')
            lb.grid(row=0, column=i+1, padx=0, pady=0, sticky=EW)

        # extra info head
        for k, text in enumerate(
            ('Плательщик:', "Платеж:", "Переплата:", "Экономия:", 'Долг:')):
            slb = Label(rowFr, text=text, relief=GROOVE,
                        justify=LEFT, bg='moccasin')
            slb.grid(row=1, column=2+k, padx=0, pady=0, sticky=EW)

        # imitation extra info
        for k, name in enumerate(self.__names):
            Label(rowFr, text=name, relief=GROOVE,
                  justify=LEFT, bg='white', height=1).grid(
                      row=2+k, column=2, padx=0, pady=0, sticky=EW)
            for column, text in enumerate(
                ('{0}'.format(info.payment[k]),
                 '{0}'.format(info.overpayment),
                 '{0}'.format(info.profit_bp),
                 '{0}'.format(round(info.loan_sum))),
                start=3):
                lb = Label(rowFr, text=text, relief=GROOVE,
                           justify=LEFT, bg='white')
                lb.grid(row=2+k, column=column, padx=0, pady=0, sticky=EW)
                # запоминаем строки, которые затем надо будет изменять
                if column > 3:
                    self.changing_cells[date].append(lb)

        self.canvas.create_window(
            0, int(float(self.canvas['scrollregion'].split(' ')[3])),
            tag=str(date), anchor=NW, window=rowFr,
            width=self.canvas_width, height=self.row_height)

        x, y = self.canvas.coords(str(date))
        self.canvas.config(
            scrollregion=(0, 0, self.canvas_width, int(y+self.row_height)))
        self.last_date = date


    def __indicate_all(self, *ign):
        """Метод разворачивает/сворачивает все строки"""
        # еще ничего нет в таблице
        if self.last_date is None:
            return

        for date, var in sorted(self.expend_rowVars.items()):
            if self.indicate_allVar.get():
                if var.get() == 0:
                    var.set(1)
                    self.expand_row(date)
            else:
                if var.get() == 1:
                    var.set(0)
                    self.expand_row(date)


    def __rollWheel(self, event):
        """Скролл мышки"""
        if event.num == 4:
            self.canvas.yview('scroll', -1, 'units')
        elif event.num == 5:
            self.canvas.yview('scroll', 1, 'units')


class Display(Frame):
    """Класс для создания диаграммы платежей"""

    def __init__(self, parent, names=None, *arg, **kw):
        """Круговая диаграмма."""
        super(Display, self).__init__(parent, *arg, **kw)
        self.canvas = Canvas(self, width=280, height=225, bg='khaki')

        self.__names = names

        # init text
        self.canvas.pack(side="left")

        self.canvas.create_text(
            140, 112, tags='init_text',
            font=('New Roman', 10),
            text=('Здесь будет диаграмма \nс информацией о Ваших платежах\n'
                  '(после добавления платежа)'),
            justify=CENTER)
        self.active = False


    def new_payments(self, calc, planning_calc=None):
        """Метод отображает новые изменения"""
        if not self.active:
            self.canvas.delete('init_text')
            self.active = True
            self.canvas.create_rectangle(5, 184, 16, 195, fill='gold')
            self.canvas.create_text(26, 190,
                                    font=('New Roman', 9),
                                    text=' - погашено долга с учётом переплат',
                                    justify=LEFT, anchor=W)
            self.canvas.create_rectangle(5, 207, 16, 218, fill='yellow')
            self.canvas.create_text(26, 213,
                                    font=('New Roman', 9),
                                    text=' - если б не было переплат',
                                    justify=LEFT, anchor=W)

        self.canvas.delete('delete')
        self.canvas.delete('delete_text')

        remaining_debt = 1 - calc.loan_sum / calc.first_loan_sum
        probable_remaining_debt = sum(
            info.loan_payment for info in calc.data.values()
            ) / calc.first_loan_sum

        self.canvas.create_oval(5, 5, 175, 175, fill='cornsilk', tag='delete')
        if remaining_debt < 1:
            self.canvas.create_arc(
                5, 5, 175, 175, extent=int(-360*remaining_debt),
                start=90, fill='gold', tag='delete')
        else:
            self.canvas.create_oval(5, 5, 175, 175, fill='gold', tag='delete')
        self.canvas.create_arc(
            15, 15, 165, 165, extent=int(-360*probable_remaining_debt),
            start=90, fill='yellow', tag='delete')

        self.canvas.create_line(92, 10, 215, 10, tag='delete')
        self.canvas.create_text(
            220, 10, font=('New Roman', 11),
            text='{0}%'.format(round(float(remaining_debt*100), 2)),
            anchor=NW, tag='delete_text', fill='black')
        self.canvas.create_line(
            215, 30, 270, 30, tag='delete', fill='gold', width=2)

        self.canvas.create_line(92, 45, 215, 45, tag='delete')
        self.canvas.create_text(
            220, 45, font=('New Roman', 11),
            text='{0}%'.format(
                round(float(probable_remaining_debt*100), 2)),
            anchor=NW, tag='delete_text', fill='black')
        self.canvas.create_line(215, 65, 270, 65,
                                tag='delete', fill='yellow', width=2)

        if planning_calc:
            self.canvas.delete('delete_text')
            pl_remaining_debt = 1 - planning_calc.loan_sum / \
                                planning_calc.first_loan_sum
            pl_probable_remaining_debt = sum(
                info.loan_payment for info in planning_calc.data.values()
                ) / planning_calc.first_loan_sum
            self.canvas.create_arc(
                5, 5, 175, 175,
                extent=int(-360*(pl_remaining_debt - remaining_debt)),
                start=90 + int(-360*remaining_debt),
                fill='pale green', tag='delete')
            self.canvas.create_arc(
                15, 15, 165, 165,
                extent=int(-360*(
                    pl_probable_remaining_debt - probable_remaining_debt)),
                start=90 + int(-360*probable_remaining_debt),
                fill='green', tag='delete')

            self.canvas.create_line(92, 10, 215, 10, tag='delete')
            self.canvas.create_text(
                220, 10, font=('New Roman', 11),
                text='{0}%'.format(
                    round(float(pl_remaining_debt*100), 2)),
                anchor=NW, tag='delete', fill='dark green')
            self.canvas.create_line(
                215, 30, 270, 30, tag='delete', fill='gold', width=2)

            self.canvas.create_line(92, 45, 215, 45, tag='delete')
            self.canvas.create_text(
                220, 45, font=('New Roman', 11),
                text='{0}%'.format(
                    round(float(pl_probable_remaining_debt*100), 2)),
                anchor=NW, tag='delete', fill='dark green')
            self.canvas.create_line(215, 65, 270, 65,
                                    tag='delete', fill='yellow', width=2)


    def the_end(self):
        """Смайл на диаграмме"""
        self.canvas.create_arc(25, 25, 155, 155, extent=-120, style=ARC,
                               start=-30, tag='delete', width=3)
        self.canvas.create_line(60, 40, 60, 100, tag='delete', width=3)
        self.canvas.create_line(120, 40, 120, 100, tag='delete', width=3)
