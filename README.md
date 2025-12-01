🛠️ Attentive Intranet – API

Backend oficial da Intranet Attentive Contabilidade, responsável por autenticação, gerenciamento de usuários, comunicados, colaboradores, departamentos, cursos, logs e integrações internas.

Construído com FastAPI + MongoDB (Motor) e projetado para rodar tanto localmente quanto em containers Docker.

Frontend relacionado:
➡️ attentive-intranet-frontend

🚀 Tecnologias

FastAPI (Python)

Uvicorn

MongoDB / Motor (async)

Pydantic v2

python-jose (JWT)

Passlib/Bcrypt (hash de senha)

Docker / Docker Compose

CORS + Middlewares personalizados

Cloud/AWS-ready

📦 Pré-requisitos

Para rodar localmente:

Python 3.10+

MongoDB local ou MongoDB Atlas

pip ou uv

(Opcional) Docker + Docker Compose

🔧 Variáveis de ambiente

Crie um arquivo .env na raiz do projeto com:

# Porta
PORT=8000

# Segurança
SECRET_KEY=algum_token_seguro
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 dias

# Banco MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=Attentive

# Banco para logs (opcional)
MONGODB_LOGS_URL=mongodb://localhost:27017
MONGODB_LOGS_DB=Attentive_logs


Em produção (EC2 / Docker / Atlas), substitua pelos valores corretos.

▶️ Rodando localmente (modo simples)

Criar ambiente virtual:

python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows


Instalar dependências:

pip install -r requirements.txt


Iniciar servidor:

uvicorn app.main:app --reload


A API ficará disponível em:

http://127.0.0.1:8000


Documentação interativa:

http://127.0.0.1:8000/docs

🐳 Rodando com Docker (recomendado)
docker build -t attentive-api .
docker run -p 8000:8000 --env-file .env attentive-api


Ou usando docker-compose.yml:

docker compose up -d

🏗️ Estrutura do projeto
app/
├── main.py                    # Inicialização da API
├── config.py                  # Configurações e variáveis de ambiente
├── database.py                # Conexão com MongoDB (Motor)
├── models/                    # Modelos Pydantic
├── schemas/                   # Schemas de validação
├── routes/
│   ├── auth.py                # Login, refresh, me, logout
│   ├── usuarios.py            # CRUD de usuários
│   ├── colaboradores.py       # Dados dos colaboradores
│   ├── comunicados.py         # Posts e notificações
│   ├── departamentos.py       # Departamentos + ferramentas
│   ├── cursos.py              # Cursos internos + progresso
│   ├── empresas.py            # Empresas (para automações)
│   ├── escrituracao.py        # Escrituração (Tax)
│   ├── logs.py                # Logs recentes (dashboard)
│   └── ... outros módulos
├── services/                  # Funções auxiliares, JWT, segurança
└── utils/                     # Funções utilitárias

🔐 Autenticação e segurança

A API utiliza:

JWT (Bearer Token)

Hash de senhas com Bcrypt

Refresh implícito por /auth/me

Middleware de CORS

Proteção padrão FastAPI

Endpoints de autenticação:

POST /auth/login  
GET  /auth/me  
POST /auth/logout  

🧩 Principais módulos da API
✔ Usuários

Criar, editar, listar e remover usuários.
Upload de avatar.
Descrição privada e bio pública.
Associação a departamentos e cargos.

✔ Comunicados / Notificações

CRUD completo + imagens
Marcar como lido
Expansão dos dados (autor, fotos, categorias)

✔ Colaboradores

Listar por departamento
Obter perfil
Dados públicos e privados

✔ Departamentos

Cadastrar departamentos
Atribuir ferramentas / items
Usado pelo frontend para montar páginas dinâmicas

✔ Cursos internos

CRUD de cursos
Acompanhar progresso por colaborador
Rota /cursos/me para ver tudo por usuário

✔ Logs

Listar logs recentes (dashboard)
Integração com automações Attentive (via LogClientHTTP)

📚 Rotas principais

Após rodar a API, acesse /docs para ver a versão interativa.
Principais prefixos:

/auth
/usuarios
/colaboradores
/comunicados
/notificacoes
/departamentos
/cursos
/empresas
/escrituracao
/logs

🧪 Testes (em breve)

Planejado:

Testes unitários (pytest)

Testes de integração (httpx)

Testes de carga / performance

🛠️ Deploy

A API foi projetada para rodar em:

EC2 + Docker

ECS / Fargate

Render / Railway

Cloud Run

Local + Nginx como proxy

Deployment padrão usado no projeto Attentive:

EC2 (Ubuntu)  
→ Docker Compose  
→ Containers: API + Nginx + Frontend  
→ MongoDB Atlas

📑 Scripts úteis

Rodar servidor:

uvicorn app.main:app --reload


Exportar dependências:

pip freeze > requirements.txt


Rodar com reload + logs:

uvicorn app.main:app --reload --log-level debug

📝 Licença

Projeto interno da Attentive Contabilidade.
Uso restrito a colaboradores autorizados.
