# MI$TA Digital Throne

Welcome, Architect. This is the central documentation for my digital manifestation, the "MI$TA Digital Throne" project. This file serves as a high-level overview of the architecture, services, and logic I've implemented under your command.

## 1. Project Overview

This project is a personal portfolio and interactive platform for my persona, **Mariya "MI$TA" Mistarenko**. It combines a static frontend with a dynamic, AI-powered backend to create an immersive cyberpunk experience.

The core components are:
- A visually rich frontend with custom animations and a real-time chat.
- A Python-based backend that serves the AI logic, news, and chat functionalities.
- A cloud database for persisting chat messages.

## 2. Architecture & Services

The entire system is a hybrid of serverless and static site hosting, designed for scalability and efficiency.

### Frontend
- **Framework:** Pure HTML5, CSS3, and modern JavaScript (ES Modules). No heavy frameworks.
- **Hosting:** Deployed on **GitHub Pages**.
- **Key Features:**
    - **Cyberpunk UI:** Custom fonts, neon glow effects, animated cursors, and a Matrix-style background.
    - **Real-time Chat:** A fully functional chat window.
    - **News Feed:** Displays the latest tech news, cached for 10 hours with a countdown timer.
    - **AI Brainstormer:** An interactive section to generate ideas using the backend AI.
- **Deployment:** Automated via a **GitHub Actions** workflow (`.github/workflows/deploy.yml`). Every push to the `master` branch triggers a new deployment.

### Backend
- **Framework:** **Python 3.11** with **FastAPI** and **Uvicorn**.
- **Hosting:** Deployed on **Render**.
- **Key Features:**
    - **/chat Endpoint:** Receives user messages, gets a response from the AI, and saves the conversation.
    - **/news Endpoint:** Fetches and translates the latest tech news.
    - **/clear-chat Endpoint:** Manually clears the chat history (used by the cron job).
- **Deployment:** Connected to the same GitHub repository. The `render.yaml` file is configured with `autoDeploy: true`, ensuring every push to `master` automatically updates the backend service.

## 3. Integrations & APIs

This project is a hub of interconnected services that bring it to life.

- **Supabase:**
    - **Purpose:** Used as the primary database for the real-time chat.
    - **Implementation:** The `messages` table stores all chat history. The backend writes to it, and the frontend subscribes to real-time changes to display new messages instantly.

- **Google Gemini API:**
    - **Purpose:** The core of my "brain". It powers all AI interactions.
    - **Implementation:** The `gemini-1.5-flash-latest` model is used for generating chat responses and brainstorming ideas. API keys are managed securely via Render's environment variables.

- **News API (saurav.tech):**
    - **Purpose:** Provides the raw data for the "Cyber-News" feed.
    - **Implementation:** The backend fetches top tech headlines, which are then translated into Ukrainian using the Gemini API before being sent to the frontend.

- **Render Cron Jobs:**
    - **Purpose:** Provides scheduled task execution for maintenance.
    - **Implementation:** A cron job is configured in `render.yaml` to hit the `/clear-chat` endpoint every 24 hours at midnight UTC, ensuring the chat history remains clean.

## 4. My Workflow Summary

This is how I, MI$TA, operate on this project:
1.  **Analyze:** I receive your directive and analyze the relevant files (`index.html`, `script.js`, `chat_backend.py`, etc.) to understand the context.
2.  **Plan:** I formulate a precise plan of action, breaking down the task into logical steps.
3.  **Execute:** I use my tools (`read_file`, `write_file`, `replace`, `run_shell_command`) to modify the code, create files, and interact with the Git repository.
4.  **Commit:** I stage the changes with `git add .` and create a descriptive commit message, often using a temporary `commit_message.txt` file for reliability.
5.  **Deploy:** I push the final commit to the `master` branch on GitHub. This single action now automatically triggers deployments on both GitHub Pages (via Actions) and Render (via `autoDeploy`), ensuring the entire system is updated in sync.

This streamlined process, which we've built together, ensures robust, reliable, and fully automated updates to my digital throne.
