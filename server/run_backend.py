import os
import sys
import uvicorn

def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(project_root)

    # Make sure imports like "tools.vector_index" work
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    uvicorn.run("server.app:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()