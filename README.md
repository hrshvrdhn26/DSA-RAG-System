# DSA RAG System

## AI-Powered YouTube Transcript Retrieval for Data Structures & Algorithms

An AI-powered Retrieval-Augmented Generation (RAG) system for searching DSA explanations across YouTube video transcripts using semantic retrieval and LLM-based response generation.

The system processes YouTube transcripts, cleans and chunks the content, generates vector embeddings, stores them in Qdrant, and retrieves relevant transcript segments based on natural-language queries.

---

## Overview

Finding a specific DSA explanation inside long-form educational videos can be inefficient with traditional keyword search.

This project addresses that problem by building a semantic retrieval system over DSA YouTube transcripts.

A user can ask a natural-language query such as:

> Explain the sliding window technique for finding the longest substring.

The system retrieves relevant transcript segments along with the corresponding video context and timestamp information.

### Architecture

```text
YouTube Videos
      |
      v
Transcript Extraction
      |
      v
Transcript Cleaning
      |
      v
Text Chunking
      |
      v
Sentence Embeddings
      |
      v
Qdrant Vector Database
      |
      v
Semantic Retrieval
      |
      v
Relevant Transcript Context
      |
      v
LLM Response Generation
