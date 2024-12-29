from typing import List, Tuple
from SPARQLWrapper import SPARQLWrapper, JSON
import os
import json
import urllib
import random
from tqdm import tqdm
from pathlib import Path
from tqdm import tqdm


path = str(Path(__file__).parent.absolute())

with open(path + '/../ontology/fb_roles', 'r') as f:
    contents = f.readlines()

roles = set()
for line in contents:
    fields = line.split()
    roles.add(fields[1])


class SparqlExecuter:
    def __init__(self, url: str="http://127.0.0.1:3093/sparql", cache_fn="sparql_cache.json"):
        self.sparql = SPARQLWrapper(url)
        self.sparql.setReturnFormat(JSON)
        self.cache_fn = cache_fn

        if not os.path.exists(self.cache_fn):
            self.cache = {}
        else:
            with open(self.cache_fn) as f:
                self.cache = json.load(f)

    def execute_query(self, query: str) -> List[str]:
        if query in self.cache:
            return self.cache[query]
        self.sparql.setQuery(query)
        try:
            results = self.sparql.query().convert()
        except urllib.error.URLError:
            print(query)
            exit(0)
        rtn = []
        for result in results['results']['bindings']:
            # assert len(result) == 1  # only select one variable
            for var in result:
                rtn.append(result[var]['value'].replace('http://rdf.freebase.com/ns/', '').replace("-08:00", ''))

        self.cache[query] = rtn
        return rtn


    def get_out_relations(self, entity: str):
        out_relations = set()

        query = ("""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX : <http://rdf.freebase.com/ns/> 
            SELECT (?x0 AS ?value) WHERE {
            SELECT DISTINCT ?x0  WHERE {
            """
                ':' + entity + ' ?x0 ?x1 . '
                                """
        FILTER regex(?x0, "http://rdf.freebase.com/ns/")
        }
        }
        """)
        if query in self.cache:
            return self.cache[query]

        self.sparql.setQuery(query)
        try:
            results = self.sparql.query().convert()
        except urllib.error.URLError:
            print(query)
            exit(0)
        for result in results['results']['bindings']:
            out_relations.add(result['value']['value'].replace('http://rdf.freebase.com/ns/', ''))

        self.cache[query] = list(out_relations)
        return out_relations


    def sample_triples(self, entity: str, limit: int = 10) -> List[Tuple[str, str]]:
        relations = self.get_out_relations(entity)
        triples = []
        for relation in relations:
            query = ("""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX : <http://rdf.freebase.com/ns/> 
                SELECT (?x1 AS ?value) WHERE {
                SELECT DISTINCT ?x1  WHERE {
                """
                    ':' + entity + ' :' + relation + ' ?x1 . '
                    """
            FILTER regex(?x1, "http://rdf.freebase.com/ns/")
            }
            }
            """)
            if query in self.cache:
                results = self.cache[query]
            else:
                self.sparql.setQuery(query)
                try:
                    results = self.sparql.query().convert()
                except urllib.error.URLError:
                    print(query)
                    exit(0)
                results = [result['value']['value'].replace('http://rdf.freebase.com/ns/', '') for result in results['results']['bindings']]
                self.cache[query] = results
            for result in results:
                if result[:2] not in ["m.", "g."]:
                    continue
                triples.append((entity, relation, result))
            
        if len(triples) >= limit:
            return random.sample(triples, limit)
        else:
            return triples



    def sample_3hop_triples(self, entity: str, limit: int = 10) -> List[Tuple[str, str, str]]:
        # get one hop triples
        triples = self.sample_triples(entity, limit)
        # print("one hop:", triples)
        # get two hop triples
        two_hop_triples = []
        for triple in triples:
            relation = triple[1]
            obj = triple[2]
            if obj[:2] in ["m.", "g."]:
                obj_triples = self.sample_triples(obj, limit)
                if obj_triples is not None:
                    for obj_triple in obj_triples:
                        two_hop_triples.append((triple[0], relation, obj_triple[2]))
        # time.sleep(2)
        # print("two hop:", two_hop_triples)
        # get three hop triples
        three_hop_triples = []
        for triple in two_hop_triples:
            relation = triple[1]
            obj = triple[2]
            if obj[:2] in ["m.", "g."]:
                obj_triples = self.sample_triples(obj, limit)
                if obj_triples is not None:
                    for obj_triple in obj_triples:
                        three_hop_triples.append((triple[0], relation, obj_triple[2]))
        # time.sleep(2)
        # print("three hop:", three_hop_triples)
        all_triples = triples + two_hop_triples + three_hop_triples
        random.shuffle(all_triples)
        return all_triples
    

    def save_cache(self):
        with open(self.cache_fn, 'w') as f:
            json.dump(self.cache, f)



if __name__ == '__main__':
    sparql_executer = SparqlExecuter()
    # results = sparql_executer.get_out_relations('m.09rl290')
    # results = sparql_executer.sample_triples('m.09rl290')
    # results = sparql_executer.sample_3hop_triples('m.0h27q91', limit=10)
    # print(results)
    # print(len(results))

    with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/data/knowledgegraph/ext.json", "r") as f:
        data = json.load(f)

    with open("/local/scratch/gu.826/projects/updated_agentbench/AgentBench/data/knowledgegraph/triples.json", "w") as f:
        triple_dict = {}
        for item in tqdm(data[:100]):
            entities = [v for k, v in item["entities"].items()]
            triples = []
            for entity in entities:
                triples += sparql_executer.sample_3hop_triples(entity, limit=10)
            triple_dict[item["qid"]] = triples
        json.dump(triple_dict, f, indent=4)

    

