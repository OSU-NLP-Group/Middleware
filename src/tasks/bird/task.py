from src.task import Task, Dataset, DataPiece
from .db_api import *

import re
import sys
import json
import sqlite3

from multiprocessing import Process, Queue

def run_query(cursor, query, result_queue):
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        result_queue.put(results)
    except Exception as e:
        result_queue.put(["exception: " + str(e)])


INSTRUCTIONS = """
You are an agent that answers questions based on the info in a database. To achieve this, you need to write the correct SQL queries step by step.
The following functions can help you to better navigate the database.

1. find_columns_containing_cell_value(value: str)
This function can help to find columns that contain the given cell value, which can help you do make better decisions in decding the right column to use. Note that, value here means cell value in the rows of the column, not the column name.

2. find_columns_containing_cell_value_fuzzy(value: str)
Sometimes find_columns_containing_cell_value may not find a column with exact matched cell value. This function can help to find columns that potentially contain the target cell value with fuzzy matching. Note that, value here means cell value in the rows of the column, not the column name.

3. get_distinct_values(table: str, column: str)
Returns the distinct values in the given column. This may mainly help you make better decisions in decding the right value to use. 

4. is_value_in_column(table: str, column: str, value: str)
Returns whether the given value is in the given column. You can use this function to better detect the right column to use.

5. get_date_format(table: str, column: str)
Returns an example item of the given Date column. This may help you to better understand the date format in the column.

6. search_by_SQL(query: str)
You may also directly explore the database by writing SQL queries. This is more flexible if the above functions cannot help you find the right information.

In addition to these DB-navigation tools, to construct the target SQL query, you MUST use the following functions to construct the SQL query step by step.
7. from(from_statement: str)
This function specifies the FROM clause, e.g., from("FROM table1") or from("FROM table1 JOIN table2 ON table1.id = table2.id")

8. where(where_statement: str)
This function specifies the WHERE clause, e.g., where("WHERE table1.id = 1")

9. select(select_statement: str)
This function specifies the SELECT clause, e.g., select("SELECT table1.id")

10. group_by(group_by_statement: str)
This function specifies the GROUP BY clause, e.g., group_by("GROUP BY table1.id")

11. having(having_statement: str)
This function specifies the HAVING clause, e.g., having("HAVING table1.id = 1")

12. order_by(statement: str)
This function specifies additional constraint like ordering. For example, order_by("ORDER BY table1.id DESC LIMIT 3").

You can only take ONE action at a time!! For each step, you may first state your thought, then take an action following the format of Thought: ... Action: ...
Make sure that the specified action comes right after Action:. 
For example, 
Thought: I need to check the distinct values of the column colB in table tabA to help me make better decisions.
Action: get_distinct_values(tabA, colB) 
Once you think you have gathered enough information, you can construct the SQL query and get the answer. Return your final SQL query by stating it right after Final Answer: ... Also, please do not include any linebreak (i.e., \\n).
e.g.,
Final Answer: SELECT x FROM tableA
"""
# add the following to weaker models' prompts (including 3.5-turbo)
# There can only be one action (i.e., one function call) after "Action: " in your response!!
# Once you have proposed a function call, please wait for me to return the execution result.

# DEMOS = """
# Here is a demo that you can use to get started.

# Question: the bipropellant rocket engine with kerosene and gas-generator cycle is designed by who? \nEntities: [Gas-generator cycle, Kerosene]
# Thought: I need to first find engines with gas-generator cycle. To acheive this, I will query the KB to find relations connected to the entity 'Gas-generator cycle' and see if any of them can help me find the answer.
# Action: get_relations(Gas-generator cycle)
# Observation: [spaceflight.rocket_engine_cycle.rocket_engines, spaceflight.satellite.orbiting, spaceflight.rocket_stage.fuel, spaceflight.satellite_manufacturer.spacecraft_manufactured, automotive.fuel.engines]
# Thought: From the above relations, I might use spaceflight.rocket_engine_cycle.rocket_engines to find the engines of Gas-generator cycle.
# Action: get_neighbors(Gas-generator cycle, spaceflight.rocket_engine_cycle.rocket_engines)
# Observation: variable #0, which are instances of spaceflight.bipropellant_rocket_engine
# Thought: I also need to find engines with kerosene. To acheive this, I will query the KB to find relations connected to the entity 'Kerosene'.
# Action: get_relations(Kerosene)
# Observation: [spaceflight.satellite_manufacturer.spacecraft_manufactured, automotive.fuel.engines, spaceflight.rocket_engine_cycle.rocket_engines]
# Thought: From the above relations, I might use spaceflight.rocket_engine_cycle.rocket_engines to find engines with kerosene cycle.
# Action: get_neighbors(Kerosene, spaceflight.rocket_engine_cycle.rocket_engines)
# Observation: variable #1, which are instances of spaceflight.bipropellant_rocket_engine
# Thought: The engines with both gas-generator cycle and kerosene cycle shoule be the intersection of variable #0 and variable #1.
# Action: intersection(#0, #1)
# Observation: variable #2, which are instances of spaceflight.bipropellant_rocket_engine
# Thought: Now I need to find who designed such engines, which will be the final answer. To acheive this, I will query the KB to find relations connected to the variable #2.
# Action: get_relations(#2)
# Observation: [spaceflight.rocket_engine.manufactured_by, spaceflight.rocket_engine.designed_by, spaceflight.rocket_engine.design_period, spaceflight.rocket_engine.status]
# Thought: From the above relations, I might use spaceflight.rocket_engine.designed_by to find the designer of the engines.
# Action: get_neighbors(#2, spaceflight.rocket_engine.designed_by)
# Observation: variable #3, which are instances of pspaceflight.rocket_engine_designer
# Thought: #3 is the final answer to the question, which represents the target rocket engine designer.
# Final Answer: #3
# """

# zero-shot for chatgpt
ONE_SHOT=[
"""
The following is a demo of formatting, which does not have real meaning, but you need to strictly follow the format.
DB Schema: ...
Question: ...
Please write the SQL query step by step.""",
"""Thought: ...
Action: get_distinct_values(...)""",
"""The distinct values for ... are [...]""",
"""Thought: ...
Action: where(...)""",
"""...""",
"""Thought: ... I have enough information to build the final SQL query. I need to return the final SQL with no linebreaks as required.
Final Answer: SELECT ... FROM ... WHERE ..."""
]

# one-shot for chatgpt
# ONE_SHOT=[
# """
# The following is a demo of formatting, which does not have real meaning, but you need to strictly follow the format.
# DB Schema: CREATE TABLE frpm
# (
#     CDSCode                                       TEXT not null
#         primary key,
#     `Academic Year`                               TEXT  null,
#     ...
# )

# CREATE TABLE satscores
# (
#     cds         TEXT not null
#         primary key,
#     rtype       TEXT  not null,
#     sname       TEXT null,
#     AvgScrMath  INTEGER          null,
#     ...
# )

# CREATE TABLE schools
# (
#     CDSCode     TEXT not null
#         primary key,
#     GSoffered   TEXT null,
#     GSserved    TEXT  null,
#     Virtual     TEXT  null,
#     Latitude    REAL      null,
#     Longitude   REAL      null,
#     ...
# )
# Question: How many schools with an average score in Math under 400 in the SAT test are exclusively virtual?
# Please write the SQL query step by step.
# """,
# """
# Thought: I first need to join the satscores with the schools table to get the information about whether the schools are exclusively virtual. This information is in the Virtual column of the schools table. The common column between the two tables is the CDSCode column.
# Action: from("FROM satscores JOIN schools ON satscores.cds = schools.CDSCode")
# """,
# """
# Please continue.
# """,
# """
# Thought: Now I can specify the where clause
# Action: where("WHERE AvgScrMath < 400 AND Virtual = 'Y'")
# """,
# """
# The following conditions do not match any rows:
# - Virtual = 'Y'
# (Note: You may try both get_distinct_values to find distinct values in Virtual and find_columns_containing_cell_value to find columns that contain the value you want first. This will provide you with more information to determine the right condition.)
# """,
# """
# Thought: I need to first check the distinct values in the Virtual column to see how values are represented in this column.
# Action: get_distinct_values("schools", "Virtual")
# """,
# """
# The distinct values for "schools".`Virtual` are: [None, P, N, F]
# """,
# """
# Thought: The distinct values in the Virtual column are None, P, N, F. It's likely that N stands for Non-virtual, F stands for Fully-virtual, and P stands for Partially-virtual. Now I can specify the where clause.
# Action: where("WHERE AvgScrMath < 400 AND Virtual = 'F'")
# """,
# """
# Please continue.
# """,
# """
# Thought: Now I need to select the count of schools that meet the conditions. This will be the final step of constructing the SQL query.
# Action: select("SELECT COUNT(*)")
# """,
# """
# Please continue.
# """,
# """
# Thought: I have constructed all parts of my SQL query. Now I will form the final SQL.
# Final Answer: SELECT COUNT(*) FROM satscores JOIN schools ON satscores.cds = schools.CDSCode WHERE AvgScrMath < 400 AND Virtual = 'F'
# """
# ]

def nice_look_table(column_names: list, values: list):
    rows = []
    # Determine the maximum width of each column
    widths = [max(len(str(value[i])) for value in values + [column_names]) for i in range(len(column_names))]

    # # print the column names
    header = ''.join(f'{column.rjust(width)} ' for column, width in zip(column_names, widths))
    # # print(header)
    # # print the values
    for value in values:
        row = ''.join(f'{str(v).rjust(width)} ' for v, width in zip(value, widths))
        rows.append(row)
    rows = "\n".join(rows)
    final_output = header + '\n' + rows
    return final_output

def generate_schema_prompt(db_path, num_rows=10):
    # extract create ddls
    '''
    :param root_place:
    :param db_name:
    :return:
    '''
    full_schema_prompt_list = []
    conn = sqlite3.connect(db_path)
    # Create a cursor object
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    schemas = {}
    for table in tables:
        if table == 'sqlite_sequence':
            continue
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='{}';".format(table[0]))   # get the create table command to be used in the prompt
        create_prompt = cursor.fetchone()[0]
        schemas[table[0]] = create_prompt
        if num_rows:   # looks like this is not used; num_rows is always None
            cur_table = table[0]
            if cur_table in ['order', 'by', 'group']:
                cur_table = "`{}`".format(cur_table)

            cursor.execute("SELECT * FROM {} LIMIT {}".format(cur_table, num_rows))
            column_names = [description[0] for description in cursor.description]
            values = cursor.fetchall()
            rows_prompt = nice_look_table(column_names=column_names, values=values)
            verbose_prompt = "/* \n {} example rows: \n SELECT * FROM {} LIMIT {}; \n {} \n */".format(num_rows, cur_table, num_rows, rows_prompt)
            schemas[table[0]] = "{} \n {}".format(create_prompt, verbose_prompt)

    for k, v in schemas.items():
        full_schema_prompt_list.append(v)

    schema_prompt = "\n\n".join(full_schema_prompt_list)

    return schema_prompt


class BirdBench(Task):
    def __init__(self, **configs):
        self.round = configs.pop("round", 15)  # maximum round
        self.data_fn = configs.pop("data_file", None)
        self.db_parent_path = configs.pop("db_parent_path", None)
        super().__init__(**configs)

    @property
    def metrics(self):
        def main_metric(outputs, targets):
            EX_sum = 0
            count = 0
            for i in range(len(outputs)):
                if outputs[i] is None:
                    continue
                count += 1    # if None, count will not increase. Pay attention to this!!!

                try:
                    db_file = outputs[i]['db_file']
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute(outputs[i]['predict'])
                    result = cursor.fetchall()
                    cursor.execute(targets[i])
                    gold_result = cursor.fetchall()

                    if len(result) == len(gold_result) == 1 and isinstance(result[0][0], float) and isinstance(gold_result[0][0], float):
                        if round(result[0][0], 2) == round(gold_result[0][0], 2):
                            EX_sum += 1
                    elif set(result) == set(gold_result):
                        EX_sum += 1
                except Exception as e:
                    # print(i, e)
                    # print(outputs[i]['predict'])
                    continue

            return EX_sum / count


        return {
            "main": lambda outputs, targets: main_metric(outputs, targets),
            "EX": lambda outputs, targets: main_metric(outputs, targets)
            }

    def get_data(self):
        data = Dataset()
        with open(self.data_fn, "r") as f:
            data_object = json.load(f)[:20]
            # data_object_tmp = []
            # for item in data_object:
            #     if "require_content_info" in item:
            #         data_object_tmp.append(item)
            # data_object = data_object_tmp

            # data_object = json.load(f)
        for item in data_object:
            if item["SQL"] == "SELECT name FROM sqlite_master WHERE type='table'":
                continue
            gold_answer = item["SQL"]
            data.append(DataPiece(item, gold_answer))  # input and target
        return data

    def predict_single(self, session, data_item): # return OUTPUT object, need to be json serializable
        # todo: return a dictionary including the prediction and metrics per data item
        answer = None   # the target SQL query
        clauses = {
            "select": None,
            "from": None,
            "where": None,
            "group_by": None,
            "having": None,
            "additional": None
        }
        
        actions = []
        useful_execution_messages = []
        
        question = data_item["question"]
        db_id = data_item["db_id"]
        db_file = self.db_parent_path + db_id + "/" + db_id + ".sqlite"
        conn = sqlite3.connect(db_file)

        if " ration " in question or " percentage " in question:
            # I am too lazy to handle the regex for these for now... so just skip them
            session.inject({"role": "user", "content": f"DB Schema: {generate_schema_prompt(db_file)}\nQuestion: {question}\nPlease write the SQL query directly. Specify your final SQL query by stating the query right after Final Answer:... Also, please do not include any linebreak (i.e., \\n).\nFor example, Final Answer: SELECT x FROM tableA"})
        else:
            session.inject({
                "role": "user",
                "content": INSTRUCTIONS 
            })
            session.inject({"role": "agent", "content": "I've understood your instruction, start please."})
            
            # for idx, shot in enumerate(ONE_SHOT):
            #     if idx % 2 == 0:
            #         session.inject({"role": "user", "content": shot})
            #     else:
            #         session.inject({"role": "agent", "content": shot})
            
            session.inject({"role": "user", "content": f"DB Schema: {generate_schema_prompt(db_file)}\nQuestion: {question}\nPlease write the SQL query step by step."})

        feedback = set()
        
        for i in range(self.round + 1):  # an extra round for direct generation if it fails
            if i == self.round - 1:
                session.history[-1]["content"] = session.history[-1]["content"] + "\nNow you MUST provide your final SQL query as this is the last round. Begin your response with Final Answer:.."
            # # print(i, session.history[-1])
            # print("send request to api..")
            try:
                message = session.action()
            except Exception as e:
                execution_messages_try = '\n'.join(useful_execution_messages)
                session.history = []
                session.inject({"role": "user", "content": f"DB Schema: {generate_schema_prompt(db_file)}\nEvidence:{execution_messages_try}\nQuestion: {question}\nPlease write the SQL query directly. Specify your final SQL query by stating the query right after Final Answer:... Also, please do not include any linebreak (i.e., \\n).\nFor example, Final Answer: SELECT x FROM tableA"})
                continue
            message = message.strip('\n')
            message = message.split("\nThought:")[0]  # for mistral
            message = message.replace("\\", "")
            # # print(i, message)
            session.history[-1]["content"] = message
            # print("received message:", message)
            # # print({"role": "agent", "content": message})
            
            pattern = r"(Final Answer:)[\s\n]*(\S)"
            replacement = r"\1\2"
            # Perform the replacement
            message = re.sub(pattern, replacement, message)   
            pattern = r'Final Answer:(.*)'
            if re.findall(r'(?:Find|Final) Answer:', message) and "Thought:" not in message:
                message = message.replace("\n\n", "$$$")
                message = message.replace("\n", " ")
                message = message.split("$$$")[0]
                message = message.split(";")[0]
            match = re.search(pattern, message)
            # final_answer = re.findall(r'(?:Find|Final) Answer:', message)
            if match: 
                answer = match.group(1)
                # print("answer:", answer)
                if answer[0] in ["'", '"'] and answer[-1] in ["'", '"']:
                    answer = answer[1:-1]
                try:
                    if answer.count("SELECT") > 2:
                        # there's no way to timeout sqlite3 effectively, that's very stupid... so to avoid
                        # some weak LLMs to hang there forever, we have to do this...
                        session.inject({"role": "user", "content": f"'{answer}' is too complicated with multiple nested SELECT clauses, which is not likely. Please make a new prediction. Specify your final SQL query by stating Final Answer:.."})
                        # print(f"'{answer}' is too complicated with multiple nested SELECT clauses, which is not likely. Please make a new prediction. Specify your final SQL query by stating Final Answer:..")
                    elif "YEAR(" in answer:
                        session.inject({"role": "user", "content": "Function YEAR is not supported. Please use strftime('%Y', ...) instead."})
                    else:
                        cursor = conn.cursor()
                        cursor.execute(answer)
                        result = cursor.fetchall()
                        
                        # result_queue = Queue()
                        # query_process = Process(target=run_query, args=(cursor, answer, result_queue))

                        # query_process.start()
                        # # Wait for 30 seconds
                        # query_process.join(timeout=30)

                        # # If process is still active, it's taking too long!
                        # if query_process.is_alive():
                        #     query_process.terminate()
                        #     query_process.join()
                        #     result = []
                        #     print("Query timeout.")
                        #     raise Exception("Query timeout.")
                        # else:
                        #     # # print("Query finished.")
                        #     result = result_queue.get()
                        #     if result[0].startswith("exception:"):
                        #         raise Exception(result[0].split("exception:")[1])

                        if len(result)  > 0:
                            break
                        else:
                            session.inject({"role": "user", "content": f"'{answer}' returns empty results. Please make a new prediction. Specify your final SQL query by stating Final Answer:.."})
                            # print(f"'{answer}' returns empty results. Please make a new prediction. Specify your final SQL query by stating Final Answer:..")

                except Exception as e:
                    # clear the history
                    # execution_messages_try = '\n'.join(useful_execution_messages)
                    # session.history = []
                    # session.inject({"role": "user", "content": f"DB Schema: {generate_schema_prompt(db_file)}\nEvidence:{execution_messages_try}\nQuestion: {question}\nPlease write the SQL query directly. Specify your final SQL query by stating the query right after Final Answer:... Also, please do not include any linebreak (i.e., \\n).\nFor example, Final Answer: SELECT x FROM tableA"})
                    
                    session.inject({"role": "user", "content": f"'{answer}' is not a correct SQL query. Please directly state the executable SQL query by stating Final Answer:.."})
                    # print(f"'{answer}' is not a correct SQL query. Please directly state the executable SQL query by stating Final Answer:..")
                    
                    # session.inject({"role": "user", "content": f"'{answer}' is not a correct SQL query. {e}"})
                    # print(f"'{answer}' is not a correct SQL query. {e}")
                    # continue
            else:
                lines = message.split("\n")
                find_action = False
                for line_id, line in enumerate(lines):
                    if re.match(r"Action.*?:", line):   # this requires the action invocation to be in the same line as 'Action:'
                        function_names = re.findall(r'(\w+)\(', line)
                        for function_name in function_names:
                            if function_name == "order_by":
                                session.inject({"role": "user", "content": "Please continue."})
                                # print("Please continue.")
                                find_action = True
                                break
                            if function_name in ["select", "from", "group_by", "having"]:   # not handled for now
                                try:
                                    matches = re.findall(r'{}\([\'"](\s*[\s\S]*?)[\'"]\s*\)'.format(function_name), line)
                                    clause = re.split(r'\s*,\s*', matches[0])[0]
                                    if clause[: len(function_name)] == function_name.upper().replace("_", " "):
                                        if function_name == "select" and clauses["from"] is None:
                                            session.inject({"role": "user", "content": "You need to specify the FROM clause first!"})
                                            # print("You need to specify the FROM clause first!")
                                        elif function_name == "select" and ("FROM" in clause or "WHERE" in clause):
                                            session.inject({"role": "user", "content": "Please don't include FROM or WHERE in the SELECT clause."})
                                            # print("Please don't include FROM or WHERE in the SELECT clause.")
                                        # elif function_name == "select" and f"{clause}," in line:
                                        #     session.inject({"role": "user", "content": "Please make sure only SELECT the target column asked in the question. For example, if the question is asking for the name of the tallest person, you should only SELECT the name column. Please continue if you have done so."})
                                        #     # print("Please make sure only SELECT the target column asked in the question. For example, if the question is asking for the name of the tallest person, you should only SELECT the name column. Please ignore this message if the specified columns are already the target.")
                                        else:
                                            clauses[function_name] = clause
                                            session.inject({"role": "user", "content": "Please continue."})
                                            # print("Please continue.")
                                    else:
                                        session.inject({"role": "user", "content": f"Please specify a {function_name.upper()} clause. Start with '{function_name.upper().replace('_', '')}'"})
                                        # print(f"Please specify a {function_name.upper()} clause. Start with '{function_name.upper().replace('_', '')}'")
                                    find_action = True
                                    break
                                except IndexError:   # i.e., due to clause = re.split(r'\s*,\s*', matches[0])[0]
                                    session.inject({"role": "user", "content": f"Please specify a {function_name.upper()} clause. Start with '{function_name.upper().replace('_', '')}'"})
                                    # print(f"Please specify a {function_name.upper()} clause. Start with '{function_name.upper().replace('_', '')}'")
                                    find_action = True
                                    break
                            if function_name == "where" and clauses["from"] is None:
                                execution_message = "You need to specify the FROM clause first!"
                                session.inject({"role": "user", "content": execution_message})
                                # print(execution_message)
                                find_action = True
                                break
                            try:
                                ori_arguments = []
                                func = getattr(sys.modules[__name__], function_name)
                                if function_name not in ["search_by_SQL", "where"]:   # if we are going to consider other constructs (like from), update them here too
                                    # matches = re.findall(r'{}\((.+?)\)'.format(function_name), line)
                                    pattern = r'{}\(((?:[^)(]+|\([^)(]*\))*)\)'.format(re.escape(function_name))
                                    matches = re.findall(pattern, line)
                                    arguments = re.split(r'\s*,\s*', matches[0])
                                else:
                                    pattern = r'(search_by_SQL|where)\("(.*?)"\)'
                                    print(message)
                                    match = re.search(pattern, line)
                                    arguments = [match.group(2)]
                                
                                ori_arguments = [argument for argument in arguments]
                                if function_name == "where":
                                    arguments.append(clauses["from"])
                                    arguments.append(conn)
                                else:
                                    arguments.append(conn)
                                if function_name == "get_distinct_values":
                                    arguments.append(question)
                                execution_message = func(*arguments)
                                if execution_message.startswith("The distinct values for") or execution_message.startswith("The columns below"):
                                    useful_execution_messages.append(execution_message)
                                actions.append(f"{function_name}({', '.join(ori_arguments)})")
                                # Sometimes a query may return empty results, which is not a problem.      
                                if execution_message in feedback and "The following conditions do not match any rows" in execution_message and function_name == "where":
                                    session.inject({"role": "user", "content": "Please continue."})
                                    # print("Please continue.")
                                else:
                                    feedback.add(execution_message)
                                    session.inject({"role": "user", "content": execution_message})
                                    # print(execution_message)
                                find_action = True
                                break # at most one function is executed in one turn
                            except Exception as e:
                                execution_message = f"{function_name}({', '.join(ori_arguments)}) is not valid. You may make a mistake and need to fix it."
                                # # print("Exception:", e)
                                # # print(execution_message)
                                # # print(message)
                                if "no such column" in str(e):
                                    execution_message = str(e) + " Please make sure the column exist in the table specified in the FROM clause, or you may reconstruct the FROM clause. Please wrap the column name with single quotes if it contains spaces."
                                else:
                                    if function_name == "where" and ('/' in ori_arguments[0] or '*' in ori_arguments[0] or '+' in ori_arguments[0] or '-' in ori_arguments[0]):
                                        execution_message += " If you are using math operators, please make sure that you use it with spaces. For example, a / b instead of a/b."
                                session.inject({"role": "user", "content": execution_message})
                                # print(execution_message)
                                find_action = True
                                break
                        # This is a bug for Mistral and Mixtral experiments
                        # message = "\n".join(lines[:line_id + 1])
                        # session.history[-1]["content"] = message
                        # correct way should be
                        if session.history[-1]["role"] == "user":
                            session.history[-2]["content"] = message
                        else:
                            session.history[-1]["content"] = message
                        break  # should at most be one line starts with Action
                
                if not find_action: 
                    session.inject({"role": "user", "content": "Now please specify your response in the format of Thought: ... Action: ... or provide a final SQL by stating Final Answer:..\nAfter output the action or the final SQL, please shut up immediately, do not add any explanations or suggestions and just shut up"})
                    # print("Now please specify your response in the format of Thought: ... Action: ... or provide a final SQL by stating Final Answer:..")
                    # # print({"role": "user", "content": "No executable function found! Need to recheck the action."})

        
        conn.close()
                        
        return {"predict": answer, "actions": actions, "db_file": db_file}
