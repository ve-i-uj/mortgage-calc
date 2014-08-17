#!/usr/bin/env python3

"""Python distutils setup script for mortgage_calc."""

from distutils.core import setup

setup(name="mortgage_calc",
      version="1.0",
      author="Alexey Burov",
      author_email="burov_alexey@mail.ru",
      description='Mortgage Calculator',
      py_modules=['Calculation', 'MyDateLib', 'MyForms', 'MyWidgets'],
      packages=[],
      requires = ['python (>= 3.1)'],
      scripts=['mortgage_calc.pyw']
      )
