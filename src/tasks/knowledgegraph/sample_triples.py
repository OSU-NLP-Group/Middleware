from src.task import Task, Dataset, DataPiece
from .api import *
from .utils.sparql_executer import SparqlExecuter
from src.tasks.knowledgegraph.relation_filter import SentenceTransformerRetrieval

import re
import sys
import json

INSTRUCTIONS = """
You are an agent that answers questions based on the knowledge stored in a knowledge base. 
To answer a question, you will be provided a set of triples from the KB, each triple is a tuple of (subject, predicate, object), where subject and object are entities and predicate is a relation between them. Each entity is an id with a prefix of either "m." or "g.".
Your task is to find the entity ids that answer the question. 
Please return your answer in the following format:
Thought: your rationale for the answer
Answer: [a list entity ids that answer the question]
(e.g., Answer: [m.05ch8k4])
"""

with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/data/knowledgegraph/triples.json", "r") as f:
    triples = json.load(f)


class KnowledgeGraph(Task):
    def __init__(self, **configs):
        self.round = configs.pop("round", 15)  # maximum round
        self.data_fn = configs.pop("data_file", None)
        self.sparql_executor = SparqlExecuter(configs.pop("sparql_url", None))
        super().__init__(**configs)

    def final_touch(self):
        self.sparql_executor.save_cache()

    @property
    def metrics(self):
        # {'predict': []} [{'answer_type': 'Entity', 'answer_argument': 'm.05ch8k4', 'entity_name': 'Guard'}]
        def main_metric(outputs, targets):
            F1_sum = 0
            count = 0
            for i in range(len(outputs)):
                if outputs[i] is None:
                    continue
                count += 1
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


        return {
            "main": lambda outputs, targets: main_metric(outputs, targets),
            "F1": lambda outputs, targets: main_metric(outputs, targets),
            "EM": lambda outputs, targets: EM(outputs, targets),
            "executability": lambda outputs, targets: executability(outputs)
                }

    def get_data(self):
        data = Dataset()
        with open(self.data_fn, "r") as f:
            data_object = json.load(f)[:100]
        for item in data_object:
            answer = item.pop("answer")
            gold_answer = set()
            for a in answer:
                gold_answer.add(a["answer_argument"])
            data.append(DataPiece(item, gold_answer))  # input and target
        return data

    def predict_single(self, session, data_item): # return OUTPUT object, need to be json serializable
        # todo: return a dictionary including the prediction and metrics per data item
        answer = []
        actions = []
        variables_list = []
        
        question = data_item["question"]
        entities = data_item["entities"]

        session.inject({
            "role": "user",
            "content": INSTRUCTIONS 
        })
        session.inject({"role": "agent", "content": "I've understood your instruction, start please."})
        item_triples = triples[data_item["qid"]]
        item_triples_str = [f"{triple[0]} {triple[1]} {triple[2]}" for triple in item_triples]
        retriever = SentenceTransformerRetrieval(list(item_triples_str), 'sentence-transformers/all-mpnet-base-v2')
        top_k_triples_str = retriever.get_top_k_sentences(question, k=10, distinct=True)
        top_k_triples_str = '\n'.join(top_k_triples_str)

        session.inject({"role": "user", "content": "Question: " + question + "\nEntities: " + f"[{', '.join([entity + ':' + entities[entity] for entity in entities])}]" + "triples: " + top_k_triples_str})
        # print("Question: " + question + "\nEntities: " + f"[{', '.join([entity + ': ' + entities[entity] for entity in entities])}]" + "triples: " + top_k_triples_str)
        
        message = session.action()
        print(message)

        bracket_content = re.search(r"Answer: \[([^\]]+)\]", message)

        # If content is found within brackets, match 'm.' or 'g.' followed by alphanumeric characters
        if bracket_content:
            ids = re.findall(r"[mg]\.\w+", bracket_content.group(1))
        else:
            ids = []
        
                        

        return {"predict": ids}
