# Document RAG Full-Stack Application

An enterprise-grade Full-Stack Document RAG (Retrieval-Augmented Generation) application built with **React (MUI + SCSS)**, **Spring Boot 3 (Java 21)**, **PostgreSQL 17**, and **Ollama (`llama3.2:3b` + `nomic-embed-text`)**.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       React Frontend (Port 5173)      |
                      |   Vite + MUI + MUI DataGrid + SCSS    |
                      +---------------------------------------+
                                          |
                              HTTP / REST + JWT Token
                                          v
                      +---------------------------------------+
                      |     Spring Boot Backend (Port 8080)   |
                      |   Spring Security + Spring Data JPA   |
                      +---------------------------------------+
                                   /             \
                    JPA / SQL     /               \  REST
                                 v                 v
            +------------------------+      +--------------------------+
            |    MySQL (Port 3306)   |      | Python RAG Engine (8000) |
            |  • users               |      | • Ollama (llama3.2:3b)   |
            |  • documents           |      | • ChromaDB Vector DB     |
            |  • chat_logs           |      | • nomic-embed-text       |
            +------------------------+      +--------------------------+
```

---

## Project Structure

* **`frontend/`**:
  * **React 19 + Vite**
  * **Material UI (MUI)**: Clean dialogs, buttons, cards, and theme layout.
  * **MUI DataGrid (`@mui/x-data-grid`)**:
    * **Chunks Explorer**: Inspect all chunked document segments, page numbers, character ranges, and source text.
    * **Query History**: View past user questions, answers, and citation counts stored in PostgreSQL.
  * **SCSS**: Custom variables and stylesheet in `src/styles/`.
* **`backend/`**:
  * **Spring Boot 3.3.5 (Java 21 LTS)**
  * **Spring Security & JWT**: Stateless authentication filter, BCrypt password hashing.
  * **Spring Data JPA**: Auto-managed schema tables (`users`, `documents`, `chat_logs`).
  * **Controllers & Services**: `AuthController`, `ChatController`, `DocumentController`, `RagService`.
* **`document-rag/`**:
  * **Python RAG Engine**: Wraps ChromaDB vector storage and Ollama generation via FastAPI on port `8000`.

---

## Quick Start Guide

### 1. Configure PostgreSQL Password
Open `backend/src/main/resources/application.properties` and ensure `spring.datasource.password` matches the password you entered when installing PostgreSQL:
```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/rag_db
spring.datasource.username=postgres
spring.datasource.password=YOUR_POSTGRES_PASSWORD
```
*(Make sure a database named `rag_db` exists in PostgreSQL: `CREATE DATABASE rag_db;`)*

### 2. Run Everything with One Click
Double-click:
```
start_all.bat
```
This launches all three services in separate command windows:
1. **Python RAG Service**: `http://127.0.0.1:8000`
2. **Spring Boot Backend**: `http://localhost:8080`
3. **React Web UI**: `http://localhost:5173`

---

## Individual Service Launchers
You can also run services independently:
* **RAG Engine**: Run `document-rag\run_rag.bat`
* **Spring Boot**: Run `backend\run_backend.bat`
* **React UI**: Run `frontend\run_frontend.bat`

