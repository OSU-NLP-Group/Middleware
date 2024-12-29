# This is the code for out-of-context candidate selection


INSTRUCTIONS = """
To answer complex questions over a knowledge base, the following tools can be used strategically to find the answer:
```
1. get_relations(variable: var) -> list of relations
A variable can be either an entity or a set of entities (i.e., the result of a previous query). This function helps to navigate all relations in the KB connected to the variable, so you can decide which relation is the most useful to find the answer to the question.

2. get_neighbors(variable: var, relation: str) -> variable
Given a variable, this function returns all entities connected to the variable via the given relation. Note that, get_neighbors() can only be used after get_relations() is used to find a set of viable relations.

3. intersection(variable1: var, variable2: var) -> variable
Given two variables, this function returns the intersection of the two variables. The two variables MUST be of the same type!

4. get_attributes(variable: var) -> list of attributes
This function helps to find all numerical attributes of the variable. Please only use it if the question seeks for a superlative accumulation (i.e., argmax or argmin).

5. argmax(variable: var, attribute: str) -> variable
Given a variable, this function returns the entity with the maximum value of the given attribute. It can only be used after get_attributes() is used to find a set of viable attributes.

6. argmin(variable: var, attribute: str) -> variable
Given a variable, this function returns the entity with the minimum value of the given attribute. It can only be used after get_attributes() is used to find a set of viable attributes.

7. count(variable: var) -> int
Given a variable, this function returns the number of entities belonging to the variable.
```

Now the task is to find a action to take at a given step. The action should be helpful to answer the question. You will be given the context of the actions taken so far, the question, and several candidate actions to choose from. Please choose the action that is most likely to lead to the answer to the question.
For example, here are some demos:
Demo 1:
Question: the bipropellant rocket engine with kerosene and gas-generator cycle is designed by who? \nEntities: [Gas-generator cycle, Kerosene]

Context:
None

Candidate actions for the next step:
a. get_relations(Gas-generator cycle)
b. get_relations(Kerosene)
Make a choice from a, b
Please output the letter of the action only (e.g., a, b, c, or d). Do not output the action itself.
Thought: I need to first find engines with gas-generator cycle. To acheive this, I will query the KB to find relations connected to the entity 'Gas-generator cycle' and see if any of them can help me find the answer.
Action: a

Demo 2:
Question: the bipropellant rocket engine with kerosene and gas-generator cycle is designed by who? \nEntities: [Gas-generator cycle, Kerosene]

Context:
Thought: I need to first find engines with gas-generator cycle. To acheive this, I will query the KB to find relations connected to the entity 'Gas-generator cycle' and see if any of them can help me find the answer.
Action: get_relations(Gas-generator cycle)
Observation: [spaceflight.rocket_engine_cycle.rocket_engines, spaceflight.satellite.orbiting, spaceflight.rocket_stage.fuel, spaceflight.satellite_manufacturer.spacecraft_manufactured, automotive.fuel.engines]

Candidate actions for the next step:
a. get_neighbors(Gas-generator cycle, spaceflight.rocket_engine_cycle.rocket_engines)
b. get_neighbors(Gas-generator cycle, spaceflight.satellite.orbiting)
c. get_neighbors(Gas-generator cycle, spaceflight.rocket_stage.fuel)
d. get_neighbors(Gas-generator cycle, spaceflight.satellite_manufacturer.spacecraft_manufactured)
e. get_neighbors(Gas-generator cycle, automotive.fuel.engines)
Make a choice from a, b, c, d, e
Please output the letter of the action only (e.g., a, b, c, or d). Do not output the action itself.
Thought: From the above relations, I might use spaceflight.rocket_engine_cycle.rocket_engines to find the engines of Gas-generator cycle.
Action: a

Demo 3:
Question: the bipropellant rocket engine with kerosene and gas-generator cycle is designed by who? \nEntities: [Gas-generator cycle, Kerosene]

Context:
Thought: I need to first find engines with gas-generator cycle. To acheive this, I will query the KB to find relations connected to the entity 'Gas-generator cycle' and see if any of them can help me find the answer.
Action: get_relations(Gas-generator cycle)
Observation: [spaceflight.rocket_engine_cycle.rocket_engines, spaceflight.satellite.orbiting, spaceflight.rocket_stage.fuel, spaceflight.satellite_manufacturer.spacecraft_manufactured, automotive.fuel.engines]
Thought: From the above relations, I might use spaceflight.rocket_engine_cycle.rocket_engines to find the engines of Gas-generator cycle.
Action: get_neighbors(Gas-generator cycle, spaceflight.rocket_engine_cycle.rocket_engines)
Observation: variable #0, which are instances of spaceflight.bipropellant_rocket_engine
Thought: I also need to find engines with kerosene. To acheive this, I will query the KB to find relations connected to the entity 'Kerosene'.
Action: get_relations(Kerosene)
Observation: [spaceflight.satellite_manufacturer.spacecraft_manufactured, automotive.fuel.engines, spaceflight.rocket_engine_cycle.rocket_engines]
Thought: From the above relations, I might use spaceflight.rocket_engine_cycle.rocket_engines to find engines with kerosene cycle.
Action: get_neighbors(Kerosene, spaceflight.rocket_engine_cycle.rocket_engines
Observation: variable #1, which are instances of spaceflight.bipropellant_rocket_engine

Candidate actions for the next step:
a. get_relations(#0)
b. get_relations(#1)
c. intersection(#0, #1)
Make a choice from a, b, c
Please output the letter of the action only (e.g., a, b, c, or d). Do not output the action itself.
Thought: The engines with both gas-generator cycle and kerosene cycle shoule be the intersection of variable #0 and variable #1.
Action: c
"""

