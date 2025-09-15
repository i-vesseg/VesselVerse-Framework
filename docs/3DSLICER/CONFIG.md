# Using a Shared Configuration File

This README explains how to use a shared configuration file (`config.sh`) across Bash scripts, Python scripts, and Jupyter Notebooks. By centralizing your configuration, you ensure consistency and flexibility while minimizing code duplication.
You can find a `toy_config.sh` to start with.

---

## 1. Setting Up the Configuration File

Create a file named `config.sh` with the following format:

```bash
# config.sh

SLICER_PATH="/path/to/Slicer"
```

- Use the `KEY=VALUE` format for variables.
- Enclose paths in quotes if they contain spaces.

---

## 2. Using the Configuration File in a Bash Script

### Example Script:
```bash
#!/bin/bash

CONFIG_FILE="$(dirname "$0")/config.sh"

if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "Configuration file $CONFIG_FILE not found!"
    exit 1
fi

echo "Slicer Path: $SLICER_PATH"
```

### How It Works:
- The `source` command loads the variables from `config.sh`.
- The script prints the paths to confirm they are loaded.

### Notes:
- Ensure `config.sh` has the correct permissions: `chmod 600 config.sh`.

---

## 3. Using the Configuration File in a Python Script

### Example Script:
```python
import os

def load_config(file_path):
    """Load configuration variables from a shell-style config file."""
    config = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip('"')
    return config

# Path to the config file
config_file = os.path.join(os.path.dirname(__file__), "config.sh")

if os.path.exists(config_file):
    config = load_config(config_file)
    SLICER_PATH = config.get("SLICER_PATH")
    MODULE_PATH = config.get("MODULE_PATH")
    print(f"Slicer Path: {SLICER_PATH}")
    print(f"Module Path: {MODULE_PATH}")
else:
    print(f"Configuration file {config_file} not found!")
```

### How It Works:
- The `load_config` function parses the `config.sh` file.
- Variables are extracted and used in the script.

### Notes:
- Ensure the paths in `config.sh` are accessible from the script’s location.

---

## 4. Using the Configuration File in a Jupyter Notebook

### Parsing the File in the Notebook
Add the following function to your notebook:

```python
def load_config(file_path):
    """Load configuration variables from a shell-style config file."""
    config = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip('"')
    return config

# Path to the config file
import os
config_file = os.path.join(os.getcwd(), "config.sh")

if os.path.exists(config_file):
    config = load_config(config_file)
    SLICER_PATH = config.get("SLICER_PATH")
    print(f"Slicer Path: {SLICER_PATH}")
else:
    print(f"Configuration file {config_file} not found!")
```

### Automating Loading with an Extension
Save the following as `load_config.py`:

```python
def load_ipython_extension(ipython):
    import os

    def load_config(file_path):
        config = {}
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip().strip('"')
        return config

    config_file = os.path.join(os.getcwd(), "config.sh")
    if os.path.exists(config_file):
        config = load_config(config_file)
        for key, value in config.items():
            ipython.user_ns[key] = value  # Add variables to the notebook's namespace
        print("Configuration loaded successfully.")
    else:
        print(f"Configuration file {config_file} not found!")
```

In your notebook, load the extension:

```python
%load_ext load_config
```

### Notes:
- The extension automatically makes the variables available in the notebook’s namespace.

---

## 5. Summary
- **Bash**: Use `source` to load the configuration file.
- **Python**: Parse the file using a custom `load_config` function.
- **Jupyter Notebooks**: Parse the file manually or use a custom extension for automatic loading.

Using this shared configuration file ensures consistency and ease of maintenance across different tools.

