import threading
import time
import random
import argparse

def background_task(name, max_steps):
    print(f"Task {name} started.")
    steps = random.randint(1, max_steps)  # Each task will have a random number of steps up to the user-provided max
    for i in range(steps):
        time.sleep(random.uniform(2.5, 5.5))  # Variable delay per step
        log_type = random.choice(["INFO", "DEBUG", "WARNING", "ERROR"])  # Random log level

        # Generate random log messages
        if log_type == "INFO":
            print(f"[INFO] Task {name}: Step {i + 1}/{steps} completed.")
        elif log_type == "DEBUG":
            print(f"[DEBUG] Task {name}: Processed data chunk {random.randint(1, 100)}.")
        elif log_type == "WARNING":
            print(f"[WARNING] Task {name}: Resource usage high at step {i + 1}.")
        elif log_type == "ERROR":
            print(f"[ERROR] Task {name}: Encountered an issue, retrying step {i + 1}.")

    print(f"Task {name} completed after {steps} steps.")

def main(num_threads, max_steps):
    # Create and start threads
    threads = []
    for i in range(num_threads):
        thread_name = f"Task-{i + 1}"
        thread = threading.Thread(target=background_task, args=(thread_name, max_steps))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    # Command-line arguments
    parser = argparse.ArgumentParser(description="Run multiple background tasks with randomized logs.")
    parser.add_argument("num_threads", type=int, help="Number of threads to run")
    parser.add_argument("max_steps", type=int, help="Maximum number of steps each thread can have")
    args = parser.parse_args()

    main(args.num_threads, args.max_steps)
