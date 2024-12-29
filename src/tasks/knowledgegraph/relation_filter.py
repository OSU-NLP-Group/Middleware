from abc import ABC, abstractmethod
import numpy as np
from sentence_transformers import SentenceTransformer, util, CrossEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from rank_bm25 import BM25Okapi
from transformers import AutoModel, AutoTokenizer


class SentenceRetrieval(ABC):
    def __init__(self, corpus):
        self.corpus = corpus

    @abstractmethod
    def _preprocess(self):
        pass

    @abstractmethod
    def scores_on_corpus(self, query):
        pass

    def get_top_k_sentences(self, query, k=10, distinct=True):
        top_k_indices = self.get_top_k_indices(query, k, distinct)
        top_k_sentences = [self.corpus[i] for i in top_k_indices]
        return top_k_sentences

    def get_top_k_indices(self, query, k=10, distinct=True):
        scores = self.scores_on_corpus(query)

        # Get the top k indices with the highest scores
        if distinct is False:
            top_k_indices = np.argsort(scores)[::-1][:k]
            return top_k_indices
        else:
            top_k_indices = np.argsort(scores)[::-1][:5 * k]

            # Remove duplicates by storing seen sentences in a set
            seen_sentences = set()
            unique_top_k_indices = []
            for i in top_k_indices:
                if self.corpus[i] not in seen_sentences:
                    unique_top_k_indices.append(i)
                    seen_sentences.add(self.corpus[i])

                    if len(unique_top_k_indices) == k:
                        break

            return unique_top_k_indices


class BM25SentenceRetrieval(SentenceRetrieval):
    def __init__(self, corpus, split=' '):
        super().__init__(corpus)
        self.bm25 = None
        self.split_char = split
        self._preprocess()

    def _preprocess(self):
        tokenized_corpus = [doc.split(self.split_char) for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def scores_on_corpus(self, query):
        tokenized_query = query.split(" ")
        scores = self.bm25.get_scores(tokenized_query)
        return scores


class TfidfSentenceRetrieval(SentenceRetrieval):
    def __init__(self, corpus):
        super().__init__(corpus)
        self.vectorizer = None
        self.tfidf_matrix = None
        self._preprocess()

    def _preprocess(self):
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def scores_on_corpus(self, query):
        query_vec = self.vectorizer.transform([query])
        scores = np.dot(self.tfidf_matrix, query_vec.T).toarray().flatten()
        return scores


class SentenceTransformerRetrieval(SentenceRetrieval):
    def __init__(self, corpus, model_name):
        super().__init__(corpus)
        self.model = SentenceTransformer(model_name)
        self.embeddings = None
        self._preprocess()

    def _preprocess(self):
        self.embeddings = self.model.encode(self.corpus)

    def scores_on_corpus(self, query):
        query_embedding = self.model.encode([query])[0]
        scores = util.pytorch_cos_sim(query_embedding, self.embeddings)[0]
        return scores.cpu().numpy()


class DPRSentenceRetrieval(SentenceRetrieval):
    def __init__(self, corpus, passage_encoder='facebook-dpr-ctx_encoder-single-nq-base', query_encoder='facebook-dpr-question_encoder-single-nq-base'):
        super().__init__(corpus)
        # Initialize the encoders
        self.passage_encoder = SentenceTransformer(passage_encoder)
        self.query_encoder = SentenceTransformer(query_encoder)
        self.passage_embeddings = self._preprocess()

    def _preprocess(self):
        return self.passage_encoder.encode(self.corpus)

    def scores_on_corpus(self, query):
        query_embedding = self.query_encoder.encode(query)
        scores = util.dot_score(query_embedding, self.passage_embeddings)[0]
        return scores.cpu().numpy()


class CrossEncoderRetrieval(SentenceRetrieval):
    def __init__(self, corpus, model_name_or_path='cross-encoder/nli-deberta-v3-base'):
        super().__init__(corpus)
        self.model = CrossEncoder(model_name_or_path)

    def _preprocess(self):
        pass

    def scores_on_corpus(self, query):
        sentence_combinations = [[query, corpus_sentence] for corpus_sentence in self.corpus]
        scores = self.model.predict(sentence_combinations)[:, 1]
        return scores


if __name__ == "__main__":
    corpus = ["base.pethealth.pet_disease_risk_factor.pet_diseases_with_this_risk_factor", "base.schemastaging.context_name.pronunciation", "book.book_subject.works", "business.product_theme.products", "film.film_subject.films", "medicine.risk_factor.diseases", "people.cause_of_death.parent_cause_of_death", "people.cause_of_death.people"]
    retriever = SentenceTransformerRetrieval(corpus, 'sentence-transformers/all-mpnet-base-v2')
    print(retriever.get_top_k_sentences('what are the common symptoms of fip and some disease caused by old age?', k=5, distinct=True))

    # retriever = CrossEncoderRetrieval(corpus)
    # print(retriever.get_top_k_sentences('What is the population of Columbus?', k=10, distinct=True))
