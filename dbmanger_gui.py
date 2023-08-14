import pandas as pd
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QScrollArea, QLabel, QTextEdit, QComboBox, QLineEdit, QPlainTextEdit, QTextBrowser, QSizePolicy
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLineEdit, QInputDialog
from PyQt5.QtCore import Qt, QObject, QEvent, QCoreApplication
from PyQt5 import QtWidgets, uic
import os
import re
import configparser
import win32gui
import win32process
import psutil
import sys
import threading
import pygetwindow as gw
import mysql.connector
import requests
import db_manager

class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # Declare variables
        self.db_manager = db_manager.DBManager()
        self.db_config = None
        self.selected_db_config = None
        self.db_name = None
        self.default_db_name = None
        self.table_name = None
        self.data_file_base_path = None
        self.data_file_path = None
        self.ref_column = None
        self.selected_rb_option = None
        self.init_ui()
        self.init_others()
    def init_ui(self):
        # Load the UI file
        uic.loadUi('db_manager.ui', self)
        self.db_config = configparser.ConfigParser()
        self.db_config.read('./ignore/db_config.ini')
        db_names = [i[0] for i in self.db_config.items()]
        self.output(f"DB list: {db_names}")
        self.cb_db_name.clear()
        self.cb_db_name.addItems([""]+db_names)
        self.rb_ignore.setChecked(True)
        self.show()
    def init_others(self):
        self.data_file_base_path = './data/'
        self.default_db_name = 'ffbe'
        self.refresh_data_foler()
    def connect_to_db(self):
        """
        DB에 연결 후, Table 이름을 받아온다.
        :return:
        """
        print(f"Connecting to DB - {self.db_name}.")
        if not self.db_name:
            self.cb_db_name.setCurrentText(self.default_db_name)
        self.set_table_names_from_server_to_cb()
        self.te_output.setText("Initiating downloader")
    def download_from_server(self):
        if not (self.db_name and self.table_name):
            print("Select db and table first")
            return False
        else:
            res = self.db_manager.server_to_excel()
            self.output(res)
    def set_table_names_from_server_to_cb(self):
        if not self.db_name:
            print("Select db first")
            return False
        else:
            table_names = self.db_manager.show_table()
            self.cb_table_name.addItems([""]+table_names)
    def write_to_server(self):
        res = self.db_manager.excel_to_server()
        self.output(res)
    def on_cb_table_name_changed(self, str):
        if str:
            self.set_params(str)
            #칼럼명 가지고 오기
            column_names = self.db_manager.show_columns()
            self.cb_col_name.clear()
            self.cb_col_name.addItems([""]+column_names)
            self.cb_data_file_name.setCurrentText(str+".xlsx")
        else:
            self.table_name = None
    def set_params(self, str):
        try:
            if str:
                self.db_name = self.cb_db_name.currentText()
                self.selected_db_config = self.db_config[self.db_name]
                self.table_name = self.cb_table_name.currentText()
                self.ref_column = self.cb_col_name.currentText()
                self.data_file_path = self.data_file_base_path + self.cb_data_file_name.currentText()
                self.selected_rb_option = 'ignore' if self.rb_ignore.isChecked() else 'replace'
                print(f"Selected RB option: {self.selected_rb_option}")
                self.set_db_manger_params()
        except Exception as e:
            self.output(f"Error in set_params with {str}")
            self.output(f"Exception: {e}")
    def refresh_data_foler(self):
        print(f"Refreshing data folder, base_pah:{self.data_file_base_path}, currentText: {self.cb_data_file_name.currentText()}")
        if self.cb_data_file_name.currentText():
            # data 폴더 refresh
            prev_selected_text = self.cb_data_file_name.currentText()
        else:
            prev_selected_text = ""
        data_files = [d for d in os.listdir(self.data_file_base_path) if os.path.isfile(self.data_file_base_path + d)]
        self.cb_data_file_name.clear()
        self.cb_data_file_name.addItems([""] + data_files)
        print("AA")
        if prev_selected_text in data_files:
            self.cb_data_file_name.setCurrentText(prev_selected_text)
    def set_db_manger_params(self):
        self.db_manager.set_params(config=self.selected_db_config,
                                   db_name=self.db_name,
                                   table_name=self.table_name,
                                   data_file_base_path=self.data_file_base_path,
                                   data_file_path=self.data_file_path,
                                   ref_column=self.ref_column,
                                   write_option=self.selected_rb_option)
    def output(self, msg):
        self.te_output.setText(f"{msg}")
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    widget = MyWidget()
    widget.setWindowTitle("DB Manager v0.1")
    sys.exit(app.exec_())