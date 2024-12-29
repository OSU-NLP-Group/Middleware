import json

from collections import defaultdict

data = json.load(open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/data/knowledgegraph/ext.json"))
print(len(data))
source_dict = defaultdict(int)
hops_count, agg_count = 0, 0
for item in data:
    source_dict[item["source"]] += 1
    for action in item["actions"]:
        if "get_relations" in action or "get_attributes" in action:
            hops_count += 1
        if "argmax" in action or "argmin" in action or "count" in action:
            agg_count += 1
# print(source_dict)
print(hops_count / 500, agg_count / 500)