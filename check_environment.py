import sys
import os
import importlib
import json

def check_module(module_name):
    """Try to import a module and return result"""
    try:
        module = importlib.import_module(module_name)
        return {"status": "ok", "location": module.__file__ if hasattr(module, "__file__") else "built-in"}
    except ImportError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

def check_file_exists(path):
    """Check if a file exists"""
    exists = os.path.isfile(path)
    return {"exists": exists, "path": path, "abs_path": os.path.abspath(path) if exists else None}

def main():
    """Check environment and report"""
    results = {
        "python_version": sys.version,
        "python_path": sys.executable,
        "sys_path": sys.path,
        "cwd": os.getcwd(),
        "modules": {
            "playwright": check_module("playwright"),
            "playwright.async_api": check_module("playwright.async_api"),
            "loguru": check_module("loguru"),
            "sqlalchemy": check_module("sqlalchemy"),
            "database": check_module("database"),
            "database.database": check_module("database.database"),
            "database.models": check_module("database.models"),
            "backend.database": check_module("backend.database"),
            "backend.database.database": check_module("backend.database.database"),
            "services": check_module("services"),
            "services.leadhoop_service": check_module("services.leadhoop_service"),
            "backend.services": check_module("backend.services"),
            "backend.services.leadhoop_service": check_module("backend.services.leadhoop_service")
        },
        "files": {
            "backend/agents/data_entry_agent.py": check_file_exists("backend/agents/data_entry_agent.py"),
            "backend/agents/voice_agent.py": check_file_exists("backend/agents/voice_agent.py"),
            "backend/database/database.py": check_file_exists("backend/database/database.py"),
            "backend/database/models.py": check_file_exists("backend/database/models.py"),
            "backend/services/leadhoop_service.py": check_file_exists("backend/services/leadhoop_service.py"),
            "backend/main.py": check_file_exists("backend/main.py")
        }
    }
    
    # Add test for __init__.py files
    init_files = {}
    for dir_path in ["backend", "backend/agents", "backend/database", "backend/services"]:
        init_path = os.path.join(dir_path, "__init__.py")
        init_files[init_path] = check_file_exists(init_path)
    results["init_files"] = init_files
    
    # Print results nicely formatted
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main() 