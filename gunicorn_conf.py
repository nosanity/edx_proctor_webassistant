from multiprocessing import cpu_count
import os

#bind = ":8138"
workers = cpu_count() * 2 + 1
preload = True
max_requests = 100
max_requests_jitter = int(max_requests / 2)
