# English Typing App (Python + Flet)

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Build Windows EXE

```powershell
pip install pyinstaller
pyinstaller --noconfirm --onefile --name english-typing-app main.py
```
