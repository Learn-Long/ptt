import subprocess

scripts = [
    "scraper.py",
    "article_scraper.py",
    "data_extractor.py",
    "ip_aggregator.py",
    "ip_cross_checker.py",
]

for script in scripts:
    print(f"Running {script}...")
    try:
        subprocess.run(["python", script], check=True)
        print(f"{script} completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script}: {e}")
        break  # Stop if a script fails
