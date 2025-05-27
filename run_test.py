import subprocess
import os

# Change to the project directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Run the tests
print("Running admin UI tests...")
result = subprocess.run(["python", "-m", "pytest", "tests/ui/test_admin.py", "-v"], 
                       capture_output=True, text=True)

# Print the output
print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)

print(f"Exit code: {result.returncode}")
