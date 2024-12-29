from src.task import Task, Dataset, DataPiece
from .db_api import *

import re
import sys
import json
import sqlite3


def nice_look_table(column_names: list, values: list):
    rows = []
    # Determine the maximum width of each column
    widths = [max(len(str(value[i])) for value in values + [column_names]) for i in range(len(column_names))]

    # Print the column names
    header = ''.join(f'{column.rjust(width)} ' for column, width in zip(column_names, widths))
    # print(header)
    # Print the values
    for value in values:
        row = ''.join(f'{str(v).rjust(width)} ' for v, width in zip(value, widths))
        rows.append(row)
    rows = "\n".join(rows)
    final_output = header + '\n' + rows
    return final_output

def generate_schema_prompt(db_path, num_rows=None):
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
                    print(i, e)
                    print(outputs[i]['predict'])
                    continue

            return EX_sum / count


        return {
            "main": lambda outputs, targets: main_metric(outputs, targets),
            "EX": lambda outputs, targets: main_metric(outputs, targets)
            }

    def get_data(self):
        data = Dataset()
        with open(self.data_fn, "r") as f:
            # data_object = json.load(f)[235:236]
            data_object = json.load(f)
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
        
        question = data_item["question"]
        evidence = data_item["evidence"]
        db_id = data_item["db_id"]
        db_file = self.db_parent_path + db_id + "/" + db_id + ".sqlite"
        conn = sqlite3.connect(db_file)

        # w/o knowledge
        session.inject({"role": "user", "content": f"DB Schema: {generate_schema_prompt(db_file)}\nQuestion: {question}\nPlease write the SQL query directly. Specify your final SQL query by stating the query right after Final Answer:... Also, please do not include any linebreak (i.e., \\n).\nFor example, Final Answer: SELECT x FROM tableA"})

        # w/ knowledge
        # session.inject({"role": "user", "content": f"DB Schema: {generate_schema_prompt(db_file)}\nExternal Knowledge: {evidence}\nQuestion: {question}\nPlease write the SQL query directly. Specify your final SQL query by stating the query right after Final Answer:... Also, please do not include any linebreak (i.e., \\n).\nFor example, Final Answer: SELECT x FROM tableA"})
        # print({"role": "user", "content": f"DB Schema: {generate_schema_prompt(db_file)}\nExternal Knowledge: {evidence}\nQuestion: {question}\nPlease write the SQL query directly. Specify your final SQL query by stating the query right after Final Answer:... Also, please do not include any linebreak (i.e., \\n).\nFor example, Final Answer: SELECT x FROM tableA"})
        
        for i in range(self.round + 1):  # an extra round for direct generation if it fails
            if i == self.round - 1:
                session.history[-1]["content"] = session.history[-1]["content"] + "\nNow you MUST provide your final SQL query as this is the last round. Begin your response with Final Answer:.."
            # print(i, session.history[-1])
            message = session.action()
            print(i, message)
            session.history[-1]["content"] = message
            # print({"role": "agent", "content": message})
            final_answer = re.findall(r'(?:Find|Final) Answer:', message)
            # print("message:", message)
            if final_answer:
                pattern = r'Final Answer: (.*)'
                message = message.replace("\n", " ")
                match = re.search(pattern, message)
                answer = match.group(1)
                # print(answer)
                if answer[0] in ["'", '"'] and answer[-1] in ["'", '"']:
                    answer = answer[1:-1]
                answer = answer.replace("\\", "") # for mistral
                answer.strip()
                print("answer:", answer)
                break
            else:
                # session.inject({"role": "user", "content": "Specify your final SQL query by stating the query right after Final Answer:... Also, please do not include any linebreak (i.e., \\n).\nFor example, Final Answer: SELECT x FROM tableA"})
                answer = message
                break

        
        conn.close()
                        
        return {"predict": answer, "actions": actions, "db_file": db_file}
