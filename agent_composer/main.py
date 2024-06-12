import subprocess
import os
import requests
import sys
import importlib
import ast
import inspect
import typing
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv, find_dotenv
from models.session_config import SessionConfig


def download_file_from_github(url, save_path):
    response = requests.get(url)
    response.raise_for_status()  # Check if the request was successful

    with open(save_path, 'wb') as file:
        file.write(response.content)


def get_function_names(file_path):
    with open(file_path, 'r') as file:
        file_content = file.read()

    # Parse the file content
    tree = ast.parse(file_content, filename=file_path)

    # Extract function names
    function_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

    return function_names


def get_imports(file_path):
    with open(file_path, 'r') as file:
        file_content = file.read()

    # Parse the file content
    tree = ast.parse(file_content, filename=file_path)

    # Extract import statements
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]

    imported_modules = []
    for node in imports:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.append(node.module)

    return imported_modules


def install_dependencies(modules):
    for module in modules:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", module],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"Successfully installed {module}:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {module}:\n{e.stderr}")


def import_function(module_name, function_name):
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    return function


def get_function_signature_and_types(function):
    signature = inspect.signature(function)
    type_hints = typing.get_type_hints(function)
    return signature, type_hints


def create_pydantic_instance(model_class):
    # For demonstration, create an instance with some sample data
    # In practice, you might want to populate this with actual data
    sample_data = {}
    for field_name, field_type in model_class.__annotations__.items():
        if field_type == int:
            sample_data[field_name] = 0
        elif field_type == str:
            sample_data[field_name] = ""
        elif field_type == float:
            sample_data[field_name] = 0.0
        elif field_type == bool:
            sample_data[field_name] = False
        elif issubclass(field_type, BaseModel):
            sample_data[field_name] = create_pydantic_instance(field_type)
        else:
            sample_data[field_name] = None
    return model_class(**sample_data)


def main():
    # Load the .env file
    path = find_dotenv()
    print(path)
    load_dotenv(override=True, verbose=True)

    # URL of the file to download from GitHub
    file_url = 'https://raw.githubusercontent.com/BenderScript/agent_composer/main/resources/remote_agents/chatbot.py'
    # Path where the downloaded file will be saved
    save_path = 'resources/local_agents/chatbot.py'

    # Step 1: Download the file from GitHub
    download_file_from_github(file_url, save_path)

    # Step 2: Add the path to the cloned repository to PYTHONPATH
    repo_path = os.path.dirname(save_path)
    sys.path.append(repo_path)

    # Step 3: Parse the file to get import statements
    imported_modules = get_imports(save_path)
    print(f"Imported modules: {imported_modules}")

    # Step 4: Install dependencies
    install_dependencies(imported_modules)

    # Step 5: Parse the file to get function names
    function_names = get_function_names(save_path)
    print(f"Functions in {save_path}: {function_names}")

    # Step 6: Dynamically import and use the function
    desired_function_name = 'chatbot'
    if desired_function_name in function_names:
        module_name = os.path.basename(save_path).replace('.py',
                                                          '')

        # Dynamically import the function
        process_data = import_function(module_name, desired_function_name)

        # Get function signature and type hints
        signature, type_hints = get_function_signature_and_types(process_data)
        print(f"Signature of {desired_function_name}: {signature}")
        print(f"Type hints of {desired_function_name}: {type_hints}")

        # Identify Pydantic types and create instances
        for param_name, param_type in type_hints.items():
            if isinstance(param_type, type) and issubclass(param_type, BaseModel):
                print(f"{param_name} is of Pydantic type {param_type}")
                # Create an instance of the Pydantic model
                try:
                    input_data = create_pydantic_instance(param_type)
                    print(f"Created instance for {param_name}: {input_data}")
                except ValidationError as e:
                    print(f"Validation error: {e}")

                # Call the function with the created instance
                result = process_data(input_data)
                print(f"Result: {result}")
            else:
                print(f"{param_name} is of type {param_type}, which is not a Pydantic model.")
    else:
        print(f"Function '{desired_function_name}' not found in the module.")


if __name__ == "__main__":
    main()
