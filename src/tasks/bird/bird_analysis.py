import json

object = json.load(open("/research/nfs_su_809/workspace/shu.251/bird/data/dev/dev_res.json"))
count = 0
for item in object:
    if len(item["results"]) == 1:
        if item["results"][0][0] is None:
            count += 1

print(count)