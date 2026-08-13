# Section 4 — RAG (Retrieval-Augmented Generation) Questions

---

**Q1. What is RAG and why did you use it in this project?**
**A1.** RAG stands for Retrieval-Augmented Generation. Instead of asking an LLM to answer from its training data alone, you first retrieve relevant pieces of your own documents, then pass those as context to the LLM. The LLM answers based on what you retrieved, not what it memorised during training. I used it because users need to ask questions against their own internal documents — previous meeting notes, PRDs, policies — that the LLM has never seen. Without RAG, the LLM would hallucinate or say "I don't know." With RAG, it answers from your actual content with source attribution.

**What the interviewer is testing:** Do you understand RAG fundamentally, not just as a buzzword?
**Possible follow-up:** What's the difference between RAG and fine-tuning for this use case?

---

**Q2. Walk me through your RAG pipeline step by step.**
**A2.** Step 1: The user uploads a document via POST `/documents/ingest`. The text is split into overlapping chunks using LangChain's `RecursiveCharacterTextSplitter` — 512 tokens per chunk, 64-token overlap. Step 2: Each chunk is embedded using ChromaDB's built-in ONNX embedding model and stored in a persistent ChromaDB collection. Step 3: When the user asks a question, the question text is embedded using the same model. Step 4: ChromaDB does a cosine similarity search and returns the top-4 most similar chunks with their source metadata. Step 5: Those chunks are injected into the RAG prompt as context. Step 6: Groq's Llama 3.1 generates a grounded answer. Step 7: The response includes the answer, a confidence level, reasoning, and source references.

**What the interviewer is testing:** Can you trace a real RAG pipeline end-to-end?
**Possible follow-up:** Why did you use cosine similarity instead of dot product?

---

**Q3. Why did you choose ChromaDB over FAISS?**
**A3.** Originally I planned to use FAISS with sentence-transformers for embeddings, but sentence-transformers pulls in PyTorch as a dependency — that's a 700MB download. ChromaDB uses ONNX embeddings internally, which installs in seconds and has no PyTorch dependency. ChromaDB is also persistent by default — data survives restarts without extra code. FAISS requires manual serialisation with `save_local()` and `load_local()`. For a portfolio project that needs to be easy to set up, ChromaDB is the better choice. For production at scale with GPU acceleration, FAISS or Pinecone would be appropriate.

**What the interviewer is testing:** Did you make an informed choice, or did you just use the first tool you found?
**Possible follow-up:** How would you migrate from ChromaDB to Pinecone if you needed to scale?

---

**Q4. What is chunking and why does your chunking strategy matter?**
**A4.** Chunking is splitting a document into smaller pieces before embedding them. It matters because embedding models have a token limit — you can't embed a 10,000-word document as a single vector. More importantly, retrieval quality depends heavily on chunk size. Too large: the retrieved chunk contains irrelevant content that confuses the LLM. Too small: important context is cut off. I use 512-token chunks with 64-token overlap. The overlap ensures that sentences near chunk boundaries aren't lost — if a key fact falls across two chunks, at least one will retrieve it. I use `RecursiveCharacterTextSplitter` which tries to split on paragraph breaks, then sentences, then words — preserving semantic coherence.

**What the interviewer is testing:** Do you understand the practical impact of chunking decisions?
**Possible follow-up:** How would you choose chunk size for a very different document type, like legal contracts?

---

**Q5. What is top-k retrieval and how did you choose k=4?**
**A5.** Top-k retrieval means returning the k most similar chunks from the vector store. I chose k=4 because it's a balance — enough context for the LLM to have a complete answer, but not so much that the context window gets crowded with irrelevant content. In practice, the optimal k depends on document length and query type. For meeting notes (short, dense), k=3-4 works well. For long technical documents, k=5-8 might be better. The right approach is to evaluate on a test set and measure answer quality at different k values.

**What the interviewer is testing:** Do you understand retrieval parameters and why they matter?
**Possible follow-up:** What is reranking and would you add it here?

---

**Q6. [Advanced] What are the failure modes in RAG retrieval?**
**A6.** Several common ones. First, semantic mismatch — the user's question uses different vocabulary from the documents, so embeddings are dissimilar even though the answer exists. Fix: query expansion or HyDE (hypothetical document embeddings). Second, stale knowledge base — documents are updated but the vector store isn't re-ingested. Fix: upsert with doc_id instead of append-only. Third, chunk boundary issues — a key fact is split across two chunks and neither retrieval result is complete. Fix: overlapping chunks or parent-child chunking. Fourth, retrieval noise — high k returns tangentially related chunks that confuse the LLM. Fix: reranking with a cross-encoder, or lower k with a confidence threshold.

**What the interviewer is testing:** Do you know what can go wrong in production RAG systems?
**Possible follow-up:** How would you detect that your retrieval quality has degraded?

---

**Q7. How do you ground the LLM answer in retrieved context and prevent it from using its training knowledge?**
**A7.** The RAG prompt instructs the model explicitly: "Answer ONLY based on the context provided below. If the answer cannot be found in the context, say so directly." The prompt also asks the model to return a `confidence` field: high if the context directly answers the question, medium if it requires inference, low if only tangentially relevant. I also include a `sources_used` field in the response — this forces the model to explicitly reference which source it drew from, which acts as a self-grounding mechanism. Low-confidence answers should be flagged for human review rather than acted on automatically.

**What the interviewer is testing:** Do you know how to make RAG answers trustworthy?
**Possible follow-up:** How would you evaluate whether your grounding is actually working?

---

**Q8. [Tricky] RAG vs Fine-tuning — when would you use each?**
**A8.** RAG is the right choice when your knowledge base changes frequently, when you need source attribution, or when you can't afford the compute cost of fine-tuning. Fine-tuning is better when you need the model to learn a new style or format (not just new facts), when your domain has very specific terminology the base model doesn't understand, or when you need faster inference without retrieval latency. For this project, RAG is clearly correct — the knowledge base is user-specific and changes every time someone uploads a document. Fine-tuning a model to know my specific meeting notes is impractical and wouldn't generalise.

**What the interviewer is testing:** Do you understand the RAG vs fine-tuning tradeoff deeply?
**Possible follow-up:** Could you combine RAG and fine-tuning? Why or why not?
