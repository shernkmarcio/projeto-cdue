# TaskManager — Flask + Python

Gerenciador de tarefas completo com autenticação, CRUD, categorias, prioridades e datas.

## Estrutura

```
taskmanager/
├── app.py                  # Aplicação Flask principal
├── requirements.txt        # Dependências
├── tasks.db                # Banco SQLite (gerado automaticamente)
├── templates/
│   ├── base.html           # Layout base
│   ├── auth.html           # Login e cadastro
│   ├── dashboard.html      # Lista de tarefas + filtros
│   └── edit_task.html      # Edição de tarefa
└── static/
    ├── css/style.css       # Estilos
    └── js/main.js          # Scripts
```

## Como rodar

```bash
# 1. Criar ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar
python app.py
```

Acesse: http://localhost:5000

## Funcionalidades

- Autenticação: cadastro, login e logout com senha hasheada (werkzeug)
- CRUD completo de tarefas por usuário
- Categorias: Trabalho, Pessoal, Estudos, Saúde, Outros
- Prioridades: Alta, Média, Baixa (ordenadas automaticamente)
- Data de conclusão com alerta visual de "Atrasada"
- Filtros: busca por texto, categoria, prioridade e status
- Dashboard com contadores: Total, Pendentes, Concluídas, Atrasadas
- Banco de dados SQLite (sem configuração extra)

## Tecnologias

- **Backend**: Python 3 + Flask
- **Banco de dados**: SQLite via módulo sqlite3 nativo
- **Autenticação**: werkzeug.security (hash bcrypt)
- **Frontend**: HTML/CSS/JS puro (sem frameworks)
