# summarization_ollama
AI-powered FastAPI service for generating concise, high-quality Italian summaries from long documents using LLaMA 3.2 and intelligent text chunking.
📄 LLaMA-Powered Summarization API
An AI-powered document summarization service built with FastAPI that utilizes the LLaMA 3.2 language model to generate concise and professional summaries of Italian texts. Designed for scalability and clarity, this API supports both individual and aggregated document summarization.

🚀 Overview
This project streamlines the process of summarizing long and complex documents by leveraging cutting-edge NLP tools and asynchronous architecture. It is ideal for applications that require formal, high-quality summaries in Italian, such as corporate documentation, legal texts, or healthcare reports.

🧰 Technologies & Tools Used
⚙️ Backend Framework
FastAPI: A modern, high-performance web framework for building APIs with automatic interactive documentation and async support.

🧠 AI & NLP
LLaMA 3.2: A powerful language model used to generate summaries that are clear, concise, and aligned with professional Italian writing standards.

Ollama API: Provides access to local or remote LLaMA instances for generating completions.

🔄 Asynchronous Processing
httpx: An async HTTP client used to interact with the LLaMA model endpoint efficiently, ensuring non-blocking operations and scalability.

✅ Data Validation
Pydantic: Used for defining and validating request schemas, ensuring structured and predictable input handling.

🔧 Utilities
Custom Chunking Logic: Implements a word-based text splitter to divide large documents into manageable segments before summarization.

Dynamic Prompt Builder: Crafts structured, context-sensitive prompts tailored for summarization tasks in Italian.

📊 Configuration
Environment Variables: Externalizes configuration (e.g., API endpoint for the model) for flexibility across different deployment environments.

🗂 Architecture Highlights
Modular Design: Clean separation of configuration, utility functions, models, and core summarization logic.

Scalable Chunking Strategy: Automatically detects large input sizes and handles chunk-wise processing and merging of summaries.

Dual Mode Support: Allows summarizing each document individually or as a single aggregated text block for high-level synthesis.

🏁 Summary
This project combines state-of-the-art AI models with an efficient, modern API architecture to deliver an intuitive and robust summarization service. With a focus on Italian language output and professional-grade summaries, it is ideal for businesses, researchers, and developers working on document automation and content distillation.
