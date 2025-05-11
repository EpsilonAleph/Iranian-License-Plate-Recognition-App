import pyodbc

# Connection parameters
server = 'localhost'
database = 'MechanicShopDB'
driver = 'ODBC Driver 17 for SQL Server'
connection_string = f'DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

try:
    conn = pyodbc.connect(connection_string)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print("Connection failed:")
    print(e)
