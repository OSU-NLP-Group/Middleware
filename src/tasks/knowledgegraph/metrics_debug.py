import json

ground_truth = json.load(open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/data/knowledgegraph/ext.json", "r"))
# print(len(ground_truth))
ground_truth_map = {}
for item in ground_truth:
    answers = set()
    for a in item["answer"]:
        answers.add(a["answer_argument"])
    ground_truth_map[item["qid"]] = answers

# path = "/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/kg_new/fuxi2_gpt4_500/generation.jsonl"
# path = "/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/kg_new/unconstrained_gpt4_500/generation.jsonl"
# path = "/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/kg_new/fuxi2_3.5_500/generation.jsonl"
# path = "/local/scratch/gu.826/projects/updated_agentbench/AgentBench/outputs/kg_new/unconstrained_500/generation.jsonl"
# path = "/research/nfs_su_809/workspace/shu.251/StructGPT/outputs/fuxi-kbqa-gpt4-500/output_wo_icl_v1.jsonl"

# path = "/local/scratch/gu.826/projects/bottom_up_parser/pangu_3.5_fuxi.txt"
path = "/local/scratch/gu.826/projects/bottom_up_parser/pangu_4_fuxi.txt"


data = {}
with open(path, "r") as f:
    for line in f:
        line_object = json.loads(line.strip())
        # data[line_object["input"]["qid"]] = line_object
        # data[line_object["qid"]] = line_object
        data[line_object["qid"]] = {"output": {"predict": line_object["answer"]}}
# print(len(data))

s_expressions = {}
with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/data/knowledgegraph/ext.json") as f:
    gold = json.load(f)
for item in gold:
    s_expressions[item["qid"]] = item["s_expression"]


outputs, targets = [], []
outputs_none, targets_none = [], []
outputs_counting, targets_counting = [], []
outputs_superlative, targets_superlative = [], []
for key in data:
    predict = []
    # for a in data[key]["answer"]:
    #     predict.append(a["answer_argument"])
    # outputs.append({"predict": predict})
    outputs.append({"predict": data[key]["output"]["predict"]})
    # print(predict, ground_truth_map[key])
    targets.append(ground_truth_map[key])
    if s_expressions[key][:4] == "(ARG":
        outputs_superlative.append({"predict": data[key]["output"]["predict"]})
        targets_superlative.append(ground_truth_map[key])
    elif s_expressions[key][:4] == "(COU":
        outputs_counting.append({"predict": data[key]["output"]["predict"]})
        targets_counting.append(ground_truth_map[key])
    else:
        outputs_none.append({"predict": data[key]["output"]["predict"]})
        targets_none.append(ground_truth_map[key])


def main_metric(outputs, targets):
    F1_sum = 0
    count = 0
    for i in range(len(outputs)):
        count += 1
        if outputs[i] is None:
            continue
        predicted_answer = set(outputs[i]['predict'])
        gold_answer = targets[i]
        TP = len(gold_answer.intersection(predicted_answer))
        FP = len(predicted_answer) - TP
        FN = len(gold_answer) - TP
        if TP == 0:
            continue
        precision = TP / (TP + FP)
        recall = TP / (TP + FN)
        F1 = 2 * precision * recall / (precision + recall)
        F1_sum += F1
    return F1_sum / count

def EM(outputs, targets):
    em_sum = 0
    count = 0
    for i in range(len(outputs)):
        if outputs[i] is None:
            continue
        count += 1
        predicted_answer = set(outputs[i]['predict'])
        gold_answer = targets[i]
        if len(gold_answer.intersection(predicted_answer)) == len(gold_answer) and len(gold_answer.intersection(predicted_answer)) == len(predicted_answer):
            em_sum += 1

    return em_sum / count

def executability(outputs):
    count = 0
    executability_sum = 0
    for i in range(len(outputs)):
        if outputs[i] is None:
            continue
        count += 1
        if outputs[i]['predict'] is not None and len(outputs[i]['predict']) > 0:
            executability_sum += 1

    return executability_sum / count

print(main_metric(outputs, targets))
print(EM(outputs, targets))
print(executability(outputs))

print(len(outputs_counting), len(outputs_superlative), len(outputs_none))

print(main_metric(outputs_counting, targets_counting))
# print(EM(outputs_counting, targets_counting))
print(executability(outputs_counting))

print(main_metric(outputs_superlative, targets_superlative))
# print(EM(outputs_superlative, targets_superlative))
print(executability(outputs_superlative))

print(main_metric(outputs_none, targets_none))
# print(EM(outputs_none, targets_none))
print(executability(outputs_none))
