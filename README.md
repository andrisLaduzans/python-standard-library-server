# Todo API

A simple HTTP Todo API built with Python's `http.server` and SQLite.

## Requirements

- Python 3.14+
- macOS or another Unix-like environment

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
```

### 2. Activate the virtual environment

```bash
source .venv/bin/activate
```

To deactivate it later:

```bash
deactivate
```

### 3. Install dependencies

If `requirements.txt` already exists:

```bash
python -m pip install -r requirements.txt
```

Otherwise, install the current dependency:

```bash
python -m pip install python-dotenv
```

### 4. Save dependencies

After installing or changing dependencies, update `requirements.txt`:

```bash
python -m pip freeze > requirements.txt
```

Commit `requirements.txt` to version control so the environment can be recreated later.

### 5. Linting

Check for lint issues

```bash
python -m ruff check .
```

Automatically fix safe lint issues

```bash
python -m ruff check . --fix
```

Format Python files

```bash
python -m ruff format .
````

## Configuration

Create a `.env` file in the project root:

```dotenv
TODO_DB_PATH=./data/todos.db
```

The application loads this configuration at startup.

Make sure the configured database's parent directory exists.

## Run the server

Activate the virtual environment if it isn't already active:

```bash
source .venv/bin/activate
```

Start the server:

```bash
python -m todo_api.main
```

The API will be available at:

```text
http://localhost:8000
```

Stop the server with `Ctrl+C`.

## Authentication

All `/todos` routes require a Bearer token. Requests without a valid token return `401 Unauthorized`.

Create a token for a user:

```bash
python -m todo_api.create_token <user_id>
```

The token is printed once. Only its hash is stored, so save it somewhere safe.

Send it with each request:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/todos
```

Tokens are stored in the database at `TODO_DB_PATH`, so the command and the server must use the same configuration.

## Testing

Run the HTTP handler tests:

```bash
python -m unittest -v
```
