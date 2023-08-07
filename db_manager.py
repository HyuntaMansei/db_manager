import pandas as pd
import os
import re
import mysql.connector

class DBManager():
    def __init__(self):
        # Declare variables
        self.selected_db_config = None
        self.db_name = None
        self.table_name = None
        self.data_file_base_path = None
        self.data_file_path = None
        self.output = callable
        self.write_option = None
        self.ref_column = None
        # Initiating Methods
        self.init_db_manager()
        self.init_others()
    def init_db_manager(self):
        self.output = print
    def init_others(self):
        pass
    def set_params(self, config=None, db_name=None, table_name=None, data_file_base_path=None, data_file_path=None, ref_column=None, write_option=None):
        if config:
            self.selected_db_config = config
        if db_name:
            self.db_name = db_name
        if table_name:
            self.table_name = table_name
        if data_file_base_path:
            self.data_file_base_path = data_file_base_path
        if data_file_path:
            self.data_file_path = data_file_path
        if ref_column:
            self.ref_column = ref_column
        if write_option:
            self.write_option = write_option
    def show_table(self):
        """
        Server에서 Table 이름을 받아온다.
        :return:
        """
        self.output("Fetch table names.")
        sql = "show tables"
        data = self.fetch_data_from_server(sql)
        table_names = [d[0] for d in data]
        return table_names
    def show_columns(self):
        """
        선택되어진 table에서 칼럼명을 돌려준다.
        :return:
        """
        if self.table_name:
            table_name = self.table_name
            sql = f"SHOW COLUMNS FROM {table_name}"
            data = self.fetch_data_from_server(sql)
            col_names = [c[0] for c in data]
            return col_names
        else:
            self.output("No table_name")
            return False
    def server_to_excel(self):
        try:
            #현재 엑셀파일이 있으면 numbering을 통해서 파일 이름을 정한다.
            file_path = self.get_file_name_to_write()
            self.output(f"Download from server, file name:{file_path}")
            sql = f'select * from {self.table_name}'
            data, col_names = self.fetch_data_from_server_with_col_names(sql)
            df = pd.DataFrame(data, columns=col_names)
            df.to_excel(file_path, index=False)
        except Exception as e:
            return e
        return True
    def excel_to_server(self):
        print("From excel to Server.")
        print(f"Table: {self.table_name}, Ref. Column: {self.ref_column}, Data File: {self.data_file_path}, write option: {self.write_option}")
        df = pd.read_excel(self.data_file_path).fillna("")
        # print(df)
        common_column_list = [c for c in self.show_columns() if c in df.columns.tolist()]
        print(common_column_list)
        res = self.df_to_server(self.table_name, common_column_list, self.ref_column, df, self.write_option)
        print("excel to server, completed")
        return res
    def df_to_server(self, table_name, column_name_list, ref_column, df:pd.DataFrame, write_option:str):
        print(f"In function df_to_server, table_name:{table_name}, column_names:{column_name_list}, ref. col: {ref_column} write option: {write_option}\ndf:{df.iloc[0].head()}")
        rows_to_replace = []
        rows_to_insert = []
        for i, d in df.iterrows():
            # sql = f"SELECT 1 FROM {table_name} where {ref_column} = '{d[ref_column]}'"
            sql = f"SELECT 1 FROM {table_name} where {ref_column} = %s"
            value = (d[ref_column],)
            print(sql, value)
            res = self.fetch_data_from_server(sql, value)
            print(res)
            if res:
                print(f"Already exist for {d[ref_column]}")
                rows_to_replace.append(i)
            else:
                rows_to_insert.append(i)
                print(f"{i}th row is ready to write:\n{d.head(n=3)}")
        df_to_replace = df.iloc[rows_to_replace][column_name_list] if rows_to_replace else None
        df_to_insert = df.iloc[rows_to_insert][column_name_list] if rows_to_insert else None
        print("Try to write to server")
        if rows_to_insert:
            sql = f"""INSERT INTO {table_name} ({','.join(column_name_list)}) VALUES 
            ({','.join(['%s']*len(column_name_list))})  
            """
            print(sql)
            self.write_to_server(sql, df_to_insert.values.tolist())
        print(df_to_replace)
        if write_option == 'replace':
            if rows_to_replace:
                print("Try to replace to server")
                values_list = []
                for i, d in df_to_replace.iterrows():
                    sql = f"""UPDATE {table_name} SET
                    {' = %s, '.join(column_name_list)}=%s WHERE
                    {ref_column}=%s
                    """
                    values_list.append((*d.values.tolist(),d[ref_column]))
                print(sql)
                print(values_list[0])
                self.write_to_server(sql, values_list)
    def connect_db(self):
        conn = mysql.connector.connect(
            user=self.selected_db_config['user'],
            host=self.selected_db_config['host'],
            password=self.selected_db_config['password'],
            database=self.selected_db_config['database'])
        return conn
    def fetch_data_from_server(self, sql, values=None):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            if not values:
                cursor.execute(sql)
            else:
                cursor.execute(sql, values)
            res = cursor.fetchall()
            cursor.close()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if conn.is_connected():
                conn.close()
        return res
    def fetch_data_from_server_with_col_names(self, sql, values=None):
        conn = self.connect_db()
        cursor = conn.cursor()
        if not values:
            cursor.execute(sql)
        else:
            cursor.execute(sql, values)
        res = cursor.fetchall()
        col_names = cursor.column_names
        cursor.close()
        conn.close()
        return res, col_names
    def write_to_server(self, sql, values):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            if type(values) != list:
                cursor.execute(sql, values)
            else:
                for i in range(len(values)):
                    cursor.execute(sql, values[i])
            res = cursor.fetchall()
            conn.commit()
            cursor.close()
        except Exception as e:
            print("Error: ", e)
        finally:
            conn.close()
            return res
    def get_file_name_to_write(self):
        #현재 path에 해당 파일이름이 있는지 확인. 있으면 넘버링 증가. 다시 확인.
        if not self.table_name:
            self.output("No table name")
            return False
        file_path = self.data_file_base_path+self.table_name
        while os.path.isfile(file_path+'.xlsx'):
            res = self.extract_and_add_one(file_path)
            # print(file_path, self.extract_numbers_between_parentheses(file_path))
            if self.extract_numbers_between_parentheses(file_path):
                #넘버링이 있는 경우
                file_path = res
                # print(f"add one: {res}")
            else:
                file_path += '(1)'
                # print(f"first numbering:", file_path)
        return file_path+'.xlsx'
    def extract_numbers_between_parentheses(self, input_string):
        pattern = r'\((\d+)\)'
        numbers = re.findall(pattern, input_string)
        return [int(num) for num in numbers]
    def extract_and_add_one(self, input_string):
        def add_one(match):
            number = int(match.group(1))
            return '('+str(number + 1)+')'
        pattern = r'\((\d+)\)'
        result = re.sub(pattern, add_one, input_string)
        return result