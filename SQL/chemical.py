import sqlite3
def query_by_cas_number(cas_number):
    conn = sqlite3.connect('/home/qhyoo/pycode/qt_code/chemicals.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM chemicals WHERE cas = ?"
    cursor.execute(query, (cas_number,))
    result = cursor.fetchone()
    conn.close()
    return result

# # 测试查询函数
# test_cas_number = '56-87-1'
# result = query_by_cas_number(test_cas_number)
# if result:
#     print(f"\nQuery result for CAS number {test_cas_number}:")
#     print(result)
# else:
#     print(f"\nNo entry found for CAS number {test_cas_number}")



