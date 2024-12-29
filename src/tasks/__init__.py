from .example_task import ExampleTask
from .composite_task import CompositeTask
try: from .bird import BirdBench
except: print("> [Warning] Bird task not available")
from .knowledgegraph import KnowledgeGraph
try: from .knowledgegraph import KnowledgeGraph
except: print("> [Warning] KnowledgeGraph task not available")
