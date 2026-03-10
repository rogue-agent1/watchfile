# watchfile

Watch files for changes and run a command. Like `entr` but zero deps.

One file. Zero deps. Reacts to changes.

## Usage

```bash
# Watch Python files, run tests on change
python3 watchfile.py "*.py" -- pytest

# Watch a directory
python3 watchfile.py src/ -- make build

# Watch specific files
python3 watchfile.py main.py config.py -- python main.py

# Pipe file list
find . -name "*.rs" | python3 watchfile.py -- cargo build
```

## Features

- Glob patterns, directories, or explicit files
- Auto-discovers new files matching patterns
- Runs command once on start, then on every change
- Stdin file list support (like `entr`)

## Requirements

Python 3.8+. No dependencies.

## License

MIT
