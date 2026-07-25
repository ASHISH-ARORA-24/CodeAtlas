# Python AST Crawler for CodeAtlas.
# This crawler reads a Python source file and uses Python's built-in ast module
# to extract structured information: function names, parameters, return types,
# docstrings, and classes. This structured data is what we will later store
# in Neo4j and use to create smart text chunks for embeddings in ChromaDB.

import ast


def read_file(file_path: str) -> str:
    """
    Reads a Python source file and returns its content as a string.

    Kept separate from parsing so each function has one purpose —
    reading is one job, parsing is another.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_docstring(node: ast.FunctionDef | ast.ClassDef) -> str:
    """
    Extracts the docstring from a function or class node if one exists.

    In an AST, a docstring is the first statement in a function or class body
    and it is a string constant. Returns empty string if no docstring exists
    so callers never have to handle None.
    """
    docstring = ast.get_docstring(node)
    return docstring if docstring else ""


def extract_parameters(node: ast.FunctionDef) -> list[dict]:
    """
    Extracts all parameters from a function node, including their type hints.

    Skips 'self' because it is not a real parameter — it is just Python's way
    of referring to the class instance inside a method.

    Returns a list of dicts, one per parameter, with keys:
    - name: the parameter name
    - type: the type annotation as a string, or "unknown" if not declared
    """
    parameters = []

    for arg in node.args.args:
        # skip self — it is a class reference, not a meaningful parameter
        if arg.arg == "self":
            continue

        # ast.unparse converts the annotation node back to a readable string
        # e.g. the annotation node for "float" becomes the string "float"
        param_type = ast.unparse(arg.annotation) if arg.annotation else "unknown"
        parameters.append({
            "name": arg.arg,
            "type": param_type,
        })

    return parameters


def extract_return_type(node: ast.FunctionDef) -> str:
    """
    Extracts the return type annotation from a function node.

    Returns the type as a string (e.g. "float", "list[str]"), or
    "unknown" if no return type is declared. This matters for the
    Neo4j graph — knowing what a function returns helps trace data flow.
    """
    if node.returns:
        return ast.unparse(node.returns)
    return "unknown"


def extract_function_info(node: ast.FunctionDef) -> dict:
    """
    Extracts all meaningful information from a single function or method node.

    Returns a dict with name, docstring, parameters, return type, and line number.
    Centralising this here avoids duplicating the same logic in both
    extract_functions and extract_methods.
    """
    return {
        "name": node.name,
        "docstring": extract_docstring(node),
        "parameters": extract_parameters(node),
        "return_type": extract_return_type(node),
        "line_number": node.lineno,
    }


def extract_functions(tree: ast.Module) -> list[dict]:
    """
    Extracts only the top-level functions from a parsed AST module.

    Iterates tree.body (direct children of the file) rather than using
    ast.walk — this ensures we only get standalone functions, not methods
    that belong to a class. Class methods are handled by extract_methods.
    """
    functions = []

    # tree.body contains only the direct top-level statements in the file
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(extract_function_info(node))

    return functions


def extract_methods(class_node: ast.ClassDef) -> list[dict]:
    """
    Extracts all methods from a single class node.

    Iterates class_node.body (direct children of the class) so we only
    get methods that truly belong to this class, not nested functions
    inside those methods.
    """
    methods = []

    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            methods.append(extract_function_info(node))

    return methods


def extract_classes(tree: ast.Module) -> list[dict]:
    """
    Extracts all classes from a parsed AST module, including their methods.

    For each class, returns a dict with:
    - name: class name
    - docstring: the class-level docstring
    - line_number: where the class starts in the file
    - methods: list of method dicts extracted by extract_methods

    This is the foundation of the Neo4j graph edge: Class → Method.
    """
    classes = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "docstring": extract_docstring(node),
                "line_number": node.lineno,
                "methods": extract_methods(node),
            })

    return classes


def print_crawler_output(file_path: str, functions: list[dict], classes: list[dict]) -> None:
    """
    Prints the extracted data in a readable format.

    Shows top-level functions first, then classes with their methods.
    This is only used for exploration and debugging — in the real
    CodeAtlas pipeline this data will be sent to Neo4j and ChromaDB.
    """
    print(f"\n{'='*60}")
    print(f"File     : {file_path}")
    print(f"Functions: {len(functions)}  |  Classes: {len(classes)}")
    print(f"{'='*60}")

    if functions:
        print("\n--- Top-Level Functions ---")
        for func in functions:
            print(f"\nFunction : {func['name']} (line {func['line_number']})")
            print(f"Docstring: {func['docstring']}")
            print(f"Returns  : {func['return_type']}")
            print(f"Params   :")
            for param in func["parameters"]:
                print(f"           {param['name']} -> {param['type']}")

    if classes:
        print("\n--- Classes ---")
        for cls in classes:
            print(f"\nClass    : {cls['name']} (line {cls['line_number']})")
            print(f"Docstring: {cls['docstring']}")
            print(f"Methods  : {len(cls['methods'])}")
            for method in cls["methods"]:
                print(f"\n  Method : {method['name']} (line {method['line_number']})")
                print(f"  Docs   : {method['docstring']}")
                print(f"  Returns: {method['return_type']}")
                print(f"  Params :")
                for param in method["parameters"]:
                    print(f"             {param['name']} -> {param['type']}")


if __name__ == "__main__":
    import sys

    # sys.argv is a list of command line arguments.
    # sys.argv[0] is always the script name itself.
    # sys.argv[1] is the first argument the user passes — our file path.
    if len(sys.argv) < 2:
        print("Usage: uv run crawlers/python_ast.py <file_path>")
        sys.exit(1)

    FILE_PATH = sys.argv[1]

    source_code = read_file(FILE_PATH)

    # Parse once, pass the tree to both extractors
    tree = ast.parse(source_code)

    functions = extract_functions(tree)
    classes = extract_classes(tree)

    print_crawler_output(FILE_PATH, functions, classes)
