# Therapist Copilot

Therapist Copilot is an AI-powered backend service designed to assist therapists by providing real-time audio transcription and risk assessment during therapy sessions. It integrates with industry-leading Speech-to-Text (STT) providers like Deepgram and OpenAI Whisper, and utilizes advanced Large Language Models (LLMs) like Google Gemini for analyzing text to detect potential risks such as suicide or self-harm.

## Features

- **Real-time Audio Transcription:**
  - High-accuracy transcription using **Deepgram** (cloud-based) or **OpenAI Whisper** (local).
  - Support for WebSocket streaming for low-latency live transcription.
- **Risk Assessment:**
  - Real-time analysis of transcribed text to detect crisis situations.
  - powered by **Google Gemini** (via LangChain) to identify risks like suicide, self-harm, and violence.
- **Flexible API:**
  - RESTful endpoints for file uploads and text analysis.
  - WebSocket endpoints for streaming audio data.
- **Robust Architecture:**
  - Built with **FastAPI** for high performance.
  - Containerized with **Docker** for easy deployment.
  - Comprehensive logging and health monitoring.
  - **Simplified Design:** No database required, in-memory session management for ease of use.

## Tech Stack

- **Language:** Python 3.11
- **Framework:** FastAPI, Uvicorn
- **AI/ML:**
  - **LLM:** LangChain, Google Gemini (via `langchain-google-genai`)
  - **STT:** Deepgram SDK, OpenAI Whisper, Torch, Torchaudio
- **Dependency Management:** Pipenv
- **Containerization:** Docker, Docker Compose

## Prerequisites

- **Docker** and **Docker Compose** (for containerized deployment)
- **Python 3.11** and **Pipenv** (for local development)
- **API Keys:**
  - **Deepgram API Key** (for Deepgram STT)
  - **Google Gemini API Key** (for Risk Assessment)

## Installation & Setup

### Using Docker (Recommended)

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd therapist-copilot
    ```

2.  **Configure Environment Variables:**
    Create a `.env` file in the `backend` directory (or root, depending on your setup) based on the configuration options below.

3.  **Build and Run:**
    You can use the provided helper script:
    ```bash
    ./start.sh
    ```
    Or use Docker Compose directly:
    ```bash
    docker-compose up --build
    ```
    The API will be available at `http://localhost:8000`.

### Local Development

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Install Dependencies:**
    ```bash
    pipenv install --dev
    ```

3.  **Activate Virtual Environment:**
    ```bash
    pipenv shell
    ```

4.  **Run the Application:**
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

## Configuration

Configure the application using environment variables. You can set these in a `.env` file.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `APP_NAME` | Name of the application | Therapist Copilot API |
| `DEBUG` | Enable debug mode | `False` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `PORT` | Server port | `8000` |
| **LLM Configuration** | | |
| `LLM_PROVIDER` | LLM Provider (e.g., `gemini`) | `gemini` |
| `LLM_MODEL_RISK` | Model for risk assessment | `gemini-2.0-flash-exp` |
| `GEMINI_API_KEY` | **Required** Google Gemini API Key | |
| **STT Configuration** | | |
| `STT_PROVIDER` | STT Provider (`deepgram` or `whisper`) | `deepgram` |
| `DEEPGRAM_API_KEY` | **Required** if using Deepgram | |
| `DEEPGRAM_MODEL` | Deepgram model to use | `nova-2` |
| `WHISPER_MODEL_SIZE` | Whisper model size (if using Whisper) | `base` |
| **Security** | | |
| `THERAPIST_TOKEN` | Token for authentication (if enabled) | `supersecret-dev-token` |
| `SECRET_KEY` | Secret key for crypto operations | `replace-me` |

## API Documentation

Once the application is running, you can access the interactive API documentation (Swagger UI) at:

**`http://localhost:8000/docs`**

### Key Endpoints

- **Health Check:** `GET /api/v1/health`
- **Transcribe File:** `POST /api/v1/stt/transcribe`
  - Upload an audio file for transcription.
- **Assess Risk:** `POST /api/v1/risk/assess`
  - Send text to be analyzed for risk.
- **WebSocket Stream:** `WS /api/v1/ws/audio/{session_id}`
  - Stream audio data for real-time transcription and analysis.

## Project Structure

```
therapist-copilot/
├── backend/                # Backend application code
│   ├── main.py             # Application entry point
│   ├── config.py           # Configuration management
│   ├── routes/             # API route handlers
│   ├── services/           # Business logic (STT, Risk Assessment)
│   ├── Dockerfile          # Docker configuration for backend
│   └── Pipfile             # Python dependencies
├── docker/                 # Additional Docker resources
├── docker-compose.yml      # Docker Compose configuration
└── scripts/                # Helper scripts
```

## License

MIT License