import json
import sqlite3
from collections import defaultdict
from multiprocessing import Process, Queue

def run_query(db_file, query, result_queue):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        # Don't forget to close the connection
        conn.close()
        result_queue.put(results)
    except Exception as e:
        result_queue.put(["invalid query"])

def compute_main_metric(outputs, targets):
    EX_sum = 0
    invalid_sum = 0
    count = 0
    for i in range(len(outputs)):
        count += 1
        if outputs[i] is None:
            continue
        # if outputs[i]['predict'] == "SELECT COUNT(*) FROM account a JOIN disp d ON a.account_id = d.account_id JOIN client c ON d.client_id = c.client_id JOIN district di ON c.district_id = di.district_id WHERE a.date > (SELECT MIN(t.date) FROM trans t WHERE t.account_id = a.account_id) AND di.A4 = 'East Bohemia'":
        #     continue
        # if outputs[i]['predict'] == "SELECT avg(height)  FROM Player  WHERE player_api_id IN (     SELECT player_api_id      FROM Player_Attributes      WHERE player_fifa_api_id IN (         SELECT player_fifa_api_id          FROM Match          WHERE country_id = (             SELECT id              FROM Country              WHERE name = 'Italy'         )     ) )":
        #     continue
        # if outputs[i]['predict'] == "SELECT COUNT(*) FROM Player JOIN Player_Attributes ON Player.player_api_id = Player_Attributes.player_api_id WHERE strftime('%Y', Player.birthday) < '1986' AND Player_Attributes.attacking_work_rate = 'medium' AND Player_Attributes.defensive_work_rate = 'medium'":
        #     continue
        # if outputs[i]['predict'] == "SELECT player_name FROM Player WHERE player_api_id IN (     SELECT player_api_id     FROM Player_Attributes     WHERE player_name = 'Alexis'     AND crossing = (         SELECT MAX(crossing)         FROM Player_Attributes         WHERE player_name = 'Alexis'     ) )":
        #     continue
        # if "SELECT DISTINCT district.A2 FROM trans, district WHERE trans.amount > 10000 AND trans.date LIKE '1997%' AND trans.account_id IN (SELECT account_id FROM account WHERE account.district_id = district.district_id)" in outputs[i]['predict']:
        #     continue
        # if "SELECT COUNT(*) FROM trans WHERE trans_id IN (SELECT trans_id FROM disp WHERE type = 'OWNER') AND k_symbol IN ('SIPO', 'POJISTNE', 'UROK', 'SANKC. UROK')" in outputs[i]['predict']:
        #     continue
        # if "SELECT COUNT(*) FROM client WHERE gender = 'M' AND birth_date BETWEEN '1974-01-01' AND '1976-12-31' AND client_id IN (SELECT client_id FROM disp WHERE disp_id IN (SELECT disp_id FROM loan WHERE loan_id IN (SELECT loan_id FROM `order` WHERE amount > 4000 AND k_symbol = 'HYP')))" in outputs[i]['predict']:
        #     continue
        # if "SELECT p.OwnerDisplayName FROM posts p WHERE p.Id = (SELECT p1.ParentId FROM posts p1 WHERE p1.Score = (SELECT MAX(p2.Score) FROM posts p2 WHERE p2.ParentId = p1.ParentId) ORDER BY p1.ParentId, p1.Id LIMIT 1)" in outputs[i]['predict']:
        #     continue
        try:
            if outputs[i]['predict'] is None:
                continue
            db_file = outputs[i]['db_file']
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            # Set the signal handler and a 5-second alarm
            print(i)
            # print(i, "start execute:", outputs[i]['predict'].split(";")[0], db_file)
            result_queue = Queue()
            query_process = Process(target=run_query, args=(db_file, outputs[i]['predict'].split(";")[0], result_queue))
            # cursor.execute(outputs[i]['predict'].split(";")[0])
            # # print("start fetchall")
            # result = cursor.fetchall()
            # Start the process
            query_process.start()
            # Wait for 60 seconds
            query_process.join(timeout=60)

            # If process is still active, it's taking too long!
            if query_process.is_alive():
                print("Query took too long. Terminating...")
                query_process.terminate()
                query_process.join()
                result = []
                invalid_sum += 1
                continue
            else:
                # print("Query finished.")
                result = result_queue.get()
                if result == ["invalid query"]:
                    invalid_sum += 1
                    continue
            cursor.execute(targets[i])
            gold_result = cursor.fetchall()
            # if len(result) == len(gold_result) == 1 and isinstance(result[0][0], float) and isinstance(gold_result[0][0], float):
            #     if round(result[0][0], 2) == round(gold_result[0][0], 2):
            #         EX_sum += 1
            if set(result) == set(gold_result):
                EX_sum += 1
            # else:
            #     print("--------------------------------------------------")
            #     print("predict:", outputs[i]['predict'].split(";")[0])
            #     print("gold:", targets[i])
        except Exception as e:
            # print(i, e, outputs[i]['predict'].split(";")[0])
            # print(outputs[i]['predict'])
            invalid_sum += 1
            continue
    print(EX_sum, count)
    print(count-invalid_sum, count)
    return EX_sum / count, (count-invalid_sum) / count

with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/data/birdbench/dev.json") as f:
    gold = json.load(f)

requires_content = set()
for item in gold:
    if item['require_content_info']:
        requires_content.add(item['question_id'])


outputs = []
targets = []
outputs_level = defaultdict(list)
targets_level = defaultdict(list)
outputs_content = defaultdict(list)
targets_content = defaultdict(list)
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_3.5_dev_300_1/runs.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/3.5_baseline_300/runs.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_3.5__300_1shot/generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_3.5_dev_300_2/generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/mistral_dev_300_1/generation.jsonl") as f:
# with open("/research/nfs_su_809/workspace/shu.251/StructGPT/outputs/bird/output_wo_icl_v1.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_4_reproduce_100/generation.jsonl") as f:
with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_4_dev_full/generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_3.5_dev_full/generation.jsonl") as f:
    for i, line in enumerate(f):
        if i == 300:
            break
        # print(i)
        line_object = json.loads(line)
        # outputs.append(line_object['output'])
        # outputs.append({"predict": "SELECT " + line_object['Prediction'].replace("\n", " "), "db_file": f"data/birdbench/dev_databases/{line_object['db_id']}/{line_object['db_id']}.sqlite"})
        
        targets.append(line_object['input']['SQL'])
        # targets.append(line_object['SQL'])
        
        
        # for difficulty level
        # outputs_level[line_object['input']['difficulty']].append(line_object['output'])
        # # outputs_level[line_object['difficulty']].append({"predict":  "SELECT " + line_object['Prediction'].replace("\n", " "),  "db_file": f"data/birdbench/dev_databases/{line_object['db_id']}/{line_object['db_id']}.sqlite"})
        # targets_level[line_object['input']['difficulty']].append(line_object['input']['SQL'])
        # # targets_level[line_object['difficulty']].append(line_object['SQL'])

        # for whether requires content exploration
        if line_object['input']['question_id'] in requires_content:
            # outputs_content[1].append(line_object['output'])
            targets_content[1].append(line_object['input']['SQL'])
        else:
            # outputs_content[0].append(line_object['output'])
            targets_content[0].append(line_object['input']['SQL'])
    
with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/gpt4_dev_full/predict_dev.json") as f:
# with open("/research/nfs_su_809/workspace/shu.251/StructGPT/outputs/bird-3.5-turbo-all/pred.json") as f:
# with open("/local/scratch/gu.826/projects/DAMO-ConvAI/bird/llm/bird_pred_sql/before_925/turbo_output_cot/predict_dev.json") as f:
# with open("/local/scratch/gu.826/projects/DAMO-ConvAI/bird/llm/bird_pred_sql/after_925/gpt4_output_kg/predict_dev.json") as f:
    data = json.load(f)
    for i, key in enumerate(data):
        if i == 300:
            continue
        # print(i)
        try:
            db_id = data[key].split("\t")[2]
            outputs.append({"predict": data[key].split("\t")[0].replace("\n", ' '),
                        "db_file": f"data/birdbench/dev_databases/{db_id}/{db_id}.sqlite"})
            if i in requires_content:
                outputs_content[1].append({"predict": data[key].split("\t")[0].replace("\n", ' '),
                        "db_file": f"data/birdbench/dev_databases/{db_id}/{db_id}.sqlite"})
            else:
                outputs_content[0].append({"predict": data[key].split("\t")[0].replace("\n", ' '),
                        "db_file": f"data/birdbench/dev_databases/{db_id}/{db_id}.sqlite"})
        except Exception:
            outputs.append({"predict": "", "db_file": ""})
            if i in requires_content:
                outputs_content[1].append({"predict": "", "db_file": ""})
            else:
                outputs_content[0].append({"predict": "", "db_file": ""})



print(compute_main_metric(outputs, targets))
# for level in outputs_level:
#     print(level, compute_main_metric(outputs_level[level], targets_level[level]))
print(1, compute_main_metric(outputs_content[1], targets_content[1]))
print(0, compute_main_metric(outputs_content[0], targets_content[0]))