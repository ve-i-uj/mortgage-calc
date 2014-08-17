#!/usr/bin/env python3
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. It is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

"""Main window of mortgage calculator"""

import copy
import datetime
import pickle
import os
import os.path
import tkinter
import tkinter.filedialog
import tkinter.messagebox

from Calculation import Calculation, Storage
from MyDateLib import date_plus_months
from MyForms import AddEditForm, PayerNames
from MyWidgets import AdvancedRepayment, IntegerEntry, MySpinBoxDate, \
                      LoanData, PaymentTable, Display


class MainWindow:
    """Класс для создания главного окна программы ипотечного калькулятора"""

    def __init__(self, parent):
        """Cоздает главное окно калькулятора"""
        self.parent = parent

        self.dirty = False
        self.calc = {}
        self.last_date = None
        self.planning_mode = False
        self.__payer_names = None
        self.__loans = None
        self.filename = None
        self.dirty = False

        self.parent.title("Ипотечный калькулятор")

        self.menubar = tkinter.Menu(self.parent, bg='bisque2')
        self.parent['menu'] = self.menubar

        fileMenu = tkinter.Menu(self.menubar, bg='cornsilk')
        for label, command, shortcut_text, shortcut in (
            ("Новый...", self.fileNew, "Ctrl+N", "<Control-n>"),
            ("Открыть...", self.fileOpen, "Ctrl+O", "<Control-o>"),
            ("Сохранить...", self.fileSave, "Ctrl+S", "<Control-s>"),
            (None, None, None, None),
            ("Выход...", self.fileQuit, "Ctrl+Q", "<Control-q>")):
            if label is None:
                fileMenu.add_separator()
            else:
                fileMenu.add_command(label=label,
                                     underline=0,
                                     command=command,
                                     accelerator=shortcut_text)
                self.parent.bind(shortcut, command)
        self.menubar.add_cascade(label="Файл", menu=fileMenu, underline=0)

        self.editMenu = tkinter.Menu(self.menubar, bg='cornsilk')
        for label, command, shortcut_text, shortcut in (
            ("Добавить...", self.paymentAdd, "Ctrl+A", "<Control-a>"),
            ("Удалить...", self.paymentRemove, "Delete", "<Delete>"),
            ("Редактировать...", self.paymentEdit, "Ctrl+E", "<Control-e>"),
            ("Планировать...", self.planningMode, "Ctrl+P", "<Control-p>"),
            (None, None, None, None)):
            if label is None:
                self.editMenu.add_separator()
            else:
                self.editMenu.add_command(
                    label=label, underline=0,
                    command=command, accelerator=shortcut_text)
                self.parent.bind(shortcut, command)
        self.menubar.add_cascade(
            label="Изменить", menu=self.editMenu, underline=0)

        viewMenu = tkinter.Menu(self.menubar, bg='cornsilk')
        self.menubar.add_cascade(label="Вид", menu=viewMenu, underline=0)

        viewsubMenu = tkinter.Menu(
            self.menubar, bg='cornsilk', tearoff=True)
        viewsubMenu.add_command(
            label="Вместе",
            command=lambda *ign: self.view(flag='together'))
        viewsubMenu.add_command(
            label="По отдельности",
            command=lambda *ign: self.view(flag='once'))
        viewMenu.add_cascade(label="Режим просмотра",
                             menu=viewsubMenu)

        self.menubar.entryconfigure(3, state='disabled')

        self.frame1 = tkinter.Frame(
            self.parent, bg='light goldenrod', borderwidth=2)
        self.ld = LoanData(self.frame1)
        self.ld.grid(row=0, column=0, columnspan=2,
                     padx=2, pady=5, sticky=tkinter.W)
        self.ld.check_changes(
            callback=lambda *ign: self.advRepWidget.set_changes(
                calc=self._new_instance_of_Calc()))

        count_payersLabel = tkinter.Label(
            self.frame1, text="Кол-во плательщиков:", underline=0,
            width=26, anchor=tkinter.W, bg='light goldenrod')
        self.count_payersEntry = IntegerEntry(
            self.frame1, width=13, from_=1, to=5,
            justify=tkinter.CENTER, readonlybackground='cornsilk')
        count_payersLabel.grid(row=1, column=0,
                               padx=2, pady=0, sticky=tkinter.W)
        self.count_payersEntry.grid(row=1, column=1, padx=2,
                                    pady=0, sticky=tkinter.W)
        self.count_payersEntry.insert(0, 2)
        self.count_payersEntry.bind(
            '<FocusOut>',
            lambda *ign: self.count_payersEntry.insert(0, 2) \
            if self.count_payersEntry.get() == '' else None)
        self.frame1.grid(row=0, column=0, padx=10, pady=0, sticky=tkinter.W)

        self.spinBox_frame = tkinter.Frame(self.parent, bg='light goldenrod')
        first_dateLable = tkinter.Label(
            self.spinBox_frame, text="Дата оформления договора:",
            underline=0, width=26, anchor=tkinter.W,
            bg='light goldenrod', justify=tkinter.LEFT)
        first_dateLable.grid(row=1, column=0, rowspan=2, padx=2,
                             pady=2, sticky=tkinter.SW)
        self.dateSpinBox = MySpinBoxDate(self.spinBox_frame)
        self.dateSpinBox.check_changes(lambda *ign: \
                                       self.advRepWidget.set_changes(
                                           calc=self._new_instance_of_Calc()))
        self.dateSpinBox.grid(row=1, column=1, padx=2, pady=2, sticky=tkinter.W)
        self.spinBox_frame.grid(row=1, column=0, padx=10,
                                pady=5, sticky=tkinter.W)

        self.advRepWidget = AdvancedRepayment(
            self.parent, calc=self._new_instance_of_Calc())
        self.advRepWidget.grid(row=2, column=0, padx=10,
                               pady=5, sticky=tkinter.W)

        self.table = PaymentTable(self.parent, names=self.__payer_names)
        self.table.grid(row=3, column=0, columnspan=2,
                        padx=10, pady=5, sticky=tkinter.W)

        self.display = Display(self.parent, bg='light goldenrod')
        self.display.grid(row=0, column=1, rowspan=3,
                          padx=10, pady=5, sticky=tkinter.EW)


        button_frame = tkinter.Frame(self.parent, bg='light goldenrod')
        self.button = []
        for (text, command) in zip(
            ('Добавить', 'Удалить', 'Редактировать'),
            [self.paymentAdd, self.paymentRemove, self.paymentEdit]):
            button = tkinter.Button(
                button_frame, text=text, width=12,
                height=1, bg='aliceblue', fg='black', font='arial 10')
            button.pack(padx=6, side=tkinter.LEFT)
            button.bind("<Button-1>", command)
            self.button.append(button)
        self.planButton = tkinter.Button(
            button_frame, text='Вкл. Планирование', width=16,
            height=1, bg='aliceblue', fg='black', font='arial 10')
        self.button.append(self.planButton)
        self.planButton.pack(padx=3, side=tkinter.RIGHT)
        self.planButton.bind("<Button-1>", self.planningMode)

        button_frame.grid(row=11, column=0, columnspan=2,
                          padx=5, pady=3, sticky=tkinter.EW)

        self.optionsOffOn(delete=False, edit=False, plan=False)

        self.parent.config(bg='light goldenrod')


    def fileLoad(self, filename):
        """Загружает ипотечную историю из файла."""
        self.filename = filename

        # всем датам выставляем галки
        for var in self.table.expend_rowVars.values():
            var.set(1)
        self.paymentRemove()
        self.dirty = False
        try:
            with open(self.filename, "rb") as fh:
                self.__payer_names = pickle.load(fh)
                self.calc = pickle.load(fh)

            if len(self.__payer_names) > 1:
                self.menubar.entryconfigure(3, state='normal')
            credit = self.calc['together'].first_loan_sum
            interest = self.calc['together'].percent * 100
            period = self.calc['together'].first_period
            self.ld.set_loan_data(credit, interest, period)
            self.dateSpinBox.set_date(self.calc['together'].first_date)

            self.ld.configure(state='readonly')
            self.count_payersEntry.configure(state='readonly')
            self.dateSpinBox.configure(state='readonly')

            self.advRepWidget.set_changes(self.calc['together'])

            self.table.set_names(self.__payer_names)
            self.table.new_payments(self.calc)
            self.display.new_payments(self.calc['together'])
            self.parent.title(
                "Ипотечный калькулятор - {0}".format(
                    os.path.basename(self.filename)))
            self.optionsOffOn(delete=True, edit=True, plan=True)
        except (EnvironmentError, pickle.PickleError) as err:
            tkinter.messagebox.showwarning(
                "Mortgage Calcaulation - Error",
                "Failed to load {0}:\n{1}".format(self.filename, err),
                parent=self.parent)


    def fileNew(self, *ignore):
        """Создает новую форму для новой ипотечной истории."""
        if self.calc:
            self._remove_payments(
                date_plus_months(self.calc['together'].first_date, 1))

        self.calc = {}
        self.__payer_names = None
        self.__loans = None
        self.filename = None
        self.dirty = False

        self.parent.title("Ипотечный калькулятор")

        self.ld.configure(state='normal')
        self.count_payersEntry.configure(state='normal')
        self.dateSpinBox.configure(state='normal')

        self.menubar.entryconfigure(3, state='disabled')

        self.optionsOffOn(add=True, delete=False, edit=False, plan=False)

        self.display.grid_forget()
        self.display = Display(self.parent, bg='light goldenrod')
        self.display.grid(row=0, column=1, rowspan=3, padx=10,
                          pady=5, sticky=tkinter.EW)

        self.ld.set_loan_data(900000, 14.5, 120)
        self.count_payersEntry.delete(0, tkinter.END)
        self.count_payersEntry.insert(0, 2)
        self.dateSpinBox.set_date(datetime.date.today())
        self.advRepWidget.set_changes(calc=self._new_instance_of_Calc())


    def fileOpen(self, *ignore):
        """Окно для выбора сохраненной ипотечной истории из файла"""
        if not self.okayToContinue():
            return
        if self.planning_mode:
            self.planningMode()
        dir_ = (os.path.dirname(self.filename) if self.filename is not None \
                else ".")
        filename = tkinter.filedialog.askopenfilename(
            title="Mortgage Calcaulation - Open File",
            initialdir=dir_,
            filetypes=[("Calculation files", "*.clc")],
            defaultextension=".clc", parent=self.parent)
        if filename:
            self.fileNew()
            self.fileLoad(filename)


    def fileSave(self, *ignore):
        """Cохраненной ипотечную историю в файл в формате '.clc'."""
        if self.planButton['text'] == 'Выкл. Планирование':
            tkinter.messagebox.showinfo(
                'Включен режим планирования',
                'В режиме "Планирование" нельзя сохранять данные.',
                parent=self.parent)
            return
        filename = tkinter.filedialog.asksaveasfilename(
            title='Mortgage Calc - Save File',
            initialdir='.',
            filetypes=[("Mortgage files", "*.clc")],
            defaultextension=".clc",
            parent=self.parent)
        if not filename:
            return False
        self.filename = filename
        if not self.filename.endswith(".clc"):
            self.filename += ".clc"
        try:
            with open(self.filename, "wb") as fh:
                pickle.dump(self.__payer_names, fh, pickle.HIGHEST_PROTOCOL)
                pickle.dump(self.calc, fh, pickle.HIGHEST_PROTOCOL)
            self.dirty = False
            self.parent.title(
                "Ипотечный калькулятор - {0}".format(
                    os.path.basename(self.filename)))
        except (EnvironmentError, pickle.PickleError) as err:
            tkinter.messagebox.showwarning(
                "Mortgage Calculation - Error",
                "Failed to save {0}:\n{1}".format(self.filename, err),
                parent=self.parent)
        return True


    def fileQuit(self, event=None):
        """Выход из калькулятора"""
        if self.okayToContinue():
            self.parent.destroy()


    def okayToContinue(self):
        """Спрашевает о сохранении изменений сделанных в калькуляторе."""
        if not self.dirty:
            return True
        reply = tkinter.messagebox.askyesnocancel(
            "Ипотечный Калькулятор - Не сохранены изменения",
            "Сохранить?", parent=self.parent)
        if reply is None:
            return False
        if reply:
            return self.fileSave()
        return True


    def optionsOffOn(self, add=None, delete=None, edit=None, plan=None):
        """Включает и выключает опции работы с платежами."""
        options = (add, delete, edit, plan)
        positions = (0, 1, 2, 3)
        methods = (self.paymentAdd, self.paymentRemove,
                   self.paymentEdit, self.planningMode)
        shortcuts = ("<Control-a>", "<Delete>", "<Control-e>", "<Control-p>")
        for opt, (pos, method, shortcut) in \
            ((opt, param) for opt, *param in \
             zip(options, positions, methods, shortcuts) if opt is not None):
            if opt:
                self.button[pos]['state'] = 'normal'
                self.parent.bind(shortcut, method)
                self.editMenu.entryconfigure(pos + 1, state='normal')
            else:
                self.button[pos]['state'] = 'disabled'
                self.parent.unbind(shortcut)
                self.editMenu.entryconfigure(pos + 1, state='disabled')


    def payersAdd(self):
        """Добавляет имена плательщиков"""
        form = PayerNames(self.parent, int(self.count_payersEntry.get()),
                          self.ld.get_loan_data().loan)
        if form.names:
            if len(form.names) > 1:
                self.menubar.entryconfigure(3, state='normal')
            self.__payer_names = form.names
            self.__loans = form.loans
            self.ld.configure(state='readonly')
            self.count_payersEntry.configure(state='readonly')


    def paymentAdd(self, *ign):
        """Метод для получения новых платежей."""
        if self.__payer_names is None:
            if self.count_payersEntry.get() == '':
                self.count_payersEntry.insert(0, 2)
            self.payersAdd()
        if not self.__payer_names:
            return
        if not self.calc:
            calc = self._new_instance_of_Calc()
        else:
            calc = self.calc['together']
        form = AddEditForm(self.parent, self.__payer_names, calculation=calc)
        if form.result:
            if not self.calc:
                self.dateSpinBox.configure(state='readonly')
                self.table.set_names(self.__payer_names)

                self.calc['together'] = self._new_instance_of_Calc()
                loan_data = self.ld.get_loan_data()
                date = self.dateSpinBox.get_date()
                for i, name in enumerate(self.__payer_names):
                    self.calc[name] = Calculation(date, self.__loans[i],
                                                  loan_data.percent,
                                                  loan_data.period)

                self.optionsOffOn(delete=True, edit=True, plan=True)

            # заполняет новыми платежами основной носитель информации
            self._fill_calc(form.result)  # form.result: {date: Storage(), ...}

            # сообщает планировщику об изменениях
            self.advRepWidget.set_changes(self.calc['together'])

            # записывает строки в таблицу
            self.table.new_payments(self.calc, planning_mode=self.planning_mode)

            # сообщаем дисплею о новом платеже
            self.display.new_payments(*(
                (self.calc['together'], None) if not self.planning_mode else \
                (self._slice_calc(
                    date_plus_months(self.last_date, 1,
                                     initdate=self.calc['together'].first_date)
                    )['together'],
                 self.calc['together'])
                ))

            self.dirty = True


    def paymentEdit(self, *ign):
        """Метод для редактирования платежей."""
        edit_dates = [date for date, var in \
                      sorted(self.table.expend_rowVars.items()) \
                      if var.get() == 1]
        if self.planning_mode:
            edit_dates = [date for date in edit_dates if date > self.last_date]
        if not edit_dates:
            return
        if len(edit_dates) == len(self.table.expend_rowVars):
            reply = tkinter.messagebox.askyesno(
                'Редактировать все даты?',
                ('Вы уверены, что хотите редактировать все даты?\n\n'
                 "(Возможно в этом случае будет проще начать"
                 "новую историю платежей)"),
                parent=self.parent)
            if not reply:
                return
        changed_payments = {} # хранит измененные платежи
        for date in edit_dates:
            reduct_form = AddEditForm(self.parent, self.__payer_names,
                                      calculation=self._slice_calc(
                                          date=date)['together'],
                                      reduct=True)
            if reduct_form.result:
                changed_payments.update(reduct_form.result)
            # на случай, если закрыли весь кредит
            if reduct_form.debt_is_end:
                last_payment_date = date
                break

        if not changed_payments:
            return
        # записываем в словарь все платежи,
        # которые были после самой ранней редактируемой даты (её тоже включаем)
        reducted_payments = {}
        for date, info in sorted(self.calc['together'].data.items(),
                                 reverse=True):
            if date < min(changed_payments): # меньше самой ранней редактируемой
                break
            if reduct_form.debt_is_end:
                if date > last_payment_date:
                    break
            reducted_payments[date] = info

        # меняем старые платежи на измененные
        reducted_payments.update(changed_payments)

        # удаляем все данные, начиная с самой первой отредактируемой даты,
        # из основного носителя и подчищаем таблицу
        self._remove_payments(min(changed_payments))

        # заполняем новыми данными, так как будто это новые платежи
        self._fill_calc(reducted_payments)
        # сообщает планировщику о изменениях
        self.advRepWidget.set_changes(self.calc['together'])

        # записывает строки в таблицу
        self.table.new_payments(self.calc, planning_mode=self.planning_mode)

        # сообщаем дисплею о изменениях
        self.display.new_payments(*(
            (self.calc['together'], None) if not self.planning_mode else \
            (self._slice_calc(
                date_plus_months(self.last_date, 1,
                                 initdate=self.calc['together'].first_date)
                )['together'], self.calc['together'])
            ))

        # развернём все строки, которые были с галками
        for date in edit_dates:
            self.table.expend_rowVars[date].set(1)
            self.table.expand_row(date)
        self.dirty = True

        self._is_loan_end_fill_calc()


    def paymentRemove(self, *ign):
        """Удаляет нижние строки в таблице, начиная с верхней выделенной"""
        for date, var in sorted(self.table.expend_rowVars.items()):
            if var.get() == 1:
                if self.planning_mode:
                    # удалять только запланированные даты
                    if date <= self.last_date:
                        continue
                break
        else: # нет ни одной галки
            return
        self._remove_payments(date)


    def planningMode(self, *ign):
        """Включает и отключает режим планирования"""
        # планирование не включено - включаем
        if self.planButton['text'] == 'Вкл. Планирование':
            self.planButton.configure(text='Выкл. Планирование',
                                      bg='pale green')
            self.menubar.configure(bg='pale green')
            # для удаления всех следующих за этой дат
            self.last_date = self.calc['together'].date
            self.planning_mode = True # для подкрашивания в зеленый строки
        else:
            self.planButton.configure(text='Вкл. Планирование', bg='aliceblue')
            self.menubar.configure(bg='bisque2')
            self.planning_mode = False
            # если есть запланированные даты
            if max(self.table.expend_rowVars) > self.last_date:
                self._remove_payments(
                    date_plus_months(self.last_date, 1,
                                     initdate=self.calc['together'].first_date))
            self.last_date = None
            self.dirty = False


    def view(self, flag='together', *ign):
        """Переключает режимы просмотра"""
        if not self.calc:
            return
        if flag != self.table.view:  # это значение и так установлено
            self.table.view_extra_row(self.calc, view=flag)


    def _fill_calc(self, new_payments):
        """Заполняет новыми платежами основной носитель информации."""
        self.calc['together'].new_payment(new_payments)
        for i, name in enumerate(self.__payer_names):
            new_d = {}
            for date, info in new_payments.items():
                new_d[date] = Storage(payment=tuple([info.payment[i]]), \
                                      recalc=info.recalc)
            self.calc[name].new_payment(new_d)
        self._is_loan_end_fill_calc()


    def _is_loan_end_fill_calc(self):
        """Проверяет выплачен ли полностью кредит."""
        # 1 вместо 0 из-за погрешности при расчетах
        if self.calc['together'].loan_sum <= 1:
            self.optionsOffOn(add=False)
            if not self.planning_mode:
                self.optionsOffOn(plan=False)
                tkinter.messagebox.showinfo('Поздравляю!',
                                            'Ипотека наконец-то закончилась! =)',
                                            parent=self.parent)
                self.display.after(500, self.display.the_end)
        else:
            if self.button[0]['state'] == 'disabled': 
                self.optionsOffOn(add=True)
                if not self.planning_mode:
                    self.optionsOffOn(plan=True)

    def _new_instance_of_Calc(self):
        """Возвращает новый экземпляр класса Calculation"""
        loan_data = self.ld.get_loan_data()
        calc = Calculation(self.dateSpinBox.get_date(), loan_data.loan, \
                           loan_data.percent, loan_data.period)
        return calc


    def _remove_payments(self, date):
        """Удаляет платежи начиная с полученной даты (включительно)."""
        self.table.remove_row(date)

        for calc in self.calc.values():
            calc.remove_payment(date)

        self.advRepWidget.set_changes(self.calc['together'])

        self.display.new_payments(*(
            (self.calc['together'], None) if not self.planning_mode else \
            (self._slice_calc(
                date_plus_months(self.last_date, 1,
                                 initdate=self.calc['together'].first_date)
                )['together'], self.calc['together'])
            ))
        self._is_loan_end_fill_calc()
        self.dirty = True


    def _slice_calc(self, date):
        """Возвращает срез словаря упорядоченного по ключам
           (от первого элемента до date).
        """
        new_calc = copy.deepcopy(self.calc)
        for calc_ in new_calc.values():
            calc_.remove_payment(date)
        return new_calc


def main():
    """Запускает главное окно калькулятора"""
    application = tkinter.Tk()
    window = MainWindow(application)
    application.protocol("WM_DELETE_WINDOW", window.fileQuit)
    application.mainloop()


main()
