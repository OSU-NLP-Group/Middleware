# this file specifies the rules to propose candidate actions for the LLM to choose from
from .relation_filter import SentenceTransformerRetrieval
num_relations = 5

class ActionGenerator:
    def __init__(self, entities: list) -> None:
        self.executed_actions = set()
        self.active_actions = [f'get_relations({e})' for e in entities]
        self.active_get_neighbors = []
        # the parse of actions. key: items in self.active_actions, value: the parse of the action (i.e., function_name and arguments)
        # the update of active_actions_parses is not very sensitive as long as it contains all the actions in self.active_actions and 
        # self.active_get_neighbors.
        self.active_actions_parses = {f'get_relations({e})': ['get_relations', e] for e in entities}
        self.variables = []


    def update(self, action, variables=None, observation=None, current_var=None, question=None, attributes=False):
        self.executed_actions.add(action)

        if variables is not None:
            self.active_get_neighbors = []
            self.active_actions.append(f"get_relations(#{len(variables) - 1})")
            self.active_actions_parses[f"get_relations(#{len(variables) - 1})"] = ['get_relations', f'#{len(variables) - 1}']
            
            # todo: intersection also cannot be applied to ancestors!!!!
            # for i in range(len(variables) - 1):  # can't intersect with yourself
            #     # if variables[i].type == variables[-1].type:
            #     if len(set(variables[i].execution).intersection(set(variables[-1].execution))) > 0:
            #         self.active_actions.append(f"intersection(#{i}, #{len(variables) - 1})")
            #         self.active_actions_parses[f"intersection(#{i}, #{len(variables) - 1})"] = ['intersection', f'#{i}', f'#{len(variables) - 1}']

            # avoid repeated actions. todo: allow get_relations to be repeatedly done for backtracking
            self.active_actions = [action for action in self.active_actions if \
                                   action not in self.executed_actions and \
                                   "return #" not in action and "count" not in action]
            self.active_actions_parses = {action: self.active_actions_parses[action] for action in self.active_actions}

            self.active_actions.append(f"return #{len(variables) - 1} as the final answer")
            self.active_actions_parses[f"return #{len(variables) - 1} as the final answer"] = []
            self.active_actions.append(f"count(#{len(variables) - 1})")
            self.active_actions_parses[f"count(#{len(variables) - 1})"] = ['count', f'#{len(variables) - 1}']
        else:
            # if len(observation) > num_relations:
            #     retriever = SentenceTransformerRetrieval(observation, 'sentence-transformers/all-mpnet-base-v2')
            #     observation = retriever.get_top_k_sentences(question, k=num_relations, distinct=True)
            # todo: include get_attributes
            if not attributes:
                self.active_get_neighbors = [f"get_neighbors({current_var}, {r})" for r in observation]
                self.active_actions_parses.update({f"get_neighbors({current_var}, {r})": ['get_neighbors', current_var, r] for r in observation})
            
            # We won't allow get_neighbors to be repeatedly done for backtracking. Not sure whether this is a good idea.
            for action in self.active_get_neighbors:
                if action in self.executed_actions:
                    self.active_get_neighbors.remove(action)



    def format_choices(self):
        # format the single-choice QA task prompt
        if len(self.active_get_neighbors) > 0:
            active_actions = self.active_get_neighbors
        else:
            active_actions = self.active_actions

        # this converts the active actions into the prompt to the LLM
        if not (1 <= len(self.active_actions) <= 15):
            print(self.active_actions)
            raise ValueError("The list of strings must contain between 1 and 15 items.")

        # A list of letters from 'a' to 'j'
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', "l", "m", "n", "o"]
        # Using a list comprehension to format the output
        formatted_choices = ["{}. {}".format(letters[i], string) for i, string in enumerate(active_actions)]
        used_letters = letters[:len(active_actions)]
        
        # Combining the formatted choices into a single string
        formatted_string = "Candidate actions:\n" + "\n".join(formatted_choices)
        
        # Adding the prompt to make a choice
        formatted_string += "\nMake a choice from " + ", ".join(letters[:len(active_actions)])

        # formatted_string += "\nPlease output the letter of the action only (e.g., a, b, c, or d). Do not output the action itself. You need to first output your rationale starting with 'Thought: ' and then output your choice starting with 'My choice: '."

        return formatted_string, used_letters    
        