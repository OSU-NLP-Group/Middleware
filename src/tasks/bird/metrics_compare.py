import json
import sqlite3
from collections import defaultdict

def compare(outputs1, outputs2, targets):
    count = 0
    for i in outputs1:
        # print(EX_sum, count)
        if outputs1[i] is None:
            continue
        # if outputs[i]['predict'] == "SELECT COUNT(*) FROM account a JOIN disp d ON a.account_id = d.account_id JOIN client c ON d.client_id = c.client_id JOIN district di ON c.district_id = di.district_id WHERE a.date > (SELECT MIN(t.date) FROM trans t WHERE t.account_id = a.account_id) AND di.A4 = 'East Bohemia'":
        #     continue   # if None, count will not increase. Pay attention to this!!!
        try:
            db_file = outputs1[i]['db_file']
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            # print("start execute:", outputs1[i]['predict'].split(";")[0])
            cursor.execute(outputs1[i]['predict'].split(";")[0])
            # print("start fetchall")
            result1 = cursor.fetchall()
            cursor.execute(outputs2[i]['predict'].split(";")[0])
            result2 = cursor.fetchall()
            cursor.execute(targets[i])
            gold_result = cursor.fetchall()
            if set(result1) == set(gold_result) and set(result2) != set(gold_result): 
                count += 1
                print("--------------------------------------------------")
                print("output1:", outputs1[i]['predict'].split(";")[0])
                print("output2:", outputs2[i]['predict'].split(";")[0])
        except Exception as e:
            # print(i, e)
            # print(outputs[i]['predict'])
            continue

    return count


outputs1, outputs2 = {}, {}
targets = {}
outputs_level = defaultdict(list)
targets_level = defaultdict(list)
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_4_dev_600_900/generation.jsonl") as f:
with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_4_dev_full/content_generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/gpt4_5row_content/generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_3.5__300_1shot/generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_3.5_dev_300_1/generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/mixtral_baseline_knowledge_300/generation.jsonl") as f:
    for i, line in enumerate(f):
        # if i > 100:
        #     break
        # print(i)
        line_object = json.loads(line)
        outputs1[line_object["input"]["question_id"]] = line_object['output']
        targets[line_object["input"]["question_id"]] = line_object['input']['SQL']

# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_3.5_dev_300_2/generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/mixtral_dev_300/generation.jsonl") as f:
# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_4_dev_300_600_1/generation.jsonl") as f:
#     for i, line in enumerate(f):
#         if i > 100:
#             break
#         # print(i)
#         line_object = json.loads(line)
#         outputs2[line_object["input"]["question_id"]] = line_object['output']

# with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/gpt4_dev_full/predict_dev.json") as f:
with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/birdbench/fuxi_4_1row_content_1/predict_dev.json") as f:
# with open("/local/scratch/gu.826/projects/DAMO-ConvAI/bird/llm/bird_pred_sql/after_925/turbo_output_kg/predict_dev.json") as f:
    data = json.load(f)
    for i, key in enumerate(data):
        # if i < 300 or i > 899:
        #     continue
        try:
            db_id = data[key].split("\t")[2]
            outputs2[int(key)] = {"predict": data[key].split("\t")[0].replace("\n", ' '),
                        "db_file": f"data/birdbench/dev_databases/{db_id}/{db_id}.sqlite"}
        except Exception:
            outputs2[int(key)] = {"predict": "", "db_file": ""}



print(compare(outputs2, outputs1, targets))
# for level in outputs_level:
#     print(level, compute_main_metric(outputs_level[level], targets_level[level]))