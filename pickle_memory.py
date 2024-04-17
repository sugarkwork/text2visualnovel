import os
import pickle
import time
import hashlib
import threading

lock = threading.Lock()

def save_memory(key, val):
    while True:
        try:
            pickle_file = 'memory.pkl'
            with lock:
                if os.path.exists(pickle_file):
                    with open(pickle_file, 'rb') as f:
                        memory = pickle.load(f)
                else:
                    memory = {}
                memory[hashlib.sha512(key.encode()).hexdigest()] = val
                with open(pickle_file, 'wb') as f:
                    pickle.dump(memory, f)
            break
        except Exception as e:
            print(f"Error saving memory: {e}")
            time.sleep(1)
            continue

def load_memory(key, defval=None):
    while True:
        try:
            pickle_file = 'memory.pkl'
            with lock:
                if os.path.exists(pickle_file):
                    with open(pickle_file, 'rb') as f:
                        memory = pickle.load(f)
                else:
                    memory = {}
            return memory.get(hashlib.sha512(key.encode()).hexdigest(), defval)
        except Exception as e:
            print(f"Error loading memory: {e}")
            time.sleep(1)
            continue