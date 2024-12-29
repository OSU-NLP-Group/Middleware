# Middleware for LLMs: Tools Are Instrumental for Language Agents in Complex Environments

[![License](https://img.shields.io/badge/License-Apache%202.0-red.svg)](https://opensource.org/licenses/Apache-2.0)
[![language-python3](https://img.shields.io/badge/Language-Python3-blue.svg?style=flat-square)](https://www.python.org/)
[![paper](https://img.shields.io/badge/Paper-EMNLP2024-gold?style=flat-square)](https://aclanthology.org/2024.emnlp-main.436.pdf)

> The applications of large language models (LLMs) have expanded well beyond the confines of text processing, signaling a new era where LLMs are envisioned as generalist agents capable of operating within complex environments. These environments are often highly expansive, making it impossible for the LLM to process them within its short-term memory. Motivated by recent research on extending the capabilities of LLMs with tools, we seek to investigate the intriguing potential of tools to augment LLMs in handling such complexity by introducing a novel class of tools, termed *middleware*, to aid in the proactive exploration within these massive environments. Such specialized tools can serve as a middleware layer shielding the LLM from environmental complexity. In two representative complex environments—knowledge bases (KBs) and databases—we demonstrate the significant potential of augmenting language agents with tools in complex environments. Notably, equipped with the middleware, GPT-4 achieves **2.8**X the performance of the best baseline in tasks requiring access to database content and **2.2**X in KB tasks. Our findings illuminate the path for advancing language agents in real-world applications.
<img width="605" alt="image" src="https://github.com/user-attachments/assets/05530abb-74e5-4914-9fe8-576adaf3a928" />


## Setup
```
conda create -n middleware python=3.9
conda activate middleware
pip install -r requirements.txt
```

### Setup for KGs
To run our experiments on Freebase, please follow [Freebase Setup](https://github.com/dki-lab/Freebase-Setup]) to set up a Virtuoso triplestore service. You can set up your Virtuoso server on port 3093. If you use a different port, please remember to correspondingly update the url [here](https://github.com/OSU-NLP-Group/Middleware/blob/990a6beb8d749932bb2891416fbd88f9a16e614b/src/tasks/knowledgegraph/utils/sparql_executer.py#L24).

### Setup for DBs
For our experiments on BIRD, please first download the databases associated with its dev set from the [official link](https://bird-bench.github.io) and put all files under `./data/birdbench/`.
Note that, in the original dev set, no information regarding whether a task requires DB content to solve is provided. We have provided the information in our own `dev.json` file under `./data/birdbench/`. Specifically, whether a task requires content-level information to solve is indicated by the following json field:
```json
{
    ...
     "require_content_info": [true|false],
    ...
}
```

## Evaluation
Our codebase is mostly adapted from the 0.1 version of [AgentBench](https://github.com/THUDM/AgentBench). 
For a more detailed description of the structure of the source code and config files, please find more detailed information there (but this is not necessary if you just want to reproduce the experiments in our Middleware work).

To run experiments using our codebase, simply do
```
python eval.py \
 --task configs/tasks/<your_task>.yaml \
 --agent configs/agents/<your_agent>.yaml \
 --workers <num_of_threads>
```
For example,
```
python eval.py \
 --task configs/tasks/knowledgegraph/dev.yaml \
 --agent configs/agents/api_agents/gpt-3.5-turbo.yaml \
 --workers 10
```
This command can be used to evaluate on dev.yaml of our KG experiments using gpt-3.5-turbo, running with 10 threads in parallel.



## Citation
```
@inproceedings{gu-etal-2024-middleware,
    title = "Middleware for {LLM}s: Tools Are Instrumental for Language Agents in Complex Environments",
    author = "Gu, Yu  and
      Shu, Yiheng  and
      Yu, Hao  and
      Liu, Xiao  and
      Dong, Yuxiao  and
      Tang, Jie  and
      Srinivasa, Jayanth  and
      Latapie, Hugo  and
      Su, Yu",
    editor = "Al-Onaizan, Yaser  and
      Bansal, Mohit  and
      Chen, Yun-Nung",
    booktitle = "Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing",
    month = nov,
    year = "2024",
    address = "Miami, Florida, USA",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2024.emnlp-main.436",
    doi = "10.18653/v1/2024.emnlp-main.436",
    pages = "7646--7663",
    abstract = "The applications of large language models (LLMs) have expanded well beyond the confines of text processing, signaling a new era where LLMs are envisioned as generalist agents capable of operating within complex environments. These environments are often highly expansive, making it impossible for the LLM to process them within its short-term memory. Motivated by recent research on extending the capabilities of LLMs with tools, we seek to investigate the intriguing potential of tools to augment LLMs in handling such complexity by introducing a novel class of tools, termed *middleware*, to aid in the proactive exploration within these massive environments. Such specialized tools can serve as a middleware layer shielding the LLM from environmental complexity. In two representative complex environments{---}knowledge bases (KBs) and databases{---}we demonstrate the significant potential of augmenting language agents with tools in complex environments. Notably, equipped with the middleware, GPT-4 achieves **2.8**X the performance of the best baseline in tasks requiring access to database content and **2.2**X in KB tasks. Our findings illuminate the path for advancing language agents in real-world applications.",
}
```
