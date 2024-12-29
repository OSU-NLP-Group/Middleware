# Middleware for LLMs: Tools Are Instrumental for Language Agents in Complex Environments

[![License](https://img.shields.io/badge/License-Apache%202.0-red.svg)](https://opensource.org/licenses/Apache-2.0)
[![language-python3](https://img.shields.io/badge/Language-Python3-blue.svg?style=flat-square)](https://www.python.org/)
[![paper](https://img.shields.io/badge/Paper-EMNLP2024-gold?style=flat-square)](https://aclanthology.org/2024.emnlp-main.436.pdf)

> The applications of large language models (LLMs) have expanded well beyond the confines of text processing, signaling a new era where LLMs are envisioned as generalist agents capable of operating within complex environments. These environments are often highly expansive, making it impossible for the LLM to process them within its short-term memory. Motivated by recent research on extending the capabilities of LLMs with tools, we seek to investigate the intriguing potential of tools to augment LLMs in handling such complexity by introducing a novel class of tools, termed *middleware*, to aid in the proactive exploration within these massive environments. Such specialized tools can serve as a middleware layer shielding the LLM from environmental complexity. In two representative complex environments—knowledge bases (KBs) and databases—we demonstrate the significant potential of augmenting language agents with tools in complex environments. Notably, equipped with the middleware, GPT-4 achieves **2.8**X the performance of the best baseline in tasks requiring access to database content and **2.2**X in KB tasks. Our findings illuminate the path for advancing language agents in real-world applications.
<img width="605" alt="image" src="https://github.com/user-attachments/assets/05530abb-74e5-4914-9fe8-576adaf3a928" />




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
