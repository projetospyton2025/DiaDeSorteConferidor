# Create project directory structure
$projectPath = "J:\Meu DrIve\ProjetosPython\LoterIas\Conferidores\diadesortecoferirdor"

# Create main directories
$directories = @(
    "",
    ".git",
    "venv",
    "__pycache__",
    ".vscode",
    "Requisitos",
    "templates",
    "static",
    "static/css",
    "static/js"
)

foreach ($dir in $directories) {
    $path = Join-Path $projectPath $dir
    if (!(Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force
    }
}

# Create required files with initial content
$files = @{
    ".env" = @"
REDIS_HOST=redis-13833.c336.samerica-east1-1.gce.redns.redis-cloud.com
REDIS_PORT=13833
REDIS_PASSWORD=B058xThhTvAbptQa0s25EAGk7A5u473O
REDIS_DB=0
FLASK_ENV=development
REDIS_URL=redis://localhost:6379/0
"@

    ".gitignore" = @"
# Ambientes virtuais
venv/
.env/

# Arquivos de cache do Python
__pycache__/
*.pyc
*.pyo

# Configurações específicas de IDEs/editores
.vscode/
.idea/

# Arquivos de log
*.log

# Arquivos de banco de dados locais
*.sqlite3

# Outras configurações específicas do projeto
"@

    "requirements.txt" = @"
aiohappyeyeballs
aiohttp --only-binary=:all:
aiosignal
annotated-types
anyio
arrow
asttokens
async-lru
asyncio
attrs
Babel
bleach
blinker
build
certifi
charset-normalizer
click
colorama
comm
decorator
defusedxml
executing
fastapi
fastjsonschema
flask[async]
Flask-Login
Flask-Mail
flask
fqdn
frozenlist
httpcore
httpx
idna
ipykernel
ipython
isoduration
itsdangerous
jedi
jsonpointer
jsonschema
jsonschema-specifications
jupyter-events
jupyter-lsp
jupyter_client
jupyter_core
jupyter_server
jupyter_server_terminals
jupyterlab
jupyterlab_pygments
jupyterlab_server
MarkupSafe
matplotlib-inline
mistune
mpmath
multidict
nbclient
nbconvert
nbformat
nest-asyncio
notebook
notebook_shim
numpy
overrides
packaging
pandas
pandocfilters
parso
pip-tools
platformdirs
prometheus_client
prompt_toolkit
propcache
psutil
pure-eval
pycparser
pydantic
pydantic_core
Pygments
pyproject_hooks
python-dotenv
python-json-logger
python-multipart
pytz
redis
"@
}

foreach ($file in $files.Keys) {
    $path = Join-Path $projectPath $file
    $files[$file] | Out-File -FilePath $path -Encoding UTF8 -Force
}

# Create virtual environment
Push-Location $projectPath
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate

# Install requirements
pip install -r requirements.txt

# Start the application
python app.py

Write-Host "Project setup complete! The application is now running."