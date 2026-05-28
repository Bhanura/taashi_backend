# Taashi Backend

This is the backend for the Taashi Assistant application, built with FastAPI.

## Getting Started

Follow these instructions to get the backend server up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.8+
- `pip` for package management
- An internet connection to download dependencies
- A running MongoDB instance.

### Installation and Setup

1.  **Navigate to the backend directory:**
    Open your terminal and change your directory to where this `README.md` file is located.
    ```bash
    cd path/to/taashi_project/taashi_backend
    ```

2.  **Create a Python virtual environment:**
    It's a best practice to create a virtual environment to keep project dependencies isolated.

    On Windows:
    ```bash
    python -m venv venv
    ```

    On macOS and Linux:
    ```bash
    python3 -m venv venv
    ```

3.  **Activate the virtual environment:**

    On Windows (PowerShell):
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```

    On Windows (Command Prompt):
    ```bash
    .\venv\Scripts\activate
    ```

    On macOS and Linux:
    ```bash
    source venv/bin/activate
    ```
    You will know the virtual environment is active when you see `(venv)` at the beginning of your terminal prompt.

4.  **Install the required packages:**
    Install all the project dependencies using the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

5.  **Create a `.env` file:**
    This project uses a `.env` file to manage environment variables. Create a file named `.env` in the `taashi_backend` directory and add the following content. Make sure to replace the placeholder with your actual MongoDB connection string.

    ```
    MONGODB_URL="your_mongodb_connection_string"
    DATABASE_NAME="your_database_name"
    ```

6.  **Run the application:**
    Now you can start the FastAPI server using `uvicorn`. The `--reload` flag will automatically restart the server when you make changes to the code.
    ```bash
    uvicorn main:app --reload
    ```

7.  **Access the API:**
    Once the server is running, you can access the API documentation in your browser at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

    The main endpoint will be available at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).
