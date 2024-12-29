import json
from datasets import load_dataset

def main():
    # Load the Spider dataset
    dataset = load_dataset("spider")
    # Display some basic information about the dataset
    print("Dataset keys: ", dataset.keys())
    for split, data in dataset.items():
        print(f"Number of samples in {split} split: ", len(data))

    # Display the first 5 samples in the train split
    print("\nFirst 5 samples in train split:")
    # for idx, sample in enumerate(dataset["train"].select(range(5))):
    for idx, sample in enumerate(dataset["validation"]):
        if len(sample["query"]) > 200:
            print(f"\nSample {idx + 1}")
            print("Database id:", sample["db_id"])
            print("Query:", sample["question"])
            print("SQL:", sample["query"])

    print(sample)

    # Some simple analysis
    num_queries = len(dataset["train"])
    unique_db_ids = len(set([sample["db_id"] for sample in dataset["train"]]))

    print("\nAnalysis:")
    print(f"Total number of queries: {num_queries}")
    print(f"Total number of unique database IDs: {unique_db_ids}")

if __name__ == "__main__":
    main()
