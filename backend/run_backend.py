import subprocess
import os
import sys
import time
import argparse
import shutil
import threading

def run_command(command, cwd=None):
    """Run a shell command and print its output."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        cwd=cwd
    )
    
    for line in iter(process.stdout.readline, b''):
        print(line.decode('utf-8'), end='')
    
    process.stdout.close()
    return process.wait()

def find_executable(executable_name):
    """Find the path to an executable in PATH or Scripts directory."""
    # First try direct command
    if shutil.which(executable_name):
        return executable_name
        
    # Look in Python Scripts directory
    python_path = sys.executable
    scripts_dir = os.path.join(os.path.dirname(python_path), 'Scripts')
    executable_path = os.path.join(scripts_dir, executable_name)
    
    if os.path.exists(executable_path):
        return executable_path
        
    # For Windows, check with .exe extension
    if os.name == 'nt' and not executable_name.endswith('.exe'):
        executable_path = os.path.join(scripts_dir, f"{executable_name}.exe")
        if os.path.exists(executable_path):
            return executable_path
    
    # If still not found, use python -m as a fallback for Python modules like uvicorn
    if executable_name in ['uvicorn', 'gunicorn']:
        print(f"Using 'python -m {executable_name}' as fallback")
        return f"{sys.executable} -m {executable_name}"
    
    # If still not found, check in current directory
    executable_path = os.path.join(os.getcwd(), executable_name)
    if os.path.exists(executable_path):
        return executable_path
        
    return None

def monitor_process_output(name, process):
    """Monitor and print output from a subprocess"""
    for line in iter(process.stdout.readline, ''):
        print(f"[{name}] {line}", end='')

def main():
    parser = argparse.ArgumentParser(description='Start the Smart News Aggregator backend')
    parser.add_argument('--no-consumer', action='store_true', help='Do not start the RabbitMQ consumer')
    parser.add_argument('--no-api', action='store_true', help='Do not start the API server')
    parser.add_argument('--init-db', action='store_true', help='Initialize database before starting')
    
    args = parser.parse_args()
    
    # Get the directory of this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Initialize database if requested
    if args.init_db:
        print("Initializing database...")
        exit_code = run_command("python init_db.py", cwd=base_dir)
        if exit_code != 0:
            print("Error initializing database. Please check if PostgreSQL is running.")
            return
    
    processes = []
    output_threads = []
    
    # Start RabbitMQ consumer (if not disabled)
    if not args.no_consumer:
        print("Starting RabbitMQ consumer in background...")
        consumer_process = subprocess.Popen(
            [sys.executable, "run_consumer.py", "--daemon"],
            cwd=base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(("RabbitMQ Consumer", consumer_process))
        
        # Create a thread to monitor and print consumer output
        consumer_thread = threading.Thread(
            target=monitor_process_output,
            args=("RabbitMQ Consumer", consumer_process),
            daemon=True
        )
        consumer_thread.start()
        output_threads.append(consumer_thread)
    
    # Start FastAPI server (if not disabled)
    if not args.no_api:
        print("Starting FastAPI server...")
        
        # Find uvicorn executable
        uvicorn_path = find_executable("uvicorn")
        
        if not uvicorn_path:
            print("Error: uvicorn command not found. Make sure uvicorn is installed (pip install uvicorn).")
            # Try to continue with other components
        else:
            try:
                # Handle uvicorn differently if it's a fallback command
                if uvicorn_path.startswith(sys.executable):
                    # It's a fallback command like "python -m uvicorn"
                    # We need to set PYTHONPATH to include the parent directory
                    env = os.environ.copy()
                    env["PYTHONPATH"] = os.path.dirname(base_dir)
                    
                    api_process = subprocess.Popen(
                        f"{sys.executable} -m uvicorn app.main:app --host 0.0.0.0 --port 8000",
                        cwd=base_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        bufsize=1,
                        universal_newlines=True,
                        env=env
                    )
                else:
                    # It's a direct executable
                    env = os.environ.copy()
                    env["PYTHONPATH"] = os.path.dirname(base_dir)
                    
                    api_process = subprocess.Popen(
                        [uvicorn_path, "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
                        cwd=base_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        bufsize=1,
                        universal_newlines=True,
                        env=env
                    )
                processes.append(("FastAPI Server", api_process))
                
                # Create a thread to monitor and print API server output
                api_thread = threading.Thread(
                    target=monitor_process_output,
                    args=("FastAPI Server", api_process),
                    daemon=True
                )
                api_thread.start()
                output_threads.append(api_thread)
            except Exception as e:
                print(f"Error starting FastAPI server: {e}")
                # Continue with other components
    
    # Print info about running services
    if processes:
        print("\nServices started successfully!")
        for name, proc in processes:
            print(f"  - {name} (PID: {proc.pid})")
        print("\nPress Ctrl+C to stop all services...\n")
    else:
        print("No services were started. Use --help to see available options.")
        return
    
    # Wait for Ctrl+C
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping services...")
        for name, proc in processes:
            print(f"Stopping {name}...")
            proc.terminate()
        
        # Wait for processes to terminate
        for name, proc in processes:
            try:
                proc.wait(timeout=5)
                print(f"{name} stopped.")
            except subprocess.TimeoutExpired:
                print(f"{name} did not terminate, killing...")
                proc.kill()
        
        print("All services stopped.")

if __name__ == "__main__":
    main()