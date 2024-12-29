import sqlite3
from fuzzywuzzy import process
from collections import defaultdict

from src.tasks.knowledgegraph.relation_filter import SentenceTransformerRetrieval

import re

def strip_quotes(s):
    if (s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'"):
        return s[1:-1]
    else:
        return s

# may not be very necessary to implement checkers for other clauses for now

def where(where_clause, from_clause, conn):  # the FROM clause must be specified before the WHERE clause
    # todo: give more fine-grained feedback when from_clause involves a JOIN
    # e.g., where("WHERE satscores.cname = 'Contra Costa' AND schools.FundingType = 'Directly funded' AND satscores.NumTstTakr <= 250")
    # 'Contra Costa' exist in both satscores.cname and schools.County, but you can't find it when the FROM clause is FROM schools JOIN satscores ON schools.CDSCode = satscores.cds.
    # Or maybe for JOIN tables, when check the condition we only do it for the original one. (I prefer this solution)

    where_clause = strip_quotes(where_clause)
    from_clause = strip_quotes(from_clause)
    if where_clause[:5] != "WHERE":
        return "Please specify a WHERE clause. Start with 'WHERE'."
    else:
        where_clause = where_clause[5:].strip()

    if "* 1.0" in where_clause:
        return "Please use CAST to convert the value type instead of multiplying by 1.0."

    conditions = []

    pattern = re.compile(
        r"([\w\.]*`[^`]+`|\b[\w\.]+\b)\s*(=|<>|!=|>=|<=|<|>|NOT LIKE|LIKE|IS NOT|IS)\s*"
        r"(NULL|TRUE|FALSE|'[^']*'|\"[^\"]*\"|\d+(?:\.\d+)?(?:,\d+)*(?:\.\d+)?)|"
        r"([\w\.]*`[^`]+`|\b[\w\.]+\b)\s+IN\s+\(([^)]+)\)|"
        r"([\w\.]*`[^`]+`|\b[\w\.]+\b)\s+BETWEEN\s+('[^']+?'\s+AND\s+'[^']+?'|\d+\s+AND\s+\d+)|"
        r"([\w\.]*`[^`]+`|\b[\w\.]+\b)\s*=\s*(\(SELECT\s+(?:(?!\)\s*\)).)+\))|"
        # nested math expressions are not supported
        r"\(?([`\w\.]+\s[*\/+-]\s[`\w\.]+)\)?\s*(=|<>|!=|>=|<=|<|>|LIKE)\s*([\d\.]+)|"
        # the remaining patterns are for CAST
        r"\(?([`\w\.\s\(\)-]+[*\/+-]\s*CAST\([`\w\.\s\(\)-]+\sAS\s[A-Z]+\))\)?\s*(=|<>|!=|>=|<=|<|>|LIKE)\s*([\d\.]+)|"
        r"\(?(CAST\([`\w\.\s\(\)-]+\sAS\s[A-Z]+\)\s*[*\/+-]\s*[`\w\.\s\(\)-]+)\)?\s*(=|<>|!=|>=|<=|<|>|LIKE)\s*([\d\.]+)|"
        r"\(?(CAST\([`\w\.\s\(\)-]+\sAS\s[A-Z]+\)\s*[*\/+-]\s*CAST\([`\w\.\s\(\)-]+\sAS\s[A-Z]+\))\)?\s*(=|<>|!=|>=|<=|<|>|LIKE)\s*([\d\.]+)",
        re.IGNORECASE | re.DOTALL
    )




    # Search for patterns and extract conditions
    for match in pattern.finditer(where_clause):
        # BETWEEN condition
        if match.group(6):
            # column = match.group(6).strip("`")
            column = match.group(6)
            values = match.group(7).replace("'", "").split(' AND ')
            conditions.append({
                'column': column,
                'operator': 'BETWEEN',
                'value': values
            })
        # IN condition
        elif match.group(4):
            # column = match.group(4).strip("`")
            column = match.group(4)
            in_values = match.group(5).split(',')
            in_values = [value.strip().strip("'\"") for value in in_values]
            conditions.append({
                'column': column,
                'operator': 'IN',
                'value': in_values
            })
        elif match.group(13):
            # column = match.group(13).strip("`")
            column = match.group(13)
            operator = match.group(14)
            value = match.group(15)
            conditions.append({
                'column': column,
                'operator': operator,
                'value': value
            })
        elif match.group(16):
            # column = match.group(16).strip("`")
            column = match.group(16)
            operator = match.group(17)
            value = match.group(18)
            conditions.append({
                'column': column,
                'operator': operator,
                'value': value
            })
        elif match.group(19):
            # column = match.group(19).strip("`")
            column = match.group(19)
            operator = match.group(20)
            value = match.group(21)
            conditions.append({
                'column': column,
                'operator': operator,
                'value': value
            })
        # Other conditions
        elif match.group(1) or match.group(10):
            # column = match.group(1) if match.group(1) else match.group(10).strip("`")
            column = match.group(1) if match.group(1) else match.group(10)
            operator = match.group(2) if match.group(2) else match.group(11)
            value = match.group(3) if match.group(3) else match.group(12)
            value = value.strip("'\"") if value not in ['NULL', 'TRUE', 'FALSE'] else value
            conditions.append({
                'column': column,
                'operator': operator,
                'value': value
            })
        # Subquery condition
        elif match.group(8):
            # column = match.group(8).strip("`")
            column = match.group(8)
            operator = '='
            # Subquery will be captured, including the SELECT keyword and parentheses
            subquery = match.group(9)
            conditions.append({
                'column': column,
                'operator': operator,
                'value': subquery
            })

    for condition in conditions:
        condition['column'] = condition['column'].strip(" ")
        # remove extra AND and OR prefix in the column name; this is a bit akward but works
        if condition['column'].startswith('AND '):
            condition['column'] = condition['column'][4:]
        elif condition['column'].startswith('OR '):
            condition['column'] = condition['column'][3:]

    for condition in conditions:
        if not (' / ' in condition['column'] or ' * ' in condition['column'] or ' + ' in condition['column'] or ' - ' in condition['column']):
            fields = condition['column'].split('.')
            if len(fields) == 2:
                if ' ' in fields[0] and fields[0][0] != '`':
                    fields[0] = f"`{fields[0]}`"
                if ' ' in fields[1] and fields[1][0] != '`':
                    fields[1] = f"`{fields[1]}`"
                condition['column'] = '.'.join(fields)
            elif len(fields) == 1:
                if ' ' in fields[0] and fields[0][0] != '`':
                    fields[0] = f"`{fields[0]}`"
                condition['column'] = fields[0]


        if condition['operator'] == 'BETWEEN':
            condition['value'] = f"'{condition['value'][0]}' AND '{condition['value'][1]}'"
        elif condition['operator'] == 'IN':
            if len(condition['value']) == 1 and condition['value'][0].__contains__('SELECT'):
                condition['value'] = f"({condition['value'][0]})"
            else:
                value_str = ""
                for value in condition['value']:
                    value_str += f"'{value}', "
                value_str = value_str[:-2]
                condition['value'] = f"({value_str})"
        else:
            if 'SELECT' not in condition['value']:
                if not (' / ' in condition['column'] or ' * ' in condition['column'] or ' + ' in condition['column'] or ' - ' in condition['column']):
                    condition['value'] = f"'{condition['value']}'"
            else:
                condition['value'] = f"({condition['value']})"
        
    results = conditions
    if len(results) == 0:
        print("Corner case WHERE:", where_clause)  
        return "Please continue."   # just continue, maybe it's a corner case that can't be handled by the current regex

    conditions_no_match = []
    conditions_partial_match = []
    for condition in results:
        cursor = conn.cursor()
        if '.' not in condition['column']:
            sql_query = f"SELECT COUNT(*) {from_clause} WHERE {condition['column']} {condition['operator']} {condition['value']}"
        else:
            try:
                table, column = condition['column'].split('.')
                if table[0] in ['"', "'", '`'] and table[-1] in ['"', "'", '`']:
                    table = table[1:-1]
                if column[0] in ['"', "'", '`'] and column[-1] in ['"', "'", '`']:
                    column = column[1:-1]
                sql_query = f"SELECT COUNT(*) FROM '{table}' WHERE `{column}` {condition['operator']} {condition['value']}"
            except Exception as e:
                # e.g., WHERE (satscores.NumGE1500 / satscores.NumTstTakr) > 0.3
                sql_query = f"SELECT COUNT(*) {from_clause} WHERE {condition['column']} {condition['operator']} {condition['value']}"
        cursor.execute(sql_query)
        count = cursor.fetchone()[0]
        if count == 0:
            conditions_no_match.append(condition)
        elif '.' in condition['column']:
            sql_query = f"SELECT COUNT(*) {from_clause} WHERE {condition['column']} {condition['operator']} {condition['value']}"
            cursor.execute(sql_query)
            count1 = cursor.fetchone()[0]
            if count1 == 0:
                conditions_partial_match.append(condition)


        cursor.close()

    if conditions_no_match or conditions_partial_match:
        rtn_str = "The following conditions do not match any rows:"
        for condition in conditions_no_match:
            rtn_str += f"\n- {condition['column']} {condition['operator']} '{condition['value']}'"
            if ' / ' in condition['column'] or ' * ' in condition['column'] or ' + ' in condition['column'] or ' - ' in condition['column']:
                rtn_str += "\nFor numerical values, you may need to use the CAST function to convert the column to a numerical type first, e.g., CAST(XXX AS REAL)."
            elif condition['operator'] in ["=", "LIKE", "IN"]:
                rtn_str += f" (Note: You may try get_distinct_values to find distinct values in {condition['column']} and find_columns_containing_cell_value to find columns that contain the value you want first. This will provide you with more information to determine the right condition. If this is a Date column, you may try get_date_format to find the right date format instead.)"
        for condition in conditions_partial_match:
            rtn_str += f"\n- {condition['column']} {condition['operator']} '{condition['value']}'"
            rtn_str += f"\nThis condition can be satisfied in the original table, but not in the joined table. You may use find_columns_containing_cell_value to find other possible columns that contain the value you want first. This will provide you with more information to determine the right condition."
            
        
        # rtn_str += "\nIt's also likely that this query is correct and expected to return no results.\nPlease continue."
        
    else:
        if "IS NOT NULL" in where_clause:
            rtn_str = "IS NOT NULL can be a weak condition sometimes. It is adivsed to further explore the column using get_distinct_values first."
        else:
            rtn_str = "Please continue."
        
    
    return rtn_str


def detect_inproper_search_value(search_value, conn):
    # Sometimes the agent may misunderstands find_columns_containing_cell_value and use it to check whether a column name exists. We need to guard against this.
    # list all column names in the database
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]
    column_names = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns = [column[1] for column in cursor.fetchall()]
        column_names.extend(columns)
    if search_value in column_names:
        return True
    else:
        return False


def find_columns_containing_cell_value(search_value, conn):
    """
    Searches for a string value in all columns of all tables in an SQLite3 database using fuzzy matching.
    
    Parameters:
    - conn: SQLite3 database connection object.
    - search_value: String value to search for.
    
    Returns:
    - List of tuples (table_name, column_name) where the value closely matches.
    """
    cursor = conn.cursor()

    # Fetch all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]
    search_value = strip_quotes(search_value)

    if detect_inproper_search_value(search_value, conn):
        return "The value you are searching for is a column name. This is not the intended usage of find_columns_containing_cell_value. If you want to find distinct values in a column, please use get_distinct_values. If you want to check whether a column exist, please directly look at the DB schema."

    matched_columns = []

    for table in tables:
        # Get all column names for the table
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns = [column[1] for column in cursor.fetchall()]
        # print(table, "columns:", columns)
        for col in columns:
            cursor.execute(f"SELECT DISTINCT `{col}` FROM '{table}'")
            distinct_values = [str(row[0]) for row in cursor.fetchall()]
            # print(col, distinct_values)
            if search_value in distinct_values:
                matched_columns.append((table, col))

    if len(matched_columns) > 0:
        rtn_str = f"The columns below contain the value {search_value}:"
        for table, column in matched_columns:
            rtn_str += f"\n- {table}.`{column}`"
    else:
        rtn_str = "No columns contain the exact value. You may try fuzzy matching."

    cursor.close()

    return rtn_str


# todo: may consider abberviation, e.g., State Special School -> SSS, high school -> HS
def find_columns_containing_cell_value_fuzzy(search_value, conn):
    """
    Searches for a string value in all columns of all tables in an SQLite3 database using fuzzy matching.
    
    Parameters:
    - conn: SQLite3 database connection object.
    - search_value: String value to search for.
    
    Returns:
    - List of tuples (table_name, column_name) where the value closely matches.
    """
    cursor = conn.cursor()

    value_map = defaultdict(lambda: [])
    values = set()
    search_value = strip_quotes(search_value)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]

    if detect_inproper_search_value(search_value, conn):
        return "The value you are searching for is a column name. This is not the intended usage of find_columns_containing_cell_value_fuzzy. If you want to find distinct values in a column, please use get_distinct_values. If you want to check whether a column exist, please directly look at the DB schema."

    for table in tables:
        # Get all column names for the table
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns = [column[1] for column in cursor.fetchall()]
        # print(table, "columns:", columns)
        for col in columns:
            cursor.execute(f"SELECT DISTINCT `{col}` FROM '{table}' LIMIT 20")
            distinct_values = [str(row[0]) for row in cursor.fetchall()]
            for value in distinct_values:
                value_map[value].append((table, col))
                values.add(value)


    retriever = SentenceTransformerRetrieval(list(values), 'sentence-transformers/all-mpnet-base-v2')
    top_k_values = retriever.get_top_k_sentences(search_value, k=5, distinct=True)

    rtn_str = f"The columns below may contain relevant values for {search_value}:"
    for value in top_k_values:
        for table, column in value_map[value]:
            rtn_str += f"\n- {table}.`{column}` contains '{value}'"

    cursor.close()

    return rtn_str


def get_distinct_values(table, column, conn, question):
    # could be nested twice
    if column[0] in ['"', "'", '`'] and column[-1] in ['"', "'", '`']:
        column = column[1:-1]
    if column[0] in ['"', "'", '`'] and column[-1] in ['"', "'", '`']:
        column = column[1:-1]
    if table[0] in ['"', "'", '`'] and table[-1] in ['"', "'", '`']:
        table = table[1:-1]
    if table[0] in ['"', "'", '`'] and table[-1] in ['"', "'", '`']:
        table = table[1:-1]
    cursor = conn.cursor()
    # sql_query = f"SELECT DISTINCT `{column}` FROM '{table}' LIMIT 50"
    sql_query = f"SELECT DISTINCT `{column}` FROM '{table}'"
    cursor.execute(sql_query)
    values = [str(row[0]) for row in cursor.fetchall()]
    if len(values) > 50:
        retriever = SentenceTransformerRetrieval(values, 'sentence-transformers/all-mpnet-base-v2')
        values = retriever.get_top_k_sentences(question, k=50, distinct=True)
    rtn_str = f"The distinct values for {table}.`{column}` are: [{', '.join(values)}]. At most 50 values are shown due to length limit. Other values are omitted. This helps you to understand how values in {table}.`{column}` are represented, which may not be the same as you expected. Some representations can be ambiguous; for example, the initial 'M' in gender column is likely interpreted to stand for 'Male'. This help you to update your query to be faithful to the database. If you don't see the value you want, please try searching for it using find_columns_containing_cell_value or is_value_in_column."
    cursor.close()
    return rtn_str


def get_date_format(table, column, conn):
    # could be nested twice
    if column[0] in ['"', "'", '`'] and column[-1] in ['"', "'", '`']:
        column = column[1:-1]
    if column[0] in ['"', "'", '`'] and column[-1] in ['"', "'", '`']:
        column = column[1:-1]
    if table[0] in ['"', "'", '`'] and table[-1] in ['"', "'", '`']:
        table = table[1:-1]
    if table[0] in ['"', "'", '`'] and table[-1] in ['"', "'", '`']:
        table = table[1:-1]
    cursor = conn.cursor()
    # sql_query = f"SELECT DISTINCT `{column}` FROM '{table}' LIMIT 50"
    sql_query = f"SELECT DISTINCT `{column}` FROM '{table}'"
    cursor.execute(sql_query)
    values = [str(row[0]) for row in cursor.fetchall()][:3]
    rtn_str = f"Several example items from {table}.`{column}` are:\n- " + "\n- ".join(values) + "\nEvery digit in these example items tells you how the date is represented in the database."
    cursor.close()
    return rtn_str


def is_value_in_column(table, column, value, conn):
    if column[0] in ['"', "'", '`'] and column[-1] in ['"', "'", '`']:
        column = column[1:-1]
    if column[0] in ['"', "'", '`'] and column[-1] in ['"', "'", '`']:
        column = column[1:-1]
    if table[0] in ['"', "'", '`'] and table[-1] in ['"', "'", '`']:
        table = table[1:-1]
    if table[0] in ['"', "'", '`'] and table[-1] in ['"', "'", '`']:
        table = table[1:-1]
    value = strip_quotes(value)
    cursor = conn.cursor()
    sql_query = f"SELECT COUNT(*) FROM '{table}' WHERE `{column}` = '{value}'"
    # print(sql_query)
    cursor.execute(sql_query)
    count = cursor.fetchone()[0]
    cursor.close()
    if count == 0:
        rtn_str = f"The value '{value}' does not exist in {table}.`{column}`."
    else:
        rtn_str = f"The value '{value}' exists in {table}.`{column}`."
    return rtn_str


def search_by_SQL(query, conn):
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    rtn_str = f"Query: {query}\n"
    rtn_str += f"Results (only first 10 rows are shown due to length limit): {results[:10]}"
    cursor.close()
    return rtn_str



