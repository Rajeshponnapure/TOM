# NLP Skills — Comprehensive Guide

## 1. Tokenization

### BPE (Byte-Pair Encoding)

```python
# BPE tokenization (used by GPT models)
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders

# Train BPE from scratch
tokenizer = Tokenizer(models.BPE())

# Pre-tokenizer: split on whitespace and punctuation
tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)

# Trainer
trainer = trainers.BpeTrainer(
    vocab_size=32000,
    min_frequency=2,
    special_tokens=["<s>", "<pad>", "</s>", "<unk>", "<mask>"],
)

# Train on files
files = ["corpus.txt", "more_data.txt"]
tokenizer.train(files, trainer)

# Post-processing
tokenizer.post_processor = processors.ByteLevel(trim_offsets=True)
tokenizer.decoder = decoders.ByteLevel()

# Save/Load
tokenizer.save("tokenizer.json")
tokenizer = Tokenizer.from_file("tokenizer.json")

# Encode/Decode
output = tokenizer.encode("Hello, world!")
print(f"Tokens: {output.tokens}")
print(f"IDs:    {output.ids}")
print(f"Decoded: {tokenizer.decode(output.ids)}")
```

### WordPiece (BERT)

```python
from transformers import BertTokenizer

# Load pretrained
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Encode
encoded = tokenizer(
    "Hello, how are you?",
    padding=True,
    truncation=True,
    max_length=128,
    return_tensors='pt',
)

print(f"Input IDs: {encoded['input_ids']}")
print(f"Attention mask: {encoded['attention_mask']}")
print(f"Token type IDs: {encoded['token_type_ids']}")

# Decode
decoded = tokenizer.decode(encoded['input_ids'][0])
print(f"Decoded: {decoded}")

# Batch encoding
batch = tokenizer(
    ["Hello world", "How are you?", "I'm fine"],
    padding=True,
    truncation=True,
    max_length=64,
    return_tensors='pt',
)

# Add special tokens manually
tokens = tokenizer.tokenize("Hello world")
print(f"Tokens: {tokens}")  # ["hello", "world"]

# Convert to IDs
ids = tokenizer.convert_tokens_to_ids(tokens)
```

### SentencePiece

```python
import sentencepiece as spm

# Train
spm.SentencePieceTrainer.train(
    input='corpus.txt',
    model_prefix='sp_model',
    vocab_size=32000,
    model_type='bpe',  # or 'unigram'
    character_coverage=1.0,
    split_by_whitespace=True,
    split_digits=True,
)

# Load
sp = spm.SentencePieceProcessor()
sp.load('sp_model.model')

# Encode
ids = sp.encode("Hello, world!")
pieces = sp.encode("Hello, world!", out_type=str)
print(f"Pieces: {pieces}")
print(f"IDs:    {ids}")

# Decode
decoded = sp.decode(ids)
print(f"Decoded: {decoded}")

# Properties
print(f"Vocab size: {sp.vocab_size()}")
print(f"Bos ID: {sp.bos_id()}, Eos ID: {sp.eos_id()}, Unknown ID: {sp.unk_id()}")
```

### tiktoken (OpenAI)

```python
import tiktoken

# Load encoding
encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4, GPT-3.5-turbo
# encoding = tiktoken.encoding_for_model("gpt-4")

# Encode
tokens = encoding.encode("Hello, world!")
print(f"Tokens: {tokens}")
print(f"Count: {len(tokens)}")

# Decode
text = encoding.decode(tokens)
print(f"Text: {text}")

# Count tokens quickly
def count_tokens(text: str, model: str = "gpt-4") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# Token cost estimator
def estimate_cost(text: str, model: str = "gpt-4") -> float:
    """Estimate API cost for input text."""
    tokens = count_tokens(text, model)
    rates = {
        "gpt-4": (0.03, 0.06),           # input, output per 1K tokens
        "gpt-3.5-turbo": (0.001, 0.002),
    }
    input_rate, output_rate = rates.get(model, (0, 0))
    return (tokens / 1000) * input_rate
```

## 2. Embeddings

### Word2Vec (Gensim)

```python
from gensim.models import Word2Vec, KeyedVectors
from gensim.models.word2vec import LineSentence

# Train
sentences = LineSentence('corpus.txt')
model = Word2Vec(
    sentences,
    vector_size=300,
    window=5,
    min_count=5,
    workers=4,
    sg=1,  # 0=CBOW, 1=Skip-gram
    negative=5,
    hs=0,  # 0=negative sampling, 1=hierarchical softmax
    epochs=10,
)

# Save/Load
model.save("word2vec.model")
model = Word2Vec.load("word2vec.model")

# Most similar words
similar = model.wv.most_similar("king", topn=10)
for word, score in similar:
    print(f"{word}: {score:.4f}")

# Analogy: king - man + woman = ?
result = model.wv.most_similar(positive=["king", "woman"], negative=["man"])
print(f"Analogy result: {result[0][0]}")

# Similarity
sim = model.wv.similarity("cat", "dog")
print(f"Similarity: {sim:.3f}")

# Get vector
vector = model.wv["king"]

# Doesnt match
odd = model.wv.doesnt_match(["cat", "dog", "car", "bird"])
print(f"Odd one out: {odd}")

# Load pretrained GloVe
# from gensim.scripts.glove2word2vec import glove2word2vec
# glove2word2vec('glove.6B.300d.txt', 'glove.6B.300d.word2vec.txt')
# glove = KeyedVectors.load_word2vec_format('glove.6B.300d.word2vec.txt')
```

### FastText

```python
from gensim.models import FastText

# FastText handles out-of-vocabulary (OOV) words via subword info
model = FastText(
    sentences=LineSentence('corpus.txt'),
    vector_size=300,
    window=5,
    min_count=5,
    min_n=3,     # min character n-gram
    max_n=6,     # max character n-gram
    workers=4,
    sg=1,
    epochs=10,
)

# OOV word handling
vector = model.wv["never_seen_word_before"]  # Still works!

# Save/Load
model.save("fasttext.model")
model = FastText.load("fasttext.model")
```

### Contextual Embeddings (Sentence Transformers)

```python
from sentence_transformers import SentenceTransformer, util

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, good quality

# Encode sentences
sentences = [
    "This is an example sentence",
    "Each sentence is converted to a vector",
    "Semantic similarity search finds related texts",
]
embeddings = model.encode(sentences)

# Compute similarities
similarities = util.cos_sim(embeddings[0], embeddings[1])
print(f"Similarity: {similarities[0][0]:.4f}")

# Semantic search
query = "Find similar documents"
query_embedding = model.encode(query)
scores = util.cos_sim(query_embedding, embeddings)[0]
best_idx = scores.argmax().item()
print(f"Best match: {sentences[best_idx]} (score: {scores[best_idx]:.4f})")

# Asymmetric models (for QA)
model = SentenceTransformer('msmarco-distilbert-base-v4')

# Batch processing
embeddings = model.encode(sentences, batch_size=32, show_progress_bar=True, normalize_embeddings=True)

# Dimensionality
print(f"Embedding dimension: {embeddings.shape[1]}")
```

## 3. RAG (Retrieval-Augmented Generation)

### Full RAG Pipeline

```python
import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Any
import hashlib

class RAGPipeline:
    def __init__(self, embedding_model="all-MiniLM-L6-v2", collection_name="docs"):
        self.embedder = SentenceTransformer(embedding_model)
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", " ", ""],
        )

    def add_documents(self, documents: List[Dict[str, str]]):
        """Add documents to vector store.

        Args:
            documents: List of {"id": str, "text": str, "metadata": dict}
        """
        texts = []
        ids = []
        metadatas = []
        all_chunks = []

        for doc in documents:
            chunks = self.text_splitter.split_text(doc["text"])
            all_chunks.extend(chunks)

            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc.get('id', hashlib.md5(chunk.encode()).hexdigest())}_{i}"
                texts.append(chunk)
                ids.append(chunk_id)
                metadatas.append({
                    **doc.get("metadata", {}),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                })

        # Generate embeddings in batch
        embeddings = self.embedder.encode(texts).tolist()

        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        return len(texts)

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query."""
        query_embedding = self.embedder.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        retrieved = []
        for i in range(len(results["documents"][0])):
            retrieved.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i],  # Convert distance to similarity
            })
        return retrieved

    def query(self, query: str, k: int = 5, llm=None) -> Dict[str, Any]:
        """Retrieve and optionally generate."""
        retrieved = self.retrieve(query, k)

        context = "\n\n".join([r["text"] for r in retrieved])

        if llm:
            prompt = f"""Answer the question based only on the provided context.

Context:
{context}

Question: {query}

Answer:"""
            response = llm(prompt)
        else:
            response = None

        return {
            "query": query,
            "response": response,
            "retrieved_chunks": retrieved,
        }
```

### Chunking Strategies

```python
# Recursive character splitting
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
    SentenceTransformersTokenTextSplitter,
    MarkdownHeaderTextSplitter,
)

# Recursive: tries to split on paragraphs -> sentences -> words
recursive_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
    length_function=len,
)

# Token-based (for LLM context limits)
token_splitter = TokenTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    encoding_name="cl100k_base",
)

# Semantic chunking (by sentence boundaries)
sentence_splitter = SentenceTransformersTokenTextSplitter(
    chunk_size=256,
    chunk_overlap=32,
    model_name="sentence-transformers/all-mpnet-base-v2",
)

# Markdown-aware
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
)

# Semantic chunking (custom — merge related sentences)
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def semantic_chunk(sentences, embedder, threshold=0.5):
    """Chunk sentences by semantic similarity."""
    embeddings = embedder.encode(sentences)
    chunks = []
    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):
        sim = cosine_similarity(
            [embeddings[i-1]], [embeddings[i]]
        )[0][0]

        if sim < threshold:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentences[i]]
        else:
            current_chunk.append(sentences[i])

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
```

### Embedding Models Comparison

| Model | Dimensions | Speed | Quality | Use Case |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | 384 | Very Fast | Good | General purpose |
| all-mpnet-base-v2 | 768 | Fast | Better | Semantic search |
| text-embedding-3-small | 1536 | API call | Very Good | OpenAI ecosystem |
| text-embedding-3-large | 3072 | API call | Best | High-accuracy |
| mxbai-embed-large-v1 | 1024 | Moderate | Excellent | Open-source |
| BAAI/bge-large-en-v1.5 | 1024 | Moderate | Excellent | Open-source |

### Reranking

```python
from sentence_transformers import CrossEncoder

# Cross-encoder reranker (more accurate than bi-encoder retrieval)
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank(query: str, candidates: List[str], top_k: int = 5):
    pairs = [[query, doc] for doc in candidates]
    scores = reranker.predict(pairs)

    # Sort by score descending
    scored = list(zip(candidates, scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored[:top_k]

# Hybrid search combining dense + sparse (BM25)
from rank_bm25 import BM25Okapi

class HybridSearch:
    def __init__(self, dense_embedder, alpha=0.5):
        self.dense = dense_embedder
        self.alpha = alpha
        self.bm25 = None
        self.documents = []

    def fit(self, documents: List[str]):
        self.documents = documents
        tokenized = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized)

    def search(self, query: str, k: int = 10):
        # Dense retrieval
        query_emb = self.dense.encode([query])
        doc_embs = self.dense.encode(self.documents)
        dense_scores = cosine_similarity(query_emb, doc_embs)[0]

        # Sparse retrieval (BM25)
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)

        # Normalize scores
        dense_scores = (dense_scores - dense_scores.min()) / (dense_scores.max() - dense_scores.min() + 1e-8)
        bm25_scores = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-8)

        # Combine
        combined = self.alpha * dense_scores + (1 - self.alpha) * bm25_scores

        # Get top k
        top_indices = combined.argsort()[-k:][::-1]
        return [(self.documents[i], combined[i]) for i in top_indices]
```

## 4. Prompt Engineering

### Zero-Shot

```python
zero_shot_prompt = """Classify the sentiment of the following text as Positive, Negative, or Neutral.

Text: I absolutely loved the movie! The acting was fantastic.
Sentiment:"""

# Result: Positive
```

### Few-Shot

```python
few_shot_prompt = """Convert natural language to SQL queries.

Example 1:
Question: Find all users who signed up in 2023.
SQL: SELECT * FROM users WHERE YEAR(created_at) = 2023;

Example 2:
Question: Get total revenue by product category for last month.
SQL: SELECT p.category, SUM(o.total) as revenue
FROM orders o
JOIN products p ON o.product_id = p.id
WHERE o.created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
GROUP BY p.category;

Example 3:
Question: List top 10 customers by lifetime value.
SQL: SELECT customer_id, SUM(total) as ltv
FROM orders
GROUP BY customer_id
ORDER BY ltv DESC
LIMIT 10;

Now answer:
Question: Find products that have never been ordered.
SQL:"""
```

### Chain-of-Thought (CoT)

```python
cot_prompt = """Solve the following math problem step by step.

Problem: A store has 120 apples. It sells 35 apples in the morning and 28 in the afternoon. How many apples are left?

Step 1: Start with total apples: 120
Step 2: Subtract morning sales: 120 - 35 = 85
Step 3: Subtract afternoon sales: 85 - 28 = 57
Step 4: Final answer: 57 apples are left.

Now solve this problem:
Problem: A train travels at 60 mph for 2 hours, then at 80 mph for 1.5 hours. What is the total distance traveled?

Step 1:"""
```

### ReAct (Reasoning + Acting)

```python
react_prompt = """You are an AI assistant with access to tools. Use them to answer questions.

Available tools:
- search(query): Search the web for information
- calculate(expression): Evaluate a mathematical expression
- get_current_time(): Get the current date and time

Use this format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the tool to use (one of: search, calculate, get_current_time)
Action Input: the input to the tool
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: What is the current temperature in Tokyo in Fahrenheit?

Thought: I need to find the current temperature in Tokyo.
Action: search
Action Input: current temperature Tokyo

Observation: Tokyo, Japan - Current temperature: 22°C

Thought: The temperature is in Celsius. I need to convert to Fahrenheit.
Action: calculate
Action Input: (22 * 9/5) + 32

Observation: 71.6

Thought: I now know the final answer.
Final Answer: The current temperature in Tokyo is 71.6°F.

Now answer:
Question: If a movie starts at 2:15 PM and lasts 148 minutes, what time does it end?
"""
```

### Self-Consistency

```python
# Generate multiple reasoning paths, take majority vote
from openai import OpenAI

client = OpenAI()

def self_consistency(question: str, n_paths: int = 5):
    responses = []
    for _ in range(n_paths):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Solve step by step."},
                {"role": "user", "content": question}
            ],
            temperature=0.7,  # Higher temperature for diversity
        )
        responses.append(response.choices[0].message.content)

    # Parse final answers (assuming they follow a pattern like "Answer: X")
    answers = []
    for r in responses:
        if "Answer:" in r:
            answer = r.split("Answer:")[-1].strip()
            answers.append(answer)

    # Majority vote
    from collections import Counter
    if answers:
        most_common = Counter(answers).most_common(1)[0]
        print(f"Consensus answer: {most_common[0]} ({most_common[1]}/{len(answers)} votes)")
        return most_common[0]
    return None
```

## 5. Fine-Tuning

### LoRA (Low-Rank Adaptation)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import torch

# Load base model
model_name = "meta-llama/Llama-2-7b-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# LoRA config
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,              # Rank
    lora_alpha=32,    # Scaling factor
    lora_dropout=0.1,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    bias="none",
)

# Apply LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Trainable params: ~0.1% of original

# Dataset preparation
def format_instruction(example):
    return {
        "text": f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['response']}{tokenizer.eos_token}"
    }

dataset = Dataset.from_list(data).map(format_instruction)

# Training
training_args = TrainingArguments(
    output_dir="./lora-finetuned",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
    report_to="none",
)

# Use SFTTrainer for supervised fine-tuning
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    dataset_text_field="text",
    tokenizer=tokenizer,
    max_seq_length=512,
)
trainer.train()

# Save adapter
model.save_pretrained("lora-adapter")
tokenizer.save_pretrained("lora-adapter")
```

### QLoRA (Quantized LoRA)

```python
from transformers import BitsAndBytesConfig

# 4-bit quantization config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",        # Normal Float 4
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,   # Double quantization
)

# Load quantized model
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16,
)

# Apply LoRA on quantized model
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Trainable params: ~0.05% (even fewer due to quantization)

# Train the same way
```

### RLHF (Reinforcement Learning from Human Feedback)

```python
# RLHF pipeline components:
# 1. SFT: Supervised fine-tuning on demonstrations
# 2. RM: Train reward model on human preferences
# 3. RL: PPO optimization using the reward model

from trl import PPOConfig, PPOTrainer
from transformers import AutoModelForSequenceClassification

# Step 1: SFT (done above)
# Step 2: Train reward model
reward_model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=1,
    torch_dtype=torch.bfloat16,
)

# Train reward model on preference pairs
# Input: (chosen_response, rejected_response) -> output: reward score

# Step 3: PPO
ppo_config = PPOConfig(
    model_name="lora-adapter",  # Your SFT model
    learning_rate=1.41e-5,
    batch_size=16,
    mini_batch_size=4,
    gradient_accumulation_steps=1,
    optimize_cuda_cache=True,
)

# ppo_trainer = PPOTrainer(ppo_config, ...)
```

### DPO (Direct Preference Optimization)

```python
from trl import DPOTrainer

# DPO avoids the explicit reward model step
training_args = TrainingArguments(
    output_dir="./dpo-finetuned",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,
    num_train_epochs=3,
    learning_rate=5e-5,
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
    report_to="none",
)

# Dataset with preference pairs
# Each example: {"prompt": "...", "chosen": "...", "rejected": "..."}

dpo_trainer = DPOTrainer(
    model=model,
    ref_model=None,  # Auto-initialized from model
    args=training_args,
    train_dataset=dpo_dataset,
    tokenizer=tokenizer,
    beta=0.1,  # DPO temperature parameter
    max_prompt_length=256,
    max_length=512,
)
dpo_trainer.train()
```

## 6. LLM Architectures

### Architecture Comparison

| Model | Parameters | Architecture | Context Length | Key Innovation |
|---|---|---|---|---|
| GPT-4 | ~1.8T (est) | Transformer Decoder | 32K-128K | MoE, RLHF |
| Llama 3 | 8B-405B | Transformer Decoder | 8K-128K | RoPE, GQA, SwiGLU |
| Mistral | 7B | Transformer Decoder | 32K | Sliding window, GQA |
| Gemma | 2B-7B | Transformer Decoder | 8K | GeGLU, RMSNorm |
| Claude 3 | Unknown | Transformer Decoder | 200K | Constitutional AI |
| DeepSeek-V2 | 236B (MoE) | Transformer Decoder | 128K | Multi-head latent attention |
| BERT | 110M-340M | Transformer Encoder | 512 | Bidirectional, MLM |
| T5 | 60M-11B | Encoder-Decoder | 512 | Text-to-text framework |

### Attention Mechanism Variants

```python
# Multi-Head Attention (standard)
class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        self.wq = nn.Linear(d_model, d_model)
        self.wk = nn.Linear(d_model, d_model)
        self.wv = nn.Linear(d_model, d_model)
        self.wo = nn.Linear(d_model, d_model)

    def forward(self, x, mask=None):
        B, T, D = x.shape
        Q = self.wq(x).view(B, T, self.n_heads, self.d_k).transpose(1, 2)
        K = self.wk(x).view(B, T, self.n_heads, self.d_k).transpose(1, 2)
        V = self.wv(x).view(B, T, self.n_heads, self.d_k).transpose(1, 2)

        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.d_k ** 0.5)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, V)
        out = out.transpose(1, 2).contiguous().view(B, T, D)
        return self.wo(out)

# Grouped Query Attention (GQA) — used in Llama 2+, Mistral
class GroupedQueryAttention(nn.Module):
    def __init__(self, d_model, n_heads, n_kv_heads):
        super().__init__()
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads
        self.n_groups = n_heads // n_kv_heads
        self.d_k = d_model // n_heads

        self.wq = nn.Linear(d_model, d_model)
        self.wk = nn.Linear(d_model, d_model * n_kv_heads // n_heads)
        self.wv = nn.Linear(d_model, d_model * n_kv_heads // n_heads)
        self.wo = nn.Linear(d_model, d_model)

    def forward(self, x, mask=None):
        B, T, D = x.shape
        Q = self.wq(x).view(B, T, self.n_heads, self.d_k).transpose(1, 2)
        K = self.wk(x).view(B, T, self.n_kv_heads, self.d_k).transpose(1, 2)
        V = self.wv(x).view(B, T, self.n_kv_heads, self.d_k).transpose(1, 2)

        # Repeat K, V for each group
        K = K.repeat_interleave(self.n_groups, dim=1)
        V = V.repeat_interleave(self.n_groups, dim=1)

        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.d_k ** 0.5)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, V)
        out = out.transpose(1, 2).contiguous().view(B, T, D)
        return self.wo(out)
```

## 7. Vector Databases

### ChromaDB

```python
import chromadb
from chromadb.config import Settings

# Client
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db"
))

# Collection
collection = client.create_collection(
    name="my_docs",
    metadata={"hnsw:space": "cosine", "hnsw:construction_ef": 100}
)

# Add documents
collection.add(
    documents=[
        "This is a document about machine learning",
        "Deep learning uses neural networks",
        "Natural language processing is a subfield of AI",
    ],
    metadatas=[
        {"source": "wiki", "category": "ML"},
        {"source": "wiki", "category": "DL"},
        {"source": "paper", "category": "NLP"},
    ],
    ids=["doc1", "doc2", "doc3"],
)

# Query
results = collection.query(
    query_texts=["What is neural network?"],
    n_results=2,
    include=["documents", "metadatas", "distances"],
)

# Filter query
results = collection.query(
    query_texts=["AI"],
    where={"category": "ML"},
    n_results=5,
)

# Update
collection.update(
    ids=["doc1"],
    documents=["Updated document about AI"],
    metadatas=[{"source": "updated"}],
)

# Delete
collection.delete(ids=["doc3"])

# Collection statistics
print(f"Count: {collection.count()}")
print(f"Name: {collection.name}")
```

### Pinecone

```python
import pinecone

# Initialize
pinecone.init(api_key="your-api-key", environment="us-west1-gcp")

# Create index
if "my-index" not in pinecone.list_indexes():
    pinecone.create_index(
        name="my-index",
        dimension=384,
        metric="cosine",
        pods=1,
        pod_type="p1.x1"
    )

# Connect
index = pinecone.Index("my-index")

# Upsert
vectors = [
    ("vec1", [0.1, 0.2, ...], {"category": "science"}),
    ("vec2", [0.3, 0.4, ...], {"category": "tech"}),
]
index.upsert(vectors=vectors, namespace="default")

# Query
results = index.query(
    vector=[0.15, 0.25, ...],
    top_k=5,
    include_metadata=True,
    filter={"category": {"$eq": "science"}}
)

# Delete
index.delete(ids=["vec1"], namespace="default")
# index.delete_all()

# Describe index stats
stats = index.describe_index_stats()
print(f"Total vectors: {stats['total_vector_count']}")
```

### Qdrant

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
)

# Client
client = QdrantClient(host="localhost", port=6333)

# Create collection
client.recreate_collection(
    collection_name="my_collection",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# Upsert
points = [
    PointStruct(id=1, vector=[0.1, 0.2, ...], payload={"text": "doc1"}),
    PointStruct(id=2, vector=[0.3, 0.4, ...], payload={"text": "doc2"}),
]
client.upsert(collection_name="my_collection", points=points)

# Search
hits = client.search(
    collection_name="my_collection",
    query_vector=[0.15, 0.25, ...],
    limit=5,
    query_filter=Filter(
        must=[FieldCondition(key="category", match=MatchValue(value="science"))]
    ),
)

# Scroll (get all)
records, next_offset = client.scroll(
    collection_name="my_collection",
    limit=100,
    with_payload=True,
    with_vectors=False,
)
```

### Weaviate

```python
import weaviate

# Client
client = weaviate.Client(
    url="http://localhost:8080",
    auth_client_secret=weaviate.AuthApiKey(api_key="your-key"),
    additional_headers={
        "X-OpenAI-Api-Key": "your-openai-key",
    }
)

# Create schema
class_obj = {
    "class": "Document",
    "vectorizer": "text2vec-openai",  # Auto-vectorization
    "properties": [
        {"name": "text", "dataType": ["text"]},
        {"name": "category", "dataType": ["string"]},
    ],
}
client.schema.create_class(class_obj)

# Add data (auto-vectorized)
client.data_object.create(
    data_object={"text": "Machine learning is fun", "category": "ML"},
    class_name="Document",
)

# Query
response = client.query.get(
    "Document", ["text", "category"]
).with_near_text({
    "concepts": ["neural networks"]
}).with_limit(5).do()

# Hybrid search (vector + keyword)
response = client.query.get(
    "Document", ["text"]
).with_hybrid(
    query="AI concepts",
    alpha=0.75  # 0.75 vector, 0.25 keyword
).with_limit(10).do()

# Filter
response = client.query.get(
    "Document", ["text"]
).with_where({
    "path": ["category"],
    "operator": "Equal",
    "valueString": "ML"
}).with_limit(10).do()
```

### Vector DB Comparison

| Feature | ChromaDB | Pinecone | Qdrant | Weaviate |
|---|---|---|---|---|
| Open source | Yes | No | Yes | Yes |
| Self-hosted | Yes | No | Yes | Yes |
| Managed cloud | No | Yes | Yes | Yes |
| Filtering | Basic | Good | Advanced | Advanced |
| Auto-embedding | No | No | No | Yes |
| Hybrid search | No | No | Yes | Yes |
| Multi-tenancy | Manual | Namespaces | Manual | Yes |
| Speed | Fast | Very Fast | Very Fast | Moderate |
| Ease of use | Easiest | Easy | Moderate | Moderate |
| Disk-based | Yes | No | Yes | Yes |
